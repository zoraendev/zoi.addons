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

    zrn_prodigyn_instance_key = fields.Char(
        string='Key de instancia',
        config_parameter='zrn_prodigyn.instance_key',
    )
    zrn_prodigyn_connection_base_url = fields.Char(
        string='URL base de conexion',
        config_parameter='zrn_prodigyn.connection_base_url',
    )
    zrn_prodigyn_connection_api_path = fields.Char(
        string='Path de conexion',
        config_parameter='zrn_prodigyn.connection_api_path',
    )
    zrn_prodigyn_connection_api_key = fields.Char(
        string='API Key de conexion',
        config_parameter='zrn_prodigyn.connection_api_key',
    )
    zrn_prodigyn_connection_addon_api_key = fields.Char(
        string='Addon API Key',
        config_parameter='zrn_prodigyn.connection_addon_api_key',
    )
    zrn_prodigyn_connection_url_preview = fields.Char(
        string='URL final de conexion',
        compute='_compute_zrn_prodigyn_url_previews',
    )
    zrn_prodigyn_support_url_preview = fields.Char(
        string='URL final de soporte',
        compute='_compute_zrn_prodigyn_url_previews',
    )

    @api.depends(
        'zrn_prodigyn_instance_key',
        'zrn_prodigyn_connection_base_url',
        'zrn_prodigyn_connection_api_path',
    )
    def _compute_zrn_prodigyn_url_previews(self):
        for record in self:
            base_url = self._normalize_validation_base_url(record.zrn_prodigyn_connection_base_url)
            api_path = self._normalize_external_key(record.zrn_prodigyn_connection_api_path).lstrip('/')
            instance_key = self._normalize_external_key(record.zrn_prodigyn_instance_key)

            record.zrn_prodigyn_connection_url_preview = (
                f'{base_url}/{api_path}'
                if base_url and api_path
                else False
            )
            record.zrn_prodigyn_support_url_preview = (
                f'https://adm.zoraen.com/support?instance={instance_key}'
                if instance_key
                else False
            )
