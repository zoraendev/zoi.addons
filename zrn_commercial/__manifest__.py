# -*- coding: utf-8 -*-
{
    'name': 'Zoraen Commercial',
    'summary': 'Capa comercial operativa independiente para Zoraen',
    'description': """
Zoraen Commercial
=================

Addon dedicado a la capa comercial operativa:
- marcas comerciales propias
- canales comerciales propios
- prospectos, oportunidades y cotizaciones clasificadas
- importacion de marcas desde catalogos existentes de Odoo
    """,
    'author': 'Zoraen Corporation',
    'website': 'https://www.zoraen.com',
    'category': 'Sales',
    'version': '0.1.1',
    'license': 'LGPL-3',
    'application': True,
    'depends': ['base', 'product', 'contacts', 'mail', 'crm', 'sale_management', 'sale_crm'],
    'data': [
        'security/ir.model.access.csv',
        'views/commercial_brand_import_views.xml',
        'views/commercial_brand_views.xml',
        'views/commercial_channel_views.xml',
        'views/product_channel_views.xml',
        'views/commercial_home_views.xml',
        'views/commercial_hub_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # Librería externa de ECharts cargada desde el módulo analítico común
            'zrn_analitics/static/lib/echarts/echarts.min.js',
            # Controlador JS para el rendering y control dinámico del dashboard comercial
            'zrn_commercial/static/src/js/commercial_form_view.js',
            # Assets del Hub comercial
            'zrn_commercial/static/src/js/commercial_hub_action.js',
            'zrn_commercial/static/src/scss/commercial_hub_action.scss',
            'zrn_commercial/static/src/xml/commercial_hub_action.xml',
            'zrn_commercial/static/src/xml/hubs/*.xml',
        ],
    },
    'installable': True,
}
