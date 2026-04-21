from calendar import monthrange
from collections import OrderedDict
from datetime import datetime, timedelta

from markupsafe import escape

from odoo import api, fields, models


class AdvancedMetricsReportWizard(models.TransientModel):
    _name = 'advanced_metrics.report.wizard'
    _description = 'Asistente de reporte de ventas e inventario'
    _rec_name = 'name'

    SALE_ORDER_STATE_SELECTION = [
        ('draft', 'Presupuesto'),
        ('sent', 'Presupuesto enviado'),
        ('sale', 'Pedido de venta'),
        ('done', 'Bloqueado'),
        ('cancel', 'Cancelado'),
    ]

    name = fields.Char(string='Titulo', default='Ordenes de venta')
    fecha_entrega_desde = fields.Date(string='Fecha de entrega desde')
    fecha_entrega_hasta = fields.Date(string='Fecha de entrega hasta')
    sale_order_state = fields.Selection(
        selection=SALE_ORDER_STATE_SELECTION,
        string='Estado de OV',
    )
    cliente_ids = fields.Many2many(
        'res.partner',
        string='Clientes',
    )
    product_ids = fields.Many2many(
        'product.product',
        string='Productos',
    )
    available_cliente_ids = fields.Many2many(
        'res.partner',
        string='Clientes disponibles',
        compute='_compute_review_data',
        readonly=True,
    )
    available_product_ids = fields.Many2many(
        'product.product',
        string='Productos disponibles',
        compute='_compute_review_data',
        readonly=True,
    )
    preview_cliente_ids = fields.Many2many(
        'res.partner',
        string='Clientes a revisar',
        compute='_compute_review_data',
        readonly=True,
    )
    preview_product_ids = fields.Many2many(
        'product.product',
        string='Productos a revisar',
        compute='_compute_review_data',
        readonly=True,
    )
    preview_cliente_count = fields.Integer(
        string='Cantidad de clientes',
        compute='_compute_review_data',
        readonly=True,
    )
    preview_product_count = fields.Integer(
        string='Cantidad de productos',
        compute='_compute_review_data',
        readonly=True,
    )
    selected_cliente_line_ids = fields.One2many(
        'advanced_metrics.report.wizard.client.line',
        'wizard_id',
        string='Clientes seleccionados',
    )
    selected_product_line_ids = fields.One2many(
        'advanced_metrics.report.wizard.product.line',
        'wizard_id',
        string='Productos seleccionados',
    )
    report_line_ids = fields.One2many(
        'advanced_metrics.report.wizard.line',
        'wizard_id',
        string='Lineas de reporte',
    )
    report_html = fields.Html(
        string='Detalle del reporte',
        sanitize=False,
        readonly=True,
    )
    production_html = fields.Html(
        string='Resumen para fabricar',
        sanitize=False,
        readonly=True,
    )
    report_ready = fields.Boolean(string='Reporte listo', default=False)
    report_row_count = fields.Integer(string='Lineas del reporte', readonly=True)
    report_order_count = fields.Integer(string='Ordenes consideradas', readonly=True)
    report_customer_count = fields.Integer(string='Clientes en reporte', readonly=True)
    report_product_count = fields.Integer(string='Productos en reporte', readonly=True)
    report_date_range_label = fields.Char(string='Rango consultado', readonly=True)

    @api.model
    def _coerce_to_date(self, value):
        if not value:
            return False
        if isinstance(value, str):
            return fields.Date.from_string(value)
        if hasattr(value, 'date'):
            return value.date()
        return value

    def _get_effective_line_date(self, line):
        effective_date = line.order_id.commitment_date or line.order_id.date_order
        return self._coerce_to_date(effective_date)

    @api.model
    def _line_matches_filter_dates(self, line, fecha_desde=False, fecha_hasta=False):
        effective_date = self._get_effective_line_date(line)
        if not effective_date:
            return False
        if fecha_desde and effective_date < fecha_desde:
            return False
        if fecha_hasta and effective_date > fecha_hasta:
            return False
        return True

    def _line_matches_date_range(self, line):
        self.ensure_one()
        return self._line_matches_filter_dates(
            line,
            fecha_desde=self.fecha_entrega_desde,
            fecha_hasta=self.fecha_entrega_hasta,
        )

    def _get_report_filters(self):
        self.ensure_one()
        return {
            'fecha_entrega_desde': fields.Date.to_string(self.fecha_entrega_desde) if self.fecha_entrega_desde else False,
            'fecha_entrega_hasta': fields.Date.to_string(self.fecha_entrega_hasta) if self.fecha_entrega_hasta else False,
            'sale_order_state': self.sale_order_state or False,
            'cliente_ids': self.cliente_ids.ids,
            'product_ids': self.product_ids.ids,
        }

    @api.model
    def _search_sale_lines_from_filters(self, filters=None, limit=None):
        filters = filters or {}
        if 'sale.order.line' not in self.env:
            return self.env['sale.order.line']

        fecha_desde = self._coerce_to_date(filters.get('fecha_entrega_desde'))
        fecha_hasta = self._coerce_to_date(filters.get('fecha_entrega_hasta'))
        cliente_ids = filters.get('cliente_ids') or []
        product_ids = filters.get('product_ids') or []
        cliente_id = filters.get('cliente_id')
        cliente_nombre = (filters.get('cliente_nombre') or '').strip()
        sale_order_state = (filters.get('sale_order_state') or '').strip()

        normalized_cliente_ids = []
        for partner_id in cliente_ids:
            try:
                normalized_cliente_ids.append(int(partner_id))
            except (TypeError, ValueError):
                continue

        normalized_product_ids = []
        for product_id in product_ids:
            try:
                normalized_product_ids.append(int(product_id))
            except (TypeError, ValueError):
                continue

        domain = [
            ('order_id.state', 'in', ['draft', 'sent', 'sale', 'done']),
            ('display_type', '=', False),
            ('product_id', '!=', False),
        ]

        if sale_order_state:
            domain[0] = ('order_id.state', '=', sale_order_state)

        if normalized_cliente_ids:
            domain.append(('order_partner_id.commercial_partner_id', 'in', normalized_cliente_ids))
        elif cliente_id:
            domain.append(('order_partner_id.commercial_partner_id', '=', int(cliente_id)))
        elif cliente_nombre:
            domain.append(('order_partner_id.commercial_partner_id.name', 'ilike', cliente_nombre))

        if normalized_product_ids:
            domain.append(('product_id', 'in', normalized_product_ids))

        sale_lines = self.env['sale.order.line'].search(domain, order='id asc')

        if fecha_desde or fecha_hasta:
            sale_lines = sale_lines.filtered(
                lambda line: self._line_matches_filter_dates(
                    line,
                    fecha_desde=fecha_desde,
                    fecha_hasta=fecha_hasta,
                )
            )

        safe_limit = min(limit or 10000, 10000)
        return sale_lines[:safe_limit]

    def _get_candidate_sale_lines(self):
        self.ensure_one()
        return self._search_sale_lines_from_filters(self._get_report_filters())

    def _sync_selected_review_lines(self, candidate_lines=None):
        ClientLine = self.env['advanced_metrics.report.wizard.client.line']
        ProductLine = self.env['advanced_metrics.report.wizard.product.line']
        StockQuant = self.env['stock.quant'] if 'stock.quant' in self.env else False

        for wizard in self:
            lines = candidate_lines if candidate_lines is not None else wizard._get_candidate_sale_lines()
            wizard.selected_cliente_line_ids.unlink()
            wizard.selected_product_line_ids.unlink()

            client_values = []
            for partner in wizard.cliente_ids:
                partner_lines = lines.filtered(
                    lambda line: line.order_partner_id.commercial_partner_id == partner
                )
                order_count = len(partner_lines.mapped('order_id'))
                total_units = sum(partner_lines.mapped('product_uom_qty'))
                client_values.append({
                    'wizard_id': wizard.id,
                    'partner_id': partner.id,
                    'city': partner.city or '',
                    'email': partner.email or '',
                    'order_count': order_count,
                    'total_units': total_units,
                })
            if client_values:
                ClientLine.create(client_values)

            product_values = []
            product_ids = wizard.product_ids.ids
            stock_data = {}
            if product_ids and StockQuant:
                grouped_quants = StockQuant.read_group(
                    [('product_id', 'in', product_ids), ('location_id.usage', '=', 'internal')],
                    ['product_id', 'available_quantity:sum', 'quantity:sum'],
                    ['product_id'],
                )
                stock_data = {
                    item['product_id'][0]: {
                        'stock_real': item.get('quantity', 0.0),
                        'stock_libre': item.get('available_quantity', 0.0),
                    }
                    for item in grouped_quants
                    if item.get('product_id')
                }

            for product in wizard.product_ids:
                product_lines = lines.filtered(lambda line: line.product_id == product)
                order_count = len(product_lines.mapped('order_id'))
                demanded_qty = sum(product_lines.mapped('product_uom_qty'))
                stock_info = stock_data.get(product.id, {})
                product_values.append({
                    'wizard_id': wizard.id,
                    'product_id': product.id,
                    'default_code': product.default_code or '',
                    'categ_name': product.categ_id.display_name or '',
                    'order_count': order_count,
                    'demanded_qty': demanded_qty,
                    'stock_real': stock_info.get('stock_real', 0.0),
                    'stock_libre': stock_info.get('stock_libre', 0.0),
                })
            if product_values:
                ProductLine.create(product_values)

    @api.depends('fecha_entrega_desde', 'fecha_entrega_hasta', 'sale_order_state', 'cliente_ids', 'product_ids')
    def _compute_review_data(self):
        for wizard in self:
            base_filters = {
                'fecha_entrega_desde': fields.Date.to_string(wizard.fecha_entrega_desde) if wizard.fecha_entrega_desde else False,
                'fecha_entrega_hasta': fields.Date.to_string(wizard.fecha_entrega_hasta) if wizard.fecha_entrega_hasta else False,
                'sale_order_state': wizard.sale_order_state or False,
            }
            available_lines = wizard._search_sale_lines_from_filters(base_filters)
            candidate_lines = wizard._get_candidate_sale_lines()

            available_client_ids = available_lines.mapped('order_partner_id.commercial_partner_id').ids
            available_product_ids = available_lines.mapped('product_id').ids

            preview_lines = candidate_lines
            if wizard.cliente_ids:
                preview_lines = preview_lines.filtered(
                    lambda line: line.order_partner_id.commercial_partner_id in wizard.cliente_ids
                )
            if wizard.product_ids:
                preview_lines = preview_lines.filtered(
                    lambda line: line.product_id in wizard.product_ids
                )

            preview_client_ids = preview_lines.mapped('order_partner_id.commercial_partner_id').ids
            preview_product_ids = preview_lines.mapped('product_id').ids

            wizard.available_cliente_ids = [(6, 0, available_client_ids)]
            wizard.available_product_ids = [(6, 0, available_product_ids)]
            wizard.preview_cliente_ids = [(6, 0, preview_client_ids)]
            wizard.preview_product_ids = [(6, 0, preview_product_ids)]
            wizard.preview_cliente_count = len(preview_client_ids)
            wizard.preview_product_count = len(preview_product_ids)

    @api.onchange('fecha_entrega_desde', 'fecha_entrega_hasta', 'sale_order_state', 'cliente_ids', 'product_ids')
    def _onchange_filters_refresh_review_data(self):
        self._reset_report_payload()
        self._compute_review_data()

    def _reset_report_payload(self):
        for wizard in self:
            if wizard.id:
                wizard.report_line_ids.unlink()
            wizard.report_html = False
            wizard.production_html = False
            wizard.report_ready = False
            wizard.report_row_count = 0
            wizard.report_order_count = 0
            wizard.report_customer_count = 0
            wizard.report_product_count = 0
            wizard.report_date_range_label = False

    def _get_effective_report_date_range(self, rows):
        self.ensure_one()

        row_dates = []
        for row in rows or []:
            fecha_value = self._coerce_to_date(row.get('fecha_entrega'))
            if fecha_value:
                row_dates.append(fecha_value)

        if row_dates:
            return min(row_dates), max(row_dates)

        return self.fecha_entrega_desde, self.fecha_entrega_hasta

    def _format_report_date_range_label(self, rows):
        self.ensure_one()
        date_from, date_to = self._get_effective_report_date_range(rows)

        if date_from and date_to:
            return f'Rango consultado: {date_from.strftime("%d/%m/%Y")} al {date_to.strftime("%d/%m/%Y")}'
        if date_from:
            return f'Rango consultado: desde {date_from.strftime("%d/%m/%Y")}'
        if date_to:
            return f'Rango consultado: hasta {date_to.strftime("%d/%m/%Y")}'
        return 'Rango consultado: todas las fechas disponibles'

    def action_clear_filters(self):
        self.ensure_one()
        self.write({
            'fecha_entrega_desde': False,
            'fecha_entrega_hasta': False,
            'sale_order_state': False,
            'cliente_ids': [(5, 0, 0)],
            'product_ids': [(5, 0, 0)],
        })
        self._reset_report_payload()
        self._compute_review_data()
        filter_view = self.env.ref('advanced_metrics.view_advanced_metrics_report_wizard_form')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Ordenes de venta',
            'res_model': 'advanced_metrics.report.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': filter_view.id,
            'views': [(filter_view.id, 'form')],
            'target': 'current',
            '_noBreadcrumbs': True,
        }

    def _format_report_number(self, value):
        value = float(value or 0.0)
        if value.is_integer():
            return f'{int(value):,}'
        return f'{value:,.2f}'

    def _format_report_day_label(self, day_name, fecha_entrega=False):
        if not fecha_entrega:
            return escape(day_name or '')

        fecha_value = self._coerce_to_date(fecha_entrega)
        if not fecha_value:
            return escape(day_name or '')

        return (
            f'<span class="zrn_am_day_heading">{escape(day_name or "")}</span>'
            f'<span class="zrn_am_day_heading_date">{escape(fecha_value.strftime("%d/%m/%Y"))}</span>'
        )

    def _get_report_week_group_key(self, fecha_entrega=False):
        fecha_value = self._coerce_to_date(fecha_entrega)
        if not fecha_value:
            return False

        week_of_month = ((fecha_value.day - 1) // 7) + 1
        return (fecha_value.year, fecha_value.month, week_of_month)

    def _format_report_week_label(self, week_key):
        if not week_key:
            return 'Semana'

        year, month, week_of_month = week_key
        month_names = {
            1: 'Enero',
            2: 'Febrero',
            3: 'Marzo',
            4: 'Abril',
            5: 'Mayo',
            6: 'Junio',
            7: 'Julio',
            8: 'Agosto',
            9: 'Septiembre',
            10: 'Octubre',
            11: 'Noviembre',
            12: 'Diciembre',
        }
        return f'Semana {week_of_month} {month_names.get(month, "")} {year}'.strip()

    def _get_report_month_group_key(self, fecha_entrega=False):
        fecha_value = self._coerce_to_date(fecha_entrega)
        if not fecha_value:
            return False
        return (fecha_value.year, fecha_value.month)

    def _format_report_month_label(self, month_key):
        if not month_key:
            return 'Total mes'

        year, month = month_key
        month_names = {
            1: 'Enero',
            2: 'Febrero',
            3: 'Marzo',
            4: 'Abril',
            5: 'Mayo',
            6: 'Junio',
            7: 'Julio',
            8: 'Agosto',
            9: 'Septiembre',
            10: 'Octubre',
            11: 'Noviembre',
            12: 'Diciembre',
        }
        return f'Total {month_names.get(month, "")} {year}'.strip()

    def _get_report_group_sort_key(self, group_key, group_meta=None):
        fecha_value = self._coerce_to_date((group_meta or {}).get('fecha_entrega') or group_key)
        if fecha_value:
            return (0, fecha_value)

        order_map = {
            'Lunes': 0,
            'Martes': 1,
            'Miercoles': 2,
            'Jueves': 3,
            'Viernes': 4,
            'Sabado': 5,
            'Domingo': 6,
        }
        day_name = (group_meta or {}).get('day_name') or group_key
        return (1, order_map.get(day_name or '', 99), day_name or '')

    def _build_report_html(self, rows):
        if not rows:
            return '<div class="zrn_am_report_empty">No hay ordenes de venta para mostrar con la seleccion actual.</div>'

        day_client_order = OrderedDict()
        day_meta_map = {}
        product_buckets = OrderedDict()

        for row in rows:
            day_date = row.get('fecha_entrega')
            day_name = row.get('dia_semana') or row.get('fecha_entrega') or ''
            day_key = day_date or day_name or ''
            client_name = row.get('cliente') or 'Cliente sin nombre'
            day_clients = day_client_order.setdefault(day_key, [])
            if client_name not in day_clients:
                day_clients.append(client_name)
            if day_key and day_key not in day_meta_map:
                day_meta_map[day_key] = {
                    'day_name': day_name,
                    'fecha_entrega': day_date,
                }

            product_key = row.get('product_id') or 0
            product_bucket = product_buckets.setdefault(product_key, {
                'barcode': row.get('barcode') or '',
                'item_vm': row.get('item_vm') or '',
                'name': row.get('producto') or 'Producto sin nombre',
                'initial_inventory': float(row.get('stock_real_total') or 0.0),
                'week_total': 0.0,
                'by_day': {},
            })
            product_bucket['week_total'] += float(row.get('cantidad_vendida') or 0.0)

            day_bucket = product_bucket['by_day'].setdefault(day_key, {})
            client_bucket = day_bucket.setdefault(client_name, {'oc': 0.0, 'cambios': 0.0})
            client_bucket['oc'] += float(row.get('cantidad_vendida') or 0.0)
            client_bucket['cambios'] += float(row.get('cambios') or 0.0)

        sorted_days = sorted(
            day_client_order.keys(),
            key=lambda group_key: self._get_report_group_sort_key(group_key, day_meta_map.get(group_key)),
        )
        week_day_order = OrderedDict()
        for day_key in sorted_days:
            week_key = self._get_report_week_group_key((day_meta_map.get(day_key) or {}).get('fecha_entrega') or day_key)
            week_day_order.setdefault(week_key, []).append(day_key)

        month_week_order = OrderedDict()
        for week_key, week_days in week_day_order.items():
            month_key = False
            for day_key in week_days:
                month_key = self._get_report_month_group_key((day_meta_map.get(day_key) or {}).get('fecha_entrega') or day_key)
                if month_key:
                    break
            month_week_order.setdefault(month_key, []).append(week_key)

        week_display_meta = {
            week_key: {
                'days': week_days,
                'show_total': len(week_days) > 1,
            }
            for week_key, week_days in week_day_order.items()
        }
        month_display_meta = {
            month_key: {
                'weeks': month_weeks,
                'show_total': len(month_weeks) > 1,
            }
            for month_key, month_weeks in month_week_order.items()
        }

        parts = [
            '<div class="zrn_am_report_matrix_wrap">',
            '<table class="zrn_am_report_matrix">',
            '<thead>',
            '<tr>',
            '<th class="zrn_am_sticky_col" rowspan="3">Cod. barra</th>',
            '<th class="zrn_am_sticky_col zrn_am_sticky_col_2" rowspan="3">Item MV</th>',
            '<th class="zrn_am_sticky_col zrn_am_sticky_col_3" rowspan="3">Producto</th>',
            '<th colspan="3">Inventario</th>',
        ]

        for month_key, month_weeks in month_week_order.items():
            for week_key in month_weeks:
                week_days = week_day_order.get(week_key, [])
                for day_key in week_days:
                    day_meta = day_meta_map.get(day_key, {})
                    parts.append(
                        f'<th colspan="{(len(day_client_order.get(day_key, [])) * 2) + 2}">{self._format_report_day_label(day_meta.get("day_name") or day_key, day_meta.get("fecha_entrega"))}</th>'
                    )
                if week_display_meta.get(week_key, {}).get('show_total'):
                    parts.append(f'<th colspan="2" class="zrn_am_week_total_head">{escape(self._format_report_week_label(week_key))}</th>')
            if month_display_meta.get(month_key, {}).get('show_total'):
                parts.append(f'<th colspan="2" class="zrn_am_month_total_head">{escape(self._format_report_month_label(month_key))}</th>')

        parts.extend([
            '</tr>',
            '<tr>',
            '<th rowspan="2">Stock inicial</th>',
            '<th rowspan="2">Total rango</th>',
            '<th rowspan="2">Stock final</th>',
        ])

        for month_key, month_weeks in month_week_order.items():
            for week_key in month_weeks:
                week_days = week_day_order.get(week_key, [])
                for day_key in week_days:
                    for client_name in day_client_order.get(day_key, []):
                        parts.append(f'<th colspan="2">{escape(client_name)}</th>')
                    parts.append('<th colspan="2" class="zrn_am_day_total_head">Ventas dia</th>')
                if week_display_meta.get(week_key, {}).get('show_total'):
                    parts.append('<th colspan="2" class="zrn_am_week_total_head zrn_am_week_total_title">Ventas semana</th>')
            if month_display_meta.get(month_key, {}).get('show_total'):
                parts.append('<th colspan="2" class="zrn_am_month_total_head zrn_am_month_total_title">Ventas mes</th>')

        parts.extend(['</tr>', '<tr>'])

        for month_key, month_weeks in month_week_order.items():
            for week_key in month_weeks:
                week_days = week_day_order.get(week_key, [])
                for day_key in week_days:
                    for _client_name in day_client_order.get(day_key, []):
                        parts.append('<th>OC</th><th>Cambios</th>')
                    parts.append('<th class="zrn_am_day_total_head zrn_am_day_total_subhead">OC</th><th class="zrn_am_day_total_head zrn_am_day_total_subhead">Cambios</th>')
                if week_display_meta.get(week_key, {}).get('show_total'):
                    parts.append('<th class="zrn_am_week_total_head zrn_am_week_total_subhead">OC</th><th class="zrn_am_week_total_head zrn_am_week_total_subhead">Cambios</th>')
            if month_display_meta.get(month_key, {}).get('show_total'):
                parts.append('<th class="zrn_am_month_total_head zrn_am_month_total_subhead">OC</th><th class="zrn_am_month_total_head zrn_am_month_total_subhead">Cambios</th>')

        parts.extend(['</tr>', '</thead>', '<tbody>'])

        for product_data in product_buckets.values():
            final_inventory = product_data['initial_inventory'] - product_data['week_total']
            parts.extend([
                '<tr>',
                f'<td class="zrn_am_sticky_col">{escape(product_data["barcode"])}</td>',
                f'<td class="zrn_am_sticky_col zrn_am_sticky_col_2">{escape(product_data["item_vm"])}</td>',
                f'<td class="zrn_am_sticky_col zrn_am_sticky_col_3 zrn_am_product_name">{escape(product_data["name"])}</td>',
                f'<td class="zrn_am_num">{self._format_report_number(product_data["initial_inventory"])}</td>',
                f'<td class="zrn_am_num">{self._format_report_number(product_data["week_total"])}</td>',
                f'<td class="zrn_am_num">{self._format_report_number(final_inventory)}</td>',
            ])

            for month_key, month_weeks in month_week_order.items():
                month_total_oc = 0.0
                month_total_changes = 0.0

                for week_key in month_weeks:
                    week_days = week_day_order.get(week_key, [])
                    week_total_oc = 0.0
                    week_total_changes = 0.0

                    for day_key in week_days:
                        day_total_oc = 0.0
                        day_total_changes = 0.0
                        day_values = product_data['by_day'].get(day_key, {})

                        for client_name in day_client_order.get(day_key, []):
                            movement = day_values.get(client_name, {'oc': 0.0, 'cambios': 0.0})
                            day_total_oc += movement['oc']
                            day_total_changes += movement['cambios']
                            parts.append(f'<td class="zrn_am_num">{self._format_report_number(movement["oc"])}</td>')
                            parts.append(f'<td class="zrn_am_num zrn_am_change_cell">{self._format_report_number(movement["cambios"])}</td>')

                        week_total_oc += day_total_oc
                        week_total_changes += day_total_changes
                        parts.append(f'<td class="zrn_am_num zrn_am_day_total">{self._format_report_number(day_total_oc)}</td>')
                        parts.append(f'<td class="zrn_am_num zrn_am_day_total zrn_am_change_cell">{self._format_report_number(day_total_changes)}</td>')

                    month_total_oc += week_total_oc
                    month_total_changes += week_total_changes
                    if week_display_meta.get(week_key, {}).get('show_total'):
                        parts.append(f'<td class="zrn_am_num zrn_am_week_total">{self._format_report_number(week_total_oc)}</td>')
                        parts.append(f'<td class="zrn_am_num zrn_am_week_total zrn_am_change_cell">{self._format_report_number(week_total_changes)}</td>')

                if month_display_meta.get(month_key, {}).get('show_total'):
                    parts.append(f'<td class="zrn_am_num zrn_am_month_total">{self._format_report_number(month_total_oc)}</td>')
                    parts.append(f'<td class="zrn_am_num zrn_am_month_total zrn_am_change_cell">{self._format_report_number(month_total_changes)}</td>')

            parts.append('</tr>')

        parts.extend(['</tbody>', '</table>', '</div>'])
        return ''.join(parts)

    def _build_production_html(self, rows):
        if not rows:
            return '<div class="zrn_am_report_empty">No hay productos para calcular fabricacion con la seleccion actual.</div>'

        product_buckets = OrderedDict()

        for row in rows:
            product_key = row.get('product_id') or 0
            bucket = product_buckets.setdefault(product_key, {
                'product_id': product_key,
                'barcode': row.get('barcode') or '',
                'item_vm': row.get('item_vm') or '',
                'product_name': row.get('producto') or 'Producto sin nombre',
                'order_ids': set(),
                'total_vendido': 0.0,
                'stock_inicial': float(row.get('stock_real_total') or 0.0),
                'stock_libre': float(row.get('stock_libre_total') or 0.0),
                'sugerido_fabricar': 0.0,
            })
            if row.get('order_id'):
                bucket['order_ids'].add(row.get('order_id'))
            bucket['total_vendido'] += float(row.get('cantidad_vendida') or 0.0)
            bucket['sugerido_fabricar'] += float(row.get('cantidad_sugerida_producir') or 0.0)

        sorted_products = sorted(
            product_buckets.values(),
            key=lambda item: (-item['sugerido_fabricar'], -item['total_vendido'], item['product_name']),
        )

        parts = [
            '<div class="zrn_am_production_table_wrap">',
            '<table class="table table-sm table-hover o_list_table zrn_am_production_table">',
            '<thead>',
            '<tr>',
            '<th>Cod. barra</th>',
            '<th>Item MV</th>',
            '<th>Producto</th>',
            '<th class="o_list_number">Total OVs</th>',
            '<th class="o_list_number">Vendido total</th>',
            '<th class="o_list_number">Stock inicial</th>',
            '<th class="o_list_number">Stock libre</th>',
            '<th class="o_list_number">Sugerido a fabricar</th>',
            '<th>Accion</th>',
            '</tr>',
            '</thead>',
            '<tbody>',
        ]

        for product_data in sorted_products:
            suggested_qty = float(product_data['sugerido_fabricar'] or 0.0)
            action_button = (
                '<button '
                'type="button" '
                'class="btn btn-primary btn-sm zrn_am_create_mo_btn" '
                f'data-product-id="{int(product_data["product_id"] or 0)}" '
                f'data-product-qty="{suggested_qty}"'
                '>'
                'Crear OF'
                '</button>'
            ) if product_data['product_id'] and suggested_qty > 0 else ''
            parts.extend([
                '<tr>',
                f'<td>{escape(product_data["barcode"])}</td>',
                f'<td>{escape(product_data["item_vm"])}</td>',
                f'<td class="zrn_am_product_name">{escape(product_data["product_name"])}</td>',
                f'<td class="o_list_number">{self._format_report_number(len(product_data["order_ids"]))}</td>',
                f'<td class="o_list_number">{self._format_report_number(product_data["total_vendido"])}</td>',
                f'<td class="o_list_number">{self._format_report_number(product_data["stock_inicial"])}</td>',
                f'<td class="o_list_number">{self._format_report_number(product_data["stock_libre"])}</td>',
                f'<td class="o_list_number zrn_am_to_produce">{self._format_report_number(product_data["sugerido_fabricar"])}</td>',
                f'<td>{action_button}</td>',
                '</tr>',
            ])

        parts.extend(['</tbody>', '</table>', '</div>'])
        return ''.join(parts)

    def _load_report_payload(self, rows):
        Line = self.env['advanced_metrics.report.wizard.line']
        for wizard in self:
            wizard.report_line_ids.unlink()
            line_values = []
            for row in rows:
                line_values.append({
                    'wizard_id': wizard.id,
                    'fecha_entrega': row.get('fecha_entrega'),
                    'dia_semana': row.get('dia_semana'),
                    'partner_id': row.get('cliente_id') or False,
                    'cliente_id': row.get('cliente_id') or False,
                    'order_id': row.get('order_id') or False,
                    'numero_orden_venta': row.get('numero_orden_venta'),
                    'product_id': row.get('product_id') or False,
                    'producto': row.get('producto'),
                    'cantidad_vendida': row.get('cantidad_vendida', 0.0),
                    'inventario_disponible': row.get('inventario_disponible', 0.0),
                    'inventario_libre_usar': row.get('inventario_libre_usar', 0.0),
                    'cantidad_sugerida_producir': row.get('cantidad_sugerida_producir', 0.0),
                })
            if line_values:
                Line.create(line_values)

            wizard.write({
                'report_html': wizard._build_report_html(rows),
                'production_html': wizard._build_production_html(rows),
                'report_ready': True,
                'report_row_count': len(rows),
                'report_order_count': len({row.get('numero_orden_venta') for row in rows if row.get('numero_orden_venta')}),
                'report_customer_count': len({row.get('cliente_id') for row in rows if row.get('cliente_id')}),
                'report_product_count': len({row.get('product_id') for row in rows if row.get('product_id')}),
                'report_date_range_label': wizard._format_report_date_range_label(rows),
            })

    @api.model
    def get_sales_orders_report_rows(self, filters=None, limit=500):
        """
        Genera las filas del reporte de planificacion semanal.

        Extrae lineas de orden de venta confirmadas, las cruza con el
        inventario actual en almacen, y calcula cuanto falta producir
        para cubrir cada pedido.

        Filtros soportados (dict):
            - fecha_entrega_desde (str YYYY-MM-DD): Limite inferior de fecha de entrega.
            - fecha_entrega_hasta (str YYYY-MM-DD): Limite superior de fecha de entrega.
            - cliente_ids (list[int]): IDs de partners para filtrar por clientes.
            - product_ids (list[int]): IDs de productos para filtrar por producto.
            - cliente_id (int): ID del partner para compatibilidad hacia atras.
            - cliente_nombre (str): Nombre parcial para busqueda difusa de cliente.

        Returns:
            list[dict]: Lista de filas con las 8 columnas del reporte:
                fecha_entrega, dia_semana, cliente, numero_orden_venta,
                producto, cantidad_vendida, inventario_disponible,
                cantidad_sugerida_producir.
        """
        filters = filters or {}

        # --- MEJORA 2: Mapa de dias de la semana en espanol ---
        # Python devuelve weekday() como 0=Lunes, 6=Domingo.
        # Este diccionario traduce el numero al nombre completo en espanol
        # para que la gerente de operaciones vea "Lunes" en vez de "2026-04-07".
        DIAS_SEMANA = {
            0: 'Lunes',
            1: 'Martes',
            2: 'Miercoles',
            3: 'Jueves',
            4: 'Viernes',
            5: 'Sabado',
            6: 'Domingo',
        }

        # --- Validacion de modelos disponibles ---
        # Si el modulo de ventas o inventario no estan instalados,
        # retornamos vacio en vez de lanzar un error.
        if 'sale.order.line' not in self.env or 'stock.quant' not in self.env:
            return []

        stock_quant_model = self.env['stock.quant']
        order_lines = self._search_sale_lines_from_filters(filters, limit=limit)
        product_ids = order_lines.mapped('product_id').ids

        # --- Consulta de inventario actual agrupado por producto ---
        # quantity representa el stock fisico total en ubicaciones internas.
        # available_quantity representa el stock libre de usar despues de reservas.
        qty_by_product_id = {}
        free_qty_by_product_id = {}
        if product_ids:
            grouped_quants = stock_quant_model.read_group(
                [('product_id', 'in', product_ids), ('location_id.usage', '=', 'internal')],
                ['product_id', 'quantity:sum', 'available_quantity:sum'],
                ['product_id'],
            )
            qty_by_product_id = {
                item['product_id'][0]: item.get('quantity', 0.0)
                for item in grouped_quants
                if item.get('product_id')
            }
            free_qty_by_product_id = {
                item['product_id'][0]: item.get('available_quantity', 0.0)
                for item in grouped_quants
                if item.get('product_id')
            }

        # --- MEMORIA DE INVENTARIO VIRTUAL (Rolling Deduction / FIFO) ---
        # MITIGACION RIESGO MATEMATICO: Para evitar la "Doble Contabilidad" de stock, 
        # creamos una copia del inventario actual. A medida que procesamos cada orden 
        # cronologicamente, vamos restando lo vendido de esta memoria virtual.
        running_stock_by_product = qty_by_product_id.copy()
        running_free_stock_by_product = free_qty_by_product_id.copy()

        # --- ORDENAMIENTO CRONOLOGICO (El pilar de la planificacion) ---
        # Paso critico: El descuento de inventario DEBE ser First-In-First-Out.
        # Ordenamos las lineas empezando por el Lunes mas temprano hasta el Domingo.
        def get_sort_date(line):
            # Usamos commitment_date como fecha primaria de entrega
            f_entrega = line.order_id.commitment_date or line.order_id.date_order or datetime.now()
            return f_entrega.date() if hasattr(f_entrega, 'date') else f_entrega

        # Ordenamiento en memoria antes de construir las filas del reporte
        sorted_lines = sorted(order_lines, key=get_sort_date)

        # --- Construccion de filas del reporte ---
        rows = []
        for line in sorted_lines:
            if not line.product_id:
                continue

            product_id = line.product_id.id
            sold_qty = float(line.product_uom_qty or 0.0)

            # LOGICA DE ASIGNACION DE STOCK (Cascada):
            # Leemos cuanto stock queda disponible y libre de usar
            # despues de las ordenes anteriores.
            available_qty_before = running_stock_by_product.get(product_id, 0.0)
            free_qty_before = running_free_stock_by_product.get(product_id, 0.0)
            
            if available_qty_before >= sold_qty:
                # Caso A: Tenemos stock suficiente para cubrir toda esta orden.
                # Sugerido a producir es 0.
                suggested_production = 0.0
                # Descontamos las unidades consumidas de la reserva virtual.
                running_stock_by_product[product_id] -= sold_qty
                running_free_stock_by_product[product_id] = max(free_qty_before - sold_qty, 0.0)
            else:
                # Caso B: El stock se agoto o no es suficiente.
                # Solo sugerimos producir el faltante neto.
                suggested_production = sold_qty - available_qty_before
                # El inventario para este producto se marca como 0 para las siguientes filas.
                running_stock_by_product[product_id] = 0.0
                running_free_stock_by_product[product_id] = max(free_qty_before - sold_qty, 0.0)

            # Fecha final para mostrar en el reporte (con filtro de respaldo)
            f_entrega = line.order_id.commitment_date or line.order_id.date_order or datetime.now()

            # Normalizacion de fecha para calculo de dia de semana
            if hasattr(f_entrega, 'date'):
                fecha_date = f_entrega.date()
            elif hasattr(f_entrega, 'weekday'):
                fecha_date = f_entrega
            else:
                fecha_date = datetime.now().date()

            rows.append({
                'order_id': line.order_id.id,
                'cliente_id': line.order_partner_id.commercial_partner_id.id,
                'product_id': product_id,
                'fecha_entrega': fecha_date.isoformat(),
                'dia_semana': DIAS_SEMANA.get(fecha_date.weekday(), ''),
                'cliente': line.order_partner_id.commercial_partner_id.display_name or '',
                'numero_orden_venta': line.order_id.name or '',
                'producto': line.product_id.display_name or '',
                'barcode': line.product_id.barcode or '',
                'item_vm': line.product_id.default_code or '',
                'cantidad_vendida': sold_qty,
                'cambios': 0.0,
                # Reportamos el stock que habia disponible JUSTO antes de esta venta
                'inventario_disponible': round(available_qty_before, 2),
                'inventario_libre_usar': round(free_qty_before, 2),
                'stock_real_total': round(qty_by_product_id.get(product_id, 0.0), 2),
                'stock_libre_total': round(free_qty_by_product_id.get(product_id, 0.0), 2),
                'cantidad_sugerida_producir': round(suggested_production, 2),
            })

        # --- MEJORA 5: ORDENAMIENTO INTELIGENTE PARA PLANIFICACION ---
        # Ordenamos primero por fecha de entrega (lunes primero) y luego
        # por nombre de cliente dentro de cada dia. Esto permite que la
        # gerente de operaciones lea el reporte de arriba a abajo como
        # un plan de produccion diario sin reordenar nada.
        rows.sort(key=lambda r: (r.get('fecha_entrega', ''), r.get('cliente', '')))

        return rows

    def action_generate_report(self):
        self.ensure_one()
        self._sync_selected_review_lines()
        rows = self.get_sales_orders_report_rows(self._get_report_filters())
        self._load_report_payload(rows)
        report_view = self.env.ref('advanced_metrics.view_advanced_metrics_report_wizard_report_form')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Detalle del reporte',
            'res_model': 'advanced_metrics.report.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': report_view.id,
            'views': [(report_view.id, 'form')],
            'target': 'current',
            '_noBreadcrumbs': True,
        }

    def action_open_production_summary(self):
        self.ensure_one()
        production_view = self.env.ref('advanced_metrics.view_advanced_metrics_report_wizard_production_form')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Resumen para fabricar',
            'res_model': 'advanced_metrics.report.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': production_view.id,
            'views': [(production_view.id, 'form')],
            'target': 'current',
            '_noBreadcrumbs': True,
        }

    def action_back_to_report(self):
        self.ensure_one()
        report_view = self.env.ref('advanced_metrics.view_advanced_metrics_report_wizard_report_form')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Detalle del reporte',
            'res_model': 'advanced_metrics.report.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': report_view.id,
            'views': [(report_view.id, 'form')],
            'target': 'current',
            '_noBreadcrumbs': True,
        }

    def action_back_to_filters(self):
        self.ensure_one()
        filter_view = self.env.ref('advanced_metrics.view_advanced_metrics_report_wizard_form')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reporte de ventas e inventario',
            'res_model': 'advanced_metrics.report.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': filter_view.id,
            'views': [(filter_view.id, 'form')],
            'target': 'current',
            '_noBreadcrumbs': True,
        }

    def action_open_mrp_production_create(self, product_id, suggested_qty=0.0):
        self.ensure_one()

        product = self.env['product.product'].browse(int(product_id or 0)).exists()
        if not product:
            return False

        action = self.env['ir.actions.actions']._for_xml_id('mrp.action_mrp_production_form')
        action_context = dict(self.env.context)
        action_context.update({
            'default_product_id': product.id,
            'default_product_uom_id': product.uom_id.id,
            'default_company_id': self.env.company.id,
            'allowed_company_ids': self.env.companies.ids,
        })

        quantity = float(suggested_qty or 0.0)
        if quantity > 0:
            action_context['default_product_qty'] = quantity

        action.update({
            'name': 'Nueva orden de fabricacion',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
            'context': action_context,
        })
        return action

    def get_selected_review_cards(self):
        self.ensure_one()
        return {
            'clients': [
                {
                    'line_id': line.id,
                    'title': line.partner_id.display_name or '',
                    'subtitle': line.city or '',
                    'meta': line.email or '',
                    'stats': [
                        {'label': 'OVs', 'value': line.order_count},
                        {'label': 'Unidades', 'value': line.total_units},
                    ],
                }
                for line in self.selected_cliente_line_ids
            ],
            'products': [
                {
                    'line_id': line.id,
                    'title': line.product_id.display_name or '',
                    'subtitle': line.default_code or '',
                    'meta': line.categ_name or '',
                    'stats': [
                        {'label': 'OVs', 'value': line.order_count},
                        {'label': 'Demanda', 'value': line.demanded_qty},
                        {'label': 'Stock libre', 'value': line.stock_libre},
                        {'label': 'Stock real', 'value': line.stock_real},
                    ],
                }
                for line in self.selected_product_line_ids
            ],
        }

    @api.model
    def _get_period_dates(self, period_type='week'):
        today = fields.Date.context_today(self)

        if period_type == 'month':
            first_day = today.replace(day=1)
            last_day = today.replace(day=monthrange(today.year, today.month)[1])
            return {
                'desde': first_day.isoformat(),
                'hasta': last_day.isoformat(),
            }

        if period_type == 'custom':
            return {
                'desde': False,
                'hasta': False,
            }

        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        return {
            'desde': week_start.isoformat(),
            'hasta': week_end.isoformat(),
        }

    @api.model
    def get_period_dates(self, period_type='week'):
        return self._get_period_dates(period_type)


    @api.model
    def get_next_week_dates(self):
        """
        Calcula el intervalo de la proxima semana (Lunes a Domingo)
        ajustado a la operacion en Guatemala.
        
        Returns:
            dict: {'desde': 'YYYY-MM-DD', 'hasta': 'YYYY-MM-DD'}
        """
        # Obtenemos la fecha actual en la zona horaria del usuario
        # Si no esta definida, usamos UTC, pero lo ideal en GT es UTC-6
        today = fields.Date.context_today(self)
        
        # weekday() en Python: 0=Lunes, 6=Domingo
        # Calculamos dias hasta el proximo lunes
        current_weekday = today.weekday()
        days_until_monday = (7 - current_weekday) if current_weekday < 7 else 1
        
        next_monday = today + timedelta(days=days_until_monday)
        next_sunday = next_monday + timedelta(days=6)
        
        return {
            'desde': next_monday.isoformat(),
            'hasta': next_sunday.isoformat(),
        }

class AdvancedMetricsReportWizardLine(models.TransientModel):
    _name = 'advanced_metrics.report.wizard.line'
    _description = 'Linea del reporte de ventas e inventario'
    # MEJORA 5: Ordenamiento ascendente por fecha para planificacion
    # (lunes primero, domingo al final).
    _order = 'fecha_entrega asc, id asc'

    wizard_id = fields.Many2one(
        'advanced_metrics.report.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    fecha_entrega = fields.Date(string='Fecha de entrega')
    # MEJORA 2: Dia de la semana en espanol (Lunes, Martes, etc.)
    dia_semana = fields.Char(string='Dia')
    partner_id = fields.Many2one('res.partner', string='Cliente comercial')
    cliente_id = fields.Many2one('res.partner', string='Cliente')
    order_id = fields.Many2one('sale.order', string='Orden de venta')
    product_id = fields.Many2one('product.product', string='Producto')
    numero_orden_venta = fields.Char(string='Numero de orden de venta')
    producto = fields.Char(string='Producto')
    cantidad_vendida = fields.Float(string='Cantidad vendida')
    inventario_disponible = fields.Float(string='Inventario disponible de producto terminado')
    inventario_libre_usar = fields.Float(string='Inventario libre de usar')
    cantidad_sugerida_producir = fields.Float(
        string='Cantidad sugerida a producir',
        default=0.0,
    )


class AdvancedMetricsReportWizardClientLine(models.TransientModel):
    _name = 'advanced_metrics.report.wizard.client.line'
    _description = 'Cliente seleccionado para el reporte'
    _order = 'partner_id'

    wizard_id = fields.Many2one(
        'advanced_metrics.report.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    partner_id = fields.Many2one('res.partner', string='Cliente', required=True)
    city = fields.Char(string='Ciudad')
    email = fields.Char(string='Correo')
    order_count = fields.Integer(string='OVs')
    total_units = fields.Float(string='Unidades')

    def action_remove(self):
        self.ensure_one()
        wizard = self.wizard_id
        wizard.cliente_ids = [(3, self.partner_id.id)]
        wizard._compute_review_data()
        return False


class AdvancedMetricsReportWizardProductLine(models.TransientModel):
    _name = 'advanced_metrics.report.wizard.product.line'
    _description = 'Producto seleccionado para el reporte'
    _order = 'product_id'

    wizard_id = fields.Many2one(
        'advanced_metrics.report.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    product_id = fields.Many2one('product.product', string='Producto', required=True)
    default_code = fields.Char(string='Referencia')
    categ_name = fields.Char(string='Categoria')
    order_count = fields.Integer(string='OVs')
    demanded_qty = fields.Float(string='Demanda')
    stock_real = fields.Float(string='Stock real')
    stock_libre = fields.Float(string='Stock libre')

    def action_remove(self):
        self.ensure_one()
        wizard = self.wizard_id
        wizard.product_ids = [(3, self.product_id.id)]
        wizard._compute_review_data()
        return False
