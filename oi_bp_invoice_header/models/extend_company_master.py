from odoo import api, fields, models, _


class ResCompanyExtend(models.Model):
    _inherit = 'res.company'

    sub_branch_id = fields.Many2one('res.company', string='Sub Branch')
