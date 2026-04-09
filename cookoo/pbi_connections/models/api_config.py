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

    @api.depends('access_token')
    def _compute_api_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for rec in self:
            rec.api_url = f"{base_url}/api/bi/customer-dashboard/frequent-customers?token={rec.access_token}"

    def action_generate_new_token(self):
        for rec in self:
            rec.access_token = str(uuid.uuid4())
