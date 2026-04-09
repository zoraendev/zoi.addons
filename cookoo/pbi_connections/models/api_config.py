# -*- coding: utf-8 -*-

import uuid

from odoo import api, fields, models


class PbiConnectionsApiConfig(models.Model):
    _name = 'pbi_connections.api.config'
    _description = 'Configuracion API para Power BI en PBI Connections'

    name = fields.Char(string='Configuracion', required=True, default='Produccion')
    access_token = fields.Char(
        string='Token de Acceso',
        copy=False,
        default=lambda self: str(uuid.uuid4()),
        readonly=True,
    )
    record_limit = fields.Integer(
        string='Limite de Registros',
        default=5000,
        required=True,
        help='Previene ataques de denegacion de servicio limitando la extraccion maxima.',
    )
    api_url = fields.Char(string='URL segura de referencia', compute='_compute_api_url')

    @api.model
    def _sync_legacy_config(self):
        self.env.cr.execute("SELECT to_regclass('advanced_metrics_api_config')")
        table_name = self.env.cr.fetchone()[0]
        if not table_name:
            return self.search([], limit=1)

        self.env.cr.execute(
            """
            SELECT name, access_token, record_limit
            FROM advanced_metrics_api_config
            WHERE access_token IS NOT NULL AND access_token != ''
            ORDER BY id
            LIMIT 1
            """
        )
        legacy_row = self.env.cr.dictfetchone()
        current = self.search([], order='id asc', limit=1)

        if not legacy_row:
            return current

        values = {
            'name': legacy_row.get('name') or 'Produccion',
            'access_token': legacy_row.get('access_token') or str(uuid.uuid4()),
            'record_limit': legacy_row.get('record_limit') or 5000,
        }

        if current:
            updates = {
                key: value
                for key, value in values.items()
                if value and current[key] != value
            }
            if updates:
                current.sudo().write(updates)
            return current

        return self.sudo().create(values)

    @api.depends('access_token')
    def _compute_api_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for rec in self:
            rec.api_url = f"{base_url}/api/bi/customer-dashboard/frequent-customers?token={rec.access_token}"

    def action_generate_new_token(self):
        for rec in self:
            rec.access_token = str(uuid.uuid4())
