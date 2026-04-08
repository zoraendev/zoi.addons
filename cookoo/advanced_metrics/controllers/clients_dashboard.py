# -*- coding: utf-8 -*-

from odoo import http

from .base_dashboard import BaseDashboardController


class ClientsDashboardController(BaseDashboardController):
    _service_model = 'advanced_metrics.customer.dashboard'
    _request_filter_keys = (
        'dateFrom',
        'dateTo',
        'top',
        'sortBy',
        'inactiveDays',
    )

    @http.route(
        '/api/bi/customer-dashboard/frequent-customers',
        type='http',
        auth='public',
        methods=['GET', 'POST'],
        csrf=False,
    )
    def get_frequent_customers(self, **kwargs):
        return self._handle_service_request(
            'get_frequent_customers_report_data',
            'Clientes más frecuentes obtenidos correctamente.',
            'No fue posible obtener los clientes más frecuentes.',
        )

    @http.route(
        '/api/bi/customer-dashboard/inactive-customers',
        type='http',
        auth='public',
        methods=['GET', 'POST'],
        csrf=False,
    )
    def get_inactive_customers(self, **kwargs):
        return self._handle_service_request(
            'get_inactive_customers_report_data',
            'Clientes inactivos obtenidos correctamente.',
            'No fue posible obtener los clientes inactivos.',
        )

    @http.route(
        '/api/bi/customer-dashboard/customer-value',
        type='http',
        auth='public',
        methods=['GET', 'POST'],
        csrf=False,
    )
    def get_customer_value(self, **kwargs):
        return self._handle_service_request(
            'get_customer_value_report_data',
            'Valor por cliente obtenido correctamente.',
            'No fue posible obtener el valor por cliente.',
        )
