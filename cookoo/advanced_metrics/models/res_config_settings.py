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
        marker = '/clients/key/'
        if marker in base_url:
            base_url = base_url.split(marker, 1)[0]
        return base_url

    advanced_metrics_instance_key = fields.Char(
        string='Key de instancia',
        config_parameter='advanced_metrics.instance_key',
    )
    advanced_metrics_client_validation_base_url = fields.Char(
        string='URL base de validacion',
        config_parameter='advanced_metrics.client_validation_base_url',
    )
    advanced_metrics_client_key = fields.Char(
        string='Clave de cliente',
        config_parameter='advanced_metrics.client_key',
    )
    advanced_metrics_client_validation_api_key = fields.Char(
        string='API Key de validacion',
        config_parameter='advanced_metrics.client_validation_api_key',
    )
    advanced_metrics_support_url = fields.Char(
        string='URL de soporte legacy',
        config_parameter='advanced_metrics.support_url',
    )
    advanced_metrics_client_validation_url_preview = fields.Char(
        string='URL final de validacion',
        compute='_compute_advanced_metrics_url_previews',
    )
    advanced_metrics_support_url_preview = fields.Char(
        string='URL final de soporte',
        compute='_compute_advanced_metrics_url_previews',
    )

    @api.depends(
        'advanced_metrics_instance_key',
        'advanced_metrics_client_validation_base_url',
        'advanced_metrics_client_key',
    )
    def _compute_advanced_metrics_url_previews(self):
        for record in self:
            base_url = self._normalize_validation_base_url(record.advanced_metrics_client_validation_base_url)
            client_key = self._normalize_external_key(record.advanced_metrics_client_key)
            instance_key = self._normalize_external_key(record.advanced_metrics_instance_key)

            record.advanced_metrics_client_validation_url_preview = (
                f'{base_url}/clients/key/{quote(client_key)}'
                if base_url and client_key
                else False
            )
            record.advanced_metrics_support_url_preview = (
                f'https://adm.zoraen.com/support?instance={quote(instance_key)}'
                if instance_key
                else False
            )
