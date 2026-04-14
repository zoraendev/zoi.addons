# -*- coding: utf-8 -*-
{
    'name': "advanced_metrics",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.zoraen.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'sale_stock', 'base_setup'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/sales_orders.xml',
        'views/templates.xml',
        'views/res_config_settings.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'advanced_metrics/static/src/js/home_form_view.js',
            'advanced_metrics/static/src/js/sales_orders_form_view.js',
            'advanced_metrics/static/src/js/sales_orders_report.js',
            'advanced_metrics/static/src/xml/home_form_view.xml',
            'advanced_metrics/static/src/scss/dashboard.scss',
        ],
        'web.assets_web_dark': [
            'advanced_metrics/static/src/scss/dashboard.dark.scss',
        ],
    },
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

