# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ZrnProdigynMfgPlan(models.Model):
    _name = 'zrn_prodigyn.mfg.plan'
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
        'zrn_prodigyn.mfg.plan.line',
        'plan_id',
        string='Lineas del plan',
    )
    source_ids = fields.One2many(
        'zrn_prodigyn.mfg.plan.source',
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

    @api.depends('line_ids', 'line_ids.supply_ids', 'source_ids')
    def _compute_counts(self):
        for plan in self:
            plan.line_count = len(plan.line_ids)
            plan.source_count = len(plan.source_ids)
            plan.supply_count = len(plan.line_ids.mapped('supply_ids'))


class ZrnProdigynMfgPlanLine(models.Model):
    _name = 'zrn_prodigyn.mfg.plan.line'
    _description = 'Linea del plan maestro de fabricacion'
    _order = 'production_date asc, sequence asc, id asc'

    plan_id = fields.Many2one(
        'zrn_prodigyn.mfg.plan',
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
        'zrn_prodigyn.mfg.plan.supply',
        'plan_line_id',
        string='Insumos',
    )
    supply_count = fields.Integer(
        string='Cantidad de insumos',
        compute='_compute_supply_count',
        store=False,
    )

    @api.depends('supply_ids')
    def _compute_supply_count(self):
        for line in self:
            line.supply_count = len(line.supply_ids)


class ZrnProdigynMfgPlanSupply(models.Model):
    _name = 'zrn_prodigyn.mfg.plan.supply'
    _description = 'Insumo requerido por una linea de plan maestro'
    _order = 'component_id, id'

    plan_line_id = fields.Many2one(
        'zrn_prodigyn.mfg.plan.line',
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


class ZrnProdigynMfgPlanSource(models.Model):
    _name = 'zrn_prodigyn.mfg.plan.source'
    _description = 'Documento origen del plan maestro'
    _order = 'source_date asc, id asc'

    plan_id = fields.Many2one(
        'zrn_prodigyn.mfg.plan',
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
