# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict
import json
import re
import uuid
from functools import partial

from lxml import etree
from dateutil.relativedelta import relativedelta
from werkzeug.urls import url_encode

from odoo import api, exceptions, fields, models, _
from odoo.tools import email_re, email_split, email_escape_char, float_is_zero, float_compare, \
    pycompat, date_utils
from odoo.tools.misc import formatLang

from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning

from odoo.addons import decimal_precision as dp
import logging



class AccountInvoice(models.Model):

    _inherit = "account.invoice"

    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'tax_line_ids.amount_rounding',
                 'currency_id', 'company_id', 'date_invoice', 'type', 'round_off')
    def _compute_amount(self):
        # round_curr = self.currency_id.round
        self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line_ids)
        print ("amount untaxed", self.amount_untaxed)
        self.amount_tax = sum((line.amount_total) for line in self.tax_line_ids)
        print("amount_tax", self.amount_tax)
        self.amount_total = self.amount_untaxed + self.amount_tax
        print ("amount total", self.amount_total)
        # self.amount_total = round(self.amount_total)
        # print ("tttttttttttttttttt",self.amount_total)
        amount_total_company_signed = self.amount_total
        amount_untaxed_signed = self.amount_untaxed
        if self.currency_id and self.company_id and self.currency_id != self.company_id.currency_id:
            currency_id = self.currency_id
            amount_total_company_signed = currency_id._convert(self.amount_total, self.company_id.currency_id, self.company_id, self.date_invoice or fields.Date.today())
            amount_untaxed_signed = currency_id._convert(self.amount_untaxed, self.company_id.currency_id, self.company_id, self.date_invoice or fields.Date.today())
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        self.amount_total_company_signed = amount_total_company_signed * sign
        self.amount_total_signed = round(self.amount_total) * sign
        self.amount_untaxed_signed = amount_untaxed_signed * sign

        if self.amount_untaxed:
            insurance_per = 0.0
            for line in self.invoice_line_ids:
                insurance_per += line.line_insurance_amount
                print("lllllllll",insurance_per)
            total = self.amount_total + insurance_per
            print("totaaaaaaaal", total)
            actual_total = total
            total = round(total)
            print("rounddddddddddddd",total)
            round_value = actual_total - total
            # self.amount_total = total
            if round_value <= 0.50:
                round_value = -(round_value)
            else:
                round_value = round_value
            self.update({
                'insurance_amount':insurance_per,
                'amount_total': total,
                'round_off':round_value})

    insurance_amount = fields.Float(string='Insurance 0.04%', compute='_compute_amount')
    round_off = fields.Float(string='Round Off',compute='_compute_amount')

    @api.multi
    def invoice_line_move_line_get(self):
        res = super(AccountInvoice, self).invoice_line_move_line_get()
        for rec in self:
            if rec.insurance_amount and not rec.company_id.insurance_account:
                raise ValidationError('Please configuration insurance account')
            if rec.round_off and not rec.company_id.round_of_account:
                raise ValidationError('Please configuration round off account')
            if rec.type in ('out_invoice','out_refund'):
                if rec.insurance_amount:
                    rcm_line_dict1 = {
                        'name':'Insurance 0.04%',
                        'price_unit': - rec.insurance_amount or 0,
                        'quantity': 1,
                        'price': rec.insurance_amount or 0,
                        'account_id': rec.company_id.insurance_account.id,
                        'invoice_id': rec.id,
                    }
                    res.append(rcm_line_dict1)
                if rec.round_off:
                    rcm_line_dict2 = {
                        'name':'Round Off',
                        'price_unit': - rec.round_off or 0,
                        'quantity': 1,
                        'price': rec.round_off or 0,
                        'account_id': rec.company_id.round_of_account.id,
                        'invoice_id': rec.id,
                    }
                    res.append(rcm_line_dict2)
            return res

    @api.model
    def _default_currency(self):
        journal = self._default_journal()
        return journal.currency_id or journal.company_id.currency_id or self.env.user.company_id.currency_id

    def _get_aml_for_amount_residual(self):
        """ Get the aml to consider to compute the amount residual of invoices """
        self.ensure_one()
        return self.sudo().move_id.line_ids.filtered(lambda l: l.account_id == self.account_id)

    @api.one
    @api.depends(
        'state', 'currency_id', 'invoice_line_ids.price_subtotal',
        'move_id.line_ids.amount_residual',
        'move_id.line_ids.currency_id')
    def _compute_residual(self):
        residual = 0.0
        residual_company_signed = 0.0
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        for line in self._get_aml_for_amount_residual():
            residual_company_signed += line.amount_residual
            if line.currency_id == self.currency_id:
                residual += line.amount_residual_currency if line.currency_id else line.amount_residual
            else:
                from_currency = line.currency_id or line.company_id.currency_id
                residual += from_currency._convert(line.amount_residual, self.currency_id, line.company_id,
                                                   line.date or fields.Date.today())
        self.residual_company_signed = abs(residual_company_signed) * sign
        self.residual_signed = abs(residual) * sign
        self.residual = abs(residual)
        self.residual = round(self.residual)
        digits_rounding_precision = self.currency_id.rounding
        if float_is_zero(self.residual, precision_rounding=digits_rounding_precision):
            self.reconciled = True
        else:
            self.reconciled = False


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    line_insurance_amount = fields.Monetary('Insurance(Amt)', digits=dp.get_precision('Product Price'), compute="_compute_price")

    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_ids', 'quantity',
        'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id', 'invoice_id.company_id',
        'invoice_id.date_invoice', 'invoice_id.date')
    def _compute_price(self):
        if self.product_id.type != 'service':
            currency = self.invoice_id and self.invoice_id.currency_id or None
            price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
            taxes = False
            if self.invoice_line_tax_ids:
                taxes = self.invoice_line_tax_ids.compute_all(price, currency, self.quantity, product=self.product_id, partner=self.invoice_id.partner_id)
            price_subtotal_signed = taxes['total_excluded'] if taxes else self.quantity * price
            self.line_insurance_amount = price_subtotal_signed * 0.04 / 100
            self.price_subtotal = price_subtotal_signed
            self.price_total = taxes['total_included'] if taxes else self.price_subtotal
            if self.invoice_id.currency_id and self.invoice_id.currency_id != self.invoice_id.company_id.currency_id:
                currency = self.invoice_id.currency_id
                date = self.invoice_id._get_currency_rate_date()
                price_subtotal_signed = currency._convert(price_subtotal_signed, self.invoice_id.company_id.currency_id, self.company_id or self.env.user.company_id, date or fields.Date.today())
            sign = self.invoice_id.type in ['in_refund', 'out_refund'] and -1 or 1
            self.price_subtotal_signed = price_subtotal_signed * sign

        else:
            currency = self.invoice_id and self.invoice_id.currency_id or None
            price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
            taxes = False
            if self.invoice_line_tax_ids:
                taxes = self.invoice_line_tax_ids.compute_all(price, currency, self.quantity,product=self.product_id,partner=self.invoice_id.partner_id)
            price_subtotal_signed = taxes['total_excluded'] if taxes else self.quantity * price
            self.line_insurance_amount = 0.00
            self.price_subtotal = price_subtotal_signed
            self.price_total = taxes['total_included'] if taxes else self.price_subtotal
            if self.invoice_id.currency_id and self.invoice_id.currency_id != self.invoice_id.company_id.currency_id:
                currency = self.invoice_id.currency_id
                date = self.invoice_id._get_currency_rate_date()
                price_subtotal_signed = currency._convert(price_subtotal_signed, self.invoice_id.company_id.currency_id, self.company_id or self.env.user.company_id,date or fields.Date.today())
            sign = self.invoice_id.type in ['in_refund', 'out_refund'] and -1 or 1
            self.price_subtotal_signed = price_subtotal_signed * sign





