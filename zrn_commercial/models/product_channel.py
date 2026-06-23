# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ZrnCommercialProductChannel(models.Model):
    _name = 'zrn_commercial.product.channel'
    _description = 'Canal de producto'
    _order = 'name, id'

    name = fields.Char(string='Canal de producto', required=True)
    code = fields.Char(string='Codigo')
    active = fields.Boolean(string='Activo', default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Compania',
        required=True,
        default=lambda self: self.env.company,
    )
    description = fields.Text(string='Descripcion')
    notes = fields.Text(string='Notas internas')
    owner_user_id = fields.Many2one('res.users', string='Responsable')
    usage_type = fields.Selection(
        [
            ('inventory', 'Inventario'),
            ('commercial', 'Comercial'),
        ],
        string='Uso',
        required=True,
        default='inventory',
    )
    min_stock_days = fields.Float(string='Cobertura minima (dias)', default=7.0)
    target_stock_days = fields.Float(string='Cobertura objetivo (dias)', default=21.0)
    max_stock_days = fields.Float(string='Cobertura maxima (dias)', default=45.0)
    product_link_ids = fields.One2many(
        'zrn_commercial.product.channel.product',
        'channel_id',
        string='Productos asignados',
    )
    product_count = fields.Integer(
        string='Productos',
        compute='_compute_product_count',
        store=False,
    )

    _sql_constraints = [
        (
            'zrn_product_channel_company_code_uniq',
            'unique(company_id, code)',
            'El codigo del canal de producto debe ser unico por compania.',
        ),
        (
            'zrn_product_channel_company_name_uniq',
            'unique(company_id, name)',
            'El nombre del canal de producto debe ser unico por compania.',
        ),
    ]

    @api.depends('product_link_ids')
    def _compute_product_count(self):
        for channel in self:
            channel.product_count = len(channel.product_link_ids.filtered(lambda link: link.active))

    @api.constrains('min_stock_days', 'target_stock_days', 'max_stock_days')
    def _check_stock_days(self):
        for channel in self:
            if channel.min_stock_days < 0 or channel.target_stock_days < 0 or channel.max_stock_days < 0:
                raise ValidationError('Los dias de cobertura no pueden ser negativos.')
            if channel.target_stock_days and channel.min_stock_days > channel.target_stock_days:
                raise ValidationError('La cobertura minima no puede ser mayor a la cobertura objetivo.')
            if channel.max_stock_days and channel.target_stock_days > channel.max_stock_days:
                raise ValidationError('La cobertura objetivo no puede ser mayor a la cobertura maxima.')

    def action_open_products(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('product.product_normal_action')
        action['domain'] = [('product_tmpl_id.zrn_product_channel_id', '=', self.id)]
        action['context'] = dict(self.env.context, default_zrn_product_channel_id=self.id)
        return action


class ZrnCommercialProductChannelProduct(models.Model):
    _name = 'zrn_commercial.product.channel.product'
    _description = 'Producto asignado a canal de producto'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Secuencia', default=10)
    channel_id = fields.Many2one(
        'zrn_commercial.product.channel',
        string='Canal de producto',
        required=True,
        ondelete='cascade',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Compania',
        related='channel_id.company_id',
        store=True,
        readonly=True,
    )
    available_product_tmpl_ids = fields.Many2many(
        'product.template',
        string='Productos disponibles',
        compute='_compute_available_product_tmpl_ids',
        store=False,
    )
    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Producto',
        required=True,
        ondelete='restrict',
        domain="[('id', 'in', available_product_tmpl_ids)]",
    )
    product_variant_id = fields.Many2one(
        'product.product',
        string='Variante principal',
        related='product_tmpl_id.product_variant_id',
        store=True,
        readonly=True,
    )
    default_code = fields.Char(
        string='Referencia interna',
        related='product_tmpl_id.default_code',
        store=True,
        readonly=True,
    )
    categ_id = fields.Many2one(
        'product.category',
        string='Categoria',
        related='product_tmpl_id.categ_id',
        store=True,
        readonly=True,
    )
    active = fields.Boolean(string='Activo', default=True)
    notes = fields.Text(string='Notas')

    _sql_constraints = [
        (
            'zrn_product_channel_product_tmpl_uniq',
            'unique(product_tmpl_id)',
            'El producto ya fue asignado a un canal de producto.',
        ),
    ]

    @api.depends('channel_id', 'product_tmpl_id')
    def _compute_available_product_tmpl_ids(self):
        ProductTemplate = self.env['product.template']
        assigned_ids = self.search([]).mapped('product_tmpl_id').ids
        for record in self:
            current_ids = record.product_tmpl_id.ids
            blocked_ids = list(set(assigned_ids) - set(current_ids))
            record.available_product_tmpl_ids = ProductTemplate.search([
                ('detailed_type', 'in', ['product', 'consu']),
                ('id', 'not in', blocked_ids),
            ])

    @api.constrains('product_tmpl_id')
    def _check_allowed_product(self):
        for record in self:
            if record.product_tmpl_id and record.product_tmpl_id.detailed_type == 'service':
                raise ValidationError('No se pueden asignar servicios a un canal de producto.')

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_template_primary_channel()
        return records

    def write(self, vals):
        result = super().write(vals)
        self._sync_template_primary_channel()
        return result

    def unlink(self):
        templates = self.mapped('product_tmpl_id')
        result = super().unlink()
        templates._compute_zrn_product_channel_id()
        return result

    def _sync_template_primary_channel(self):
        templates = self.mapped('product_tmpl_id')
        templates._compute_zrn_product_channel_id()


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    zrn_product_channel_id = fields.Many2one(
        'zrn_commercial.product.channel',
        string='Canal de producto principal',
        compute='_compute_zrn_product_channel_id',
        search='_search_zrn_product_channel_id',
        store=False,
    )

    def _compute_zrn_product_channel_id(self):
        link_model = self.env['zrn_commercial.product.channel.product'].sudo()
        grouped_links = {
            link.product_tmpl_id.id: link.channel_id
            for link in link_model.search([('product_tmpl_id', 'in', self.ids)])
        }
        for template in self:
            template.zrn_product_channel_id = grouped_links.get(template.id)

    def _search_zrn_product_channel_id(self, operator, value):
        links = self.env['zrn_commercial.product.channel.product'].sudo().search([
            ('channel_id', operator, value),
        ])
        return [('id', 'in', links.mapped('product_tmpl_id').ids)]
