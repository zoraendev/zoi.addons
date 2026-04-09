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

