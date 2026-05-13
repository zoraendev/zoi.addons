# -*- coding: utf-8 -*-
{
    'name': "Prodigyn",

    'summary': "Modulo principal de Prodigyn",

    'description': """
Modulo principal de Prodigyn.
    """,

    'author': "Zoraen Corporation",
    'website': "https://www.zoraen.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Productivity',
    'version': '0.1',
    'license': 'LGPL-3',
    'application': True,

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'zrn_prodigyn/static/zrn/css/colors.css',
            'zrn_prodigyn/static/zrn/css/lib.css',
        ],
        'web.assets_web_dark': [
            'zrn_prodigyn/static/zrn/css/colors-dark.css',
            'zrn_prodigyn/static/zrn/css/lib-dark.css',
        ],
    },
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
