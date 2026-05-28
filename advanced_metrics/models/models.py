import json
import logging
from urllib.parse import quote
from urllib.error import HTTPError, URLError
from urllib.request import HTTPSHandler, ProxyHandler, Request, build_opener

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class AdvancedMetricsInicio(models.Model):
    _name = 'advanced_metrics.inicio'
    _description = 'Pantalla principal de Advanced Metrics'

    _DEFAULT_CONNECTION_BASE_URL = 'https://api.zoraen.com'
    _DEFAULT_CONNECTION_API_PATH = '/api/production/addons/vladdonconnection'
    _DEFAULT_CONNECTION_API_KEY = ''
    _DEFAULT_CONNECTION_ADDON_API_KEY = ''
    _DEFAULT_INSTANCE_KEY = ''
    _INSTANCE_BASE_URL = 'https://adm.zoraen.com/instances/i'
    _SUPPORT_BASE_URL = 'https://adm.zoraen.com/support?instance='

    name = fields.Char(string='Nombre', required=True)
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
    support_url = fields.Char(string='URL de soporte', default='https://www.zoraen.com')
    client_status_title = fields.Char(
        string='Titulo de estado del cliente',
        default='Metricas disponibles',
    )
    client_status_message = fields.Text(
        string='Mensaje de estado del cliente',
        default='La instancia esta lista para consultar los reportes operativos de ventas e inventario.',
    )
    client_validation_debug = fields.Text(
        string='Detalle tecnico de validacion',
        readonly=True,
    )

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

    @api.model
    def _get_client_validation_settings(self):
        config = self.env['ir.config_parameter'].sudo()
        instance_key = config.get_param('advanced_metrics.instance_key', self._DEFAULT_INSTANCE_KEY)
        instance_key = self._normalize_external_key(instance_key)
        return {
            'base_url': self._normalize_validation_base_url(
                config.get_param('advanced_metrics.connection_base_url', self._DEFAULT_CONNECTION_BASE_URL)
            ),
            'api_path': self._normalize_external_key(
                config.get_param('advanced_metrics.connection_api_path', self._DEFAULT_CONNECTION_API_PATH)
            ),
            'api_key': self._normalize_external_key(
                config.get_param('advanced_metrics.connection_api_key', self._DEFAULT_CONNECTION_API_KEY)
            ),
            'addon_api_key': self._normalize_external_key(
                config.get_param('advanced_metrics.connection_addon_api_key', self._DEFAULT_CONNECTION_ADDON_API_KEY)
            ),
            'support_url': config.get_param('advanced_metrics.support_url', ''),
            'instance_key': instance_key,
        }

    @api.model
    def _build_instance_and_support_urls(self, settings=None):
        settings = settings or self._get_client_validation_settings()
        safe_key = quote(self._normalize_external_key(settings.get('instance_key')))

        instance_url = f'{self._INSTANCE_BASE_URL}/{safe_key}'
        support_url = f'{self._SUPPORT_BASE_URL}{safe_key}'
        return instance_url, support_url

    @api.model
    def _get_missing_required_settings(self, settings=None):
        settings = settings or self._get_client_validation_settings()
        required_values = {
            'base_url': settings.get('base_url'),
            'api_path': settings.get('api_path'),
            'api_key': settings.get('api_key'),
            'addon_api_key': settings.get('addon_api_key'),
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
        api_path = self._normalize_external_key(settings.get('api_path')).lstrip('/')
        if not base_url or not api_path:
            raise ValueError(_('No se ha configurado la URL base o el path de conexion.'))
        url = f'{base_url}/{api_path}'

        headers = {
            'Accept': 'application/json',
        }
        if settings.get('api_key'):
            headers['x-api-key'] = settings['api_key']
        if settings.get('addon_api_key'):
            headers['x-addonapi-key'] = settings['addon_api_key']

        request = Request(url, headers=headers, method='GET')
        # Bypass environment proxy settings; curl works here while urllib may fail
        # if a broken proxy is injected into the Python process environment.
        opener = build_opener(ProxyHandler({}), HTTPSHandler())
        with opener.open(request, timeout=10) as response:
            payload = response.read().decode('utf-8') or '{}'
        return json.loads(payload)

    @api.model
    def _build_client_status_values(self, payload=None, error_message=None, settings=None):
        settings = settings or self._get_client_validation_settings()
        instance_url, support_url = self._build_instance_and_support_urls(settings)
        missing_settings = self._get_missing_required_settings(settings)

        values = {
            'show_dashboard': True,
            'client_validation_state': 'ok',
            'client_status_code': '',
            'support_url': support_url,
            'client_status_title': _('Metricas disponibles'),
            'client_status_message': _('La instancia esta lista para consultar los reportes operativos de ventas e inventario.'),
            'client_validation_debug': '',
        }

        if missing_settings:
            values.update({
                'show_dashboard': False,
                'client_validation_state': 'inactive',
                'client_status_code': 'missing_configuration',
                'client_status_title': _('Configuracion incompleta'),
                'client_status_message': _(
                    'Debes completar la configuracion de integracion (Key de instancia, URL base, path, API key y Addon API key) antes de usar el modulo.'
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
        success = payload.get('success') is True
        response_code = str(payload.get('rescode') or '')
        values['client_status_code'] = response_code
        values['client_validation_debug'] = json.dumps({
            'success': payload.get('success'),
            'rescode': payload.get('rescode'),
            'response': payload,
        }, ensure_ascii=False)

        if not success:
            values.update({
                'show_dashboard': False,
                'client_validation_state': 'error',
                'client_status_code': response_code or 'invalid_response',
                'client_status_title': _('Cliente no valido'),
                'client_status_message': _(
                    'La conexion no fue autorizada. Verifica la configuracion y revisa el codigo de respuesta devuelto por el servicio.'
                ),
            })
            return values

        return values

    def _refresh_client_validation_status(self):
        if not self:
            return

        settings = self._get_client_validation_settings()
        payload = {}
        error_message = None

        try:
            payload = self._fetch_client_validation_payload(settings)
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            error_message = str(exc)
            _logger.warning('Advanced Metrics client validation failed: %s', exc)
        except Exception as exc:
            error_message = str(exc)
            _logger.exception('Unexpected error during Advanced Metrics client validation: %s', exc)

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

    def action_request_support(self):
        self.ensure_one()
        instance_url, support_url = self._build_instance_and_support_urls()
        return {
            'type': 'ir.actions.act_url',
            'url': support_url,
            'target': 'new',
        }

    def action_open_external_instance(self):
        self.ensure_one()
        instance_url, _ = self._build_instance_and_support_urls()
        return {
            'type': 'ir.actions.act_url',
            'url': instance_url,
            'target': 'new',
        }

    def action_open_sales_report(self):
        self.ensure_one()
        blocked_action = self._get_blocked_dashboard_action()
        if blocked_action:
            return blocked_action
        action = self.env.ref('advanced_metrics.action_advanced_metrics_report_wizard').read()[0]
        wizard = self.env['advanced_metrics.report.wizard'].create({})
        form_view = self.env.ref('advanced_metrics.view_advanced_metrics_report_wizard_form')
        action['res_id'] = wizard.id
        action['view_id'] = form_view.id
        action['views'] = [(form_view.id, 'form')]
        action['_noBreadcrumbs'] = True
        return action

    def action_open_api_config(self):
        self.ensure_one()
        blocked_action = self._get_blocked_dashboard_action()
        if blocked_action:
            return blocked_action

        return self.env.ref('pbi_connections.action_pbi_connections_api_config').read()[0]

    def action_open_settings(self):
        self.ensure_one()
        action = self.env.ref('advanced_metrics.action_advanced_metrics_settings').read()[0]
        action['_noBreadcrumbs'] = True
        return action


class AdvancedMetricsRegistro(models.Model):
    _name = 'advanced_metrics.registro'
    _description = 'Registro de Advanced Metrics'

    name = fields.Char(string='Nombre', required=True)
    descripcion = fields.Text(string='Descripción')
