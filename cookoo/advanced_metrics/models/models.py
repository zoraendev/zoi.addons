import logging

import requests
from requests import RequestException

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class AdvancedMetricsInicio(models.Model):
    _name = 'advanced_metrics.inicio'
    _description = 'Pantalla principal de Advanced Metrics'

    _DEFAULT_CLIENT_VALIDATION_URL = 'https://clients-service.vercel.app/api/production-v1-public/clients/key/SDSAW54D'
    _DEFAULT_CLIENT_VALIDATION_API_KEY = 'SHKJSDHKA'
    _DEFAULT_SUPPORT_URL = 'https://www.zoraen.com'

    name = fields.Char(string='Nombre', required=True)
    show_dashboard = fields.Boolean(compute='_compute_client_validation_state')
    client_validation_state = fields.Selection(
        selection=[
            ('ok', 'Activo'),
            ('payment_due', 'Pago pendiente'),
            ('inactive', 'Inactivo'),
            ('error', 'Error'),
        ],
        compute='_compute_client_validation_state',
    )
    client_status_code = fields.Integer(compute='_compute_client_validation_state')
    client_status_title = fields.Char(compute='_compute_client_validation_state')
    client_status_message = fields.Text(compute='_compute_client_validation_state')
    support_url = fields.Char(compute='_compute_client_validation_state')

    @api.model
    def _get_client_validation_settings(self):
        params = self.env['ir.config_parameter'].sudo()
        return {
            'url': params.get_param(
                'advanced_metrics.client_validation_url',
                self._DEFAULT_CLIENT_VALIDATION_URL,
            ),
            'api_key': params.get_param(
                'advanced_metrics.client_validation_api_key',
                self._DEFAULT_CLIENT_VALIDATION_API_KEY,
            ),
            'support_url': params.get_param(
                'advanced_metrics.support_url',
                self._DEFAULT_SUPPORT_URL,
            ),
        }

    @api.model
    def _get_client_validation_result(self):
        settings = self._get_client_validation_settings()
        headers = {}
        if settings['api_key']:
            headers['x-api-key'] = settings['api_key']

        try:
            response = requests.get(settings['url'], headers=headers, timeout=10)
            response.raise_for_status()
            payload = response.json()
        except RequestException:
            _logger.exception('Advanced Metrics client validation request failed.')
            return {
                'state': 'error',
                'status_code': 0,
                'show_dashboard': False,
                'title': _('No se pudo validar el cliente'),
                'message': _('Ocurrió un error al consultar el servicio. Intenta nuevamente o contacta a soporte.'),
                'support_url': settings['support_url'],
            }
        except ValueError:
            _logger.exception('Advanced Metrics client validation returned a non-JSON response.')
            return {
                'state': 'error',
                'status_code': 0,
                'show_dashboard': False,
                'title': _('Respuesta inválida del servicio'),
                'message': _('El servicio externo respondió con un formato inesperado. Contacta a soporte si el problema continúa.'),
                'support_url': settings['support_url'],
            }

        client_data = payload.get('data') or {}
        if payload.get('code') != 200 or not isinstance(client_data, dict):
            _logger.warning('Advanced Metrics client validation returned an unexpected payload: %s', payload)
            return {
                'state': 'error',
                'status_code': 0,
                'show_dashboard': False,
                'title': _('No fue posible validar el acceso'),
                'message': _('La respuesta del servicio no contiene la información esperada. Contacta a soporte.'),
                'support_url': settings['support_url'],
            }

        client_name = client_data.get('name') or _('cliente')
        raw_status = client_data.get('status', 0)
        try:
            status = int(raw_status)
        except (TypeError, ValueError):
            status = 0

        if status == 5:
            return {
                'state': 'payment_due',
                'status_code': status,
                'show_dashboard': False,
                'title': _('Pago pendiente'),
                'message': _('El cliente %s tiene un pago pendiente. Para habilitar las opciones, regulariza el pago o solicita ayuda a soporte.') % client_name,
                'support_url': settings['support_url'],
            }

        if status != 1:
            return {
                'state': 'inactive',
                'status_code': status,
                'show_dashboard': False,
                'title': _('Acceso no disponible'),
                'message': _('La cuenta del cliente %s no se encuentra activa en este momento. Contacta a soporte para revisar el estado.') % client_name,
                'support_url': settings['support_url'],
            }

        return {
            'state': 'ok',
            'status_code': status,
            'show_dashboard': True,
            'title': _('Cliente activo'),
            'message': _('La suscripción de %s fue validada correctamente.') % client_name,
            'support_url': settings['support_url'],
        }

    @api.depends('name')
    def _compute_client_validation_state(self):
        result = self._get_client_validation_result()
        for record in self:
            record.show_dashboard = result['show_dashboard']
            record.client_validation_state = result['state']
            record.client_status_code = result['status_code']
            record.client_status_title = result['title']
            record.client_status_message = result['message']
            record.support_url = result['support_url']

    def action_request_support(self):
        self.ensure_one()
        support_url = self.support_url or self._get_client_validation_settings()['support_url']
        return {
            'type': 'ir.actions.act_url',
            'url': support_url,
            'target': 'new',
        }

    def _get_blocked_notification_action(self, result):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': result['title'],
                'message': result['message'],
                'type': 'warning' if result['state'] != 'error' else 'danger',
                'sticky': True,
            },
        }

    def action_open_sales_report(self):
        self.ensure_one()
        result = self._get_client_validation_result()
        if not result['show_dashboard']:
            return self._get_blocked_notification_action(result)
        return self.env['ir.actions.actions']._for_xml_id('advanced_metrics.action_advanced_metrics_report_wizard')

    def action_open_api_config(self):
        self.ensure_one()
        result = self._get_client_validation_result()
        if not result['show_dashboard']:
            return self._get_blocked_notification_action(result)
        return self.env['ir.actions.actions']._for_xml_id('advanced_metrics.action_advanced_metrics_api_config')


class AdvancedMetricsRegistro(models.Model):
    _name = 'advanced_metrics.registro'
    _description = 'Registro de Advanced Metrics'

    name = fields.Char(string='Nombre', required=True)
    descripcion = fields.Text(string='Descripción')