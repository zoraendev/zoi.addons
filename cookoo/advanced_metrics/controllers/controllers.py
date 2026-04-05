# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime
from io import BytesIO

import xlwt

from odoo import http
from odoo.http import content_disposition, request

_logger = logging.getLogger(__name__)


class AdvancedMetricsController(http.Controller):
    def _load_json_payload(self):
        payload = {}
        raw_body = request.httprequest.data
        if raw_body:
            try:
                payload = json.loads(raw_body.decode('utf-8'))
            except (ValueError, UnicodeDecodeError):
                payload = {}
        return payload

    def _build_sales_orders_xls(self, rows):
        workbook = xlwt.Workbook(encoding='utf-8')
        sheet = workbook.add_sheet('Ordenes de Venta')

        header_style = xlwt.easyxf(
            'font: bold on, colour white;'
            'pattern: pattern solid, fore_colour ocean_blue;'
            'align: horiz center, vert center;'
            'borders: left thin, right thin, top thin, bottom thin;'
        )
        text_style = xlwt.easyxf(
            'align: vert center;'
            'borders: left thin, right thin, top thin, bottom thin;'
        )
        number_style = xlwt.easyxf(
            'align: horiz right, vert center;'
            'borders: left thin, right thin, top thin, bottom thin;',
            num_format_str='#,##0.00',
        )

        headers = [
            'Fecha de entrega',
            'Cliente',
            'Numero de orden de venta',
            'Producto',
            'Cantidad vendida',
            'Inventario disponible de producto terminado',
            'Cantidad sugerida a producir',
        ]
        widths = [5500, 9000, 8000, 9000, 5000, 8000, 6500]

        for col_index, header in enumerate(headers):
            sheet.write(0, col_index, header, header_style)
            sheet.col(col_index).width = widths[col_index]

        for row_index, row in enumerate(rows, start=1):
            sheet.write(row_index, 0, row.get('fecha_entrega') or '', text_style)
            sheet.write(row_index, 1, row.get('cliente') or '', text_style)
            sheet.write(row_index, 2, row.get('numero_orden_venta') or '', text_style)
            sheet.write(row_index, 3, row.get('producto') or '', text_style)
            sheet.write(row_index, 4, float(row.get('cantidad_vendida') or 0), number_style)
            sheet.write(row_index, 5, float(row.get('inventario_disponible') or 0), number_style)
            sheet.write(row_index, 6, float(row.get('cantidad_sugerida_producir') or 0), number_style)

        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        return output.getvalue()

    def _make_error_response(self, message, status=500):
        return request.make_json_response(
            {
                'success': False,
                'message': message,
                'rows': [],
                'count': 0,
            },
            status=status,
        )

    @http.route('/advanced_metrics/report/generate', type='http', auth='user', methods=['POST'], csrf=False)
    def generate_sales_orders_report(self, **kwargs):
        payload = self._load_json_payload()
        filters = payload.get('filters') or {}
        export_xls = bool(payload.get('export_xls'))

        try:
            rows = request.env['advanced_metrics.report.wizard'].sudo().get_sales_orders_report_rows(filters)
        except Exception:
            _logger.exception('Advanced Metrics report generation failed.')
            return self._make_error_response(
                'No fue posible generar el archivo Excel.' if export_xls else 'No fue posible generar el reporte.',
                status=500,
            )

        total_rows = len(rows)
        if export_xls:
            file_content = self._build_sales_orders_xls(rows)
            filename = f"reporte_ordenes_venta_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xls"
            return request.make_response(
                file_content,
                headers=[
                    ('Content-Type', 'application/vnd.ms-excel'),
                    ('Content-Disposition', content_disposition(filename)),
                ],
            )

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

    @http.route('/api/advanced_metrics/sales_inventory', type='http', auth='public', methods=['GET'], csrf=False)
    def get_sales_inventory_api(self, token=None, **kwargs):
        if not token:
            return request.make_response(json.dumps({'error': 'Unauthorized: Token is missing'}), headers=[('Content-Type', 'application/json')], status=401)

        config = request.env['advanced_metrics.api.config'].sudo().search([('access_token', '=', token)], limit=1)
        if not config:
            return request.make_response(json.dumps({'error': 'Unauthorized: Invalid token'}), headers=[('Content-Type', 'application/json')], status=401)

        limit = config.record_limit or 5000
        try:
            rows = request.env['advanced_metrics.report.wizard'].sudo().get_sales_orders_report_rows(filters={}, limit=limit)
            return request.make_response(json.dumps({'data': rows}), headers=[('Content-Type', 'application/json')])
        except Exception as e:
            return request.make_response(json.dumps({'error': f'Internal Error: {str(e)}'}), headers=[('Content-Type', 'application/json')], status=500)


