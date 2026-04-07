# -*- coding: utf-8 -*-
import json

from odoo import http
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
