# -*- coding: utf-8 -*-
# Part of Kiran Infosoft. See LICENSE file for full copyright and licensing details.
from odoo.tools import float_round
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    is_insurance_apply = fields.Boolean(
        string="Is Insurance Applicable?",
        default=True,
        readonly=True,
        states={
            'draft': [('readonly', False)]
        }
    )
    insurance_amount = fields.Monetary(
        string='Insurance Amount',
        store=True,
        readonly=True,
        compute='_compute_insurance_amount',
        track_visibility='onchange',
        track_sequence=7
    )
    total_round_off = fields.Monetary(
        string='Round Off',
        store=True,
        readonly=True,
        compute='_compute_amount',
        track_visibility='onchange',
        track_sequence=8
    )

    
    @api.one
    @api.depends(
        'amount_untaxed',
        'is_insurance_apply',
        'invoice_line_ids.price_subtotal',
    )
    def _compute_insurance_amount(self):
        if self.is_insurance_apply and self.type in ['out_invoice', 'out_refund']:
            invoice_line_ids = self.invoice_line_ids.filtered(
                lambda i: i.product_id.type != 'service'
            )
            if invoice_line_ids:
                amount_untaxed = sum(
                    line.price_subtotal for line in invoice_line_ids
                )
                self.insurance_amount = (amount_untaxed * 0.04) / 100.0
        else:
            self.insurance_amount = 0.0

    @api.one
    @api.depends(
        'invoice_line_ids.price_subtotal',
        'tax_line_ids.amount',
        'tax_line_ids.amount_rounding',
        'currency_id',
        'company_id',
        'date_invoice',
        'type',
        'is_insurance_apply'
    )
    def _compute_amount(self):
        res = super(AccountInvoice, self)._compute_amount()
        if self.type not in ['out_invoice', 'out_refund']:
            return res
        if not self.is_insurance_apply:
            return res
 
        round_curr = self.currency_id.round
        self.amount_total = self.amount_total + self.insurance_amount
        amount_total = self.amount_total
        rounding = 0.5
#         rounding_method = 'HALF-UP'
#         rounding_amount = float_round(
#             amount_total,
#             precision_rounding=rounding,
#             rounding_method=rounding_method
#         )

        rounding_amount = round(amount_total)
        difference = rounding_amount - amount_total
        total_round_off = self.currency_id.round(difference)
        self.total_round_off = total_round_off
        self.amount_total = rounding_amount

        amount_total_company_signed = self.amount_total
        amount_untaxed_signed = self.amount_untaxed
        if self.currency_id and self.company_id and self.currency_id != self.company_id.currency_id:
            currency_id = self.currency_id
            amount_total_company_signed = currency_id._convert(
                self.amount_total,
                self.company_id.currency_id,
                self.company_id,
                self.date_invoice or fields.Date.today()
            )
            amount_untaxed_signed = currency_id._convert(
                self.amount_untaxed,
                self.company_id.currency_id,
                self.company_id,
                self.date_invoice or fields.Date.today()
            )
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        self.amount_total_company_signed = amount_total_company_signed * sign
        self.amount_total_signed = self.amount_total * sign
        self.amount_untaxed_signed = amount_untaxed_signed * sign


    def _prepare_insurance_tax_line_vals(self):
        """ Prepare values to create an account.invoice.tax line

        The line parameter is an account.invoice.line, and the
        tax parameter is the output of account.tax.compute_all().
        """

#         insurance_tax = self.company_id.insurance_tax_id
        invoice_line_ids = self.invoice_line_ids.filtered(
            lambda i: i.product_id.type != 'service'
        )
        insurance_tax = invoice_line_ids.mapped('invoice_line_tax_ids')
        if insurance_tax:
            insurance_tax = insurance_tax[0]
        taxes = insurance_tax.compute_all(
            price_unit=self.insurance_amount,
            currency=self.currency_id,
            quantity=1.0,
#             product=self.company_id.insurance_product_id,
            partner=self.partner_id
        )['taxes']
#         tax = taxes[0]
        tax_vals = []
        for tax in taxes:
            vals = {
                'invoice_id': self.id,
                'name': tax['name'],
                'tax_id': tax['id'],
                'amount': tax['amount'],
                'base': tax['base'],
                'manual': False,
                'sequence': tax['sequence'],
                'account_id': tax['account_id'] or tax['refund_account_id'],
            }
            tax_vals.append(vals)
        return tax_vals

    @api.onchange(
        'insurance_amount',
        'is_insurance_apply'
    )
    def onchange_insurance_amount(self):
        self._onchange_invoice_line_ids()

    @api.onchange('invoice_line_ids')
    def _onchange_invoice_line_ids(self):
        super(AccountInvoice, self)._onchange_invoice_line_ids()
        tax_name = 'Insurance Tax: 18.0 %'
        tax_lines = self.env['account.invoice.tax']
        if self.is_insurance_apply:
            tax_vals = self._prepare_insurance_tax_line_vals()
            if tax_vals:
                for vals in tax_vals:
                    exist_line = self.tax_line_ids.filtered(
                        lambda t: t.tax_id.id == vals['tax_id']
                    )
                    vals['name'] = 'Insurance Tax: %s' %(vals['name'])
                    if exist_line:
                        base_amt = exist_line.base
                        amount = exist_line.amount
                        exist_line.update({
                            'amount': amount + vals['amount'],
                            'base': base_amt + vals['base']
                        })
                    else:
                        self.tax_line_ids += tax_lines.new(vals)

    @api.model
    def invoice_line_move_line_get(self):
        lines = super(AccountInvoice, self).invoice_line_move_line_get()
        if not self.is_insurance_apply or self.type not in ['out_invoice', 'out_refund']:
            return lines
        company = self.company_id

        part = self.partner_id
        fpos = self.fiscal_position_id
        company = self.company_id
        currency = self.currency_id
        type = self.type

        if self.insurance_amount:
            if not company.insurance_account_id:
                raise ValidationError(
                    _('Please configure Insurance Account on Company Form!')
                )

#             insurance_account = self.env['account.invoice.line'].get_invoice_line_account(
#                 type, company.insurance_product_id, fpos, company
#             )
            insurance_account = company.insurance_account_id
#             if not insurance_account:
#                 raise ValidationError(
#                     _('Please configure Income Account on Product : %s!' %(
#                         company.insurance_product_id.name
#                     ))
#                 )

            insurance_line_dict = {
                'type': 'src',
                'name': 'Insurance Charges (0.04%)',
                'price_unit': self.insurance_amount,
                'quantity': 1.0,
                'price': self.insurance_amount,
                'account_id': insurance_account.id,
#                 'product_id': company.insurance_product_id.id,
#                 'uom_id': company.insurance_product_id.uom_id.id,
                'account_analytic_id': False,
                'analytic_tag_ids': [],
                'tax_ids': [],
                'invoice_id': self.id,
            }
            lines.append(insurance_line_dict)

        if self.total_round_off:
            if not company.roundoff_account_id:
                raise ValidationError(
                    _('Please configure Roundoff Account on Company Form!')
                )

#             roundoff_account = self.env['account.invoice.line'].get_invoice_line_account(
#                 type, company.roundoff_product_id, fpos, company
#             )
            roundoff_account = company.roundoff_account_id
#             if not roundoff_account:
#                 raise ValidationError(
#                     _('Please configure Income Account on Product : %s!' %(
#                         company.roundoff_product_id.name
#                     ))
#                 )

            round_off_line_dict = {
                'type': 'src',
                'name': 'Round Off',
                'price_unit': self.total_round_off,
                'quantity': 1.0,
                'price': self.total_round_off,
                'account_id': roundoff_account.id,
#                 'product_id': company.roundoff_product_id.id,
#                 'uom_id': company.roundoff_product_id.uom_id.id,
                'account_analytic_id': False,
                'analytic_tag_ids': [],
                'tax_ids': [],
                'invoice_id': self.id,
            }
            lines.append(round_off_line_dict)

        return lines
