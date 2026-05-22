# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ZrnProdigynProductionPlanningWizard(models.TransientModel):
    _name = 'zrn_prodigyn.production.planning.wizard'
    _description = 'Filtros de planeacion de produccion'
    _rec_name = 'name'

    name = fields.Char(string='Titulo', default='Planeacion de fabricacion')
    fecha_entrega_desde = fields.Date(string='Fecha de entrega desde')
    fecha_entrega_hasta = fields.Date(string='Fecha de entrega hasta')
    cliente_ids = fields.Many2many(
        'res.partner',
        string='Puntos de venta',
    )
    product_ids = fields.Many2many(
        'product.product',
        string='Productos',
    )
    available_cliente_ids = fields.Many2many(
        'res.partner',
        string='Puntos de venta disponibles',
        compute='_compute_filter_data',
        readonly=True,
    )
    available_product_ids = fields.Many2many(
        'product.product',
        string='Productos disponibles',
        compute='_compute_filter_data',
        readonly=True,
    )
    preview_cliente_count = fields.Integer(
        string='Cantidad de puntos de venta',
        compute='_compute_filter_data',
        readonly=True,
    )
    preview_product_count = fields.Integer(
        string='Cantidad de productos',
        compute='_compute_filter_data',
        readonly=True,
    )
    preview_order_count = fields.Integer(
        string='Cantidad de pedidos de venta',
        compute='_compute_filter_data',
        readonly=True,
    )
    report_customer_line_ids = fields.One2many(
        'zrn_prodigyn.production.planning.wizard.report.customer.line',
        'wizard_id',
        string='Clientes del reporte',
    )
    report_product_line_ids = fields.One2many(
        'zrn_prodigyn.production.planning.wizard.report.product.line',
        'wizard_id',
        string='Productos del reporte',
    )
    report_order_line_ids = fields.One2many(
        'zrn_prodigyn.production.planning.wizard.report.order.line',
        'wizard_id',
        string='OVs del reporte',
    )
    report_ready = fields.Boolean(string='Reporte listo', default=False)
    report_active_tab = fields.Selection(
        [
            ('overview', 'Reporte'),
            ('customers', 'Clientes'),
            ('products', 'Productos'),
            ('orders', 'OVs'),
        ],
        string='Vista activa del reporte',
        default='overview',
        readonly=True,
    )
    report_row_count = fields.Integer(string='Lineas del reporte', readonly=True)
    report_order_count = fields.Integer(string='Ordenes consideradas', readonly=True)
    report_customer_count = fields.Integer(string='Clientes en reporte', readonly=True)
    report_product_count = fields.Integer(string='Productos en reporte', readonly=True)
    report_date_range_label = fields.Char(string='Rango consultado', readonly=True)
    report_date_from_label = fields.Char(string='Fecha inicial del reporte', readonly=True)
    report_date_to_label = fields.Char(string='Fecha final del reporte', readonly=True)
    report_date_range_mode = fields.Selection(
        [
            ('all', 'Todas las fechas'),
            ('from', 'Desde'),
            ('to', 'Hasta'),
            ('range', 'Rango'),
        ],
        string='Modo del rango del reporte',
        default='all',
        readonly=True,
    )

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

    def _get_filter_values(self, include_selected=True):
        self.ensure_one()
        values = {
            'fecha_entrega_desde': fields.Date.to_string(self.fecha_entrega_desde) if self.fecha_entrega_desde else False,
            'fecha_entrega_hasta': fields.Date.to_string(self.fecha_entrega_hasta) if self.fecha_entrega_hasta else False,
        }
        if include_selected:
            values.update({
                'cliente_ids': self.cliente_ids.ids,
                'product_ids': self.product_ids.ids,
            })
        return values

    @api.model
    def _search_sale_lines_from_filters(self, filters=None, limit=None):
        filters = filters or {}
        if 'sale.order.line' not in self.env:
            return self.env['sale.order.line']

        fecha_desde = self._coerce_to_date(filters.get('fecha_entrega_desde'))
        fecha_hasta = self._coerce_to_date(filters.get('fecha_entrega_hasta'))
        cliente_ids = [int(partner_id) for partner_id in filters.get('cliente_ids') or [] if partner_id]
        product_ids = [int(product_id) for product_id in filters.get('product_ids') or [] if product_id]

        domain = [
            ('order_id.state', '=', 'sale'),
            ('display_type', '=', False),
            ('product_id', '!=', False),
        ]

        if cliente_ids:
            domain.append(('order_id.partner_shipping_id', 'in', cliente_ids))
        if product_ids:
            domain.append(('product_id', 'in', product_ids))

        sale_lines = self.env['sale.order.line'].search(domain, order='id asc')
        sale_lines = sale_lines.filtered(
            lambda line: float(line.qty_delivered or 0.0) < float(line.product_uom_qty or 0.0)
        )
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

    @api.depends('fecha_entrega_desde', 'fecha_entrega_hasta', 'cliente_ids', 'product_ids')
    def _compute_filter_data(self):
        for wizard in self:
            available_lines = wizard._search_sale_lines_from_filters(
                wizard._get_filter_values(include_selected=False)
            )
            candidate_lines = wizard._search_sale_lines_from_filters(
                wizard._get_filter_values(include_selected=True)
            )

            wizard.available_cliente_ids = [(6, 0, available_lines.mapped('order_id.partner_shipping_id').ids)]
            wizard.available_product_ids = [(6, 0, available_lines.mapped('product_id').ids)]
            wizard.preview_cliente_count = len(candidate_lines.mapped('order_id.partner_shipping_id'))
            wizard.preview_product_count = len(candidate_lines.mapped('product_id'))
            wizard.preview_order_count = len(candidate_lines.mapped('order_id'))

    @api.onchange('fecha_entrega_desde', 'fecha_entrega_hasta', 'cliente_ids', 'product_ids')
    def _onchange_filters_refresh_data(self):
        self._compute_filter_data()

    def action_clear_filters(self):
        self.ensure_one()
        self.write({
            'fecha_entrega_desde': False,
            'fecha_entrega_hasta': False,
            'cliente_ids': [(5, 0, 0)],
            'product_ids': [(5, 0, 0)],
        })
        self._reset_report_payload()
        self._compute_filter_data()
        return self.action_open_filters()

    def action_open_filters(self):
        self.ensure_one()
        filter_view = self.env.ref('zrn_prodigyn.view_zrn_prodigyn_production_planning_filter_form')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Planeacion de fabricacion',
            'res_model': 'zrn_prodigyn.production.planning.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': filter_view.id,
            'views': [(filter_view.id, 'form')],
            'target': 'main',
        }

    def action_back_to_production_planning(self):
        self.ensure_one()
        action = self.env.ref('zrn_prodigyn.action_zrn_prodigyn_production_planning').read()[0]
        action['target'] = 'main'
        return action

    def _reset_report_payload(self):
        for wizard in self:
            wizard.report_customer_line_ids.unlink()
            wizard.report_product_line_ids.unlink()
            wizard.report_order_line_ids.unlink()
            wizard.report_ready = False
            wizard.report_active_tab = 'overview'
            wizard.report_row_count = 0
            wizard.report_order_count = 0
            wizard.report_customer_count = 0
            wizard.report_product_count = 0
            wizard.report_date_range_label = False
            wizard.report_date_from_label = False
            wizard.report_date_to_label = False
            wizard.report_date_range_mode = 'all'

    def _get_effective_report_date_range(self, candidate_lines):
        self.ensure_one()
        line_dates = [
            wizard_date
            for wizard_date in (
                self._get_effective_line_date(line) for line in candidate_lines
            )
            if wizard_date
        ]
        if line_dates:
            return min(line_dates), max(line_dates)
        return self.fecha_entrega_desde, self.fecha_entrega_hasta

    def _get_report_date_range_payload(self, candidate_lines):
        self.ensure_one()
        date_from, date_to = self._get_effective_report_date_range(candidate_lines)
        if date_from and date_to:
            return {
                'label': f'{date_from.strftime("%d/%m/%Y")} al {date_to.strftime("%d/%m/%Y")}',
                'from_label': date_from.strftime("%d/%m/%Y"),
                'to_label': date_to.strftime("%d/%m/%Y"),
                'mode': 'range',
            }
        if date_from:
            return {
                'label': f'desde {date_from.strftime("%d/%m/%Y")}',
                'from_label': date_from.strftime("%d/%m/%Y"),
                'to_label': False,
                'mode': 'from',
            }
        if date_to:
            return {
                'label': f'hasta {date_to.strftime("%d/%m/%Y")}',
                'from_label': False,
                'to_label': date_to.strftime("%d/%m/%Y"),
                'mode': 'to',
            }
        return {
            'label': 'todas las fechas disponibles',
            'from_label': False,
            'to_label': False,
            'mode': 'all',
        }

    def _sync_report_customer_lines(self, candidate_lines):
        SummaryLine = self.env['zrn_prodigyn.production.planning.wizard.report.customer.line']
        for wizard in self:
            wizard.report_customer_line_ids.unlink()
            grouped_lines = {}
            for line in candidate_lines.sorted(
                key=lambda item: (
                    item.order_id.partner_shipping_id.display_name or '',
                    item.id,
                )
            ):
                partner = line.order_id.partner_shipping_id
                if not partner:
                    continue
                grouped_lines.setdefault(partner.id, self.env['sale.order.line'])
                grouped_lines[partner.id] |= line

            summary_values = []
            for partner_id, lines in grouped_lines.items():
                partner = self.env['res.partner'].browse(partner_id)
                order_ids = lines.mapped('order_id')
                product_ids = lines.mapped('product_id')
                delivery_dates = [
                    effective_date for effective_date in
                    (wizard._get_effective_line_date(line) for line in lines)
                    if effective_date
                ]
                summary_values.append({
                    'wizard_id': wizard.id,
                    'partner_id': partner.id,
                    'customer_id': (partner.parent_id or partner.commercial_partner_id).id,
                    'city': partner.city or '',
                    'order_count': len(order_ids),
                    'line_count': len(lines),
                    'product_count': len(product_ids),
                    'total_units': sum(lines.mapped('product_uom_qty')),
                    'first_delivery_date': min(delivery_dates) if delivery_dates else False,
                    'last_delivery_date': max(delivery_dates) if delivery_dates else False,
                })
            if summary_values:
                SummaryLine.create(summary_values)

    def _sync_report_product_lines(self, candidate_lines):
        SummaryLine = self.env['zrn_prodigyn.production.planning.wizard.report.product.line']
        StockQuant = self.env['stock.quant'] if 'stock.quant' in self.env else False
        for wizard in self:
            wizard.report_product_line_ids.unlink()
            grouped_lines = {}
            for line in candidate_lines.sorted(
                key=lambda item: (
                    item.product_id.display_name or '',
                    item.id,
                )
            ):
                product = line.product_id
                if not product:
                    continue
                grouped_lines.setdefault(product.id, self.env['sale.order.line'])
                grouped_lines[product.id] |= line

            stock_data = {}
            product_ids = list(grouped_lines.keys())
            if product_ids and StockQuant:
                grouped_quants = StockQuant.read_group(
                    [('product_id', 'in', product_ids), ('location_id.usage', '=', 'internal')],
                    ['product_id', 'available_quantity:sum', 'quantity:sum'],
                    ['product_id'],
                )
                stock_data = {
                    item['product_id'][0]: {
                        'stock_initial': item.get('quantity', 0.0),
                        'stock_free': item.get('available_quantity', 0.0),
                    }
                    for item in grouped_quants
                    if item.get('product_id')
                }

            summary_values = []
            for product_id, lines in grouped_lines.items():
                product = self.env['product.product'].browse(product_id)
                order_ids = lines.mapped('order_id')
                customer_ids = lines.mapped('order_id.partner_shipping_id')
                delivery_dates = [
                    effective_date for effective_date in
                    (wizard._get_effective_line_date(line) for line in lines)
                    if effective_date
                ]
                stock_info = stock_data.get(product.id, {})
                summary_values.append({
                    'wizard_id': wizard.id,
                    'product_id': product.id,
                    'default_code': product.default_code or '',
                    'categ_name': product.categ_id.display_name or '',
                    'customer_count': len(customer_ids),
                    'order_count': len(order_ids),
                    'line_count': len(lines),
                    'total_units': sum(lines.mapped('product_uom_qty')),
                    'stock_initial': stock_info.get('stock_initial', 0.0),
                    'stock_free': stock_info.get('stock_free', 0.0),
                    'first_delivery_date': min(delivery_dates) if delivery_dates else False,
                    'last_delivery_date': max(delivery_dates) if delivery_dates else False,
                })
            if summary_values:
                SummaryLine.create(summary_values)

    def _sync_report_order_lines(self, candidate_lines):
        SummaryLine = self.env['zrn_prodigyn.production.planning.wizard.report.order.line']
        order_state_labels = {
            'draft': 'Presupuesto',
            'sent': 'Presupuesto enviado',
            'sale': 'Pedido de venta',
            'done': 'Bloqueado',
            'cancel': 'Cancelado',
        }
        for wizard in self:
            wizard.report_order_line_ids.unlink()
            grouped_lines = {}
            for line in candidate_lines.sorted(
                key=lambda item: (
                    item.order_id.name or '',
                    item.id,
                )
            ):
                order = line.order_id
                if not order:
                    continue
                grouped_lines.setdefault(order.id, self.env['sale.order.line'])
                grouped_lines[order.id] |= line

            summary_values = []
            for order_id, lines in grouped_lines.items():
                order = self.env['sale.order'].browse(order_id)
                delivery_dates = [
                    effective_date for effective_date in
                    (wizard._get_effective_line_date(line) for line in lines)
                    if effective_date
                ]
                summary_values.append({
                    'wizard_id': wizard.id,
                    'order_id': order.id,
                    'customer_id': (order.partner_shipping_id or order.partner_id).id,
                    'state': order.state or '',
                    'state_label': order_state_labels.get(order.state or '', order.state or ''),
                    'product_count': len(lines.mapped('product_id')),
                    'line_count': len(lines),
                    'total_units': sum(lines.mapped('product_uom_qty')),
                    'first_delivery_date': min(delivery_dates) if delivery_dates else False,
                    'last_delivery_date': max(delivery_dates) if delivery_dates else False,
                })
            if summary_values:
                SummaryLine.create(summary_values)

    def action_open_report(self):
        self.ensure_one()
        report_view = self.env.ref('zrn_prodigyn.view_zrn_prodigyn_production_planning_report_form')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Resumen de fabricacion',
            'res_model': 'zrn_prodigyn.production.planning.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': report_view.id,
            'views': [(report_view.id, 'form')],
            'target': 'main',
        }

    def _open_report_tab(self, tab_name):
        self.ensure_one()
        self.report_active_tab = tab_name
        return self.action_open_report()

    def action_open_report_overview(self):
        self.ensure_one()
        return self._open_report_tab('overview')

    def action_back_to_filters(self):
        self.ensure_one()
        return self.action_open_filters()

    def action_open_report_customers(self):
        self.ensure_one()
        return self._open_report_tab('customers')

    def action_open_report_products(self):
        self.ensure_one()
        return self._open_report_tab('products')

    def action_open_report_orders(self):
        self.ensure_one()
        return self._open_report_tab('orders')

    def action_continue(self):
        self.ensure_one()
        candidate_lines = self._search_sale_lines_from_filters(
            self._get_filter_values(include_selected=True)
        )
        self._reset_report_payload()
        self._sync_report_customer_lines(candidate_lines)
        self._sync_report_product_lines(candidate_lines)
        self._sync_report_order_lines(candidate_lines)
        self.write({
            'report_ready': True,
            'report_active_tab': 'overview',
            'report_row_count': len(candidate_lines),
            'report_order_count': len(candidate_lines.mapped('order_id')),
            'report_customer_count': len(candidate_lines.mapped('order_id.partner_shipping_id')),
            'report_product_count': len(candidate_lines.mapped('product_id')),
        })
        date_range_payload = self._get_report_date_range_payload(candidate_lines)
        self.write({
            'report_date_range_label': date_range_payload['label'],
            'report_date_from_label': date_range_payload['from_label'],
            'report_date_to_label': date_range_payload['to_label'],
            'report_date_range_mode': date_range_payload['mode'],
        })
        return self.action_open_report()


class ZrnProdigynProductionPlanningWizardReportCustomerLine(models.TransientModel):
    _name = 'zrn_prodigyn.production.planning.wizard.report.customer.line'
    _description = 'Resumen de cliente del reporte de fabricacion'
    _order = 'first_delivery_date asc, partner_id'

    wizard_id = fields.Many2one(
        'zrn_prodigyn.production.planning.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    partner_id = fields.Many2one('res.partner', string='Punto de venta', required=True)
    customer_id = fields.Many2one('res.partner', string='Cliente')
    city = fields.Char(string='Ciudad')
    order_count = fields.Integer(string='OVs')
    line_count = fields.Integer(string='Lineas')
    product_count = fields.Integer(string='Productos')
    total_units = fields.Float(string='Unidades')
    first_delivery_date = fields.Date(string='Primera entrega')
    last_delivery_date = fields.Date(string='Ultima entrega')
    partner_image_1920 = fields.Binary(related='partner_id.image_1920', readonly=True)
    report_detail_sale_line_ids = fields.Many2many(
        'sale.order.line',
        string='Lineas incluidas',
        compute='_compute_report_detail_sale_line_ids',
        readonly=True,
    )

    @api.depends('wizard_id', 'partner_id')
    def _compute_report_detail_sale_line_ids(self):
        for line in self:
            detail_lines = self.env['sale.order.line']
            if line.wizard_id and line.partner_id:
                candidate_lines = line.wizard_id._search_sale_lines_from_filters(
                    line.wizard_id._get_filter_values(include_selected=True)
                )
                detail_lines = candidate_lines.filtered(
                    lambda sale_line: sale_line.order_id.partner_shipping_id == line.partner_id
                )
            line.report_detail_sale_line_ids = [(6, 0, detail_lines.ids)]

    def action_return_to_report(self):
        self.ensure_one()
        return self.wizard_id.action_open_report()


class ZrnProdigynProductionPlanningWizardReportProductLine(models.TransientModel):
    _name = 'zrn_prodigyn.production.planning.wizard.report.product.line'
    _description = 'Resumen de producto del reporte de fabricacion'
    _order = 'first_delivery_date asc, product_id'

    wizard_id = fields.Many2one(
        'zrn_prodigyn.production.planning.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    product_id = fields.Many2one('product.product', string='Producto', required=True)
    default_code = fields.Char(string='Referencia')
    categ_name = fields.Char(string='Categoria')
    customer_count = fields.Integer(string='Clientes')
    order_count = fields.Integer(string='OVs')
    line_count = fields.Integer(string='Lineas')
    total_units = fields.Float(string='Demanda total')
    stock_initial = fields.Float(string='Stock inicial')
    stock_free = fields.Float(string='Stock libre')
    first_delivery_date = fields.Date(string='Primera entrega')
    last_delivery_date = fields.Date(string='Ultima entrega')
    product_image_1920 = fields.Binary(related='product_id.image_1920', readonly=True)
    report_detail_sale_line_ids = fields.Many2many(
        'sale.order.line',
        string='Lineas incluidas',
        compute='_compute_report_detail_sale_line_ids',
        readonly=True,
    )

    @api.depends('wizard_id', 'product_id')
    def _compute_report_detail_sale_line_ids(self):
        for line in self:
            detail_lines = self.env['sale.order.line']
            if line.wizard_id and line.product_id:
                candidate_lines = line.wizard_id._search_sale_lines_from_filters(
                    line.wizard_id._get_filter_values(include_selected=True)
                )
                detail_lines = candidate_lines.filtered(
                    lambda sale_line: sale_line.product_id == line.product_id
                )
            line.report_detail_sale_line_ids = [(6, 0, detail_lines.ids)]

    def action_return_to_report(self):
        self.ensure_one()
        return self.wizard_id.action_open_report()


class ZrnProdigynProductionPlanningWizardReportOrderLine(models.TransientModel):
    _name = 'zrn_prodigyn.production.planning.wizard.report.order.line'
    _description = 'Resumen de OV del reporte de fabricacion'
    _order = 'first_delivery_date asc, order_id'

    wizard_id = fields.Many2one(
        'zrn_prodigyn.production.planning.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    order_id = fields.Many2one('sale.order', string='Orden de venta', required=True)
    customer_id = fields.Many2one('res.partner', string='Punto de venta')
    state = fields.Char(string='Estado tecnico')
    state_label = fields.Char(string='Estado')
    product_count = fields.Integer(string='Productos')
    line_count = fields.Integer(string='Lineas')
    total_units = fields.Float(string='Unidades')
    first_delivery_date = fields.Date(string='Primera entrega')
    last_delivery_date = fields.Date(string='Ultima entrega')
    report_detail_sale_line_ids = fields.Many2many(
        'sale.order.line',
        string='Lineas incluidas',
        compute='_compute_report_detail_sale_line_ids',
        readonly=True,
    )

    @api.depends('wizard_id', 'order_id')
    def _compute_report_detail_sale_line_ids(self):
        for line in self:
            detail_lines = self.env['sale.order.line']
            if line.wizard_id and line.order_id:
                candidate_lines = line.wizard_id._search_sale_lines_from_filters(
                    line.wizard_id._get_filter_values(include_selected=True)
                )
                detail_lines = candidate_lines.filtered(
                    lambda sale_line: sale_line.order_id == line.order_id
                )
            line.report_detail_sale_line_ids = [(6, 0, detail_lines.ids)]

    def action_return_to_report(self):
        self.ensure_one()
        return self.wizard_id.action_open_report()
