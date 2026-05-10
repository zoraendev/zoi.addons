# -*- coding: utf-8 -*-

from urllib.parse import quote

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.model
    def _normalize_external_key(self, value):
        return (value or '').strip().strip("'").strip('"')

    @api.model
    def _normalize_validation_base_url(self, value):
        base_url = self._normalize_external_key(value).rstrip('/')
        if base_url.startswith('ttps://'):
            base_url = f'https://{base_url[len("ttps://"):]}'
        elif base_url.startswith('ttp://'):
            base_url = f'http://{base_url[len("ttp://"):]}'
        marker = '/clients/key/'
        if marker in base_url:
            base_url = base_url.split(marker, 1)[0]
        return base_url

    peack_planing_instance_key = fields.Char(
        string='Key de instancia',
        config_parameter='peack_planing.instance_key',
    )
    peack_planing_client_validation_base_url = fields.Char(
        string='URL base de validacion',
        config_parameter='peack_planing.client_validation_base_url',
    )
    peack_planing_client_key = fields.Char(
        string='Clave de cliente',
        config_parameter='peack_planing.client_key',
    )
    peack_planing_client_validation_api_key = fields.Char(
        string='API Key de validacion',
        config_parameter='peack_planing.client_validation_api_key',
    )
    peack_planing_support_url = fields.Char(
        string='URL de soporte legacy',
        config_parameter='peack_planing.support_url',
    )
    peack_planing_client_validation_url_preview = fields.Char(
        string='URL final de validacion',
        compute='_compute_peack_planing_url_previews',
    )
    peack_planing_support_url_preview = fields.Char(
        string='URL final de soporte',
        compute='_compute_peack_planing_url_previews',
    )

    @api.depends(
        'peack_planing_instance_key',
        'peack_planing_client_validation_base_url',
        'peack_planing_client_key',
    )
    def _compute_peack_planing_url_previews(self):
        for record in self:
            base_url = self._normalize_validation_base_url(record.peack_planing_client_validation_base_url)
            client_key = self._normalize_external_key(record.peack_planing_client_key)
            instance_key = self._normalize_external_key(record.peack_planing_instance_key)

            record.peack_planing_client_validation_url_preview = (
                f'{base_url}/clients/key/{quote(client_key)}'
                if base_url and client_key
                else False
            )
            record.peack_planing_support_url_preview = (
                f'https://adm.zoraen.com/support?instance={quote(instance_key)}'
                if instance_key
                else False
            )
