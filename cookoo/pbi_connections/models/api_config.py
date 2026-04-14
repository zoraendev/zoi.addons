# -*- coding: utf-8 -*-

import json
import logging
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPSHandler, ProxyHandler, Request, build_opener

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class PbiConnectionsApiConfig(models.Model):
    _name = 'pbi_connections.api.config'
    _description = 'Configuracion API para Power BI en PBI Connections'

    _DEFAULT_CLIENT_VALIDATION_BASE_URL = 'https://api.zoraen.com/api/production-v1-public'
    _DEFAULT_CLIENT_KEY = ''
    _DEFAULT_CLIENT_VALIDATION_API_KEY = ''
    _INSTANCE_BASE_URL = 'https://adm.zoraen.com/instances/i'
    _SUPPORT_BASE_URL = 'https://adm.zoraen.com/support?instance='

    name = fields.Char(string='Configuracion', required=True, default='Produccion')
    show_dashboard = fields.Boolean(string='Mostrar dashboard', default=True)
    client_validation_state = fields.Selection(
        [
            ('ok', 'Activo'),
            ('payment_due', 'Pago pendiente'),
            ('inactive', 'Inactivo'),
            ('error', 'Error'),
        ],
        string='Estado de validacion del cliente',
        default='ok',
    )
    client_status_code = fields.Char(string='Codigo de estado del cliente')
    support_url = fields.Char(string='URL de soporte')
    client_status_title = fields.Char(
        string='Titulo de estado del cliente',
        default='Conexion disponible',
    )
    client_status_message = fields.Text(
        string='Mensaje de estado del cliente',
        default='La instancia esta lista para gestionar la conexion y consumir endpoints desde Power BI.',
    )
    client_validation_debug = fields.Text(
        string='Detalle tecnico de validacion',
        readonly=True,
    )
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

    @api.model
    def _get_navigation_settings(self):
        config = self.env['ir.config_parameter'].sudo()
        instance_key = config.get_param('pbi_connections.instance_key', '')
        if not instance_key:
            instance_key = config.get_param('pbi_connections.client_key', self._DEFAULT_CLIENT_KEY)
        instance_key = self._normalize_external_key(instance_key)
        return {
            'base_url': self._normalize_validation_base_url(
                config.get_param('pbi_connections.client_validation_base_url', self._DEFAULT_CLIENT_VALIDATION_BASE_URL)
            ),
            'client_key': self._normalize_external_key(
                config.get_param('pbi_connections.client_key', self._DEFAULT_CLIENT_KEY)
            ),
            'api_key': self._normalize_external_key(
                config.get_param('pbi_connections.client_validation_api_key', self._DEFAULT_CLIENT_VALIDATION_API_KEY)
            ),
            'instance_key': instance_key,
            'support_url': config.get_param('pbi_connections.support_url', ''),
        }

    @api.model
    def _build_instance_and_support_urls(self, settings=None):
        settings = settings or self._get_navigation_settings()
        key = quote(self._normalize_external_key(settings.get('instance_key')))
        return (
            f'{self._INSTANCE_BASE_URL}/{key}',
            f'{self._SUPPORT_BASE_URL}{key}',
        )

    @api.model
    def _get_missing_required_settings(self, settings=None):
        settings = settings or self._get_navigation_settings()
        required_values = {
            'base_url': settings.get('base_url'),
            'client_key': settings.get('client_key'),
            'api_key': settings.get('api_key'),
            'instance_key': settings.get('instance_key'),
        }
        return [
            key
            for key, value in required_values.items()
            if not (value or '').strip()
        ]

    @api.model
    def _fetch_client_validation_payload(self, settings):
        base_url = self._normalize_validation_base_url(settings.get('base_url'))
        client_key = self._normalize_external_key(settings.get('client_key'))
        if not base_url or not client_key:
            raise ValueError(_('No se ha configurado la URL base o la clave de cliente.'))
        url = f'{base_url}/clients/key/{client_key}'

        headers = {
            'Accept': 'application/json',
        }
        if settings.get('api_key'):
            headers['x-api-key'] = settings['api_key']

        request = Request(url, headers=headers, method='GET')
        # Bypass environment proxy settings; curl works here while urllib may fail
        # if a broken proxy is injected into the Python process environment.
        opener = build_opener(ProxyHandler({}), HTTPSHandler())
        with opener.open(request, timeout=10) as response:
            payload = response.read().decode('utf-8') or '{}'
        return json.loads(payload)

    @api.model
    def _build_client_status_values(self, payload=None, error_message=None, settings=None):
        settings = settings or self._get_navigation_settings()
        instance_url, support_url = self._build_instance_and_support_urls(settings)
        missing_settings = self._get_missing_required_settings(settings)

        values = {
            'show_dashboard': True,
            'client_validation_state': 'ok',
            'client_status_code': '',
            'support_url': support_url,
            'client_status_title': _('Conexion disponible'),
            'client_status_message': _('La instancia esta lista para gestionar la conexion y consumir endpoints desde Power BI.'),
            'client_validation_debug': '',
        }

        if missing_settings:
            values.update({
                'show_dashboard': False,
                'client_validation_state': 'inactive',
                'client_status_code': 'missing_configuration',
                'client_status_title': _('Configuracion incompleta'),
                'client_status_message': _(
                    'Debes completar la configuracion de integracion (Key de instancia, clave de cliente, API key y URL base) antes de usar este modulo.'
                ),
                'client_validation_debug': _('Parametros faltantes: %s') % ', '.join(missing_settings),
            })
            return values

        if error_message:
            values.update({
                'show_dashboard': False,
                'client_validation_state': 'error',
                'client_status_code': 'validation_error',
                'client_status_title': _('No se pudo validar el estado del cliente'),
                'client_status_message': _(
                    'No fue posible confirmar el estado del servicio en este momento. Intenta nuevamente o contacta a soporte si el problema persiste.'
                ),
                'client_validation_debug': error_message,
            })
            return values

        payload = payload if isinstance(payload, dict) else {}
        payload_code = str(payload.get('code') or '')
        raw_data = payload.get('data')
        data = {}
        if isinstance(raw_data, list) and raw_data:
            first_item = raw_data[0]
            if isinstance(first_item, dict):
                data = first_item
        elif isinstance(raw_data, dict):
            data = raw_data

        has_status = 'status' in data and data.get('status') not in (None, '')
        status_code = data.get('status') if has_status else ''
        values['client_status_code'] = str(status_code or '')
        values['client_validation_debug'] = json.dumps({
            'code': payload.get('code'),
            'status': status_code,
            'userMessage': payload.get('userMessage'),
            'technicalMessage': payload.get('technicalMessage'),
            'data': raw_data,
        }, ensure_ascii=False)

        user_message = (payload.get('userMessage') or '').strip()
        technical_message = (payload.get('technicalMessage') or '').strip()

        if payload_code != '200' or not has_status:
            values.update({
                'show_dashboard': False,
                'client_validation_state': 'error',
                'client_status_code': payload_code or 'invalid_response',
                'client_status_title': _('Cliente no valido'),
                'client_status_message': user_message or technical_message or _(
                    'La respuesta del servicio no confirma un cliente valido. Verifica la clave del cliente, la API key y la URL configurada.'
                ),
            })
            return values

        if str(status_code) == '5':
            values.update({
                'show_dashboard': False,
                'client_validation_state': 'payment_due',
                'client_status_title': _('Cliente insolvente'),
                'client_status_message': user_message or technical_message or _(
                    'La instancia presenta un saldo pendiente. Contacta a soporte para reactivar el acceso al servicio.'
                ),
            })
            return values

        if str(status_code) != '1':
            values.update({
                'show_dashboard': False,
                'client_validation_state': 'error',
                'client_status_title': _('Cliente sin acceso'),
                'client_status_message': user_message or technical_message or _(
                    'El estado del cliente no permite acceder al servicio en este momento.'
                ),
            })

        return values

    def _refresh_client_validation_status(self):
        if not self:
            return

        settings = self._get_navigation_settings()
        payload = {}
        error_message = None

        try:
            payload = self._fetch_client_validation_payload(settings)
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            error_message = str(exc)
            _logger.warning('PBI Connections client validation failed: %s', exc)
        except Exception as exc:
            error_message = str(exc)
            _logger.exception('Unexpected error during PBI Connections client validation: %s', exc)

        values = self._build_client_status_values(
            payload=payload,
            error_message=error_message,
            settings=settings,
        )

        for record in self:
            updates = {
                key: value
                for key, value in values.items()
                if record[key] != value
            }
            if updates:
                record.with_context(skip_client_validation_refresh=True).sudo().write(updates)

    def read(self, fields=None, load='_classic_read'):
        if not self.env.context.get('skip_client_validation_refresh'):
            self._refresh_client_validation_status()
        return super().read(fields=fields, load=load)

    def _get_blocked_dashboard_action(self):
        self.ensure_one()
        self._refresh_client_validation_status()
        if self.show_dashboard:
            return None

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': self.client_status_title or _('Servicio restringido'),
                'message': self.client_status_message or _('Contacta a soporte para reactivar el servicio.'),
                'type': 'warning',
                'sticky': False,
            },
        }

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

    def action_open_external_instance(self):
        self.ensure_one()
        blocked_action = self._get_blocked_dashboard_action()
        if blocked_action:
            return blocked_action

        instance_url, support_url = self._build_instance_and_support_urls()
        return {
            'type': 'ir.actions.act_url',
            'url': instance_url,
            'target': 'new',
        }

    def action_request_support(self):
        self.ensure_one()
        instance_url, support_url = self._build_instance_and_support_urls()
        return {
            'type': 'ir.actions.act_url',
            'url': support_url,
            'target': 'new',
        }

    def action_open_settings(self):
        self.ensure_one()
        return self.env.ref('pbi_connections.action_pbi_connections_settings').read()[0]
