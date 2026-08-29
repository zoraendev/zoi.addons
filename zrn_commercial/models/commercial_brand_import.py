# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError


class ZrnCommercialBrandImportWizard(models.TransientModel):
    _name = 'zrn_commercial.brand.import.wizard'
    _description = 'Asistente de importacion de marcas comerciales'

    company_id = fields.Many2one(
        'res.company',
        string='Compania',
        required=True,
        default=lambda self: self.env.company,
    )
    source_model_id = fields.Many2one(
        'ir.model',
        string='Modelo origen',
        required=True,
        domain="[('id', 'in', available_source_model_ids)]",
    )
    available_source_model_ids = fields.Many2many(
        'ir.model',
        compute='_compute_available_source_model_ids',
        string='Modelos origen disponibles',
    )
    import_line_ids = fields.One2many(
        'zrn_commercial.brand.import.wizard.line',
        'wizard_id',
        string='Marcas detectadas',
    )
    detected_count = fields.Integer(
        string='Total detectadas',
        compute='_compute_detected_count',
    )
    selected_count = fields.Integer(
        string='Seleccionadas',
        compute='_compute_detected_count',
    )

    @api.depends('source_model_id')
    def _compute_available_source_model_ids(self):
        model_ids = self.env['zrn_commercial.commercial.brand']._get_available_source_model_ids()
        for wizard in self:
            wizard.available_source_model_ids = [(6, 0, model_ids)]

    @api.depends('import_line_ids', 'import_line_ids.selected')
    def _compute_detected_count(self):
        for wizard in self:
            wizard.detected_count = len(wizard.import_line_ids)
            wizard.selected_count = len(wizard.import_line_ids.filtered('selected'))

    def action_scan_sources(self):
        self.ensure_one()
        if not self.source_model_id:
            raise UserError('Selecciona primero un modelo origen para detectar marcas.')

        source_model = self.env[self.source_model_id.model].sudo().with_context(active_test=False)
        domain = []
        if 'company_id' in source_model._fields:
            domain = ['|', ('company_id', '=', False), ('company_id', '=', self.company_id.id)]
        source_records = source_model.search(domain, order='id desc')

        commands = [(5, 0, 0)]
        Brand = self.env['zrn_commercial.commercial.brand']
        for source_record in source_records:
            source_values = Brand._extract_source_brand_values(source_record, company=self.company_id)
            existing_brand = Brand._find_existing_brand_from_source(
                self.source_model_id.model,
                source_record.id,
                source_values,
                company=self.company_id,
            )
            commands.append((0, 0, {
                'selected': not existing_brand,
                'source_model': self.source_model_id.model,
                'source_record_id': source_record.id,
                'source_name': source_values.get('name'),
                'source_code': source_values.get('code'),
                'existing_brand_id': existing_brand.id,
            }))

        self.write({'import_line_ids': commands})

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_import_selected(self):
        self.ensure_one()
        selected_lines = self.import_line_ids.filtered('selected')
        if not selected_lines:
            raise UserError('Selecciona al menos una marca para importar.')

        self.env['zrn_commercial.commercial.brand'].import_from_source_records(
            self.source_model_id.model,
            selected_lines.mapped('source_record_id'),
            company=self.company_id,
        )
        return self.env['ir.actions.actions']._for_xml_id('zrn_commercial.action_zrn_commercial_brands')

    def action_import_all_pending(self):
        self.ensure_one()
        pending_lines = self.import_line_ids.filtered(lambda line: not line.existing_brand_id)
        if not pending_lines:
            raise UserError('No hay marcas pendientes por importar en el modelo seleccionado.')

        self.env['zrn_commercial.commercial.brand'].import_from_source_records(
            self.source_model_id.model,
            pending_lines.mapped('source_record_id'),
            company=self.company_id,
        )
        return self.env['ir.actions.actions']._for_xml_id('zrn_commercial.action_zrn_commercial_brands')


class ZrnCommercialBrandImportWizardLine(models.TransientModel):
    _name = 'zrn_commercial.brand.import.wizard.line'
    _description = 'Linea detectada para importacion de marca'
    _order = 'source_name, id'

    wizard_id = fields.Many2one(
        'zrn_commercial.brand.import.wizard',
        string='Asistente',
        required=True,
        ondelete='cascade',
    )
    selected = fields.Boolean(string='Importar', default=True)
    source_model = fields.Char(string='Modelo origen', required=True)
    source_record_id = fields.Integer(string='ID origen', required=True)
    source_name = fields.Char(string='Marca origen', required=True)
    source_code = fields.Char(string='Codigo origen')
    existing_brand_id = fields.Many2one(
        'zrn_commercial.commercial.brand',
        string='Marca Zoraen existente',
    )
