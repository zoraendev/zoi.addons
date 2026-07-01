# -*- coding: utf-8 -*-

from datetime import datetime, time

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .planning_models import ZrnPlanningNavigationMixin


class ZrnPlanningInventoryReconciliation(ZrnPlanningNavigationMixin, models.Model):
    _name = 'zrn_planning.inventory.reconciliation'
    _description = 'Cuadre de inventario'

    name = fields.Char(string='Nombre', required=True, default='Cuadre Inventario')
    date_from = fields.Date(string='Fecha desde')
    date_to = fields.Date(string='Fecha hasta')
    only_on_hand = fields.Boolean(string='Solo con stock disponible', default=True)
    show_archived = fields.Boolean(string='Mostrar archivados')
    line_ids = fields.One2many(
        'zrn_planning.inventory.reconciliation.line',
        'reconciliation_id',
        string='Lotes visibles',
    )
    lot_ids = fields.Many2many('stock.lot', string='Lotes filtrados', compute='_compute_lot_ids', readonly=True)
    lot_count = fields.Integer(string='Lotes', compute='_compute_lot_ids', readonly=True)
    active_lot_count = fields.Integer(string='Activos', compute='_compute_lot_ids', readonly=True)
    archived_lot_count = fields.Integer(string='Archivados', compute='_compute_lot_ids', readonly=True)
    stock_qty_total = fields.Float(string='Stock total', compute='_compute_lot_ids', readonly=True)
    selected_line_count = fields.Integer(string='Lotes seleccionados', compute='_compute_selected_line_count', readonly=True)
    date_range_mode = fields.Selection(
        [('range', 'Rango'), ('from', 'Desde'), ('to', 'Hasta'), ('all', 'Todos')],
        compute='_compute_date_range_labels',
        readonly=True,
    )
    date_from_label = fields.Char(string='Fecha desde label', compute='_compute_date_range_labels', readonly=True)
    date_to_label = fields.Char(string='Fecha hasta label', compute='_compute_date_range_labels', readonly=True)
    date_range_label = fields.Char(string='Etiqueta de rango', compute='_compute_date_range_labels', readonly=True)

    @api.depends('date_from', 'date_to')
    def _compute_date_range_labels(self):
        for record in self:
            record.date_from_label = fields.Date.to_string(record.date_from) if record.date_from else False
            record.date_to_label = fields.Date.to_string(record.date_to) if record.date_to else False
            if record.date_from and record.date_to:
                record.date_range_mode = 'range'
                record.date_range_label = False
            elif record.date_from:
                record.date_range_mode = 'from'
                record.date_range_label = False
            elif record.date_to:
                record.date_range_mode = 'to'
                record.date_range_label = False
            else:
                record.date_range_mode = 'all'
                record.date_range_label = 'Todos los lotes vigentes'

    @api.depends('date_from', 'date_to', 'only_on_hand', 'show_archived')
    def _compute_lot_ids(self):
        for record in self:
            lots = record._get_filtered_lots()
            record.lot_ids = lots
            record.lot_count = len(lots)
            record.active_lot_count = len(lots.filtered('active'))
            record.archived_lot_count = len(lots.filtered(lambda lot: not lot.active))
            record.stock_qty_total = sum(lots.mapped('product_qty'))

    @api.depends('line_ids.is_selected')
    def _compute_selected_line_count(self):
        for record in self:
            record.selected_line_count = len(record.line_ids.filtered('is_selected'))

    def _get_lot_search_model(self):
        self.ensure_one()
        lot_model = self.env['stock.lot']
        if self.show_archived:
            lot_model = lot_model.with_context(active_test=False)
        return lot_model

    def _get_filtered_lots(self):
        self.ensure_one()
        domain = []
        if self.only_on_hand:
            domain.append(('product_qty', '>', 0))
        if self.date_from:
            date_from = datetime.combine(self.date_from, time.min)
            domain.append(('create_date', '>=', fields.Datetime.to_string(date_from)))
        if self.date_to:
            date_to = datetime.combine(self.date_to, time.max)
            domain.append(('create_date', '<=', fields.Datetime.to_string(date_to)))
        return self._get_lot_search_model().search(domain, order='create_date asc, id asc')

    def _sync_lot_lines(self, lots=None):
        self.ensure_one()
        lots = lots or self._get_filtered_lots()
        existing_lines = {line.lot_id.id: line for line in self.line_ids}
        wanted_ids = set(lots.ids)

        stale_lines = self.line_ids.filtered(lambda line: line.lot_id.id not in wanted_ids)
        if stale_lines:
            stale_lines.unlink()

        create_vals = []
        for sequence, lot in enumerate(lots, start=1):
            line = existing_lines.get(lot.id)
            if line:
                if line.sequence != sequence:
                    line.sequence = sequence
                continue
            create_vals.append({
                'reconciliation_id': self.id,
                'lot_id': lot.id,
                'sequence': sequence,
            })
        if create_vals:
            self.env['zrn_planning.inventory.reconciliation.line'].create(create_vals)

    def _clear_line_selection(self):
        self.ensure_one()
        selected_lines = self.line_ids.filtered('is_selected')
        if selected_lines:
            selected_lines.write({'is_selected': False})

    def _get_selected_lots(self):
        self.ensure_one()
        return self.line_ids.filtered('is_selected').mapped('lot_id')

    def _require_scope_for_mass_action(self):
        self.ensure_one()
        if not self.date_from and not self.date_to:
            raise UserError(_('Defina al menos una fecha antes de ejecutar una accion masiva sobre lotes.'))

    def action_apply_filters(self):
        self.ensure_one()
        self._sync_lot_lines()
        return self._open_singleton_action('zrn_planning.action_zrn_planning_inventory_reconciliation')

    def action_archive_filtered_lots(self):
        self.ensure_one()
        self._require_scope_for_mass_action()
        lots = self._get_filtered_lots().filtered('active')
        if not lots:
            raise UserError(_('No hay lotes activos dentro del rango seleccionado.'))
        lots.action_archive()
        self._clear_line_selection()
        self._sync_lot_lines()
        return self._open_singleton_action('zrn_planning.action_zrn_planning_inventory_reconciliation')

    def action_archive_selected_lots(self):
        self.ensure_one()
        self._require_scope_for_mass_action()
        lots = self._get_selected_lots().filtered('active')
        if not lots:
            raise UserError(_('Seleccione al menos un lote activo para archivarlo.'))
        lots.action_archive()
        self._clear_line_selection()
        self._sync_lot_lines()
        return self._open_singleton_action('zrn_planning.action_zrn_planning_inventory_reconciliation')

    def action_unarchive_filtered_lots(self):
        self.ensure_one()
        self._require_scope_for_mass_action()
        lots = self.env['stock.lot'].with_context(active_test=False).browse(self._get_filtered_lots().ids).filtered(lambda lot: not lot.active)
        if not lots:
            raise UserError(_('No hay lotes archivados dentro del rango seleccionado.'))
        lots.action_unarchive()
        self._clear_line_selection()
        self._sync_lot_lines()
        return self._open_singleton_action('zrn_planning.action_zrn_planning_inventory_reconciliation')

    def action_open_filtered_lots(self):
        self.ensure_one()
        action = self.env.ref('stock.action_production_lot_form').read()[0]
        action['name'] = _('Lotes filtrados')
        action['domain'] = [('id', 'in', self._get_filtered_lots().ids)]
        action['context'] = {
            'active_test': False,
            'display_complete': True,
            'search_default_group_by_product': 1,
            'search_default_on_hand': 1,
            'default_company_id': self.env.company.id,
        }
        return action


class ZrnPlanningInventoryReconciliationLine(models.Model):
    _name = 'zrn_planning.inventory.reconciliation.line'
    _description = 'Linea visible de cuadre de inventario'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Secuencia', default=10)
    reconciliation_id = fields.Many2one(
        'zrn_planning.inventory.reconciliation',
        string='Cuadre',
        required=True,
        ondelete='cascade',
    )
    lot_id = fields.Many2one('stock.lot', string='Lote', required=True, ondelete='cascade')
    is_selected = fields.Boolean(string='Seleccionar')
    lot_state = fields.Selection(
        [
            ('active', 'Activo'),
            ('archived', 'Archivado'),
        ],
        string='Estado',
        compute='_compute_lot_state',
        readonly=True,
    )
    name = fields.Char(related='lot_id.name', string='Codigo lote', readonly=True)
    product_id = fields.Many2one(related='lot_id.product_id', string='Producto', readonly=True)
    ref = fields.Char(related='lot_id.ref', string='Referencia interna', readonly=True)
    create_date = fields.Datetime(related='lot_id.create_date', string='Fecha lote', readonly=True)
    zrn_oldest_in_date = fields.Datetime(related='lot_id.zrn_oldest_in_date', string='Primera entrada', readonly=True)
    product_qty = fields.Float(related='lot_id.product_qty', string='Stock disponible', readonly=True)
    zrn_location_names = fields.Char(related='lot_id.zrn_location_names', string='Ubicaciones', readonly=True)
    company_id = fields.Many2one(related='lot_id.company_id', string='Compania', readonly=True)

    @api.depends('lot_id.active')
    def _compute_lot_state(self):
        for line in self:
            line.lot_state = 'active' if line.lot_id.active else 'archived'
