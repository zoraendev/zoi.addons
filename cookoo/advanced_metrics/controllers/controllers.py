# -*- coding: utf-8 -*-
import json

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request


class AdvancedMetricsController(http.Controller):
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

        for key in ('dateFrom', 'dateTo', 'warehouseId', 'categoryId', 'limit', 'groupBy', 'daysWithoutMovement'):
            value = request.httprequest.args.get(key)
            if value not in (None, ''):
                filters[key] = value

        return filters

    @http.route('/advanced_metrics/report/generate', type='http', auth='user', methods=['POST'], csrf=False)
    def generate_sales_orders_report(self, **kwargs):
        payload = self._get_json_payload()
        filters = payload.get('filters') or {}
        rows = request.env['advanced_metrics.report.wizard'].sudo().get_sales_orders_report_rows(filters)
        total_rows = len(rows)

        return request.make_json_response({
            'success': True,
            'message': (
                f'Se encontraron {total_rows} resultados.'
                if total_rows
                else 'No se encontraron resultados con los filtros seleccionados.'
            ),
            'rows': rows,
            'count': total_rows,
        })

    @http.route('/api/bi/inventory-intelligent/top-products', type='http', auth='public', methods=['POST'], csrf=False)
    def get_top_products(self, **kwargs):
        filters = self._get_request_filters()

        try:
            report_data = request.env['advanced_metrics.report.wizard'].sudo().get_top_products_report_data(filters)
            return request.make_json_response({
                'success': True,
                'message': 'Top productos obtenido correctamente.',
                'generatedAt': report_data['generatedAt'],
                'filters': report_data['filters'],
                'data': report_data['data'],
            })
        except ValidationError as error:
            return request.make_json_response({
                'success': False,
                'message': error.args[0],
                'generatedAt': None,
                'filters': filters or {},
                'data': [],
            }, status=400)
        except Exception:
            return request.make_json_response({
                'success': False,
                'message': 'No fue posible obtener el top de productos.',
                'generatedAt': None,
                'filters': filters or {},
                'data': [],
            }, status=500)

    @http.route('/api/bi/inventory-intelligent/products-sales', type='http', auth='public', methods=['POST'], csrf=False)
    def get_products_sales(self, **kwargs):
        filters = self._get_request_filters()

        try:
            report_data = request.env['advanced_metrics.report.wizard'].sudo().get_products_sales_report_data(filters)
            return request.make_json_response({
                'success': True,
                'message': 'Ventas por producto obtenidas correctamente.',
                'generatedAt': report_data['generatedAt'],
                'filters': report_data['filters'],
                'data': report_data['data'],
            })
        except ValidationError as error:
            return request.make_json_response({
                'success': False,
                'message': error.args[0],
                'generatedAt': None,
                'filters': filters or {},
                'data': [],
            }, status=400)
        except Exception:
            return request.make_json_response({
                'success': False,
                'message': 'No fue posible obtener las ventas por producto.',
                'generatedAt': None,
                'filters': filters or {},
                'data': [],
            }, status=500)

    @http.route('/api/bi/inventory-intelligent/sales-trend', type='http', auth='public', methods=['POST'], csrf=False)
    def get_sales_trend(self, **kwargs):
        filters = self._get_request_filters()

        try:
            report_data = request.env['advanced_metrics.report.wizard'].sudo().get_sales_trend_report_data(filters)
            return request.make_json_response({
                'success': True,
                'message': 'Tendencia de ventas obtenida correctamente.',
                'generatedAt': report_data['generatedAt'],
                'filters': report_data['filters'],
                'data': report_data['data'],
                'periodSummary': report_data['periodSummary'],
            })
        except ValidationError as error:
            return request.make_json_response({
                'success': False,
                'message': error.args[0],
                'generatedAt': None,
                'filters': filters or {},
                'data': [],
                'periodSummary': {},
            }, status=400)
        except Exception:
            return request.make_json_response({
                'success': False,
                'message': 'No fue posible obtener la tendencia de ventas.',
                'generatedAt': None,
                'filters': filters or {},
                'data': [],
                'periodSummary': {},
            }, status=500)

    @http.route('/api/bi/inventory-intelligent/dead-products', type='http', auth='public', methods=['POST'], csrf=False)
    def get_dead_products(self, **kwargs):
        filters = self._get_request_filters()

        try:
            report_data = request.env['advanced_metrics.report.wizard'].sudo().get_dead_products_report_data(filters)
            return request.make_json_response({
                'success': True,
                'message': 'Productos sin movimiento obtenidos correctamente.',
                'generatedAt': report_data['generatedAt'],
                'filters': report_data['filters'],
                'data': report_data['data'],
            })
        except ValidationError as error:
            return request.make_json_response({
                'success': False,
                'message': error.args[0],
                'generatedAt': None,
                'filters': filters or {},
                'data': [],
            }, status=400)
        except Exception:
            return request.make_json_response({
                'success': False,
                'message': 'No fue posible obtener los productos sin movimiento.',
                'generatedAt': None,
                'filters': filters or {},
                'data': [],
            }, status=500)

