# -*- coding: utf-8 -*-

from odoo import _, fields, models


class PbiConnectionsInicio(models.Model):
    _name = 'pbi_connections.inicio'
    _description = 'Pantalla principal de PBI Connections'

    name = fields.Char(string='Nombre', required=True, default='PBI Connections')

    def action_open_endpoints(self):
        self.ensure_one()
        action = self.env.ref('pbi_connections.action_pbi_connections_endpoint').read()[0]
        action['_noBreadcrumbs'] = True
        return action

    def action_open_api_config(self):
        self.ensure_one()
        action = self.env.ref('pbi_connections.action_pbi_connections_api_config').read()[0]
        self.env['pbi_connections.api.config'].sudo()._sync_legacy_config()
        config_record = self.env['pbi_connections.api.config'].sudo().search([], limit=1)
        if config_record:
            action.update({
                'view_mode': 'form',
                'res_id': config_record.id,
                'views': [(self.env.ref('pbi_connections.view_pbi_connections_api_config_form').id, 'form')],
            })
        action['_noBreadcrumbs'] = True
        return action

    def action_show_roadmap(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Siguiente paso'),
                'message': _('Aqui moveremos los endpoints y conexiones que hoy viven en Advanced Metrics.'),
                'type': 'info',
                'sticky': False,
            },
        }


class PbiConnectionsEndpoint(models.Model):
    _name = 'pbi_connections.endpoint'
    _description = 'Endpoint de PBI Connections'
    _order = 'name'

    name = fields.Char(string='Nombre', required=True)
    technical_name = fields.Char(string='Identificador tecnico')
    description = fields.Text(string='Descripcion')
    active = fields.Boolean(string='Activo', default=True)

