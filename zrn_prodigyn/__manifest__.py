# -*- coding: utf-8 -*-
{
    'name': "Prodigyn",

    'summary': "Modulo principal de Prodigyn",

    'description': """
Modulo principal de Prodigyn.
    """,

    'author': "Zoraen Corporation",
    'website': "https://www.zoraen.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Productivity',
    'version': '0.1',
    'license': 'LGPL-3',
    'application': True,

    # any module necessary for this one to work correctly
    'depends': ['base', 'base_setup', 'sale_stock', 'mrp', 'purchase_stock'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings.xml',
        'views/commercial_planning_views.xml',
        'views/commercial_planning_placeholders.xml',
        'views/production_planning_views.xml',
        'views/purchase_planning_views.xml',
        'views/delivery_planning_views.xml',
        'views/reporting_analysis/reporting_analysis_views.xml',
        'views/reporting_analysis/executive/reporting_executive_views.xml',
        'views/reporting_analysis/placeholders/reporting_commercial_views.xml',
        'views/reporting_analysis/placeholders/reporting_channels_views.xml',
        'views/reporting_analysis/placeholders/reporting_customers_views.xml',
        'views/reporting_analysis/placeholders/reporting_skus_views.xml',
        'views/reporting_analysis/placeholders/reporting_financial_views.xml',
        'views/reporting_analysis/placeholders/reporting_margin_views.xml',
        'views/reporting_analysis/placeholders/reporting_receivables_views.xml',
        'views/reporting_analysis/placeholders/reporting_operations_views.xml',
        'views/reporting_analysis/placeholders/reporting_forecast_views.xml',
        'views/reporting_analysis/placeholders/reporting_stockouts_views.xml',
        'views/reporting_analysis/placeholders/reporting_coverage_views.xml',
        'views/reporting_analysis/placeholders/reporting_velocity_views.xml',
        'views/reporting_analysis/placeholders/reporting_rrhh_views.xml',
        'views/reporting_analysis/placeholders/reporting_media_views.xml',
        'views/reporting_analysis/placeholders/reporting_scenarios_views.xml',
        'views/internal_tool_views.xml',
        'views/views.xml',
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'zrn_prodigyn/static/src/js/prodigyn_form_view.js',
            'zrn_prodigyn/static/src/js/production_report_form_view.js',
            'zrn_prodigyn/static/src/js/report_summary_list_view.js',
            'zrn_prodigyn/static/src/reporting_analysis/executive/js/reporting_executive_view.js',
            'zrn_prodigyn/static/lib/echarts/echarts.min.js',
            'zrn_prodigyn/static/src/reporting_analysis/commercial/js/reporting_commercial_tabs.js',
            'zrn_prodigyn/static/src/xml/prodigyn_form_view.xml',
            'zrn_prodigyn/static/src/xml/production_report_form_view.xml',
            'zrn_prodigyn/static/src/xml/report_summary_list_view.xml',
            'zrn_prodigyn/static/src/reporting_analysis/executive/scss/reporting_executive.scss',
            'zrn_prodigyn/static/src/reporting_analysis/commercial/scss/reporting_commercial.scss',
            'zrn_prodigyn/static/zrn/css/colors.css',
            'zrn_prodigyn/static/zrn/css/lib.css',
        ],
        'web.assets_web_dark': [
            'zrn_prodigyn/static/zrn/css/colors-dark.css',
            'zrn_prodigyn/static/zrn/css/lib-dark.css',
        ],
    },
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
