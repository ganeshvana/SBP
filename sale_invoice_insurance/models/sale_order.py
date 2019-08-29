# -*- coding: utf-8 -*-

from odoo.tools import float_round
from odoo.exceptions import ValidationError

from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_insurance_apply = fields.Boolean(
        string="Is Insurance Applicable?",
        default=True,
        readonly=True,
        states={
            'draft': [('readonly', False)],
            'sent': [('readonly', False)]
        }
    )
    insurance_amount = fields.Monetary(
        string='Insurance Amount',
        store=True,
        readonly=True,
        compute='_amount_all',
        track_visibility='onchange',
        track_sequence=7
    )
    total_round_off = fields.Monetary(
        string='Round Off',
        store=True,
        readonly=True,
        compute='_amount_all',
        track_visibility='onchange',
        track_sequence=8
    )


    @api.depends(
        'order_line.price_total',
        'is_insurance_apply'
    )
    def _amount_all(self):
        super(SaleOrder, self)._amount_all()
        for order in self:
            if order.is_insurance_apply and order.amount_total:
                amount_to_insurance = 0.0
                line_taxes = 0.0

                order_line = order.order_line.filtered(lambda i: i.product_id.type != 'service')
                if not order_line:
                    continue
                amount_to_insurance = sum(l.price_subtotal for l in order_line)

#                 tax = order.company_id.insurance_tax_id
                tax = order_line.mapped('tax_id')
                if tax:
                    tax = tax[0]
                insurance_tax = 0.0

                insurance_amount = (amount_to_insurance * 0.04) / 100.0
                if tax:
#                     product = order.company_id.insurance_product_id
#                     insurance_tax = tax._compute_amount(
#                         base_amount=insurance_amount,
#                         price_unit=insurance_amount,
#                         quantity=1.0,
# #                         product=product,
#                         partner=order.partner_id
#                     ) or 0.0
                    insurance_taxes = tax.compute_all(
                        price_unit=insurance_amount,
                        currency=order.currency_id,
                        quantity=1.0,
                        partner=order.partner_id
                    )
                    total_included = insurance_taxes.get('total_included', 0.0)
                    total_excluded = insurance_taxes.get('total_excluded', 0.0)
                    insurance_tax = total_included - total_excluded

                # Tax amount
                amount_tax = order.amount_tax + insurance_tax

                # Total amount
                amount_total = amount_tax + insurance_amount + order.amount_untaxed

#                 rounding = 0.5
#                 rounding_method = 'UP'
#                 rounding_amount = float_round(
#                     amount_total,
#                     precision_rounding=rounding,
#                     rounding_method=rounding_method
#                 )


                rounding_amount = round(amount_total)
                difference = rounding_amount - amount_total
                total_round_off = order.currency_id.round(difference)

                order.update({
                    'insurance_amount': insurance_amount,
                    'amount_tax': order.amount_tax + insurance_tax,
                    'amount_total': rounding_amount,
                    'total_round_off': total_round_off
                })

    @api.multi
    def _prepare_invoice(self):
        values = super(SaleOrder, self)._prepare_invoice()
        values.update({'is_insurance_apply': self.is_insurance_apply})
        return values


    @api.multi
    def action_invoice_create(self, grouped=False, final=False):
        invoice_ids = super(SaleOrder, self).action_invoice_create(
            grouped=grouped, final=final
        )
        invoices = self.env['account.invoice'].sudo().browse(invoice_ids)
        invoices.onchange_insurance_amount()
        return invoice_ids

