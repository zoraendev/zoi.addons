# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ZrnProdigynProductionPlanningWizard(models.TransientModel):
    _name = 'zrn_prodigyn.production.planning.wizard'
    _description = 'Filtros de planeacion de produccion'
    _rec_name = 'name'

    name = fields.Char(string='Titulo', default='Filtros de fabricacion')
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
        self._compute_filter_data()
        return self.action_open_filters()

    def action_open_filters(self):
        self.ensure_one()
        filter_view = self.env.ref('zrn_prodigyn.view_zrn_prodigyn_production_planning_filter_form')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Filtros de fabricacion',
            'res_model': 'zrn_prodigyn.production.planning.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': filter_view.id,
            'views': [(filter_view.id, 'form')],
            'target': 'current',
            '_noBreadcrumbs': True,
        }

    def action_continue(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Filtros listos',
                'message': 'La vista del reporte se agregara en el siguiente paso.',
                'type': 'info',
                'sticky': False,
            },
        }
