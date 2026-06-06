# -*- coding: utf-8 -*-

import json
import logging
from collections import defaultdict
from datetime import timedelta
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

    def _open_first_available_action(self, *action_xmlids):
        self.ensure_one()
        for action_xmlid in action_xmlids:
            action = self.env.ref(action_xmlid, raise_if_not_found=False)
            if action:
                action_data = action.read()[0]
                action_data['target'] = 'main'
                return action_data
        raise UserError('No se encontro la accion configurada para esta pantalla.')

    def action_open_home(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_inicio')

    def action_open_button_1(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_summary')

    def action_open_button_2(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_commercial_planning')

    def action_open_button_3(self):
        return self._open_first_available_action(
            'zrn_planning.action_zrn_planning_production_planning',
            'zrn_prodigyn.action_zrn_prodigyn_production_planning',
        )

    def action_open_button_4(self):
        return self._open_first_available_action(
            'zrn_planning.action_zrn_planning_purchase_planning',
            'zrn_prodigyn.action_zrn_prodigyn_purchase_planning',
        )

    def action_open_button_5(self):
        return self._open_first_available_action(
            'zrn_planning.action_zrn_planning_delivery_planning',
            'zrn_prodigyn.action_zrn_prodigyn_delivery_planning',
        )

    def action_open_reporting_center(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_reporting_analysis')

    def action_open_commercial_center(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_commercial_planning')

    def action_open_settings_dashboard(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_settings')

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
        return self._open_first_available_action(
            'zrn_planning.action_zrn_planning_production_planning',
            'zrn_prodigyn.action_zrn_prodigyn_production_planning',
        )

    def action_open_supply_planning(self):
        return self._open_first_available_action(
            'zrn_planning.action_zrn_planning_purchase_planning',
            'zrn_prodigyn.action_zrn_prodigyn_purchase_planning',
        )

    def action_open_logistics_planning(self):
        return self._open_first_available_action(
            'zrn_planning.action_zrn_planning_delivery_planning',
            'zrn_prodigyn.action_zrn_prodigyn_delivery_planning',
        )

    def action_open_resource_planning(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_resource_planning')

    def action_open_scenarios(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_reporting_scenarios')

    def action_open_reporting(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_reporting_analysis')

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
        wizard_model = 'zrn_planning.production.planning.wizard'
        if wizard_model not in self.env:
            wizard_model = 'zrn_prodigyn.production.planning.wizard'
        wizard = self.env[wizard_model].create({})
        return wizard.action_open_filters()

    def action_open_supply_filters(self):
        self.ensure_one()
        wizard_model = 'zrn_planning.purchase.planning.wizard'
        if wizard_model not in self.env:
            wizard_model = 'zrn_prodigyn.purchase.planning.wizard'
        wizard = self.env[wizard_model].create({})
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
    company_currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        default=lambda self: self.env.company.currency_id.id,
        readonly=True,
    )
    commercial_date_from = fields.Date(string='Fecha inicial comercial', readonly=True)
    commercial_date_to = fields.Date(string='Fecha final comercial', readonly=True)
    commercial_period_label = fields.Char(string='Periodo comercial', readonly=True)
    commercial_total_amount = fields.Monetary(
        string='Venta total',
        currency_field='company_currency_id',
        readonly=True,
    )
    commercial_order_count = fields.Integer(string='Pedidos considerados', readonly=True)
    commercial_customer_count = fields.Integer(string='Clientes comerciales', readonly=True)
    commercial_point_count = fields.Integer(string='PDVs considerados', readonly=True)
    commercial_product_count = fields.Integer(string='Productos vendidos', readonly=True)
    commercial_daily_graph_data = fields.Text(string='Grafica de venta diaria', readonly=True)
    commercial_totals_graph_data = fields.Text(string='Grafica de venta total', readonly=True)
    commercial_ranking_graph_data = fields.Text(string='Grafica de ranking comercial', readonly=True)
    commercial_stacked_chart_data = fields.Text(string='Grafica apilada comercial', readonly=True)
    commercial_pareto_chart_data = fields.Text(string='Grafica pareto comercial', readonly=True)
    commercial_heatmap_chart_data = fields.Text(string='Grafica heatmap comercial', readonly=True)
    commercial_donut_chart_data = fields.Text(string='Grafica donut comercial', readonly=True)
    commercial_scatter_chart_data = fields.Text(string='Grafica scatter comercial', readonly=True)
    commercial_channel_line_ids = fields.One2many(
        'zrn_prodigyn.reporting.commercial.channel.line',
        'tool_id',
        string='Top canales',
        readonly=True,
    )
    commercial_customer_line_ids = fields.One2many(
        'zrn_prodigyn.reporting.commercial.customer.line',
        'tool_id',
        string='Top clientes / PDVs',
        readonly=True,
    )
    commercial_product_line_ids = fields.One2many(
        'zrn_prodigyn.reporting.commercial.product.line',
        'tool_id',
        string='Top productos',
        readonly=True,
    )

    @api.model
    def _get_commercial_tool_record(self):
        return self.env.ref(
            'zrn_prodigyn.zrn_prodigyn_reporting_commercial_default',
            raise_if_not_found=False,
        )

    @api.model
    def _get_commercial_summary_period(self):
        date_to = fields.Date.to_date(fields.Date.context_today(self))
        date_from = date_to.replace(month=1, day=1)
        return date_from, date_to

    @api.model
    def _get_commercial_sale_orders(self, date_from, date_to):
        if 'sale.order' not in self.env:
            return self.env['sale.order']

        domain = [
            ('state', 'in', ['sale', 'done']),
            ('partner_id', '!=', False),
        ]
        if date_from:
            domain.append(('date_order', '>=', f'{date_from} 00:00:00'))
        if date_to:
            domain.append(('date_order', '<=', f'{date_to} 23:59:59'))

        return self.env['sale.order'].search(domain, order='date_order desc, id desc')

    @api.model
    def _get_commercial_sale_order_lines(self, date_from, date_to):
        if 'sale.order.line' not in self.env:
            return self.env['sale.order.line']

        domain = [
            ('order_id.state', 'in', ['sale', 'done']),
            ('display_type', '=', False),
            ('product_id', '!=', False),
        ]
        if date_from:
            domain.append(('order_id.date_order', '>=', f'{date_from} 00:00:00'))
        if date_to:
            domain.append(('order_id.date_order', '<=', f'{date_to} 23:59:59'))

        return self.env['sale.order.line'].search(domain, order='id desc')

    @api.model
    def _build_commercial_period_label(self, date_from, date_to):
        if not date_from or not date_to:
            return 'Sin periodo'
        return '%s al %s' % (
            fields.Date.to_string(date_from),
            fields.Date.to_string(date_to),
        )

    @api.model
    def _build_commercial_line_chart_json(self, orders, date_from, date_to):
        series_start = max(date_from, date_to - timedelta(days=13)) if date_from and date_to else date_from
        daily_amounts = defaultdict(float)
        current_date = series_start

        for order in orders:
            if not order.date_order:
                continue
            order_date = fields.Datetime.to_datetime(order.date_order).date()
            if order_date < series_start or order_date > date_to:
                continue
            daily_amounts[order_date] += float(order.amount_total or 0.0)

        values = []
        while current_date and current_date <= date_to:
            values.append({
                'x': current_date.strftime('%d/%m'),
                'y': round(daily_amounts.get(current_date, 0.0), 2),
                'name': current_date.strftime('%d/%m/%Y'),
            })
            current_date += timedelta(days=1)

        if not values:
            fallback_date = date_to or fields.Date.context_today(self)
            values.append({
                'x': fallback_date.strftime('%d/%m'),
                'y': 0.0,
                'name': fallback_date.strftime('%d/%m/%Y'),
            })

        return json.dumps([{
            'values': values,
            'title': _('Venta diaria'),
            'key': _('Venta diaria'),
            'area': True,
            'color': '#355eff',
            'is_sample_data': False,
        }])

    @api.model
    def _build_commercial_totals_chart_json(self, orders, date_from, date_to):
        series_start = max(date_from, date_to - timedelta(days=55)) if date_from and date_to else date_from
        weekly_amounts = defaultdict(float)
        week_order = []

        for order in orders:
            if not order.date_order:
                continue
            order_date = fields.Datetime.to_datetime(order.date_order).date()
            if order_date < series_start or order_date > date_to:
                continue
            week_start = order_date - timedelta(days=order_date.weekday())
            if week_start not in weekly_amounts:
                week_order.append(week_start)
            weekly_amounts[week_start] += float(order.amount_total or 0.0)

        values = []
        for week_start in sorted(week_order):
            week_end = min(week_start + timedelta(days=6), date_to)
            values.append({
                'label': '%s - %s' % (
                    week_start.strftime('%d/%m'),
                    week_end.strftime('%d/%m'),
                ),
                'value': round(weekly_amounts[week_start], 2),
                'type': 'past',
            })

        if not values and date_to:
            values.append({
                'label': date_to.strftime('%d/%m'),
                'value': 0.0,
                'type': 'past',
            })

        return json.dumps([{
            'values': values,
            'title': _('Venta total'),
            'key': _('Venta total por semana'),
            'is_sample_data': False,
        }])

    @api.model
    def _build_commercial_ranking_chart_json(self, products):
        product_map = {
            product.id: product.display_name
            for product in self.env['product.product'].browse([item['product_id'] for item in products if item.get('product_id')])
        }
        labels = [(product_map.get(item['product_id']) or _('Sin producto'))[:24] for item in products[:8]]
        values = [round(item['sales_amount'], 2) for item in products[:8]]

        if not labels:
            labels = [_('Sin ventas')]
            values = [0.0]

        return json.dumps({
            'labels': labels,
            'values': values,
        })

    @api.model
    def _build_commercial_stacked_chart_json(self, channel_map, order_lines):
        ranked_channels = sorted(channel_map.values(), key=lambda item: item['total_amount'], reverse=True)[:5]
        ranked_channel_ids = [item['partner_id'] for item in ranked_channels]

        product_amounts = defaultdict(float)
        channel_product_amounts = defaultdict(lambda: defaultdict(float))
        for line in order_lines:
            partner = line.order_id.partner_id.commercial_partner_id or line.order_id.partner_id
            product = line.product_id
            if not partner or partner.id not in ranked_channel_ids or not product:
                continue
            amount = float(line.price_total or 0.0)
            product_amounts[product.id] += amount
            channel_product_amounts[partner.id][product.id] += amount

        top_product_ids = [product_id for product_id, _amount in sorted(product_amounts.items(), key=lambda item: item[1], reverse=True)[:4]]
        product_map = {
            product.id: product.display_name[:24]
            for product in self.env['product.product'].browse(top_product_ids)
        }
        labels = []
        series = []

        for channel in ranked_channels:
            partner = self.env['res.partner'].browse(channel['partner_id'])
            labels.append(partner.display_name[:24])

        for product_id in top_product_ids:
            series.append({
                'name': product_map.get(product_id) or _('Producto'),
                'type': 'bar',
                'stack': 'total',
                'data': [
                    round(channel_product_amounts[channel['partner_id']].get(product_id, 0.0), 2)
                    for channel in ranked_channels
                ],
            })

        return json.dumps({
            'labels': labels,
            'series': series,
        })

    @api.model
    def _build_commercial_pareto_chart_json(self, products):
        top_products = products[:10]
        total_sales = sum(item['sales_amount'] for item in top_products) or 1.0
        labels = []
        bar_values = []
        cumulative_values = []
        running_total = 0.0

        product_map = {
            product.id: product.display_name
            for product in self.env['product.product'].browse([item['product_id'] for item in top_products if item.get('product_id')])
        }

        for item in top_products:
            running_total += item['sales_amount']
            labels.append((product_map.get(item['product_id']) or _('Producto'))[:24])
            bar_values.append(round(item['sales_amount'], 2))
            cumulative_values.append(round((running_total / total_sales) * 100, 2))

        return json.dumps({
            'labels': labels,
            'bar_values': bar_values,
            'line_values': cumulative_values,
        })

    @api.model
    def _build_commercial_heatmap_chart_json(self, orders, date_from, date_to):
        series_start = max(date_from, date_to - timedelta(days=55)) if date_from and date_to else date_from
        current_date = series_start
        order_counts = defaultdict(int)

        for order in orders:
            if not order.date_order:
                continue
            order_date = fields.Datetime.to_datetime(order.date_order).date()
            if order_date < series_start or order_date > date_to:
                continue
            order_counts[order_date] += 1

        week_labels = []
        day_labels = ['Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab', 'Dom']
        data = []
        week_index_map = {}

        while current_date and current_date <= date_to:
            week_start = current_date - timedelta(days=current_date.weekday())
            if week_start not in week_index_map:
                week_index_map[week_start] = len(week_labels)
                week_labels.append(week_start.strftime('%d/%m'))
            data.append([
                week_index_map[week_start],
                current_date.weekday(),
                order_counts.get(current_date, 0),
            ])
            current_date += timedelta(days=1)

        return json.dumps({
            'week_labels': week_labels,
            'day_labels': day_labels,
            'data': data,
        })

    @api.model
    def _build_commercial_donut_chart_json(self, channel_map):
        ranked_channels = sorted(channel_map.values(), key=lambda item: item['total_amount'], reverse=True)[:6]
        partner_map = {
            partner.id: partner.display_name
            for partner in self.env['res.partner'].browse([item['partner_id'] for item in ranked_channels if item.get('partner_id')])
        }
        series = [{
            'name': (partner_map.get(item['partner_id']) or _('Canal'))[:28],
            'value': round(item['total_amount'], 2),
        } for item in ranked_channels]
        return json.dumps({'series': series})

    @api.model
    def _build_commercial_scatter_chart_json(self, customers):
        top_customers = customers[:10]
        partner_map = {
            partner.id: partner.display_name
            for partner in self.env['res.partner'].browse([item['partner_id'] for item in top_customers if item.get('partner_id')])
        }
        points = []
        for item in top_customers:
            order_count = item.get('order_count') or 0
            average_ticket = item.get('average_ticket')
            if average_ticket is None:
                average_ticket = (float(item.get('total_amount') or 0.0) / order_count) if order_count else 0.0
            points.append({
                'name': (partner_map.get(item['partner_id']) or _('PDV'))[:24],
                'value': [
                    round(average_ticket, 2),
                    order_count,
                    round(float(item.get('total_amount') or 0.0), 2),
                ],
            })
        return json.dumps({'points': points})

    @api.model
    def _build_commercial_summary_payload(self, date_from, date_to):
        orders = self._get_commercial_sale_orders(date_from, date_to)
        order_lines = self._get_commercial_sale_order_lines(date_from, date_to)

        valid_order_lines_by_order = defaultdict(list)
        for line in order_lines:
            valid_order_lines_by_order[line.order_id.id].append(line)

        channel_map = {}
        customer_map = {}
        product_map = {}

        for order in orders:
            order_partner = order.partner_id
            commercial_partner = order_partner.commercial_partner_id or order_partner
            if not commercial_partner:
                continue

            valid_lines = valid_order_lines_by_order.get(order.id, [])
            unit_count = sum(line.product_uom_qty for line in valid_lines)
            amount_total = float(order.amount_total or 0.0)
            order_date = fields.Datetime.to_datetime(order.date_order).date() if order.date_order else False

            channel_entry = channel_map.setdefault(
                commercial_partner.id,
                {
                    'partner_id': commercial_partner.id,
                    'order_count': 0,
                    'unit_count': 0.0,
                    'total_amount': 0.0,
                    'last_order_date': False,
                },
            )
            channel_entry['order_count'] += 1
            channel_entry['unit_count'] += unit_count
            channel_entry['total_amount'] += amount_total
            if order_date and (
                not channel_entry['last_order_date']
                or order_date > channel_entry['last_order_date']
            ):
                channel_entry['last_order_date'] = order_date

            customer_entry = customer_map.setdefault(
                order_partner.id,
                {
                    'partner_id': order_partner.id,
                    'customer_id': commercial_partner.id,
                    'order_count': 0,
                    'unit_count': 0.0,
                    'total_amount': 0.0,
                    'last_order_date': False,
                },
            )
            customer_entry['order_count'] += 1
            customer_entry['unit_count'] += unit_count
            customer_entry['total_amount'] += amount_total
            if order_date and (
                not customer_entry['last_order_date']
                or order_date > customer_entry['last_order_date']
            ):
                customer_entry['last_order_date'] = order_date

        for line in order_lines:
            product = line.product_id
            if not product:
                continue
            commercial_partner = line.order_id.partner_id.commercial_partner_id or line.order_id.partner_id
            product_entry = product_map.setdefault(
                product.id,
                {
                    'product_id': product.id,
                    'default_code': product.default_code or '',
                    'category_name': product.categ_id.display_name or '',
                    'quantity_sold': 0.0,
                    'sales_amount': 0.0,
                    'customer_ids': set(),
                    'order_ids': set(),
                },
            )
            product_entry['quantity_sold'] += float(line.product_uom_qty or 0.0)
            product_entry['sales_amount'] += float(line.price_total or 0.0)
            if commercial_partner:
                product_entry['customer_ids'].add(commercial_partner.id)
            if line.order_id:
                product_entry['order_ids'].add(line.order_id.id)

        top_channels = sorted(channel_map.values(), key=lambda item: item['total_amount'], reverse=True)[:10]
        top_customers = sorted(customer_map.values(), key=lambda item: item['total_amount'], reverse=True)[:10]
        top_products = sorted(product_map.values(), key=lambda item: item['sales_amount'], reverse=True)[:10]

        return {
            'summary': {
                'company_currency_id': self.env.company.currency_id.id,
                'commercial_date_from': date_from,
                'commercial_date_to': date_to,
                'commercial_period_label': self._build_commercial_period_label(date_from, date_to),
                'commercial_total_amount': round(sum(float(amount or 0.0) for amount in orders.mapped('amount_total')), 2),
                'commercial_order_count': len(orders),
                'commercial_customer_count': len(channel_map),
                'commercial_point_count': len(customer_map),
                'commercial_product_count': len(product_map),
            },
            'charts': {
                'commercial_daily_graph_data': self._build_commercial_line_chart_json(orders, date_from, date_to),
                'commercial_totals_graph_data': self._build_commercial_totals_chart_json(orders, date_from, date_to),
                'commercial_ranking_graph_data': self._build_commercial_ranking_chart_json(top_products),
                'commercial_stacked_chart_data': self._build_commercial_stacked_chart_json(channel_map, order_lines),
                'commercial_pareto_chart_data': self._build_commercial_pareto_chart_json(top_products),
                'commercial_heatmap_chart_data': self._build_commercial_heatmap_chart_json(orders, date_from, date_to),
                'commercial_donut_chart_data': self._build_commercial_donut_chart_json(channel_map),
                'commercial_scatter_chart_data': self._build_commercial_scatter_chart_json(top_customers),
            },
            'channels': [
                {
                    'sequence': index + 1,
                    'partner_id': item['partner_id'],
                    'order_count': item['order_count'],
                    'unit_count': item['unit_count'],
                    'total_amount': round(item['total_amount'], 2),
                    'average_ticket': round(item['total_amount'] / item['order_count'], 2) if item['order_count'] else 0.0,
                    'last_order_date': item['last_order_date'],
                }
                for index, item in enumerate(top_channels)
            ],
            'customers': [
                {
                    'sequence': index + 1,
                    'partner_id': item['partner_id'],
                    'customer_id': item['customer_id'],
                    'order_count': item['order_count'],
                    'unit_count': item['unit_count'],
                    'total_amount': round(item['total_amount'], 2),
                    'average_ticket': round(item['total_amount'] / item['order_count'], 2) if item['order_count'] else 0.0,
                    'last_order_date': item['last_order_date'],
                }
                for index, item in enumerate(top_customers)
            ],
            'products': [
                {
                    'sequence': index + 1,
                    'product_id': item['product_id'],
                    'default_code': item['default_code'],
                    'category_name': item['category_name'],
                    'quantity_sold': item['quantity_sold'],
                    'sales_amount': round(item['sales_amount'], 2),
                    'customer_count': len(item['customer_ids']),
                    'order_count': len(item['order_ids']),
                }
                for index, item in enumerate(top_products)
            ],
        }

    def _refresh_commercial_summary(self):
        commercial_record = self._get_commercial_tool_record()
        if not commercial_record:
            return

        target_records = self.filtered(lambda record: record.id == commercial_record.id)
        if not target_records:
            return

        date_from, date_to = self._get_commercial_summary_period()
        payload = self._build_commercial_summary_payload(date_from, date_to)

        for record in target_records:
            values = dict(payload['summary'])
            values.update(payload['charts'])
            values.update({
                'commercial_channel_line_ids': [(5, 0, 0)] + [
                    (0, 0, line_values) for line_values in payload['channels']
                ],
                'commercial_customer_line_ids': [(5, 0, 0)] + [
                    (0, 0, line_values) for line_values in payload['customers']
                ],
                'commercial_product_line_ids': [(5, 0, 0)] + [
                    (0, 0, line_values) for line_values in payload['products']
                ],
            })
            record.with_context(skip_commercial_summary_refresh=True).sudo().write(values)

    def read(self, fields=None, load='_classic_read'):
        if not self.env.context.get('skip_commercial_summary_refresh'):
            self._refresh_commercial_summary()
        return super().read(fields=fields, load=load)


class ZrnProdigynReportingCommercialChannelLine(models.Model):
    _name = 'zrn_prodigyn.reporting.commercial.channel.line'
    _description = 'Resumen comercial por canal'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Secuencia', readonly=True)
    tool_id = fields.Many2one('zrn_prodigyn.internal.tool', string='Herramienta', required=True, ondelete='cascade')
    currency_id = fields.Many2one('res.currency', related='tool_id.company_currency_id', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Canal / cuenta', required=True, readonly=True)
    order_count = fields.Integer(string='Pedidos', readonly=True)
    unit_count = fields.Float(string='Unidades', readonly=True)
    total_amount = fields.Monetary(string='Venta total', currency_field='currency_id', readonly=True)
    average_ticket = fields.Monetary(string='Ticket promedio', currency_field='currency_id', readonly=True)
    last_order_date = fields.Date(string='Ultimo pedido', readonly=True)


class ZrnProdigynReportingCommercialCustomerLine(models.Model):
    _name = 'zrn_prodigyn.reporting.commercial.customer.line'
    _description = 'Resumen comercial por cliente o PDV'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Secuencia', readonly=True)
    tool_id = fields.Many2one('zrn_prodigyn.internal.tool', string='Herramienta', required=True, ondelete='cascade')
    currency_id = fields.Many2one('res.currency', related='tool_id.company_currency_id', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Punto de venta', required=True, readonly=True)
    customer_id = fields.Many2one('res.partner', string='Cliente comercial', readonly=True)
    order_count = fields.Integer(string='Pedidos', readonly=True)
    unit_count = fields.Float(string='Unidades', readonly=True)
    total_amount = fields.Monetary(string='Venta total', currency_field='currency_id', readonly=True)
    average_ticket = fields.Monetary(string='Ticket promedio', currency_field='currency_id', readonly=True)
    last_order_date = fields.Date(string='Ultimo pedido', readonly=True)


class ZrnProdigynReportingCommercialProductLine(models.Model):
    _name = 'zrn_prodigyn.reporting.commercial.product.line'
    _description = 'Resumen comercial por producto'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Secuencia', readonly=True)
    tool_id = fields.Many2one('zrn_prodigyn.internal.tool', string='Herramienta', required=True, ondelete='cascade')
    currency_id = fields.Many2one('res.currency', related='tool_id.company_currency_id', readonly=True)
    product_id = fields.Many2one('product.product', string='Producto', required=True, readonly=True)
    default_code = fields.Char(string='Referencia interna', readonly=True)
    category_name = fields.Char(string='Categoria', readonly=True)
    quantity_sold = fields.Float(string='Unidades vendidas', readonly=True)
    sales_amount = fields.Monetary(string='Venta total', currency_field='currency_id', readonly=True)
    customer_count = fields.Integer(string='Clientes', readonly=True)
    order_count = fields.Integer(string='Pedidos', readonly=True)
