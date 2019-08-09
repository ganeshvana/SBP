# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models,fields,api, _
from odoo.addons import decimal_precision as dp


class SaleOrder(models.Model):

    _inherit = "sale.order"

    @api.depends('order_line.price_total', 'round_off')
    def _amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = insurance_per = 0.0
            for line in order.order_line:
                insurance_per += line.line_insurance_amount
                print("PPPPPPP:::::::::::::::", insurance_per)
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
                'insurance_amount': insurance_per,
            })

            if order.amount_untaxed:
                total = order.amount_total + insurance_per
                actual_total = total
                total = round(total)
                round_value = actual_total - total
                order.amount_total = total
                if round_value <= 0.50:
                    round_value = -(round_value)
                else:
                    round_value = round_value
                order.update({
                    'amount_total': total,
                    'round_off': round_value})
                print("round value",round_value)


    insurance_amount = fields.Float(string='Insurance 0.04%', compute='_amount_all')
    round_off = fields.Float(string='Round Off',  compute='_amount_all')

    @api.model
    def _prepare_invoice(self):
        res = super(SaleOrder, self)._prepare_invoice()
        if self.insurance_amount:
            res.update({'insurance_amount' : self.insurance_amount,
                'amount_total': self.amount_total,
                'round_off':self.round_off,
                })
        return res



class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    line_insurance_amount = fields.Monetary('Insurance(Amt)', digits=dp.get_precision('Product Price'),compute="_compute_amount")

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """Compute the amounts of the SO line"""
        for line in self:
            if line.product_id.type != 'service':
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,product=line.product_id, partner=line.order_id.partner_shipping_id)
                line.update({
                    'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                    'price_total': taxes['total_included'],
                    'line_insurance_amount': taxes['total_excluded'] * 0.04 / 100,
                    'price_subtotal': taxes['total_excluded'],
                })
            else:
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                                product=line.product_id, partner=line.order_id.partner_shipping_id)
                line.update({
                    'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                    'price_total': taxes['total_included'],
                    'line_insurance_amount': 0.00,
                    'price_subtotal': taxes['total_excluded'],
                })







