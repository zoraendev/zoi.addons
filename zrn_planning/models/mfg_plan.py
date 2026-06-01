# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ZrnPlanningMfgPlan(models.Model):
    _name = 'zrn_planning.mfg.plan'
    _description = 'Plan maestro de fabricacion y abastecimiento'
    _order = 'date_start desc, id desc'

    name = fields.Char(
        string='Nombre',
        required=True,
        default='Nuevo plan de fabricacion',
    )
    active = fields.Boolean(string='Activo', default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Compania',
        required=True,
        default=lambda self: self.env.company,
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Bodega',
        default=lambda self: self.env['stock.warehouse'].search(
            [('company_id', '=', self.env.company.id)],
            limit=1,
        ),
    )
    date_start = fields.Date(string='Fecha inicio')
    date_end = fields.Date(string='Fecha fin')
    planning_basis = fields.Selection(
        [
            ('sale', 'Ordenes de venta'),
            ('mrp', 'Ordenes de fabricacion'),
            ('mixed', 'Mixto'),
        ],
        string='Base de planeacion',
        required=True,
        default='sale',
    )
    state = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('pending_confirmation', 'Pendiente de confirmar'),
            ('approved', 'Aprobado'),
            ('released', 'Liberado'),
            ('done', 'Finalizado'),
            ('cancel', 'Cancelado'),
        ],
        string='Estado',
        required=True,
        default='draft',
    )
    notes = fields.Text(string='Notas')
    approved_at = fields.Datetime(string='Aprobado el')
    approved_by = fields.Many2one('res.users', string='Aprobado por')
    released_at = fields.Datetime(string='Liberado el')
    released_by = fields.Many2one('res.users', string='Liberado por')
    line_ids = fields.One2many(
        'zrn_planning.mfg.plan.line',
        'plan_id',
        string='Lineas del plan',
    )
    source_ids = fields.One2many(
        'zrn_planning.mfg.plan.source',
        'plan_id',
        string='Origenes del plan',
    )
    line_count = fields.Integer(
        string='Lineas',
        compute='_compute_counts',
        store=False,
    )
    source_count = fields.Integer(
        string='Origenes',
        compute='_compute_counts',
        store=False,
    )
    supply_count = fields.Integer(
        string='Insumos',
        compute='_compute_counts',
        store=False,
    )
    production_ids = fields.Many2many(
        'mrp.production',
        string='Ordenes de fabricacion',
        compute='_compute_counts',
        store=False,
    )
    production_count = fields.Integer(
        string='OFs',
        compute='_compute_counts',
        store=False,
    )

    @api.depends('line_ids', 'line_ids.supply_ids', 'line_ids.production_ids', 'source_ids')
    def _compute_counts(self):
        for plan in self:
            plan.line_count = len(plan.line_ids)
            plan.source_count = len(plan.source_ids)
            plan.supply_count = len(plan.line_ids.mapped('supply_ids'))
            plan.production_ids = [(6, 0, plan.line_ids.mapped('production_ids').ids)]
            plan.production_count = len(plan.line_ids.mapped('production_ids'))

    def _create_draft_mrp_productions(self):
        Production = self.env['mrp.production']
        created_productions = Production

        for plan in self:
            for line in plan.line_ids:
                if line.production_ids:
                    continue
                if not line.product_id:
                    continue

                bom = line.bom_id
                if not bom:
                    bom = self.env['mrp.bom'].search([('product_id', '=', line.product_id.id)], limit=1)
                if not bom:
                    bom = self.env['mrp.bom'].search(
                        [('product_tmpl_id', '=', line.product_id.product_tmpl_id.id)],
                        limit=1,
                    )

                qty_planned = float(line.qty_planned or 0.0)
                if qty_planned <= 0:
                    continue

                production_vals = {
                    'product_id': line.product_id.id,
                    'product_uom_id': line.product_id.uom_id.id,
                    'product_qty': qty_planned,
                    'bom_id': bom.id if bom else False,
                    'date_start': line.production_date,
                    'date_deadline': line.delivery_date or line.production_date,
                    'origin': plan.name,
                    'company_id': plan.company_id.id,
                    'location_src_id': (
                        plan.warehouse_id.lot_stock_id.id
                        if plan.warehouse_id and plan.warehouse_id.lot_stock_id
                        else False
                    ),
                    'location_dest_id': (
                        bom.picking_type_id.default_location_dest_id.id
                        if bom and bom.picking_type_id and bom.picking_type_id.default_location_dest_id
                        else (
                            plan.warehouse_id.manu_type_id.default_location_dest_id.id
                            if plan.warehouse_id and plan.warehouse_id.manu_type_id
                            and plan.warehouse_id.manu_type_id.default_location_dest_id
                            else False
                        )
                    ),
                    'picking_type_id': (
                        bom.picking_type_id.id
                        if bom and bom.picking_type_id
                        else (
                            plan.warehouse_id.manu_type_id.id
                            if plan.warehouse_id and plan.warehouse_id.manu_type_id
                            else False
                        )
                    ),
                    'zrn_planning_plan_id': plan.id,
                    'zrn_planning_plan_line_id': line.id,
                }
                production = Production.create(production_vals)
                line.qty_released = qty_planned
                line.state = 'released'
                created_productions |= production

        return created_productions

    def action_confirm_plan(self):
        for plan in self:
            if plan.state not in ('draft', 'pending_confirmation'):
                continue
            if not plan.line_ids:
                raise UserError(_('El planning no tiene lineas para confirmar.'))

            plan._create_draft_mrp_productions()
            plan.write({
                'state': 'approved',
                'approved_at': fields.Datetime.now(),
                'approved_by': self.env.user.id,
            })
        return True


class ZrnPlanningMfgPlanLine(models.Model):
    _name = 'zrn_planning.mfg.plan.line'
    _description = 'Linea del plan maestro de fabricacion'
    _order = 'production_date asc, sequence asc, id asc'

    plan_id = fields.Many2one(
        'zrn_planning.mfg.plan',
        string='Plan',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(string='Secuencia', default=10)
    company_id = fields.Many2one(
        related='plan_id.company_id',
        string='Compania',
        store=True,
        readonly=True,
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Bodega',
        default=lambda self: self.env['stock.warehouse'].search(
            [('company_id', '=', self.env.company.id)],
            limit=1,
        ),
    )
    responsible_id = fields.Many2one('res.users', string='Responsable')
    product_id = fields.Many2one(
        'product.product',
        string='Producto terminado',
        required=True,
        domain=[('detailed_type', 'in', ['product', 'consu'])],
    )
    bom_id = fields.Many2one(
        'mrp.bom',
        string='Receta',
        domain="[('product_tmpl_id', '=', product_id.product_tmpl_id)]",
    )
    production_date = fields.Date(string='Fecha de produccion', required=True)
    delivery_date = fields.Date(string='Fecha de entrega objetivo')
    qty_planned = fields.Float(string='Cantidad planeada', digits='Product Unit of Measure', default=0.0)
    qty_released = fields.Float(string='Cantidad liberada', digits='Product Unit of Measure', default=0.0)
    qty_executed = fields.Float(string='Cantidad ejecutada', digits='Product Unit of Measure', default=0.0)
    state = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('ready', 'Lista'),
            ('released', 'Liberada'),
            ('in_progress', 'En proceso'),
            ('done', 'Finalizada'),
            ('cancel', 'Cancelada'),
        ],
        string='Estado',
        required=True,
        default='draft',
    )
    notes = fields.Text(string='Notas')
    supply_ids = fields.One2many(
        'zrn_planning.mfg.plan.supply',
        'plan_line_id',
        string='Insumos',
    )
    supply_count = fields.Integer(
        string='Cantidad de insumos',
        compute='_compute_supply_count',
        store=False,
    )
    production_ids = fields.One2many(
        'mrp.production',
        'zrn_planning_plan_line_id',
        string='Ordenes de fabricacion',
        readonly=True,
    )
    production_count = fields.Integer(
        string='Cantidad de OFs',
        compute='_compute_supply_count',
        store=False,
    )

    @api.depends('supply_ids', 'production_ids')
    def _compute_supply_count(self):
        for line in self:
            line.supply_count = len(line.supply_ids)
            line.production_count = len(line.production_ids)


class ZrnPlanningMfgPlanSupply(models.Model):
    _name = 'zrn_planning.mfg.plan.supply'
    _description = 'Insumo requerido por una linea de plan maestro'
    _order = 'component_id, id'

    plan_line_id = fields.Many2one(
        'zrn_planning.mfg.plan.line',
        string='Linea del plan',
        required=True,
        ondelete='cascade',
    )
    company_id = fields.Many2one(
        related='plan_line_id.company_id',
        string='Compania',
        store=True,
        readonly=True,
    )
    component_id = fields.Many2one(
        'product.product',
        string='Insumo',
        required=True,
        domain=[('detailed_type', 'in', ['product', 'consu'])],
    )
    qty_per_unit = fields.Float(string='Cantidad por unidad', digits='Product Unit of Measure', default=0.0)
    qty_required = fields.Float(string='Cantidad requerida', digits='Product Unit of Measure', default=0.0)
    qty_on_hand = fields.Float(string='Stock actual', digits='Product Unit of Measure', default=0.0)
    qty_forecast = fields.Float(string='Stock proyectado', digits='Product Unit of Measure', default=0.0)
    qty_to_buy = fields.Float(string='Cantidad a comprar', digits='Product Unit of Measure', default=0.0)
    qty_to_produce = fields.Float(string='Cantidad a producir', digits='Product Unit of Measure', default=0.0)
    supply_status = fields.Selection(
        [
            ('pending', 'Pendiente'),
            ('covered_stock', 'Cubierto con stock'),
            ('to_buy', 'Comprar'),
            ('to_produce', 'Producir'),
            ('mixed', 'Mixto'),
        ],
        string='Estado de abastecimiento',
        required=True,
        default='pending',
    )


class ZrnPlanningMfgPlanSource(models.Model):
    _name = 'zrn_planning.mfg.plan.source'
    _description = 'Documento origen del plan maestro'
    _order = 'source_date asc, id asc'

    plan_id = fields.Many2one(
        'zrn_planning.mfg.plan',
        string='Plan',
        required=True,
        ondelete='cascade',
    )
    source_model = fields.Char(string='Modelo origen', required=True)
    source_id = fields.Integer(string='ID origen', required=True)
    source_ref = fields.Char(string='Referencia')
    customer_id = fields.Many2one('res.partner', string='Cliente / punto de venta')
    source_date = fields.Date(string='Fecha origen')
    source_state = fields.Char(string='Estado origen')


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    zrn_planning_plan_id = fields.Many2one(
        'zrn_planning.mfg.plan',
        string='Planning Planning',
        readonly=True,
        copy=False,
    )
    zrn_planning_plan_line_id = fields.Many2one(
        'zrn_planning.mfg.plan.line',
        string='Linea de planning Planning',
        readonly=True,
        copy=False,
    )
