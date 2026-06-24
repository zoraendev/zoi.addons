# -*- coding: utf-8 -*-
{
    'name': 'Zoraen Planning',
    'summary': 'Planeacion operativa, abastecimiento y logistica para Zoraen',
    'description': """
Zoraen Planning
===============

Addon dedicado a planeacion operativa:
- planeacion de produccion
- planeacion de abastecimiento
- planeacion logistica
- planes desacoplados de ejecucion
    """,
    'author': 'Zoraen Corporation',
    'website': 'https://www.zoraen.com',
    'category': 'Operations/Inventory',
    'version': '0.1.1',
    'license': 'LGPL-3',
    'application': True,
    'depends': ['base', 'sale_stock', 'mrp', 'purchase_stock'],
    'data': [
        'security/ir.model.access.csv',
        'data/inventory_reconciliation_demo_products.xml',
        'data/inventory_reconciliation_demo_stock.xml',
        'views/planning_home_views.xml',
        'views/production_planning_views.xml',
        'views/purchase_planning_views.xml',
        'views/delivery_planning_views.xml',
        'views/inventory_reconciliation_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'zrn_analitics/static/lib/echarts/echarts.min.js',
            'zrn_planning/static/src/js/planning_form_view.js',
            'zrn_planning/static/src/js/production_report_form_view.js',
            'zrn_planning/static/src/xml/planning_form_view.xml',
            'zrn_planning/static/src/xml/production_report_form_view.xml',
            'zrn_planning/static/zrn/css/colors.css',
            'zrn_planning/static/zrn/css/lib.css',
        ],
        # Dark mode: Odoo solo inyecta estos assets cuando html.dark está activo
        'web.assets_web_dark': [
            'zrn_planning/static/zrn/css/colors-dark.css',
        ],
    },
    'installable': True,
}
