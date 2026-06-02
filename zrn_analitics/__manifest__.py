# -*- coding: utf-8 -*-
{
    'name': 'Zoraen Analitics',
    'summary': 'Centro base para hubs, reporteria y analisis de datos de Zoraen',
    'description': """
Zoraen Analitics
================

Addon base para la capa analitica:
- hubs ejecutivos y operativos
- reporteria y analisis
- dashboards dinamicos
- procesamiento de datos para metricas
    """,
    'author': 'Zoraen Corporation',
    'website': 'https://www.zoraen.com',
    'category': 'Reporting',
    'version': '0.1',
    'license': 'LGPL-3',
    'application': True,
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/analitics_home_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'zrn_analitics/static/src/js/analitics_form_view.js',
            'zrn_analitics/static/src/xml/analitics_form_view.xml',
            'zrn_analitics/static/zrn/css/colors.css',
            'zrn_analitics/static/zrn/css/lib.css',
        ],
    },
    'installable': True,
}
