# -*- coding: utf-8 -*-

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
        return base_url

    advanced_metrics_instance_key = fields.Char(
        string='Key de instancia',
        config_parameter='advanced_metrics.instance_key',
    )
    advanced_metrics_connection_base_url = fields.Char(
        string='URL base de conexion',
        config_parameter='advanced_metrics.connection_base_url',
    )
    advanced_metrics_connection_api_path = fields.Char(
        string='Path de conexion',
        config_parameter='advanced_metrics.connection_api_path',
    )
    advanced_metrics_connection_api_key = fields.Char(
        string='API Key de conexion',
        config_parameter='advanced_metrics.connection_api_key',
    )
    advanced_metrics_connection_addon_api_key = fields.Char(
        string='Addon API Key',
        config_parameter='advanced_metrics.connection_addon_api_key',
    )
    advanced_metrics_support_url = fields.Char(
        string='URL de soporte legacy',
        config_parameter='advanced_metrics.support_url',
    )
    advanced_metrics_connection_url_preview = fields.Char(
        string='URL final de conexion',
        compute='_compute_advanced_metrics_url_previews',
    )
    advanced_metrics_support_url_preview = fields.Char(
        string='URL final de soporte',
        compute='_compute_advanced_metrics_url_previews',
    )

    @api.depends(
        'advanced_metrics_instance_key',
        'advanced_metrics_connection_base_url',
        'advanced_metrics_connection_api_path',
    )
    def _compute_advanced_metrics_url_previews(self):
        for record in self:
            base_url = self._normalize_validation_base_url(record.advanced_metrics_connection_base_url)
            api_path = self._normalize_external_key(record.advanced_metrics_connection_api_path).lstrip('/')
            instance_key = self._normalize_external_key(record.advanced_metrics_instance_key)

            record.advanced_metrics_connection_url_preview = (
                f'{base_url}/{api_path}'
                if base_url and api_path
                else False
            )
            record.advanced_metrics_support_url_preview = (
                f'https://adm.zoraen.com/support?instance={instance_key}'
                if instance_key
                else False
            )
