import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class AdvancedMetricsInicio(models.Model):
    _name = 'advanced_metrics.inicio'
    _description = 'Pantalla principal de Advanced Metrics'

    _DEFAULT_CLIENT_VALIDATION_URL = 'https://clients-service.vercel.app/api/production-v1-public/clients/key/SDSAW54D'
    _DEFAULT_CLIENT_VALIDATION_API_KEY = 'SHKJSDHKA'
    _DEFAULT_SUPPORT_URL = 'https://www.zoraen.com'

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
        default='La instancia esta lista para consultar los reportes y endpoints de BI.',
    )

    @api.model
    def _get_client_validation_settings(self):
        config = self.env['ir.config_parameter'].sudo()
        return {
            'url': config.get_param('advanced_metrics.client_validation_url', self._DEFAULT_CLIENT_VALIDATION_URL),
            'api_key': config.get_param('advanced_metrics.client_validation_api_key', self._DEFAULT_CLIENT_VALIDATION_API_KEY),
            'support_url': config.get_param('advanced_metrics.support_url', self._DEFAULT_SUPPORT_URL),
        }

    @api.model
    def _fetch_client_validation_payload(self, settings):
        url = settings.get('url')
        if not url:
            raise ValueError(_('No se ha configurado la URL de validacion del cliente.'))

        headers = {
            'Accept': 'application/json',
        }
        if settings.get('api_key'):
            headers['x-api-key'] = settings['api_key']

        request = Request(url, headers=headers, method='GET')
        with urlopen(request, timeout=10) as response:
            payload = response.read().decode('utf-8') or '{}'
        return json.loads(payload)

    @api.model
    def _build_client_status_values(self, payload=None, error_message=None, settings=None):
        settings = settings or self._get_client_validation_settings()
        support_url = settings.get('support_url') or self._DEFAULT_SUPPORT_URL

        values = {
            'show_dashboard': True,
            'client_validation_state': 'ok',
            'client_status_code': '',
            'support_url': support_url,
            'client_status_title': _('Metricas disponibles'),
            'client_status_message': _('La instancia esta lista para consultar los reportes y endpoints de BI.'),
        }

        if error_message:
            values.update({
                'client_validation_state': 'error',
                'client_status_code': 'validation_error',
                'client_status_title': _('No se pudo validar el estado del cliente'),
                'client_status_message': _(
                    'No fue posible confirmar el estado del servicio en este momento. Intenta nuevamente o contacta a soporte si el problema persiste.'
                ),
            })
            return values

        data = payload.get('data') or {}
        status_code = data.get('status', payload.get('code', ''))
        values['client_status_code'] = str(status_code or '')

        user_message = (payload.get('userMessage') or '').strip()
        technical_message = (payload.get('technicalMessage') or '').strip()

        if str(status_code) == '5':
            values.update({
                'show_dashboard': False,
                'client_validation_state': 'payment_due',
                'client_status_title': _('Cliente insolvente'),
                'client_status_message': user_message or technical_message or _(
                    'La instancia presenta un saldo pendiente. Contacta a soporte para reactivar el acceso a Ordenes de Venta y Credenciales Power BI.'
                ),
            })

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
        return {
            'type': 'ir.actions.act_url',
            'url': self.support_url or self._DEFAULT_SUPPORT_URL,
            'target': 'new',
        }

    def action_open_sales_report(self):
        self.ensure_one()
        blocked_action = self._get_blocked_dashboard_action()
        if blocked_action:
            return blocked_action
        action = self.env.ref('advanced_metrics.action_advanced_metrics_report_wizard').read()[0]
        action['_noBreadcrumbs'] = True
        return action

    def action_open_api_config(self):
        self.ensure_one()
        blocked_action = self._get_blocked_dashboard_action()
        if blocked_action:
            return blocked_action

        action_ref = 'pbi_connections.action_pbi_connections_api_config'
        if 'pbi_connections.api.config' not in self.env:
            action_ref = 'advanced_metrics.action_advanced_metrics_api_config'
        return self.env.ref(action_ref).read()[0]


class AdvancedMetricsRegistro(models.Model):
    _name = 'advanced_metrics.registro'
    _description = 'Registro de Advanced Metrics'

    name = fields.Char(string='Nombre', required=True)
    descripcion = fields.Text(string='Descripción')
