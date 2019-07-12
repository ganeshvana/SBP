# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Header',
    'version' : '12.0.1.1',
	'author' : 'Oodu Implementers Private Limited',
    'summary': 'Inherit default Header',
    'description': """""",
    'category' : 'Report',
    'website': 'https://www.odooimplementers.com',
    'depends' : ['base', 'account', 'web','l10n_in'],
    'data': ['views/company_extend_view.xml', 'report/header.xml'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'OEEL-1',
}
