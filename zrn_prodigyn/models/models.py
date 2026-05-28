# -*- coding: utf-8 -*-

import json
import logging
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPSHandler, ProxyHandler, Request, build_opener

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ZrnProdigynNavigationMixin:
    def _open_singleton_action(self, action_xmlid):
        self.ensure_one()
        action = self.env.ref(action_xmlid, raise_if_not_found=False)
        if not action:
            raise UserError('No se encontro la accion configurada para esta pantalla.')
        action_data = action.read()[0]
        action_data['target'] = 'main'
        return action_data

    def action_open_home(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_inicio')

    def action_open_button_1(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_summary')

    def action_open_button_2(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_commercial_planning')

    def action_open_button_3(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_production_planning')

    def action_open_button_4(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_purchase_planning')

    def action_open_button_5(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_delivery_planning')

    def action_open_support(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'name': 'Open Support',
            'url': self.support_url or self._build_support_url(),
            'target': 'new',
        }

    def action_open_prodigyn_go(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'name': 'Prodigyn Go',
            'url': 'https://prodigyn.zoraen.com/go?tkn=cualquier_cosa_por_ahora',
            'target': 'new',
        }


class ZrnProdigynInicio(ZrnProdigynNavigationMixin, models.Model):
    _name = 'zrn_prodigyn.inicio'
    _description = 'Pantalla principal de Prodigyn'
    _order = 'sequence, id'

    _DEFAULT_CONNECTION_BASE_URL = 'https://api.zoraen.com'
    _DEFAULT_CONNECTION_API_PATH = '/api/production/addons/vladdonconnection'
    _DEFAULT_CONNECTION_API_KEY = ''
    _DEFAULT_CONNECTION_ADDON_API_KEY = ''
    _DEFAULT_INSTANCE_KEY = ''
    _SUPPORT_BASE_URL = 'https://adm.zoraen.com/support?instance='

    name = fields.Char(string='Nombre', required=True, default='Prodigyn')
    sequence = fields.Integer(string='Secuencia', default=10)
    page_key = fields.Selection(
        [
            ('overview', 'Resumen'),
            ('workspace', 'Workspace'),
        ],
        string='Pagina',
        required=True,
        default='overview',
    )
    show_dashboard = fields.Boolean(string='Mostrar dashboard', default=True)
    client_validation_state = fields.Selection(
        [
            ('ok', 'Activo'),
            ('inactive', 'Inactivo'),
            ('error', 'Error'),
        ],
        string='Estado de validacion',
        default='ok',
    )
    client_status_code = fields.Char(string='Codigo de estado')
    support_url = fields.Char(string='URL de soporte', default='https://www.zoraen.com')
    client_status_title = fields.Char(
        string='Titulo de estado',
        default='Prodigyn disponible',
    )
    client_status_message = fields.Text(
        string='Mensaje de estado',
        default='La instancia esta lista para usar Prodigyn.',
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
        instance_key = self._normalize_external_key(
            config.get_param('zrn_prodigyn.instance_key', self._DEFAULT_INSTANCE_KEY)
        )
        return {
            'base_url': self._normalize_validation_base_url(
                config.get_param('zrn_prodigyn.connection_base_url', self._DEFAULT_CONNECTION_BASE_URL)
            ),
            'api_path': self._normalize_external_key(
                config.get_param('zrn_prodigyn.connection_api_path', self._DEFAULT_CONNECTION_API_PATH)
            ),
            'api_key': self._normalize_external_key(
                config.get_param('zrn_prodigyn.connection_api_key', self._DEFAULT_CONNECTION_API_KEY)
            ),
            'addon_api_key': self._normalize_external_key(
                config.get_param('zrn_prodigyn.connection_addon_api_key', self._DEFAULT_CONNECTION_ADDON_API_KEY)
            ),
            'instance_key': instance_key,
        }

    @api.model
    def _build_support_url(self, settings=None):
        settings = settings or self._get_client_validation_settings()
        instance_key = quote(self._normalize_external_key(settings.get('instance_key')))
        return (
            f'{self._SUPPORT_BASE_URL}{instance_key}'
            if instance_key
            else 'https://www.zoraen.com'
        )

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
        opener = build_opener(ProxyHandler({}), HTTPSHandler())
        with opener.open(request, timeout=10) as response:
            payload = response.read().decode('utf-8') or '{}'
        return json.loads(payload)

    @api.model
    def _build_client_status_values(self, payload=None, error_message=None, settings=None):
        settings = settings or self._get_client_validation_settings()
        missing_settings = self._get_missing_required_settings(settings)

        values = {
            'show_dashboard': True,
            'client_validation_state': 'ok',
            'client_status_code': '',
            'support_url': self._build_support_url(settings),
            'client_status_title': _('Prodigyn disponible'),
            'client_status_message': _('La instancia esta lista para usar Prodigyn.'),
            'client_validation_debug': '',
        }

        if missing_settings:
            values.update({
                'show_dashboard': False,
                'client_validation_state': 'inactive',
                'client_status_code': 'missing_configuration',
                'client_status_title': _('Configuracion incompleta'),
                'client_status_message': _(
                    'Debes completar la configuracion de integracion de Prodigyn antes de usar el modulo.'
                ),
                'client_validation_debug': _('Parametros faltantes: %s') % ', '.join(missing_settings),
            })
            return values

        if error_message:
            values.update({
                'show_dashboard': False,
                'client_validation_state': 'error',
                'client_status_code': 'validation_error',
                'client_status_title': _('No se pudo validar la conexion'),
                'client_status_message': _(
                    'No fue posible validar la conexion con el servicio en este momento. Intenta nuevamente o contacta a soporte.'
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
                'client_status_title': _('Conexion no autorizada'),
                'client_status_message': _(
                    'La conexion no fue autorizada. Verifica la configuracion y revisa el codigo de respuesta del servicio.'
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
            _logger.warning('Prodigyn client validation failed: %s', exc)
        except Exception as exc:
            error_message = str(exc)
            _logger.exception('Unexpected error during Prodigyn client validation: %s', exc)

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

    def action_open_summary(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_summary')

    def action_open_commercial_planning(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_commercial_planning')

    def action_open_production_planning(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_production_planning')

    def action_open_supply_planning(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_purchase_planning')

    def action_open_logistics_planning(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_delivery_planning')

    def action_open_resource_planning(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_resource_planning')

    def action_open_scenarios(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_scenarios')

    def action_open_reporting(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_reporting')

    def action_open_settings_dashboard(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_settings')


class ZrnProdigynProductionPlanning(ZrnProdigynNavigationMixin, models.Model):
    _name = 'zrn_prodigyn.production.planning'
    _description = 'Planeacion de produccion y fabricacion'
    _order = 'sequence, id'

    name = fields.Char(string='Nombre', required=True, default='Planeacion de produccion/fabricacion')
    sequence = fields.Integer(string='Secuencia', default=10)
    page_key = fields.Selection(
        [
            ('overview', 'Resumen'),
            ('workspace', 'Workspace'),
        ],
        string='Pagina',
        required=True,
        default='overview',
    )

    def action_open_sale_order_filters(self):
        self.ensure_one()
        wizard = self.env['zrn_prodigyn.production.planning.wizard'].create({})
        return wizard.action_open_filters()

    def action_open_supply_filters(self):
        self.ensure_one()
        wizard = self.env['zrn_prodigyn.purchase.planning.wizard'].create({})
        return wizard.action_open_filters()


class ZrnProdigynPurchasePlanning(ZrnProdigynNavigationMixin, models.Model):
    _name = 'zrn_prodigyn.purchase.planning'
    _description = 'Planeacion de insumos y compras'

    name = fields.Char(string='Nombre', required=True, default='Planeacion de Abastecimiento')


class ZrnProdigynDeliveryPlanning(ZrnProdigynNavigationMixin, models.Model):
    _name = 'zrn_prodigyn.delivery.planning'
    _description = 'Planeacion de entregas'

    name = fields.Char(string='Nombre', required=True, default='Planeacion Logistica')


class ZrnProdigynInternalTool(ZrnProdigynNavigationMixin, models.Model):
    _name = 'zrn_prodigyn.internal.tool'
    _description = 'Herramienta interna de Prodigyn'

    name = fields.Char(string='Nombre', required=True)
