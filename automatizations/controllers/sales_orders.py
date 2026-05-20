# -*- coding: utf-8 -*-

import json

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

from ..application.sales_orders.transactions import SalesOrderTransactionService


class AutomatizationsSalesOrdersController(http.Controller):
    """Endpoints para armado y confirmacion de pedidos automatizados."""

    @http.route(
        ['/api/automatizations/sales-orders/create'],
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def create_sales_orders(self, **kwargs):
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

    @staticmethod
    def _get_json_payload():
        raw_body = request.httprequest.data
        if not raw_body:
            return {}
        try:
            payload = json.loads(raw_body.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}
