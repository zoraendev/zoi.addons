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
        'data/commercial_channel_data.xml',
        'views/commercial_brand_import_views.xml',
        'views/commercial_brand_views.xml',
        'views/commercial_channel_views.xml',
        'views/commercial_home_views.xml',
        'views/commercial_flow_views.xml',
        'views/commercial_hub_views.xml',
    ],
    'installable': True,
}
