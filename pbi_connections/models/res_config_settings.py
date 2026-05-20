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

    pbi_connections_instance_key = fields.Char(
        string='Key de instancia',
        config_parameter='pbi_connections.instance_key',
    )
    pbi_connections_client_validation_base_url = fields.Char(
        string='URL base de validacion',
        config_parameter='pbi_connections.client_validation_base_url',
    )
    pbi_connections_client_key = fields.Char(
        string='Clave de cliente',
        config_parameter='pbi_connections.client_key',
    )
    pbi_connections_client_validation_api_key = fields.Char(
        string='API Key de validacion',
        config_parameter='pbi_connections.client_validation_api_key',
    )
    pbi_connections_support_url = fields.Char(
        string='URL de soporte legacy',
        config_parameter='pbi_connections.support_url',
    )
    pbi_connections_client_validation_url_preview = fields.Char(
        string='URL final de validacion',
        compute='_compute_pbi_connections_url_previews',
    )
    pbi_connections_support_url_preview = fields.Char(
        string='URL final de soporte',
        compute='_compute_pbi_connections_url_previews',
    )

    @api.depends(
        'pbi_connections_instance_key',
        'pbi_connections_client_validation_base_url',
        'pbi_connections_client_key',
    )
    def _compute_pbi_connections_url_previews(self):
        for record in self:
            base_url = self._normalize_validation_base_url(record.pbi_connections_client_validation_base_url)
            client_key = self._normalize_external_key(record.pbi_connections_client_key)
            instance_key = self._normalize_external_key(record.pbi_connections_instance_key)

            record.pbi_connections_client_validation_url_preview = (
                f'{base_url}/clients/key/{quote(client_key)}'
                if base_url and client_key
                else False
            )
            record.pbi_connections_support_url_preview = (
                f'https://adm.zoraen.com/support?instance={quote(instance_key)}'
                if instance_key
                else False
            )
