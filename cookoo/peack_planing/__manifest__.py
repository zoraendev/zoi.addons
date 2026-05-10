# -*- coding: utf-8 -*-
{
    'name': "PeackPlaning",
    'summary': "Módulo completo de planeación de fabricación y métricas avanzadas",
    'description': """
        Módulo de Planeación de Fabricación (PeackPlaning) para la gestión 
        operativa y seguimiento de órdenes de venta, inventario y producción.
    """,
    'author': "Zoraen",
    'website': "https://www.zoraen.com",
    'category': 'Manufacturing',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'sale_stock', 'base_setup', 'mrp'],

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
            'peack_planing/static/src/js/home_form_view.js',
            'peack_planing/static/src/js/production_form_view.js',
            'peack_planing/static/src/js/report_form_view.js',
            'peack_planing/static/src/xml/home_form_view.xml',
            'peack_planing/static/src/xml/production_form_view.xml',
            'peack_planing/static/src/xml/report_form_view.xml',
            'peack_planing/static/src/scss/dashboard.scss',
        ],
        'web.assets_web_dark': [
            'peack_planing/static/src/scss/dashboard.dark.scss',
        ],
    },
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

