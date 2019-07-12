# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models,fields,api
  
class Company(models.Model):
    _inherit = 'res.company'

    insurance_account = fields.Many2one("account.account", string="Insurance Account")
    round_of_account = fields.Many2one("account.account", string="Round of Account")