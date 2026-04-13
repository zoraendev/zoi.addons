# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class PbiConnectionsInicio(models.Model):
    _name = 'pbi_connections.inicio'
    _description = 'Pantalla principal de PBI Connections'

    name = fields.Char(string='Nombre', required=True, default='PBI Connections')
    show_dashboard = fields.Boolean(
        string='Mostrar dashboard',
        compute='_compute_status_fields',
    )
    client_validation_state = fields.Selection(
        [
            ('ok', 'Activo'),
            ('payment_due', 'Pago pendiente'),
            ('inactive', 'Inactivo'),
            ('error', 'Error'),
        ],
        string='Estado de validacion del cliente',
        compute='_compute_status_fields',
    )
    client_status_code = fields.Char(
        string='Codigo de estado del cliente',
        compute='_compute_status_fields',
    )
    support_url = fields.Char(
        string='URL de soporte',
        compute='_compute_status_fields',
    )
    client_status_title = fields.Char(
        string='Titulo de estado del cliente',
        compute='_compute_status_fields',
    )
    client_status_message = fields.Text(
        string='Mensaje de estado del cliente',
        compute='_compute_status_fields',
    )
    client_validation_debug = fields.Text(
        string='Detalle tecnico de validacion',
        compute='_compute_status_fields',
    )
    access_token = fields.Char(
        string='Token de Acceso',
        compute='_compute_status_fields',
    )
    record_limit = fields.Integer(
        string='Limite de Registros',
        compute='_compute_status_fields',
        inverse='_inverse_record_limit',
    )
    api_url = fields.Char(
        string='URL segura de referencia',
        compute='_compute_status_fields',
    )

    def _get_or_create_config_record(self):
        config_model = self.env['pbi_connections.api.config'].sudo()
        config_model._sync_legacy_config()
        config_record = config_model.search([], order='id asc', limit=1)
        if not config_record:
            config_record = config_model.create({
                'name': 'Produccion',
            })
        return config_record

    @api.depends('name')
    def _compute_status_fields(self):
        config_record = self._get_or_create_config_record()

        config_record._refresh_client_validation_status()

        for record in self:
            record.show_dashboard = config_record.show_dashboard
            record.client_validation_state = config_record.client_validation_state
            record.client_status_code = config_record.client_status_code
            record.support_url = config_record.support_url
            record.client_status_title = config_record.client_status_title
            record.client_status_message = config_record.client_status_message
            record.client_validation_debug = config_record.client_validation_debug
            record.access_token = config_record.access_token
            record.record_limit = config_record.record_limit
            record.api_url = config_record.api_url

    def _inverse_record_limit(self):
        config_record = self._get_or_create_config_record()
        for record in self:
            if record.record_limit and config_record.record_limit != record.record_limit:
                config_record.write({'record_limit': record.record_limit})

    def action_generate_new_token(self):
        self.ensure_one()
        config_record = self._get_or_create_config_record()
        config_record.action_generate_new_token()
        return {
            'type': 'ir.actions.act_window',
            'name': _('PBI Connections'),
            'res_model': 'pbi_connections.inicio',
            'view_mode': 'form',
            'view_id': self.env.ref('pbi_connections.view_pbi_connections_inicio_form').id,
            'res_id': self.id,
            'target': 'current',
        }

    def action_open_external_instance(self):
        self.ensure_one()
        config_record = self._get_or_create_config_record()
        return config_record.action_open_external_instance()

    def action_request_support(self):
        self.ensure_one()
        config_record = self._get_or_create_config_record()
        return config_record.action_request_support()

    def action_open_endpoints(self):
        self.ensure_one()
        action = self.env.ref('pbi_connections.action_pbi_connections_endpoint').read()[0]
        action['_noBreadcrumbs'] = True
        return action

    def action_open_api_config(self):
        self.ensure_one()
        action = self.env.ref('pbi_connections.action_pbi_connections_api_config').read()[0]
        config_record = self._get_or_create_config_record()
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

    def action_open_settings(self):
        self.ensure_one()
        action = self.env.ref('pbi_connections.action_pbi_connections_settings').read()[0]
        action['_noBreadcrumbs'] = True
        return action


class PbiConnectionsEndpoint(models.Model):
    _name = 'pbi_connections.endpoint'
    _description = 'Endpoint de PBI Connections'
    _order = 'name'

    name = fields.Char(string='Nombre', required=True)
    technical_name = fields.Char(string='Identificador tecnico')
    description = fields.Text(string='Descripcion')
    active = fields.Boolean(string='Activo', default=True)
