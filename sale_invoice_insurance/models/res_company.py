# -*- coding: utf-8 -*-
from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

#     insurance_product_id = fields.Many2one(
#         'product.product',
#         string="Insurance Charge Product",
#     )
#     roundoff_product_id = fields.Many2one(
#         'product.product',
#         string="Roundoff Product",
#     )
#     insurance_tax_id = fields.Many2one(
#         'account.tax',
#         string="Insurance Charge Tax",
#     )
    insurance_account_id = fields.Many2one(
        'account.account',
        string="Insurance Charge Account",
    )
    roundoff_account_id = fields.Many2one(
        'account.account',
        string="Roundoff Account",
    )