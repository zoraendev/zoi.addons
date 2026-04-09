# -*- coding: utf-8 -*-
{
    'name': "pbi_connections",
    'summary': "Panel inicial para centralizar conexiones y endpoints de Power BI",
    'description': """
Modulo base para separar y administrar desde aqui las conexiones
Power BI que hoy viven dentro de Advanced Metrics.
    """,
    'author': "My Company",
    'website': "https://www.zoraen.com",
    'category': 'Sales',
    'version': '0.1',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pbi_connections/static/src/js/home_form_view.js',
            'pbi_connections/static/src/xml/home_form_view.xml',
            'pbi_connections/static/src/scss/dashboard.scss',
        ],
    },
    'demo': [
        'demo/demo.xml',
    ],
}

