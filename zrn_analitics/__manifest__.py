# -*- coding: utf-8 -*-
{
    'name': 'Zoraen Analytics',
    'summary': 'Centro base para hubs, reporteria y analisis de datos de Zoraen',
    'description': """
Zoraen Analytics
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
        'views/analytics/analytics_home_views.xml',
        'views/analytics/placeholders/analytics_overview_views.xml',
        'views/analytics/placeholders/analytics_workspace_views.xml',
        'views/analytics/placeholders/analytics_scenarios_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'zrn_analitics/static/src/js/analytics_form_view.js',
            'zrn_analitics/static/src/xml/analytics_form_view.xml',
            'zrn_analitics/static/zrn/css/colors.css',
            'zrn_analitics/static/zrn/css/lib.css',
        ],
    },
    'installable': True,
}
