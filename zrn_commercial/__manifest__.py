# -*- coding: utf-8 -*-
{
    'name': 'Zoraen Commercial',
    'summary': 'Marcas comerciales y base operativa comercial para Zoraen',
    'description': """
Zoraen Commercial
=================

Addon dedicado a la capa comercial operativa:
- marcas comerciales
- relaciones de productos por marca
- futura base para portafolio, canales y pricing
    """,
    'author': 'Zoraen Corporation',
    'website': 'https://www.zoraen.com',
    'category': 'Sales',
    'version': '0.1',
    'license': 'LGPL-3',
    'application': True,
    'depends': ['base', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'views/commercial_brand_views.xml',
    ],
    'installable': True,
}
