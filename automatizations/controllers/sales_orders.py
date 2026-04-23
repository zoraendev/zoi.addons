# -*- coding: utf-8 -*-

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

from .base_controller import AutomatizationsBaseController
from ..application.sales_orders.queries import SalesOrderQueryService
from ..application.sales_orders.transactions import SalesOrderTransactionService


class AutomatizationsSalesOrdersController(AutomatizationsBaseController):
    """Endpoints para armado, confirmacion y consulta de pedidos automatizados."""

    @http.route(
        ['/api/automatizations/sales-orders/query'],
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def query_sales_orders(self, **kwargs):
        if not self._authenticate():
            return self._make_auth_error_response()

        payload = self._get_json_payload()
        criteria = payload.get('criteria') or payload.get('filters') or payload

        try:
            result = SalesOrderQueryService(request.env).query_orders(criteria)
        except ValidationError as error:
            return request.make_json_response({
                'success': False,
                'message': error.args[0],
                'count': 0,
                'orders': [],
            }, status=400)

        return request.make_json_response({
            'success': True,
            'message': 'Consulta de ordenes procesada correctamente.',
            'criteria': result['criteria'],
            'matched_fields': result['matched_fields'],
            'count': result['count'],
            'orders': result['orders'],
        })

    @http.route(
        ['/api/automatizations/sales-orders/create'],
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def create_sales_orders(self, **kwargs):
        if not self._authenticate():
            return self._make_auth_error_response()

        payload = self._get_json_payload()
        orders = payload.get('orders') or payload.get('sales_orders') or []
        orders = orders if isinstance(orders, list) else []

        if not orders:
            return request.make_json_response({
                'success': False,
                'message': 'Debes enviar la lista de ordenes a crear en el campo orders.',
                'count': 0,
                'created_count': 0,
                'results': [],
            }, status=400)

        try:
            result = SalesOrderTransactionService(request.env).create_orders(orders)
        except ValidationError as error:
            return request.make_json_response({
                'success': False,
                'message': error.args[0],
                'count': 0,
                'created_count': 0,
                'results': [],
            }, status=400)

        return request.make_json_response({
            'success': True,
            'message': 'Proceso de creacion de ordenes ejecutado.',
            'count': result['count'],
            'created_count': result['created_count'],
            'results': result['results'],
        })

