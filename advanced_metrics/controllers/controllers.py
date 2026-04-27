# -*- coding: utf-8 -*-
import io
import json
from collections import OrderedDict
from datetime import datetime
from html import escape as html_escape
from odoo import http
from odoo.http import request

# Intentamos importar xlsxwriter para exportacion Excel
try:
    import xlsxwriter
    XLSXWRITER_AVAILABLE = True
except ImportError:
    XLSXWRITER_AVAILABLE = False

class AdvancedMetricsController(http.Controller):
    """
    Controlador principal para el Reporte de Planificacion Semanal.
    Maneja la visualizacion web (JSON) y la exportacion profesional (Excel).
    """

    @staticmethod
    def _get_json_payload():
        """Extrae de forma segura el cuerpo JSON de la peticion HTTP."""
        payload = {}
        raw_body = request.httprequest.data
        if raw_body:
            try:
                payload = json.loads(raw_body.decode('utf-8'))
            except (ValueError, UnicodeDecodeError):
                payload = {}
        return payload if isinstance(payload, dict) else {}

    @http.route('/advanced_metrics/report/next-week-dates', type='json', auth='user', methods=['POST'], csrf=False)
    def get_next_week_dates(self, **kwargs):
        """
        Calcula las fechas de la semana siguiente (Lunes a Domingo) 
        usando la logica centralizada en el servidor (Python).
        """
        return request.env['advanced_metrics.report.wizard'].sudo().get_next_week_dates()

    @http.route('/advanced_metrics/report/period-dates', type='json', auth='user', methods=['POST'], csrf=False)
    def get_period_dates(self, **kwargs):
        """Retorna el rango de fechas para semana o mes actual."""
        payload = self._get_json_payload()
        params = payload.get('params') or {}
        period_type = params.get('period_type') or kwargs.get('period_type') or 'week'
        return request.env['advanced_metrics.report.wizard'].sudo().get_period_dates(period_type)

    @http.route('/advanced_metrics/report/generate', type='http', auth='user', methods=['POST'], csrf=False)
    def generate_sales_orders_report(self, **kwargs):
        """
        Punto de entrada para generar el reporte.
        Soporta respuesta JSON para la tabla web y respuesta Binaria para Excel.
        """
        payload = self._get_json_payload()
        filters = payload.get('filters') or {}
        export_xls = payload.get('export_xls', False)
        
        # Obtenemos las filas con la logica FIFO ya aplicada desde el wizard
        rows = request.env['advanced_metrics.report.wizard'].sudo().get_sales_orders_report_rows(filters)
        
        if export_xls:
            return self._generate_xlsx_response(rows, filters)

        return request.make_json_response({
            'success': True,
            'message': f'Se encontraron {len(rows)} resultados.',
            'rows': rows,
            'count': len(rows),
        })

    @http.route('/advanced_metrics/report/export_excel/<int:wizard_id>', type='http', auth='user')
    def export_current_report_excel(self, wizard_id, **kwargs):
        wizard = request.env['advanced_metrics.report.wizard'].sudo().browse(wizard_id).exists()
        if not wizard:
            return request.not_found()

        document = self._build_excel_html_document(wizard)
        filename = f"planificacion_zoraen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xls"
        return request.make_response(document.encode('utf-8'), headers=[
            ('Content-Type', 'application/vnd.ms-excel; charset=utf-8'),
            ('Content-Disposition', f'attachment; filename="{filename}"'),
        ])

    def _build_excel_html_document(self, wizard):
        range_label = html_escape(wizard.report_date_range_label or '')
        report_html = wizard.report_html or '<div>No hay datos para exportar.</div>'
        return f"""<!DOCTYPE html>
<html xmlns:o="urn:schemas-microsoft-com:office:office"
      xmlns:x="urn:schemas-microsoft-com:office:excel"
      xmlns="http://www.w3.org/TR/REC-html40">
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <meta name="ProgId" content="Excel.Sheet" />
    <meta name="Generator" content="Odoo Advanced Metrics" />
    <style>
        body {{
            font-family: Calibri, Arial, sans-serif;
            color: #1f2937;
            margin: 24px;
        }}
        .zrn_am_export_title {{
            font-size: 22px;
            font-weight: 700;
            margin-bottom: 6px;
        }}
        .zrn_am_export_subtitle {{
            font-size: 13px;
            margin-bottom: 18px;
        }}
        .zrn_am_report_matrix_wrap {{
            overflow: visible !important;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
        }}
        th, td {{
            border: 1px solid #d7d8ea;
            padding: 8px 10px;
            vertical-align: middle;
        }}
        thead th {{
            background: #857194;
            color: #ffffff;
            text-align: center;
            font-weight: 700;
        }}
        .zrn_am_sticky_col,
        .zrn_am_sticky_col_2,
        .zrn_am_sticky_col_3 {{
            background: #857194;
            color: #ffffff;
            font-weight: 700;
        }}
        .zrn_am_num {{
            text-align: right;
            mso-number-format: "0.00";
        }}
        .zrn_am_day_total,
        .zrn_am_day_total_head,
        .zrn_am_day_total_subhead {{
            background: #d9cdea;
            font-weight: 700;
        }}
        .zrn_am_week_total,
        .zrn_am_week_total_head,
        .zrn_am_week_total_title,
        .zrn_am_week_total_subhead {{
            background: #d8e8d6;
            font-weight: 700;
        }}
        .zrn_am_month_total,
        .zrn_am_month_total_head,
        .zrn_am_month_total_title,
        .zrn_am_month_total_subhead {{
            background: #c7dbf5;
            font-weight: 700;
        }}
        .zrn_am_product_name {{
            min-width: 220px;
        }}
        .zrn_am_day_heading {{
            display: block;
            font-weight: 700;
        }}
        .zrn_am_day_heading_date {{
            display: block;
            font-size: 12px;
            margin-top: 4px;
        }}
    </style>
</head>
<body>
    <div class="zrn_am_export_title">Detalle operativo</div>
    <div class="zrn_am_export_subtitle">{range_label}</div>
    {report_html}
</body>
</html>"""

    def _generate_xlsx_response(self, rows, filters):
        """Orquestador de la generacion de archivos Excel (.xlsx)."""
        if not XLSXWRITER_AVAILABLE:
            wizard = request.env['advanced_metrics.report.wizard'].sudo().create({})
            wizard._load_report_payload(rows)
            document = self._build_excel_html_document(wizard)
            filename = f"planificacion_zoraen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xls"
            return request.make_response(document.encode('utf-8'), headers=[
                ('Content-Type', 'application/vnd.ms-excel; charset=utf-8'),
                ('Content-Disposition', f'attachment; filename="{filename}"'),
            ])

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Generamos estilos compartidos
        styles = self._create_xlsx_styles(workbook)
        
        # Hoja 1: Detalle operativo con subtotales amarillos
        self._write_detail_sheet(workbook, styles, rows, filters)
        
        # Hoja 2: Resumen ejecutivo por SKU
        self._write_product_summary_sheet(workbook, styles, rows)
        
        workbook.close()
        output.seek(0)
        
        filename = f"planificacion_zoraen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return request.make_response(output.getvalue(), headers=[
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Disposition', f"attachment; filename={filename}")
        ])

    def _create_xlsx_styles(self, workbook):
        """Define la identidad visual del reporte Excel."""
        return {
            'header': workbook.add_format({'bold': True, 'bg_color': '#714B67', 'font_color': 'white', 'border': 1, 'align': 'center'}),
            'text': workbook.add_format({'border': 1}),
            'text_alt': workbook.add_format({'border': 1, 'bg_color': '#F8F9FA'}),
            'number': workbook.add_format({'border': 1, 'num_format': '#,##0.00'}),
            'number_alt': workbook.add_format({'border': 1, 'num_format': '#,##0.00', 'bg_color': '#F8F9FA'}),
            'subtotal_text': workbook.add_format({'bold': True, 'bg_color': '#FFF2CC', 'border': 1, 'font_color': '#7F6000'}),
            'subtotal_number': workbook.add_format({'bold': True, 'bg_color': '#FFF2CC', 'border': 1, 'num_format': '#,##0.00', 'font_color': '#7F6000'}),
            'total_label': workbook.add_format({'bold': True, 'bg_color': '#714B67', 'font_color': 'white', 'border': 1}),
        }

    def _write_detail_sheet(self, workbook, styles, rows, filters):
        """Escribe la hoja de detalle con logica de agrupacion por dia."""
        ws = workbook.add_worksheet('Planificacion Detallada')
        headers = ['Fecha Entrega', 'Dia Semana', 'Nombre Cliente', 'Orden Venta', 'Producto / Combo', 'Cant. Vendida', 'Stock Disponible', 'Stock Libre', 'Sugerido Producir']
        for i, h in enumerate(headers): ws.write(0, i, h, styles['header'])
        ws.set_column('A:I', 20)

        current_row, current_date, current_day = 1, None, ""
        day_totals = {'v': 0.0, 's': 0.0}
        
        for r in rows:
            # Detectamos cambio de dia para insertar fila de subtotal
            if current_date and r['fecha_entrega'] != current_date:
                self._write_day_subtotal(ws, styles, current_row, current_date, current_day, day_totals)
                current_row += 1
                day_totals = {'v': 0.0, 's': 0.0}
            
            current_date, current_day = r['fecha_entrega'], r['dia_semana']
            is_alt = current_row % 2 == 0
            fmt = styles['text_alt'] if is_alt else styles['text']
            num_fmt = styles['number_alt'] if is_alt else styles['number']
            
            ws.write(current_row, 0, r['fecha_entrega'], fmt)
            ws.write(current_row, 1, r['dia_semana'], fmt)
            ws.write(current_row, 2, r['cliente'], fmt)
            ws.write(current_row, 3, r['numero_orden_venta'], fmt)
            ws.write(current_row, 4, r['producto'], fmt)
            ws.write_number(current_row, 5, r['cantidad_vendida'], num_fmt)
            ws.write_number(current_row, 6, r['inventario_disponible'], num_fmt)
            ws.write_number(current_row, 7, r.get('inventario_libre_usar', 0.0), num_fmt)
            ws.write_number(current_row, 8, r['cantidad_sugerida_producir'], num_fmt)
            
            day_totals['v'] += r['cantidad_vendida']
            day_totals['s'] += r['cantidad_sugerida_producir']
            current_row += 1
            
        # Al terminar el bucle, escribimos el ultimo subtotal pendiente
        if current_date:
            self._write_day_subtotal(ws, styles, current_row, current_date, current_day, day_totals)

    def _write_day_subtotal(self, ws, styles, row, date, day, totals):
        """Escribe una fila resumen de dia con fondo amarillo."""
        ws.write(row, 0, f"TOTAL {day.upper()}", styles['subtotal_text'])
        ws.write(row, 1, date, styles['subtotal_text'])
        for i in range(2, 5): ws.write(row, i, "", styles['subtotal_text'])
        ws.write_number(row, 5, totals['v'], styles['subtotal_number'])
        ws.write(row, 6, "---", styles['subtotal_text'])
        ws.write(row, 7, "---", styles['subtotal_text'])
        ws.write_number(row, 8, totals['s'], styles['subtotal_number'])

    def _write_product_summary_sheet(self, workbook, styles, rows):
        """Escribe la hoja resumen consolidada por producto."""
        ws = workbook.add_worksheet('Resumen por Producto')
        summary = OrderedDict()
        for r in rows:
            p = r['producto']
            if p not in summary:
                summary[p] = {
                    'v': 0.0,
                    's': 0.0,
                    'i': r['inventario_disponible'],
                    'f': r.get('inventario_libre_usar', 0.0),
                }
            summary[p]['v'] += r['cantidad_vendida']
            summary[p]['s'] += r['cantidad_sugerida_producir']
        
        headers = ["Producto / Combo", "Vendido Total", "Stock Snapshot", "Stock Libre Snapshot", "Total Sugerido a Fabricar"]
        for i, h in enumerate(headers): ws.write(0, i, h, styles['header'])
        ws.set_column('A:A', 40); ws.set_column('B:E', 18)
        
        row = 1
        for p, t in summary.items():
            ws.write(row, 0, p, styles['text'])
            ws.write_number(row, 1, t['v'], styles['number'])
            ws.write_number(row, 2, t['i'], styles['number'])
            ws.write_number(row, 3, t['f'], styles['number'])
            ws.write_number(row, 4, t['s'], styles['number'])
            row += 1
