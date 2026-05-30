# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ZrnProdigynCommercialBrand(models.Model):
    _name = 'zrn_prodigyn.commercial.brand'
    _description = 'Marca comercial'
    _order = 'name, id'

    name = fields.Char(string='Marca comercial', required=True)
    code = fields.Char(string='Codigo')
    active = fields.Boolean(string='Activo', default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Compania',
        required=True,
        default=lambda self: self.env.company,
    )
    owner_partner_id = fields.Many2one(
        'res.partner',
        string='Titular / proveedor',
        domain=[('is_company', '=', True)],
    )
    logo = fields.Image(string='Logo', max_width=512, max_height=512, attachment=False)
    website = fields.Char(string='Sitio web')
    email = fields.Char(string='Correo')
    phone = fields.Char(string='Telefono')
    country_id = fields.Many2one('res.country', string='Pais')
    launch_date = fields.Date(string='Fecha de lanzamiento')
    description = fields.Text(string='Descripcion')
    notes = fields.Text(string='Notas internas')
    product_link_ids = fields.One2many(
        'zrn_prodigyn.commercial.brand.product',
        'brand_id',
        string='Productos asignados',
    )
    product_count = fields.Integer(
        string='Productos',
        compute='_compute_product_count',
        store=False,
    )

    _sql_constraints = [
        (
            'company_code_uniq',
            'unique(company_id, code)',
            'El codigo de marca debe ser unico por compania.',
        ),
    ]

    @api.depends('product_link_ids')
    def _compute_product_count(self):
        for brand in self:
            brand.product_count = len(brand.product_link_ids)


class ZrnProdigynCommercialBrandProduct(models.Model):
    _name = 'zrn_prodigyn.commercial.brand.product'
    _description = 'Producto asignado a marca comercial'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Secuencia', default=10)
    brand_id = fields.Many2one(
        'zrn_prodigyn.commercial.brand',
        string='Marca comercial',
        required=True,
        ondelete='cascade',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Compania',
        related='brand_id.company_id',
        store=True,
        readonly=True,
    )
    product_id = fields.Many2one(
        'product.product',
        string='Producto',
        required=True,
        ondelete='restrict',
        domain=[('sale_ok', '=', True)],
    )
    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Plantilla de producto',
        related='product_id.product_tmpl_id',
        store=True,
        readonly=True,
    )
    default_code = fields.Char(
        string='Referencia interna',
        related='product_id.default_code',
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
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unidad de medida',
        related='product_id.uom_id',
        store=True,
        readonly=True,
    )
    active = fields.Boolean(string='Activo', default=True)
    notes = fields.Text(string='Notas')

    _sql_constraints = [
        (
            'product_uniq',
            'unique(product_id)',
            'El producto ya fue asignado a una marca comercial.',
        ),
    ]

    @api.constrains('product_id')
    def _check_sale_ok_product(self):
        for record in self:
            if record.product_id and not record.product_id.sale_ok:
                raise ValidationError('Solo se pueden asignar productos configurados para venta.')
