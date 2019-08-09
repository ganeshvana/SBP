# -*- coding: utf-8 -*-

{
    'name': 'Sale Insurance',
    'version': '12.0',
    'category': 'stock',
    'depends': ['sale_management', 'account'],
    'summary': 'This module calculate sale insurance and round off ',
    'description': 'This module calculate sale insurance and round off ',
    'data': [
        'views/sale_view.xml',
        'views/account_invoice_view.xml',
        'views/res_company.xml',
        'report/sale_templates.xml',
        'report/report_invoice.xml',

    ],
    'application': False,
    'installable': True,
    'auto_install': False,
}
