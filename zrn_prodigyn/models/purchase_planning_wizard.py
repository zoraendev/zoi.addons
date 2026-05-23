# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ZrnProdigynPurchasePlanningWizard(models.TransientModel):
    _name = 'zrn_prodigyn.purchase.planning.wizard'
    _description = 'Filtros de planeacion de abastecimiento'
    _rec_name = 'name'

    name = fields.Char(string='Titulo', default='Planeacion de abastecimiento')
    fecha_desde = fields.Date(string='Fecha desde')
    fecha_hasta = fields.Date(string='Fecha hasta')
    planning_basis = fields.Selection(
        [
            ('mrp', 'Ordenes de fabricacion'),
            ('sale', 'Ordenes de venta'),
        ],
        string='Base de la planeacion',
        default='mrp',
        required=True,
    )
    mrp_source_state = fields.Selection(
        [
            ('all_open', 'Confirmadas y en proceso'),
            ('confirmed', 'Confirmadas para fabricar'),
            ('progress', 'En progreso'),
            ('to_close', 'Por cerrar'),
            ('done', 'Finalizadas'),
            ('draft', 'Borrador'),
            ('cancel', 'Canceladas'),
        ],
        string='Estado de orden de fabricacion',
        default='confirmed',
        required=True,
    )
    sale_source_state = fields.Selection(
        [
            ('pending_delivery', 'Confirmadas pendientes de entrega'),
            ('sale', 'Pedido de venta'),
            ('done', 'Bloqueado'),
            ('draft', 'Presupuesto'),
            ('sent', 'Presupuesto enviado'),
            ('cancel', 'Cancelado'),
            ('all_open', 'Todos excepto cancelado'),
        ],
        string='Estado de orden de venta',
        default='pending_delivery',
        required=True,
    )
    supply_product_ids = fields.Many2many(
        'product.product',
        string='Insumos para fabricar',
    )
    available_supply_product_ids = fields.Many2many(
        'product.product',
        string='Insumos disponibles',
        compute='_compute_filter_data',
        readonly=True,
    )
    preview_supply_product_count = fields.Integer(
        string='Cantidad de insumos',
        compute='_compute_filter_data',
        readonly=True,
    )
    preview_bom_count = fields.Integer(
        string='Cantidad de recetas',
        compute='_compute_filter_data',
        readonly=True,
    )
    preview_source_count = fields.Integer(
        string='Cantidad de documentos base',
        compute='_compute_filter_data',
        readonly=True,
    )
    report_requirement_line_ids = fields.One2many(
        'zrn_prodigyn.purchase.planning.wizard.report.requirement.line',
        'wizard_id',
        string='Lineas del requerimiento',
    )
    report_supply_line_ids = fields.One2many(
        'zrn_prodigyn.purchase.planning.wizard.report.supply.line',
        'wizard_id',
        string='Insumos del reporte',
    )
    report_product_line_ids = fields.One2many(
        'zrn_prodigyn.purchase.planning.wizard.report.product.line',
        'wizard_id',
        string='Productos del reporte',
    )
    report_document_line_ids = fields.One2many(
        'zrn_prodigyn.purchase.planning.wizard.report.document.line',
        'wizard_id',
        string='Ordenes del reporte',
    )
    report_ready = fields.Boolean(string='Reporte listo', default=False)
    report_active_tab = fields.Selection(
        [
            ('overview', 'Reporte'),
            ('supplies', 'Insumos'),
            ('products', 'Productos'),
            ('documents', 'Ordenes'),
        ],
        string='Vista activa del reporte',
        default='overview',
        readonly=True,
    )
    report_row_count = fields.Integer(string='Lineas del reporte', readonly=True)
    report_supply_count = fields.Integer(string='Insumos en reporte', readonly=True)
    report_product_count = fields.Integer(string='Productos en reporte', readonly=True)
    report_document_count = fields.Integer(string='Ordenes consideradas', readonly=True)
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

    def _get_filter_values(self, include_selected=True):
        self.ensure_one()
        values = {
            'fecha_desde': fields.Date.to_string(self.fecha_desde) if self.fecha_desde else False,
            'fecha_hasta': fields.Date.to_string(self.fecha_hasta) if self.fecha_hasta else False,
            'planning_basis': self.planning_basis,
            'mrp_source_state': self.mrp_source_state,
            'sale_source_state': self.sale_source_state,
        }
        if include_selected:
            values['supply_product_ids'] = self.supply_product_ids.ids
        return values

    def _get_bom_for_product(self, product):
        Bom = self.env['mrp.bom']
        bom = Bom.search([('product_id', '=', product.id)], limit=1)
        if bom:
            return bom
        return Bom.search([('product_tmpl_id', '=', product.product_tmpl_id.id)], limit=1)

    def _get_effective_sale_date(self, sale_line):
        return self._coerce_to_date(sale_line.order_id.commitment_date or sale_line.order_id.date_order)

    def _get_effective_production_date(self, production):
        return self._coerce_to_date(production.date_start or production.date_deadline or production.create_date)

    def _matches_date_range(self, effective_date, fecha_desde=False, fecha_hasta=False):
        if not effective_date:
            return False
        if fecha_desde and effective_date < fecha_desde:
            return False
        if fecha_hasta and effective_date > fecha_hasta:
            return False
        return True

    def _search_sale_source_lines_from_filters(self, filters=None, limit=None):
        filters = filters or {}
        fecha_desde = self._coerce_to_date(filters.get('fecha_desde'))
        fecha_hasta = self._coerce_to_date(filters.get('fecha_hasta'))
        sale_state = filters.get('sale_source_state') or 'pending_delivery'

        domain = [
            ('display_type', '=', False),
            ('product_id', '!=', False),
        ]

        if sale_state == 'pending_delivery':
            domain.append(('order_id.state', '=', 'sale'))
        elif sale_state == 'all_open':
            domain.append(('order_id.state', '!=', 'cancel'))
        else:
            domain.append(('order_id.state', '=', sale_state))

        sale_lines = self.env['sale.order.line'].search(domain, order='id asc')
        sale_lines = sale_lines.filtered(lambda line: bool(self._get_bom_for_product(line.product_id)))
        if sale_state == 'pending_delivery':
            sale_lines = sale_lines.filtered(
                lambda line: float(line.qty_delivered or 0.0) < float(line.product_uom_qty or 0.0)
            )
        if fecha_desde or fecha_hasta:
            sale_lines = sale_lines.filtered(
                lambda line: self._matches_date_range(
                    self._get_effective_sale_date(line),
                    fecha_desde=fecha_desde,
                    fecha_hasta=fecha_hasta,
                )
            )

        safe_limit = min(limit or 10000, 10000)
        return sale_lines[:safe_limit]

    def _search_mrp_sources_from_filters(self, filters=None, limit=None):
        filters = filters or {}
        fecha_desde = self._coerce_to_date(filters.get('fecha_desde'))
        fecha_hasta = self._coerce_to_date(filters.get('fecha_hasta'))
        mrp_state = filters.get('mrp_source_state') or 'confirmed'

        domain = [('product_id', '!=', False)]
        if mrp_state == 'all_open':
            domain.append(('state', 'in', ['confirmed', 'progress', 'to_close']))
        else:
            domain.append(('state', '=', mrp_state))

        productions = self.env['mrp.production'].search(domain, order='id asc')
        productions = productions.filtered(lambda mo: bool(mo.bom_id or self._get_bom_for_product(mo.product_id)))
        if fecha_desde or fecha_hasta:
            productions = productions.filtered(
                lambda production: self._matches_date_range(
                    self._get_effective_production_date(production),
                    fecha_desde=fecha_desde,
                    fecha_hasta=fecha_hasta,
                )
            )

        safe_limit = min(limit or 10000, 10000)
        return productions[:safe_limit]

    def _build_requirement_rows_from_filters(self, filters=None, include_selected_components=True):
        filters = filters or {}
        selected_component_ids = set(int(product_id) for product_id in (filters.get('supply_product_ids') or []) if product_id)
        planning_basis = filters.get('planning_basis') or 'mrp'
        rows = []

        sale_state_labels = {
            'draft': 'Presupuesto',
            'sent': 'Presupuesto enviado',
            'sale': 'Pedido de venta',
            'done': 'Bloqueado',
            'cancel': 'Cancelado',
        }
        mrp_state_labels = {
            'draft': 'Borrador',
            'confirmed': 'Confirmada',
            'progress': 'En progreso',
            'to_close': 'Por cerrar',
            'done': 'Finalizada',
            'cancel': 'Cancelada',
        }

        if planning_basis == 'sale':
            sale_lines = self._search_sale_source_lines_from_filters(filters=filters)
            for sale_line in sale_lines:
                bom = self._get_bom_for_product(sale_line.product_id)
                if not bom:
                    continue
                source_qty = max(float(sale_line.product_uom_qty or 0.0) - float(sale_line.qty_delivered or 0.0), 0.0)
                if filters.get('sale_source_state') != 'pending_delivery':
                    source_qty = float(sale_line.product_uom_qty or 0.0)
                if source_qty <= 0:
                    continue

                factor = source_qty / float(bom.product_qty or 1.0)
                source_date = self._get_effective_sale_date(sale_line)
                for bom_line in bom.bom_line_ids:
                    component = bom_line.product_id
                    if not component:
                        continue
                    if include_selected_components and selected_component_ids and component.id not in selected_component_ids:
                        continue
                    rows.append({
                        'source_model': 'sale.order',
                        'source_type_label': 'Orden de venta',
                        'source_reference': sale_line.order_id.name or '',
                        'source_record_id': sale_line.order_id.id,
                        'source_state': sale_line.order_id.state or '',
                        'source_state_label': sale_state_labels.get(sale_line.order_id.state or '', sale_line.order_id.state or ''),
                        'customer_id': (sale_line.order_id.partner_shipping_id or sale_line.order_id.partner_id).id,
                        'schedule_date': source_date,
                        'bom_id': bom.id,
                        'finished_product_id': sale_line.product_id.id,
                        'component_id': component.id,
                        'component_uom_id': bom_line.product_uom_id.id,
                        'planned_qty': source_qty,
                        'required_qty': float(bom_line.product_qty or 0.0) * factor,
                    })
        else:
            productions = self._search_mrp_sources_from_filters(filters=filters)
            for production in productions:
                bom = production.bom_id or self._get_bom_for_product(production.product_id)
                if not bom:
                    continue
                source_qty = float(production.product_qty or 0.0)
                if source_qty <= 0:
                    continue

                factor = source_qty / float(bom.product_qty or 1.0)
                source_date = self._get_effective_production_date(production)
                for bom_line in bom.bom_line_ids:
                    component = bom_line.product_id
                    if not component:
                        continue
                    if include_selected_components and selected_component_ids and component.id not in selected_component_ids:
                        continue
                    rows.append({
                        'source_model': 'mrp.production',
                        'source_type_label': 'Orden de fabricacion',
                        'source_reference': production.name or '',
                        'source_record_id': production.id,
                        'source_state': production.state or '',
                        'source_state_label': mrp_state_labels.get(production.state or '', production.state or ''),
                        'customer_id': False,
                        'schedule_date': source_date,
                        'bom_id': bom.id,
                        'finished_product_id': production.product_id.id,
                        'component_id': component.id,
                        'component_uom_id': bom_line.product_uom_id.id,
                        'planned_qty': source_qty,
                        'required_qty': float(bom_line.product_qty or 0.0) * factor,
                    })

        return rows

    def _get_stock_snapshot(self, component_ids):
        if not component_ids or 'stock.quant' not in self.env:
            return {}
        grouped_quants = self.env['stock.quant'].read_group(
            [('product_id', 'in', list(component_ids)), ('location_id.usage', '=', 'internal')],
            ['product_id', 'available_quantity:sum', 'quantity:sum'],
            ['product_id'],
        )
        return {
            item['product_id'][0]: {
                'stock_initial': item.get('quantity', 0.0),
                'stock_free': item.get('available_quantity', 0.0),
            }
            for item in grouped_quants
            if item.get('product_id')
        }

    def _build_requirement_rows_payload(self, filters=None, include_selected_components=True):
        rows = self._build_requirement_rows_from_filters(
            filters=filters,
            include_selected_components=include_selected_components,
        )
        stock_snapshot = self._get_stock_snapshot({row['component_id'] for row in rows})
        for row in rows:
            stock_info = stock_snapshot.get(row['component_id'], {})
            stock_initial = stock_info.get('stock_initial', 0.0)
            stock_free = stock_info.get('stock_free', 0.0)
            row['stock_initial'] = stock_initial
            row['stock_free'] = stock_free
            row['suggested_purchase_qty'] = max(float(row['required_qty'] or 0.0) - float(stock_free or 0.0), 0.0)
        return rows

    @api.depends(
        'fecha_desde',
        'fecha_hasta',
        'planning_basis',
        'mrp_source_state',
        'sale_source_state',
        'supply_product_ids',
    )
    def _compute_filter_data(self):
        for wizard in self:
            base_filters = wizard._get_filter_values(include_selected=False)
            candidate_filters = wizard._get_filter_values(include_selected=True)

            available_rows = wizard._build_requirement_rows_payload(
                filters=base_filters,
                include_selected_components=False,
            )
            candidate_rows = wizard._build_requirement_rows_payload(
                filters=candidate_filters,
                include_selected_components=True,
            )

            wizard.available_supply_product_ids = [(6, 0, list({row['component_id'] for row in available_rows}))]
            wizard.preview_supply_product_count = len({row['component_id'] for row in candidate_rows})
            wizard.preview_bom_count = len({row['bom_id'] for row in candidate_rows if row.get('bom_id')})
            wizard.preview_source_count = len({
                (row['source_model'], row['source_record_id'])
                for row in candidate_rows
                if row.get('source_record_id')
            })

    @api.onchange(
        'fecha_desde',
        'fecha_hasta',
        'planning_basis',
        'mrp_source_state',
        'sale_source_state',
        'supply_product_ids',
    )
    def _onchange_filters_refresh_data(self):
        self._compute_filter_data()

    def action_open_filters(self):
        self.ensure_one()
        filter_view = self.env.ref('zrn_prodigyn.view_zrn_prodigyn_purchase_planning_filter_form')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Planeacion de abastecimiento',
            'res_model': 'zrn_prodigyn.purchase.planning.wizard',
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

    def action_back_to_filters(self):
        self.ensure_one()
        return self.action_open_filters()

    def action_clear_filters(self):
        self.ensure_one()
        self.write({
            'fecha_desde': False,
            'fecha_hasta': False,
            'planning_basis': 'mrp',
            'mrp_source_state': 'confirmed',
            'sale_source_state': 'pending_delivery',
            'supply_product_ids': [(5, 0, 0)],
        })
        self._reset_report_payload()
        self._compute_filter_data()
        return self.action_open_filters()

    def _reset_report_payload(self):
        for wizard in self:
            wizard.report_requirement_line_ids.unlink()
            wizard.report_supply_line_ids.unlink()
            wizard.report_product_line_ids.unlink()
            wizard.report_document_line_ids.unlink()
            wizard.report_ready = False
            wizard.report_active_tab = 'overview'
            wizard.report_row_count = 0
            wizard.report_supply_count = 0
            wizard.report_product_count = 0
            wizard.report_document_count = 0
            wizard.report_date_range_label = False
            wizard.report_date_from_label = False
            wizard.report_date_to_label = False
            wizard.report_date_range_mode = 'all'

    def _get_effective_report_date_range(self, requirement_lines):
        self.ensure_one()
        line_dates = [line.schedule_date for line in requirement_lines if line.schedule_date]
        if line_dates:
            return min(line_dates), max(line_dates)
        return self.fecha_desde, self.fecha_hasta

    def _get_report_date_range_payload(self, requirement_lines):
        self.ensure_one()
        date_from, date_to = self._get_effective_report_date_range(requirement_lines)
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

    def _sync_requirement_lines(self, row_payloads):
        RequirementLine = self.env['zrn_prodigyn.purchase.planning.wizard.report.requirement.line']
        for wizard in self:
            wizard.report_requirement_line_ids.unlink()
            values = []
            for row in row_payloads:
                values.append({
                    'wizard_id': wizard.id,
                    'source_model': row['source_model'],
                    'source_type_label': row['source_type_label'],
                    'source_reference': row['source_reference'],
                    'source_record_id': row['source_record_id'],
                    'source_state': row['source_state'],
                    'source_state_label': row['source_state_label'],
                    'customer_id': row['customer_id'],
                    'schedule_date': row['schedule_date'],
                    'bom_id': row['bom_id'],
                    'finished_product_id': row['finished_product_id'],
                    'component_id': row['component_id'],
                    'component_uom_id': row['component_uom_id'],
                    'planned_qty': row['planned_qty'],
                    'required_qty': row['required_qty'],
                    'stock_initial': row['stock_initial'],
                    'stock_free': row['stock_free'],
                    'suggested_purchase_qty': row['suggested_purchase_qty'],
                })
            if values:
                RequirementLine.create(values)

    def _sync_supply_lines(self):
        SummaryLine = self.env['zrn_prodigyn.purchase.planning.wizard.report.supply.line']
        for wizard in self:
            wizard.report_supply_line_ids.unlink()
            grouped_lines = {}
            for line in wizard.report_requirement_line_ids.sorted(
                key=lambda item: (item.component_id.display_name or '', item.id)
            ):
                if not line.component_id:
                    continue
                grouped_lines.setdefault(line.component_id.id, self.env['zrn_prodigyn.purchase.planning.wizard.report.requirement.line'])
                grouped_lines[line.component_id.id] |= line

            values = []
            for component_id, lines in grouped_lines.items():
                component = self.env['product.product'].browse(component_id)
                schedule_dates = [line.schedule_date for line in lines if line.schedule_date]
                stock_initial = lines[:1].stock_initial if lines else 0.0
                stock_free = lines[:1].stock_free if lines else 0.0
                total_required_qty = sum(lines.mapped('required_qty'))
                values.append({
                    'wizard_id': wizard.id,
                    'component_id': component.id,
                    'default_code': component.default_code or '',
                    'categ_name': component.categ_id.display_name or '',
                    'document_count': len({(line.source_model, line.source_record_id) for line in lines}),
                    'product_count': len(lines.mapped('finished_product_id')),
                    'line_count': len(lines),
                    'total_required_qty': total_required_qty,
                    'stock_initial': stock_initial,
                    'stock_free': stock_free,
                    'suggested_purchase_qty': max(total_required_qty - stock_free, 0.0),
                    'first_required_date': min(schedule_dates) if schedule_dates else False,
                    'last_required_date': max(schedule_dates) if schedule_dates else False,
                })
            if values:
                SummaryLine.create(values)

    def _sync_product_lines(self):
        SummaryLine = self.env['zrn_prodigyn.purchase.planning.wizard.report.product.line']
        for wizard in self:
            wizard.report_product_line_ids.unlink()
            grouped_lines = {}
            for line in wizard.report_requirement_line_ids.sorted(
                key=lambda item: (item.finished_product_id.display_name or '', item.id)
            ):
                if not line.finished_product_id:
                    continue
                grouped_lines.setdefault(line.finished_product_id.id, self.env['zrn_prodigyn.purchase.planning.wizard.report.requirement.line'])
                grouped_lines[line.finished_product_id.id] |= line

            values = []
            for product_id, lines in grouped_lines.items():
                product = self.env['product.product'].browse(product_id)
                schedule_dates = [line.schedule_date for line in lines if line.schedule_date]
                values.append({
                    'wizard_id': wizard.id,
                    'product_id': product.id,
                    'default_code': product.default_code or '',
                    'categ_name': product.categ_id.display_name or '',
                    'document_count': len({(line.source_model, line.source_record_id) for line in lines}),
                    'component_count': len(lines.mapped('component_id')),
                    'line_count': len(lines),
                    'planned_qty': sum(lines.mapped('planned_qty')),
                    'first_required_date': min(schedule_dates) if schedule_dates else False,
                    'last_required_date': max(schedule_dates) if schedule_dates else False,
                })
            if values:
                SummaryLine.create(values)

    def _sync_document_lines(self):
        SummaryLine = self.env['zrn_prodigyn.purchase.planning.wizard.report.document.line']
        for wizard in self:
            wizard.report_document_line_ids.unlink()
            grouped_lines = {}
            for line in wizard.report_requirement_line_ids.sorted(
                key=lambda item: (item.source_reference or '', item.id)
            ):
                key = (line.source_model, line.source_record_id)
                if not key[1]:
                    continue
                grouped_lines.setdefault(key, self.env['zrn_prodigyn.purchase.planning.wizard.report.requirement.line'])
                grouped_lines[key] |= line

            values = []
            for (_source_model, _source_record_id), lines in grouped_lines.items():
                first_line = lines[:1]
                schedule_dates = [line.schedule_date for line in lines if line.schedule_date]
                values.append({
                    'wizard_id': wizard.id,
                    'source_model': first_line.source_model,
                    'source_type_label': first_line.source_type_label,
                    'source_reference': first_line.source_reference,
                    'source_record_id': first_line.source_record_id,
                    'customer_id': first_line.customer_id.id,
                    'state': first_line.source_state,
                    'state_label': first_line.source_state_label,
                    'product_count': len(lines.mapped('finished_product_id')),
                    'line_count': len(lines),
                    'planned_qty': sum(lines.mapped('planned_qty')),
                    'first_required_date': min(schedule_dates) if schedule_dates else False,
                    'last_required_date': max(schedule_dates) if schedule_dates else False,
                })
            if values:
                SummaryLine.create(values)

    def action_open_report(self):
        self.ensure_one()
        report_view = self.env.ref('zrn_prodigyn.view_zrn_prodigyn_purchase_planning_report_form')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Resumen de abastecimiento',
            'res_model': 'zrn_prodigyn.purchase.planning.wizard',
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

    def _open_summary_list_action(self, action_xmlid, tab_name):
        self.ensure_one()
        action = self.env.ref(action_xmlid).read()[0]
        action['domain'] = [('wizard_id', '=', self.id)]
        action['context'] = {
            'active_id': self.id,
            'default_wizard_id': self.id,
            'zrn_prodigyn_origin_view': 'report',
            'zrn_prodigyn_summary_tab': tab_name,
            'zrn_prodigyn_clean_export_fields': True,
            'zrn_prodigyn_wizard_model': 'zrn_prodigyn.purchase.planning.wizard',
        }
        action['target'] = 'current'
        return action

    def action_open_report_overview(self):
        self.ensure_one()
        return self._open_report_tab('overview')

    def action_open_report_supplies(self):
        self.ensure_one()
        return self._open_report_tab('supplies')

    def action_open_report_supplies_list(self):
        self.ensure_one()
        return self._open_summary_list_action(
            'zrn_prodigyn.action_zrn_prodigyn_purchase_report_supplies',
            'supplies',
        )

    def action_open_report_products(self):
        self.ensure_one()
        return self._open_report_tab('products')

    def action_open_report_products_list(self):
        self.ensure_one()
        return self._open_summary_list_action(
            'zrn_prodigyn.action_zrn_prodigyn_purchase_report_products',
            'products',
        )

    def action_open_report_documents(self):
        self.ensure_one()
        return self._open_report_tab('documents')

    def action_open_report_documents_list(self):
        self.ensure_one()
        return self._open_summary_list_action(
            'zrn_prodigyn.action_zrn_prodigyn_purchase_report_documents',
            'documents',
        )

    @api.model
    def action_back_to_report_from_context(self, wizard_id, summary_tab='overview'):
        wizard = self.browse(wizard_id).exists()
        if not wizard:
            return False
        wizard.report_active_tab = summary_tab or 'overview'
        return wizard.action_open_report()

    def action_continue(self):
        self.ensure_one()
        row_payloads = self._build_requirement_rows_payload(
            filters=self._get_filter_values(include_selected=True),
            include_selected_components=True,
        )
        self._reset_report_payload()
        self._sync_requirement_lines(row_payloads)
        self._sync_supply_lines()
        self._sync_product_lines()
        self._sync_document_lines()
        self.write({
            'report_ready': True,
            'report_active_tab': 'overview',
            'report_row_count': len(self.report_requirement_line_ids),
            'report_supply_count': len(self.report_supply_line_ids),
            'report_product_count': len(self.report_product_line_ids),
            'report_document_count': len(self.report_document_line_ids),
        })
        date_range_payload = self._get_report_date_range_payload(self.report_requirement_line_ids)
        self.write({
            'report_date_range_label': date_range_payload['label'],
            'report_date_from_label': date_range_payload['from_label'],
            'report_date_to_label': date_range_payload['to_label'],
            'report_date_range_mode': date_range_payload['mode'],
        })
        return self.action_open_report()


class ZrnProdigynPurchasePlanningWizardReportRequirementLine(models.TransientModel):
    _name = 'zrn_prodigyn.purchase.planning.wizard.report.requirement.line'
    _description = 'Linea de requerimiento del reporte de abastecimiento'
    _order = 'schedule_date asc, source_reference, component_id'

    wizard_id = fields.Many2one(
        'zrn_prodigyn.purchase.planning.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    source_model = fields.Char(string='Modelo origen')
    source_type_label = fields.Char(string='Tipo de origen')
    source_reference = fields.Char(string='Documento base')
    source_record_id = fields.Integer(string='ID origen')
    source_state = fields.Char(string='Estado tecnico')
    source_state_label = fields.Char(string='Estado')
    customer_id = fields.Many2one('res.partner', string='Punto de venta')
    schedule_date = fields.Date(string='Fecha base')
    bom_id = fields.Many2one('mrp.bom', string='Receta')
    finished_product_id = fields.Many2one('product.product', string='Producto terminado')
    component_id = fields.Many2one('product.product', string='Insumo')
    component_uom_id = fields.Many2one('uom.uom', string='UdM')
    planned_qty = fields.Float(string='Cantidad planeada')
    required_qty = fields.Float(string='Cantidad requerida')
    stock_initial = fields.Float(string='Stock inicial')
    stock_free = fields.Float(string='Stock libre')
    suggested_purchase_qty = fields.Float(string='Compra sugerida')


class ZrnProdigynPurchasePlanningWizardReportSupplyLine(models.TransientModel):
    _name = 'zrn_prodigyn.purchase.planning.wizard.report.supply.line'
    _description = 'Resumen de insumo del reporte de abastecimiento'
    _order = 'first_required_date asc, component_id'

    wizard_id = fields.Many2one(
        'zrn_prodigyn.purchase.planning.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    component_id = fields.Many2one('product.product', string='Insumo', required=True)
    default_code = fields.Char(string='Referencia')
    categ_name = fields.Char(string='Categoria')
    document_count = fields.Integer(string='Ordenes')
    product_count = fields.Integer(string='Productos')
    line_count = fields.Integer(string='Lineas')
    total_required_qty = fields.Float(string='Requerido total')
    stock_initial = fields.Float(string='Stock inicial')
    stock_free = fields.Float(string='Stock libre')
    suggested_purchase_qty = fields.Float(string='Compra sugerida')
    first_required_date = fields.Date(string='Primera fecha')
    last_required_date = fields.Date(string='Ultima fecha')
    component_image_1920 = fields.Binary(related='component_id.image_1920', readonly=True)
    report_detail_requirement_line_ids = fields.Many2many(
        'zrn_prodigyn.purchase.planning.wizard.report.requirement.line',
        string='Lineas incluidas',
        compute='_compute_report_detail_requirement_line_ids',
        readonly=True,
    )

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        fields_info = super().fields_get(allfields=allfields, attributes=attributes)
        if (
            not self.env.context.get('zrn_prodigyn_clean_export_fields')
            or allfields not in (None, [])
        ):
            return fields_info
        allowed_fields = {
            'first_required_date',
            'last_required_date',
            'component_id',
            'default_code',
            'categ_name',
            'document_count',
            'product_count',
            'line_count',
            'total_required_qty',
            'stock_initial',
            'stock_free',
            'suggested_purchase_qty',
        }
        return {
            field_name: field_data
            for field_name, field_data in fields_info.items()
            if field_name in allowed_fields
        }

    @api.depends('wizard_id', 'component_id')
    def _compute_report_detail_requirement_line_ids(self):
        for line in self:
            detail_lines = self.env['zrn_prodigyn.purchase.planning.wizard.report.requirement.line']
            if line.wizard_id and line.component_id:
                detail_lines = line.wizard_id.report_requirement_line_ids.filtered(
                    lambda requirement: requirement.component_id == line.component_id
                )
            line.report_detail_requirement_line_ids = [(6, 0, detail_lines.ids)]

    def action_return_to_report(self):
        self.ensure_one()
        return self.wizard_id.action_open_report()


class ZrnProdigynPurchasePlanningWizardReportProductLine(models.TransientModel):
    _name = 'zrn_prodigyn.purchase.planning.wizard.report.product.line'
    _description = 'Resumen de producto del reporte de abastecimiento'
    _order = 'first_required_date asc, product_id'

    wizard_id = fields.Many2one(
        'zrn_prodigyn.purchase.planning.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    product_id = fields.Many2one('product.product', string='Producto', required=True)
    default_code = fields.Char(string='Referencia')
    categ_name = fields.Char(string='Categoria')
    document_count = fields.Integer(string='Ordenes')
    component_count = fields.Integer(string='Insumos')
    line_count = fields.Integer(string='Lineas')
    planned_qty = fields.Float(string='Cantidad planeada')
    first_required_date = fields.Date(string='Primera fecha')
    last_required_date = fields.Date(string='Ultima fecha')
    product_image_1920 = fields.Binary(related='product_id.image_1920', readonly=True)
    report_detail_requirement_line_ids = fields.Many2many(
        'zrn_prodigyn.purchase.planning.wizard.report.requirement.line',
        string='Lineas incluidas',
        compute='_compute_report_detail_requirement_line_ids',
        readonly=True,
    )

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        fields_info = super().fields_get(allfields=allfields, attributes=attributes)
        if (
            not self.env.context.get('zrn_prodigyn_clean_export_fields')
            or allfields not in (None, [])
        ):
            return fields_info
        allowed_fields = {
            'first_required_date',
            'last_required_date',
            'product_id',
            'default_code',
            'categ_name',
            'document_count',
            'component_count',
            'line_count',
            'planned_qty',
        }
        return {
            field_name: field_data
            for field_name, field_data in fields_info.items()
            if field_name in allowed_fields
        }

    @api.depends('wizard_id', 'product_id')
    def _compute_report_detail_requirement_line_ids(self):
        for line in self:
            detail_lines = self.env['zrn_prodigyn.purchase.planning.wizard.report.requirement.line']
            if line.wizard_id and line.product_id:
                detail_lines = line.wizard_id.report_requirement_line_ids.filtered(
                    lambda requirement: requirement.finished_product_id == line.product_id
                )
            line.report_detail_requirement_line_ids = [(6, 0, detail_lines.ids)]

    def action_return_to_report(self):
        self.ensure_one()
        return self.wizard_id.action_open_report()


class ZrnProdigynPurchasePlanningWizardReportDocumentLine(models.TransientModel):
    _name = 'zrn_prodigyn.purchase.planning.wizard.report.document.line'
    _description = 'Resumen de documento del reporte de abastecimiento'
    _order = 'first_required_date asc, source_reference'

    wizard_id = fields.Many2one(
        'zrn_prodigyn.purchase.planning.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    source_model = fields.Char(string='Modelo origen')
    source_type_label = fields.Char(string='Tipo de origen')
    source_reference = fields.Char(string='Documento base')
    source_record_id = fields.Integer(string='ID origen')
    customer_id = fields.Many2one('res.partner', string='Punto de venta')
    state = fields.Char(string='Estado tecnico')
    state_label = fields.Char(string='Estado')
    product_count = fields.Integer(string='Productos')
    line_count = fields.Integer(string='Lineas')
    planned_qty = fields.Float(string='Cantidad planeada')
    first_required_date = fields.Date(string='Primera fecha')
    last_required_date = fields.Date(string='Ultima fecha')
    report_detail_requirement_line_ids = fields.Many2many(
        'zrn_prodigyn.purchase.planning.wizard.report.requirement.line',
        string='Lineas incluidas',
        compute='_compute_report_detail_requirement_line_ids',
        readonly=True,
    )

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        fields_info = super().fields_get(allfields=allfields, attributes=attributes)
        if (
            not self.env.context.get('zrn_prodigyn_clean_export_fields')
            or allfields not in (None, [])
        ):
            return fields_info
        allowed_fields = {
            'first_required_date',
            'last_required_date',
            'source_type_label',
            'source_reference',
            'customer_id',
            'state_label',
            'product_count',
            'line_count',
            'planned_qty',
        }
        return {
            field_name: field_data
            for field_name, field_data in fields_info.items()
            if field_name in allowed_fields
        }

    @api.depends('wizard_id', 'source_model', 'source_record_id')
    def _compute_report_detail_requirement_line_ids(self):
        for line in self:
            detail_lines = self.env['zrn_prodigyn.purchase.planning.wizard.report.requirement.line']
            if line.wizard_id and line.source_model and line.source_record_id:
                detail_lines = line.wizard_id.report_requirement_line_ids.filtered(
                    lambda requirement: (
                        requirement.source_model == line.source_model
                        and requirement.source_record_id == line.source_record_id
                    )
                )
            line.report_detail_requirement_line_ids = [(6, 0, detail_lines.ids)]

    def action_return_to_report(self):
        self.ensure_one()
        return self.wizard_id.action_open_report()
