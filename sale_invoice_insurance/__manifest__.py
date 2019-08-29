# -*- coding: utf-8 -*-
# Part of Kiran Infosoft. See LICENSE file for full copyright and licensing details.
{
    'name': "Insurance on Sale and Invoice",
    'summary': """
Insurance on Sale and Invoice
""",
    'description': """
- Insurance amount (0.04%) should be arrived automatically from Untaxed amount calculation.
- Round off calculation should be calculated automatically for rounding off the decimal value.
- Applies only Sale order to Invoice & Invoice payment.
- Register payment should include insurance amount automatically.
- Automatic Journal entry has to be created separately for the Insurance & round off for invoice wise.
- Insurance & round off should not appear in Purchase order, vendor bill and vendor payment.
""",
    "version": "1.3",
    "category": "Sales",
    'author': "oodu implementers pvt ltd",
    "website": "http://www.odooimplementers.com.com",
    'license': 'Other proprietary',
    "depends": [
        'sale_management',
    ],
    "data": [
        'views/sale_order_view.xml',
        'views/account_invoice_view.xml',
        'views/res_company_view.xml'
    ],
    "application": False,
    'installable': True,
}
