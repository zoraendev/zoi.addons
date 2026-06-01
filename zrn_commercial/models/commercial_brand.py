# -*- coding: utf-8 -*-

import base64
import binascii

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.image import ImageProcess
from odoo.tools.mimetypes import guess_mimetype


class ZrnCommercialBrand(models.Model):
    _name = 'zrn_commercial.commercial.brand'
    _description = 'Marca comercial'
    _order = 'name, id'

    _LOGO_MAX_FILE_SIZE = 5 * 1024 * 1024
    _LOGO_ALLOWED_MIMETYPES = {
        'image/jpeg',
        'image/png',
        'image/webp',
    }

    name = fields.Char(string='Marca comercial', required=True)
    code = fields.Char(string='Codigo')
    active = fields.Boolean(string='Activo', default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Compania',
        required=True,
        default=lambda self: self.env.company,
    )
    owner_name = fields.Char(string='Empresa titular')
    logo = fields.Image(string='Logo', max_width=512, max_height=512, attachment=False)
    website = fields.Char(string='Sitio web')
    email = fields.Char(string='Correo')
    phone = fields.Char(string='Telefono')
    country_id = fields.Many2one('res.country', string='Pais')
    launch_date = fields.Date(string='Fecha de lanzamiento')
    description = fields.Text(string='Descripcion')
    notes = fields.Text(string='Notas internas')
    product_link_ids = fields.One2many(
        'zrn_commercial.commercial.brand.product',
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

    @api.constrains('logo')
    def _check_logo_file(self):
        for brand in self:
            if not brand.logo:
                continue

            try:
                logo_binary = base64.b64decode(brand.logo, validate=True)
            except (binascii.Error, ValueError):
                raise ValidationError('El logo no tiene un formato de archivo valido.')

            if len(logo_binary) > self._LOGO_MAX_FILE_SIZE:
                raise ValidationError(
                    'El logo excede el tamano permitido de 5 MB. Usa una imagen mas liviana.'
                )

            mimetype = guess_mimetype(logo_binary, default='application/octet-stream')
            if mimetype not in self._LOGO_ALLOWED_MIMETYPES:
                raise ValidationError('El logo debe estar en formato PNG, JPG/JPEG o WEBP.')

            try:
                ImageProcess(logo_binary, verify_resolution=True)
            except Exception as error:
                raise ValidationError(
                    f'No se pudo validar la imagen del logo: {error}'
                ) from error


class ZrnCommercialBrandProduct(models.Model):
    _name = 'zrn_commercial.commercial.brand.product'
    _description = 'Producto asignado a marca comercial'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Secuencia', default=10)
    brand_id = fields.Many2one(
        'zrn_commercial.commercial.brand',
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
    available_product_ids = fields.Many2many(
        'product.product',
        string='Productos disponibles',
        compute='_compute_available_product_ids',
        store=False,
    )
    product_id = fields.Many2one(
        'product.product',
        string='Producto',
        required=True,
        ondelete='restrict',
        domain="[('id', 'in', available_product_ids)]",
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

    @api.depends('brand_id', 'product_id')
    def _compute_available_product_ids(self):
        Product = self.env['product.product']
        assigned_product_ids = self.search([]).mapped('product_id').ids
        for record in self:
            current_product_ids = record.product_id.ids
            blocked_product_ids = list(set(assigned_product_ids) - set(current_product_ids))
            available_products = Product.search([
                ('sale_ok', '=', True),
                ('id', 'not in', blocked_product_ids),
            ])
            record.available_product_ids = available_products

    @api.constrains('product_id')
    def _check_sale_ok_product(self):
        for record in self:
            if record.product_id and not record.product_id.sale_ok:
                raise ValidationError('Solo se pueden asignar productos configurados para venta.')
