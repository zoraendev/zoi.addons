# -*- coding: utf-8 -*-

import base64
import binascii

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
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
    playbook_notes = fields.Text(string='Lineamientos comerciales')
    commercial_status = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('active', 'Activa'),
            ('hold', 'En pausa'),
            ('retired', 'Retirada'),
        ],
        string='Estado comercial',
        default='active',
    )
    suggested_channel_ids = fields.Many2many(
        'zrn_commercial.commercial.channel',
        'zrn_commercial_brand_channel_rel',
        'brand_id',
        'channel_id',
        string='Canales sugeridos',
    )
    responsible_user_ids = fields.Many2many(
        'res.users',
        'zrn_commercial_brand_user_rel',
        'brand_id',
        'user_id',
        string='Responsables comerciales',
    )
    focus_product_ids = fields.Many2many(
        'product.product',
        'zrn_commercial_brand_focus_product_rel',
        'brand_id',
        'product_id',
        string='Productos foco',
        domain="[('sale_ok', '=', True)]",
    )
    source_model = fields.Char(string='Modelo origen', readonly=True, copy=False)
    source_model_name = fields.Char(string='Nombre del modelo origen', readonly=True, copy=False)
    source_record_id = fields.Integer(string='ID origen', readonly=True, copy=False)
    source_record_name = fields.Char(string='Registro origen', readonly=True, copy=False)
    source_sync_date = fields.Datetime(string='Ultima sincronizacion', readonly=True, copy=False)
    opportunity_count = fields.Integer(
        string='Oportunidades',
        compute='_compute_related_counts',
        store=False,
    )
    customer_count = fields.Integer(
        string='Clientes',
        compute='_compute_related_counts',
        store=False,
    )
    quotation_count = fields.Integer(
        string='Cotizaciones',
        compute='_compute_related_counts',
        store=False,
    )
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

    def _compute_related_counts(self):
        lead_model = self.env['crm.lead'].sudo()
        partner_model = self.env['res.partner'].sudo()
        order_model = self.env['sale.order'].sudo()
        for brand in self:
            brand.opportunity_count = lead_model.search_count([
                ('zrn_brand_id', '=', brand.id),
                ('type', '=', 'opportunity'),
            ])
            brand.customer_count = partner_model.search_count([
                '|',
                ('zrn_primary_brand_id', '=', brand.id),
                ('zrn_brand_ids', 'in', brand.id),
            ])
            brand.quotation_count = order_model.search_count([
                ('zrn_brand_id', '=', brand.id),
                ('state', 'in', ['draft', 'sent', 'sale']),
            ])

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

    @api.model
    def _get_available_source_model_ids(self):
        model_ids = []
        candidate_models = self.env['ir.model'].sudo().search([('transient', '=', False)])
        for model in candidate_models:
            haystack = '%s %s' % (model.model or '', model.name or '')
            haystack = haystack.lower()
            if 'brand' not in haystack and 'marca' not in haystack:
                continue
            if model.model not in self.env:
                continue
            model_obj = self.env[model.model]
            if 'name' not in model_obj._fields:
                continue
            model_ids.append(model.id)
        return model_ids

    @api.model
    def _extract_source_brand_values(self, source_record, company=None):
        def _get_scalar(field_names):
            for field_name in field_names:
                if field_name not in source_record._fields:
                    continue
                value = source_record[field_name]
                if not value:
                    continue
                if isinstance(value, models.BaseModel):
                    return value.display_name
                return value
            return False

        image_value = False
        for image_field in ('logo', 'image_1920', 'image_1024', 'image_512', 'image_256', 'image_128', 'image'):
            if image_field in source_record._fields and source_record[image_field]:
                image_value = source_record[image_field]
                break

        company_record = company
        if not company_record and 'company_id' in source_record._fields:
            company_record = source_record.company_id

        return {
            'name': _get_scalar(('name', 'display_name')),
            'code': _get_scalar(('code', 'default_code', 'short_name')),
            'owner_name': _get_scalar(('owner_name', 'manufacturer_name', 'partner_id', 'company_id')),
            'website': _get_scalar(('website',)),
            'email': _get_scalar(('email',)),
            'phone': _get_scalar(('phone',)),
            'description': _get_scalar(('description', 'comment', 'notes')),
            'logo': image_value,
            'company_id': company_record.id if company_record else self.env.company.id,
            'source_model': source_record._name,
            'source_model_name': source_record._description or source_record._name,
            'source_record_id': source_record.id,
            'source_record_name': source_record.display_name,
        }

    @api.model
    def _find_existing_brand_from_source(self, source_model, source_record_id, source_values, company=None):
        company = company or self.env.company
        brand = self.search([
            ('source_model', '=', source_model),
            ('source_record_id', '=', source_record_id),
            ('company_id', '=', company.id),
        ], limit=1)
        if brand:
            return brand
        if source_values.get('code'):
            brand = self.search([
                ('company_id', '=', company.id),
                ('code', '=', source_values['code']),
            ], limit=1)
            if brand:
                return brand
        return self.search([
            ('company_id', '=', company.id),
            ('name', '=', source_values.get('name')),
        ], limit=1)

    @api.model
    def import_from_source_records(self, source_model, source_record_ids, company=None):
        if not source_model or not source_record_ids:
            return self.browse()

        if source_model not in self.env:
            raise UserError(_('El modelo origen seleccionado ya no esta disponible para importar marcas.'))

        company = company or self.env.company
        imported_brands = self.browse()
        source_records = self.env[source_model].sudo().browse(source_record_ids).exists()
        for source_record in source_records:
            source_values = self._extract_source_brand_values(source_record, company=company)
            existing_brand = self._find_existing_brand_from_source(
                source_model,
                source_record.id,
                source_values,
                company=company,
            )
            if existing_brand:
                sync_values = {
                    'source_model': source_values['source_model'],
                    'source_model_name': source_values['source_model_name'],
                    'source_record_id': source_values['source_record_id'],
                    'source_record_name': source_values['source_record_name'],
                    'source_sync_date': fields.Datetime.now(),
                }
                if not existing_brand.code and source_values.get('code'):
                    sync_values['code'] = source_values['code']
                if not existing_brand.owner_name and source_values.get('owner_name'):
                    sync_values['owner_name'] = source_values['owner_name']
                if not existing_brand.website and source_values.get('website'):
                    sync_values['website'] = source_values['website']
                if not existing_brand.email and source_values.get('email'):
                    sync_values['email'] = source_values['email']
                if not existing_brand.phone and source_values.get('phone'):
                    sync_values['phone'] = source_values['phone']
                if not existing_brand.logo and source_values.get('logo'):
                    sync_values['logo'] = source_values['logo']
                existing_brand.write(sync_values)
                imported_brands |= existing_brand
                continue

            create_values = {
                'name': source_values['name'],
                'code': source_values.get('code'),
                'owner_name': source_values.get('owner_name'),
                'website': source_values.get('website'),
                'email': source_values.get('email'),
                'phone': source_values.get('phone'),
                'description': source_values.get('description'),
                'logo': source_values.get('logo'),
                'company_id': company.id,
                'source_model': source_values['source_model'],
                'source_model_name': source_values['source_model_name'],
                'source_record_id': source_values['source_record_id'],
                'source_record_name': source_values['source_record_name'],
                'source_sync_date': fields.Datetime.now(),
                'notes': 'Importada desde catalogo existente de Odoo.',
            }
            imported_brands |= self.create(create_values)
        return imported_brands

    def action_open_import_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'zrn_commercial.brand.import.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_company_id': self.env.company.id,
            },
        }

    def action_sync_from_source(self):
        self.ensure_one()
        if not self.source_model or not self.source_record_id:
            raise UserError('Esta marca no tiene un origen registrado para sincronizar.')
        self.import_from_source_records(
            self.source_model,
            [self.source_record_id],
            company=self.company_id,
        )
        return True

    def action_open_opportunities(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('zrn_commercial.action_zrn_commercial_opportunities')
        action['domain'] = [('zrn_brand_id', '=', self.id), ('type', '=', 'opportunity')]
        action['context'] = dict(self.env.context, default_zrn_brand_id=self.id)
        return action

    def action_open_customers(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('zrn_commercial.action_zrn_commercial_customers')
        action['domain'] = ['|', ('zrn_primary_brand_id', '=', self.id), ('zrn_brand_ids', 'in', self.id)]
        action['context'] = dict(self.env.context, default_zrn_primary_brand_id=self.id)
        return action

    def action_open_quotations(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('zrn_commercial.action_zrn_commercial_quotations')
        action['domain'] = [('zrn_brand_id', '=', self.id)]
        action['context'] = dict(self.env.context, default_zrn_brand_id=self.id)
        return action


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
