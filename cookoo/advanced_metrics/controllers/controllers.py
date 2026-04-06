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
        payload = self._get_json_payload()
        filters = payload.get('filters') or payload

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

