# -*- coding: utf-8 -*-
{
    'name': 'Zoraen Commercial',
    'summary': 'Capa comercial operativa independiente para Zoraen',
    'description': """
Zoraen Commercial
=================

Addon dedicado a la capa comercial operativa:
- marcas comerciales propias con categorias
- canales comerciales propios
- importacion de marcas desde catalogos existentes de Odoo
    """,
    'author': 'Zoraen Corporation',
    'website': 'https://www.zoraen.com',
    'category': 'Sales',
    'version': '0.1.1',
    'license': 'LGPL-3',
    'application': True,
    'depends': ['base', 'product', 'contacts'],
    'data': [
        'security/ir.model.access.csv',
        'views/commercial_brand_import_views.xml',
        'views/commercial_brand_views.xml',
        'views/commercial_channel_views.xml',
        'views/commercial_home_views.xml',
        'views/commercial_hub_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'zrn_commercial/static/src/js/commercial_hub_action.js',
            'zrn_commercial/static/src/scss/commercial_hub_action.scss',
            'zrn_commercial/static/src/xml/commercial_hub_action.xml',
            'zrn_commercial/static/src/xml/hubs/*.xml',
        ],
    },
    'installable': True,
}
