# -*- coding: utf-8 -*-
import io
import json
from collections import OrderedDict
from datetime import datetime
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

    def _generate_xlsx_response(self, rows, filters):
        """Orquestador de la generacion de archivos Excel (.xlsx)."""
        if not XLSXWRITER_AVAILABLE:
            return request.make_json_response({'success': False, 'message': 'xlsxwriter no instalado'}, status=500)

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
