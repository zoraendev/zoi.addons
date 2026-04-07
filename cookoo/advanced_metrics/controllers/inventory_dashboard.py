# -*- coding: utf-8 -*-
import json

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request


class InventoryDashboardController(http.Controller):
    @staticmethod
    def _get_json_payload():
        payload = {}
        raw_body = request.httprequest.data
        if raw_body:
            try:
                payload = json.loads(raw_body.decode('utf-8'))
            except (ValueError, UnicodeDecodeError):
                payload = {}
        return payload if isinstance(payload, dict) else {}

    def _get_request_filters(self):
        payload = self._get_json_payload()
        filters = payload.get('filters') or payload or {}

        for key in (
            'dateFrom',
            'dateTo',
            'warehouseId',
            'categoryId',
            'limit',
            'groupBy',
            'daysWithoutMovement',
        ):
            value = request.httprequest.args.get(key)
            if value not in (None, ''):
                filters[key] = value

        return filters

    def _authenticate(self):
        token = request.httprequest.headers.get('Access-Token') or request.httprequest.headers.get('Authorization')
        if token and token.startswith('Bearer '):
            token = token[7:]
        if not token:
            return None
        return request.env['advanced_metrics.api.config'].sudo().search([('access_token', '=', token)], limit=1)

    @staticmethod
    def _make_success_response(message, report_data, extra_keys=None):
        response = {
            'success': True,
            'message': message,
            'generatedAt': report_data.get('generatedAt'),
            'filters': report_data.get('filters', {}),
            'data': report_data.get('data', []),
        }
        for key in extra_keys or []:
            response[key] = report_data.get(key, {})
        return request.make_json_response(response)

    @staticmethod
    def _make_error_response(message, filters, status=500, extra_payload=None):
        response = {
            'success': False,
            'message': message,
            'generatedAt': None,
            'filters': filters or {},
            'data': [],
        }
        if extra_payload:
            response.update(extra_payload)
        return request.make_json_response(response, status=status)

    @http.route('/api/bi/inventory-intelligent/top-products', type='http', auth='public', methods=['POST'], csrf=False)
    def get_top_products(self, **kwargs):
        if not self._authenticate():
            return self._make_error_response('Acceso no autorizado: Token invalido o ausente en las cabeceras.', {}, status=401)
        filters = self._get_request_filters()

        try:
            report_data = request.env['advanced_metrics.report.wizard'].sudo().get_top_products_report_data(filters)
            return self._make_success_response('Top productos obtenido correctamente.', report_data)
        except ValidationError as error:
            return self._make_error_response(error.args[0], filters, status=400)
        except Exception:
            return self._make_error_response('No fue posible obtener el top de productos.', filters)

    @http.route('/api/bi/inventory-intelligent/products-sales', type='http', auth='public', methods=['POST'], csrf=False)
    def get_products_sales(self, **kwargs):
        if not self._authenticate():
            return self._make_error_response('Acceso no autorizado: Token invalido o ausente en las cabeceras.', {}, status=401)
        filters = self._get_request_filters()

        try:
            report_data = request.env['advanced_metrics.report.wizard'].sudo().get_products_sales_report_data(filters)
            return self._make_success_response('Ventas por producto obtenidas correctamente.', report_data)
        except ValidationError as error:
            return self._make_error_response(error.args[0], filters, status=400)
        except Exception:
            return self._make_error_response('No fue posible obtener las ventas por producto.', filters)

    @http.route('/api/bi/inventory-intelligent/sales-trend', type='http', auth='public', methods=['POST'], csrf=False)
    def get_sales_trend(self, **kwargs):
        if not self._authenticate():
            return self._make_error_response('Acceso no autorizado: Token invalido o ausente en las cabeceras.', {}, status=401)
        filters = self._get_request_filters()

        try:
            report_data = request.env['advanced_metrics.report.wizard'].sudo().get_sales_trend_report_data(filters)
            return self._make_success_response(
                'Tendencia de ventas obtenida correctamente.',
                report_data,
                extra_keys=['periodSummary'],
            )
        except ValidationError as error:
            return self._make_error_response(error.args[0], filters, status=400, extra_payload={'periodSummary': {}})
        except Exception:
            return self._make_error_response(
                'No fue posible obtener la tendencia de ventas.',
                filters,
                extra_payload={'periodSummary': {}},
            )

    @http.route('/api/bi/inventory-intelligent/dead-products', type='http', auth='public', methods=['POST'], csrf=False)
    def get_dead_products(self, **kwargs):
        if not self._authenticate():
            return self._make_error_response('Acceso no autorizado: Token invalido o ausente en las cabeceras.', {}, status=401)
        filters = self._get_request_filters()

        try:
            report_data = request.env['advanced_metrics.report.wizard'].sudo().get_dead_products_report_data(filters)
            return self._make_success_response('Productos sin movimiento obtenidos correctamente.', report_data)
        except ValidationError as error:
            return self._make_error_response(error.args[0], filters, status=400)
        except Exception:
            return self._make_error_response('No fue posible obtener los productos sin movimiento.', filters)

    @http.route('/api/bi/inventory-intelligent/high-rotation-products', type='http', auth='public', methods=['POST'], csrf=False)
    def get_high_rotation_products(self, **kwargs):
        if not self._authenticate():
            return self._make_error_response('Acceso no autorizado: Token invalido o ausente en las cabeceras.', {}, status=401)
        filters = self._get_request_filters()

        try:
            report_data = request.env['advanced_metrics.report.wizard'].sudo().get_high_rotation_products_report_data(filters)
            return self._make_success_response('Productos con alta rotación obtenidos correctamente.', report_data)
        except ValidationError as error:
            return self._make_error_response(error.args[0], filters, status=400)
        except Exception:
            return self._make_error_response('No fue posible obtener los productos con alta rotación.', filters)
