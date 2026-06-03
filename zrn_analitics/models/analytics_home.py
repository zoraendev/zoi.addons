# -*- coding: utf-8 -*-

from collections import defaultdict
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ZrnAnalyticsNavigationMixin:
    def _open_singleton_action(self, action_xmlid):
        self.ensure_one()
        action = self.env.ref(action_xmlid, raise_if_not_found=False)
        if not action:
            raise UserError('No se encontro la accion configurada para esta pantalla.')
        action_data = action.read()[0]
        action_data['target'] = 'main'
        return action_data

    def action_open_home(self):
        return self._open_singleton_action('zrn_analitics.action_zrn_analitics_home')

    def action_open_workspace(self):
        return self._open_singleton_action('zrn_analitics.action_zrn_analitics_workspace')

    def action_open_scenarios(self):
        return self._open_singleton_action('zrn_analitics.action_zrn_analitics_scenarios')

    def action_open_hubs_client(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'name': 'Hubs',
            'tag': 'zrn_analitics.hubs',
            'target': 'main',
        }

    def action_open_button_1(self):
        return self.action_open_home()

    def action_open_button_2(self):
        return self.action_open_workspace()

    def action_open_button_3(self):
        return self.action_open_scenarios()

    def action_open_button_4(self):
        return self.action_open_workspace()

    def action_open_button_5(self):
        return self.action_open_workspace()


class ZrnAnalyticsHome(ZrnAnalyticsNavigationMixin, models.Model):
    _name = 'zrn_analitics.home'
    _description = 'Centro principal de Zoraen Analytics'
    _order = 'sequence, id'

    name = fields.Char(string='Nombre', required=True, default='Zoraen Analytics')
    sequence = fields.Integer(string='Secuencia', default=10)
    page_key = fields.Selection(
        [
            ('overview', 'Resumen'),
            ('workspace', 'Workspace'),
            ('scenarios', 'Escenarios'),
        ],
        string='Pagina',
        required=True,
        default='overview',
    )

    def action_open_hubs(self):
        self.ensure_one()
        return self.action_open_hubs_client()

    def action_open_dashboards(self):
        self.ensure_one()
        return self.action_open_workspace()

    def action_open_processing(self):
        self.ensure_one()
        return self.action_open_workspace()

    def action_open_scenarios(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_analitics.action_zrn_analitics_scenarios')

    @api.model
    def _get_commercial_hub_period(self):
        date_to = fields.Date.to_date(fields.Date.context_today(self))
        date_from = date_to.replace(month=1, day=1)
        return date_from, date_to

    @api.model
    def _get_commercial_brand_records(self):
        return self.env['zrn_commercial.commercial.brand'].search([
            ('active', '=', True),
            ('company_id', '=', self.env.company.id),
        ], order='name asc, id asc')

    @api.model
    def _get_commercial_brand_map(self):
        brands = self._get_commercial_brand_records()
        product_brand_map = {}
        for brand in brands:
            active_links = brand.product_link_ids.filtered(lambda link: link.active and link.product_id)
            for link in active_links:
                product_brand_map[link.product_id.id] = {
                    'brand_id': brand.id,
                    'brand_name': brand.name,
                }
        return brands, product_brand_map

    @api.model
    def _get_commercial_channel_records(self, channel_names=None):
        domain = [
            ('active', '=', True),
            ('company_id', '=', self.env.company.id),
        ]
        if channel_names:
            domain.append(('name', 'in', list(channel_names)))
        return self.env['zrn_commercial.commercial.channel'].search(domain, order='name asc, id asc')

    @api.model
    def _get_channel_setup_status(self):
        channels = self._get_commercial_channel_records()
        links = self.env['zrn_commercial.commercial.channel.partner'].search([
            ('active', '=', True),
            ('company_id', '=', self.env.company.id),
        ])
        return {
            'channels': channels,
            'links': links,
            'has_channels': bool(channels),
            'has_assignments': bool(links),
        }

    @api.model
    def _get_channel_empty_message(self, setup_status):
        if not setup_status['has_channels']:
            return 'No hay canales comerciales creados en Zoraen Commercial.'
        if not setup_status['has_assignments']:
            return 'No hay PDVs o clientes cargados en los canales comerciales.'
        return 'No hay datos para los filtros seleccionados.'

    @api.model
    def _get_explicit_channel_name(self, partner):
        if not partner:
            return False
        channel_link = self.env['zrn_commercial.commercial.channel.partner'].search([
            ('partner_id', '=', partner.id),
            ('active', '=', True),
            ('company_id', '=', self.env.company.id),
        ], limit=1)
        return channel_link.channel_id.name if channel_link and channel_link.channel_id else False

    @api.model
    def _get_commercial_sale_order_lines(self, date_from, date_to, product_ids):
        domain = [
            ('order_id.state', 'in', ['sale', 'done']),
            ('display_type', '=', False),
            ('product_id', 'in', product_ids),
        ]
        if date_from:
            domain.append(('order_id.date_order', '>=', f'{date_from} 00:00:00'))
        if date_to:
            domain.append(('order_id.date_order', '<=', f'{date_to} 23:59:59'))
        order_lines = self.env['sale.order.line'].search(domain)
        return order_lines.sorted(
            key=lambda line: (
                line.order_id.date_order or fields.Datetime.now(),
                line.id,
            )
        )

    @api.model
    def _get_recent_month_labels(self, date_to, count=5):
        labels = []
        current = date_to.replace(day=1)
        for _index in range(count):
            labels.append(current)
            previous_month_last_day = current - timedelta(days=1)
            current = previous_month_last_day.replace(day=1)
        labels.reverse()
        month_names = {
            1: 'Ene',
            2: 'Feb',
            3: 'Mar',
            4: 'Abr',
            5: 'May',
            6: 'Jun',
            7: 'Jul',
            8: 'Ago',
            9: 'Sep',
            10: 'Oct',
            11: 'Nov',
            12: 'Dic',
        }
        return labels, [month_names[item.month] for item in labels]

    @api.model
    def _get_coverage_universe(self, date_from=False, date_to=False):
        universe_partner_ids = set()
        by_channel = defaultdict(set)
        by_municipio = defaultdict(set)
        domain = [
            ('state', 'in', ['sale', 'done']),
            ('company_id', '=', self.env.company.id),
        ]
        if date_from:
            domain.append(('date_order', '>=', f'{date_from} 00:00:00'))
        if date_to:
            domain.append(('date_order', '<=', f'{date_to} 23:59:59'))

        orders = self.env['sale.order'].search(domain)
        for order in orders:
            partner = order.partner_id.commercial_partner_id or order.partner_id
            if not partner or partner.id in universe_partner_ids:
                continue
            channel_name = self._resolve_partner_channel(partner)
            if not channel_name:
                continue
            universe_partner_ids.add(partner.id)
            by_channel[channel_name].add(partner.id)
            municipio = partner.city or partner.state_id.name or partner.country_id.name or 'Sin municipio'
            by_municipio[municipio].add(partner.id)

        if not universe_partner_ids:
            fallback_partners = self.env['res.partner'].search([
                ('customer_rank', '>', 0),
                ('company_id', 'in', [False, self.env.company.id]),
                ('type', '!=', 'private'),
            ], order='name asc, id asc')
            for partner in fallback_partners:
                commercial_partner = partner.commercial_partner_id or partner
                if not commercial_partner or commercial_partner.id in universe_partner_ids:
                    continue
                channel_name = self._resolve_partner_channel(commercial_partner)
                if not channel_name:
                    continue
                universe_partner_ids.add(commercial_partner.id)
                by_channel[channel_name].add(commercial_partner.id)
                municipio = (
                    commercial_partner.city
                    or commercial_partner.state_id.name
                    or commercial_partner.country_id.name
                    or 'Sin municipio'
                )
                by_municipio[municipio].add(commercial_partner.id)

        channel_rows = sorted(
            [
                {'name': name, 'value': len(partner_ids)}
                for name, partner_ids in by_channel.items()
            ],
            key=lambda item: item['value'],
            reverse=True,
        )
        municipio_rows = sorted(
            [
                {'name': name, 'value': len(partner_ids)}
                for name, partner_ids in by_municipio.items()
            ],
            key=lambda item: item['value'],
            reverse=True,
        )[:8]
        return {
            'total': len(universe_partner_ids),
            'by_channel': {
                item['name']: item['value']
                for item in channel_rows
            },
            'by_municipio': {
                item['name']: item['value']
                for item in municipio_rows
            },
            'channel_rows': channel_rows,
            'municipio_rows': municipio_rows,
        }

    @api.model
    def _infer_coverage_channel(self, partner_name):
        name = (partner_name or '').upper()
        if 'SUPER 7' in name or 'PUMA' in name:
            return 'PUMA Super 7'
        if 'WALMART' in name or 'PAIZ' in name:
            return 'Walmart/Paiz'
        if 'LA TORRE' in name:
            return 'La Torre'
        if 'B3' in name:
            return 'B3'
        if 'CIRCLE K' in name:
            return 'Circle K'
        if 'FRESH' in name or 'GTA' in name or 'MSF' in name:
            return 'GTA / MSF'
        return 'Otros'

    @api.model
    def _resolve_partner_channel(self, partner):
        return self._get_explicit_channel_name(partner)

    @api.model
    def _get_empty_coverage_dashboard_data(self, empty_message=''):
        date_to = fields.Date.to_date(fields.Date.context_today(self))
        universe = self._get_coverage_universe(date_to - timedelta(days=365), date_to)
        return {
            'summary_cards': [],
            'coverage_by_channel': [],
            'pdv_universe': universe,
            'channel_brand_matrix': {
                'brands': [],
                'rows': [],
            },
            'sku_distribution': [],
            'portfolio_holes': {
                'core_skus': [],
                'rows': [],
            },
            'clients_at_risk': [],
            'empty_message': empty_message,
            'notes_sources': [
                {
                    'label': 'Odoo',
                    'detail': 'Ventas YTD por cliente, producto y marca desde sale.order.line.',
                },
                {
                    'label': 'Universo PDV',
                    'detail': 'Universo PDV derivado de partners con actividad comercial real en Odoo.',
                },
            ],
        }

    @api.model
    def _get_empty_commercial_hub_payload(self, empty_message='No hay marcas comerciales creadas en Zoraen Commercial.'):
        date_from, date_to = self._get_commercial_hub_period()
        _month_starts, month_labels = self._get_recent_month_labels(date_to)
        return {
            'summary': {
                'sync_label': fields.Date.to_string(date_to),
                'period_label': '%s al %s' % (
                    fields.Date.to_string(date_from),
                    fields.Date.to_string(date_to),
                ),
                'total_amount': 0.0,
                'order_count': 0,
                'customer_count': 0,
                'point_count': 0,
                'product_count': 0,
                'brand_count': 0,
                'average_ticket': 0.0,
                'currency_symbol': self.env.company.currency_id.symbol or '$',
            },
            'has_brands': False,
            'empty_message': empty_message,
            'revenue_series': [
                {'label': label, 'value': 0.0}
                for label in month_labels
            ],
            'brand_mix': [],
            'brand_catalog': [],
            'top_customers': [],
            'top_channels': [],
            'top_products': [],
        }

    @api.model
    def _get_channel_period_range(self, period_key):
        date_to = fields.Date.to_date(fields.Date.context_today(self))
        normalized_key = period_key or 'ytd'
        if normalized_key == 'current_month':
            date_from = date_to.replace(day=1)
        elif normalized_key == 'rolling_90':
            date_from = date_to - timedelta(days=89)
        elif normalized_key == 'rolling_12':
            date_from = date_to - timedelta(days=364)
        else:
            normalized_key = 'ytd'
            date_from = date_to.replace(month=1, day=1)
        return normalized_key, date_from, date_to

    @api.model
    def _get_channel_period_options(self):
        return [
            {'value': 'ytd', 'label': 'YTD'},
            {'value': 'current_month', 'label': 'Mes actual'},
            {'value': 'rolling_90', 'label': 'Ultimos 90 dias'},
            {'value': 'rolling_12', 'label': 'Ultimos 12 meses'},
        ]

    @api.model
    def _normalize_channel_filters(self, filters=None):
        filters = filters or {}
        period_key, date_from, date_to = self._get_channel_period_range(filters.get('period_key'))
        return {
            'period_key': period_key,
            'date_from': date_from,
            'date_to': date_to,
            'channel_ids': self._normalize_channel_ids(filters),
            'brand_ids': self._normalize_filter_ids(filters.get('brand_ids') or filters.get('brand')),
            'category_ids': self._normalize_filter_ids(filters.get('category_ids') or filters.get('category')),
            'search': (filters.get('search') or '').strip(),
        }

    @api.model
    def _normalize_filter_ids(self, values):
        if not values:
            return []
        if not isinstance(values, (list, tuple, set)):
            values = [values]
        normalized = []
        for value in values:
            if isinstance(value, dict):
                value = value.get('id')
            try:
                record_id = int(value)
            except (TypeError, ValueError):
                continue
            if record_id > 0 and record_id not in normalized:
                normalized.append(record_id)
        return normalized

    @api.model
    def _normalize_channel_ids(self, filters=None):
        filters = filters or {}
        channel_ids = self._normalize_filter_ids(filters.get('channel_ids'))
        if channel_ids:
            return channel_ids
        channel_name = (filters.get('channel') or '').strip()
        if not channel_name:
            return []
        return self._get_commercial_channel_records([channel_name]).ids

    @api.model
    def _get_brand_filter_options(self, brands):
        return [
            {
                'id': brand.id,
                'name': brand.name,
            }
            for brand in brands
        ]

    @api.model
    def _get_channel_filter_options(self, channel_names=None):
        return [
            {
                'id': channel.id,
                'name': channel.name,
            }
            for channel in self._get_commercial_channel_records(channel_names)
        ]

    @api.model
    def _get_selected_channel_names(self, normalized_filters):
        channel_ids = normalized_filters.get('channel_ids') or []
        if not channel_ids:
            return set()
        return set(self.env['zrn_commercial.commercial.channel'].browse(channel_ids).mapped('name'))

    @api.model
    def _serialize_active_filters(self, normalized_filters):
        return {
            'period_key': normalized_filters['period_key'],
            'channel_ids': normalized_filters['channel_ids'],
            'brand_ids': normalized_filters['brand_ids'],
            'category_ids': normalized_filters['category_ids'],
            'search': normalized_filters['search'],
        }

    @api.model
    def _build_filter_options(self, order_lines, brands=None, include_channels=True):
        brands = brands or self._get_commercial_brand_records()
        categories = {}
        for line in order_lines:
            order = line.order_id
            partner = order.partner_id if order else False
            product = line.product_id
            if product:
                category = product.categ_id
                if category and category.id:
                    categories[category.id] = category.display_name or category.name or 'Sin categoria'
        return {
            'periods': self._get_channel_period_options(),
            'channels': self._get_channel_filter_options() if include_channels else [],
            'brands': self._get_brand_filter_options(brands),
            'categories': [
                {
                    'id': category_id,
                    'name': name,
                }
                for category_id, name in sorted(categories.items(), key=lambda item: item[1])
            ],
        }

    @api.model
    def _line_matches_filters(self, line, product_brand_map, normalized_filters):
        order = line.order_id
        partner = order.partner_id if order else False
        commercial_partner = partner.commercial_partner_id if partner else False
        product = line.product_id
        if not order or not partner or not product:
            return False

        brand_info = product_brand_map.get(product.id)
        if not brand_info:
            return False

        channel_name = self._resolve_partner_channel(partner)
        category_name = product.categ_id.display_name or 'Sin categoria'
        if not channel_name:
            return False
        selected_channel_names = self._get_selected_channel_names(normalized_filters)
        if selected_channel_names and channel_name not in selected_channel_names:
            return False
        if normalized_filters['brand_ids'] and brand_info['brand_id'] not in normalized_filters['brand_ids']:
            return False
        if normalized_filters['category_ids'] and product.categ_id.id not in normalized_filters['category_ids']:
            return False

        search_term = normalized_filters['search'].lower()
        if search_term:
            search_haystack = ' '.join([
                partner.display_name or '',
                commercial_partner.display_name or '',
                product.display_name or '',
                product.default_code or '',
                brand_info['brand_name'],
                category_name,
                channel_name,
            ]).lower()
            if search_term not in search_haystack:
                return False
        return True

    @api.model
    def _build_empty_channel_dashboard_payload(self, filters=None, filter_options=None, brands=None, product_brand_map=None):
        normalized_filters = self._normalize_channel_filters(filters)
        brands = brands if brands is not None else self._get_commercial_brand_records()
        product_brand_map = product_brand_map if product_brand_map is not None else self._get_commercial_brand_map()[1]
        filter_options = filter_options or {
            'periods': self._get_channel_period_options(),
            'channels': self._get_channel_filter_options(),
            'brands': self._get_brand_filter_options(brands),
            'categories': [],
        }
        date_from = normalized_filters['date_from']
        date_to = normalized_filters['date_to']
        return {
            'summary': {
                'sync_label': fields.Date.to_string(date_to),
                'period_label': '%s al %s' % (
                    fields.Date.to_string(date_from),
                    fields.Date.to_string(date_to),
                ),
                'currency_symbol': self.env.company.currency_id.symbol or '$',
            },
            'active_filters': self._serialize_active_filters(normalized_filters),
            'filter_options': filter_options,
            'summary_cards': [
                {'label': 'Canales activos', 'value': 0, 'type': 'count'},
                {'label': 'Revenue filtrado', 'value': 0.0, 'type': 'currency'},
                {'label': 'PDVs filtrados', 'value': 0, 'type': 'count'},
                {'label': 'Ticket promedio', 'value': 0.0, 'type': 'currency'},
            ],
            'rows': [],
            'empty_message': (
                'No hay marcas comerciales activas para construir la vista.'
                if not product_brand_map
                else 'No hay datos para los filtros seleccionados.'
            ),
        }

    @api.model
    def get_commercial_hub_payload(self, filters=None):
        normalized_filters = self._normalize_channel_filters(filters)
        date_from = normalized_filters['date_from']
        date_to = normalized_filters['date_to']
        currency_symbol = self.env.company.currency_id.symbol or '$'
        brands, product_brand_map = self._get_commercial_brand_map()
        channel_setup = self._get_channel_setup_status()
        if not brands or not product_brand_map:
            payload = self._get_empty_commercial_hub_payload()
            payload['active_filters'] = self._serialize_active_filters(normalized_filters)
            payload['filter_options'] = self._build_filter_options([], brands)
            return payload
        if not channel_setup['has_channels'] or not channel_setup['has_assignments']:
            payload = self._get_empty_commercial_hub_payload(
                self._get_channel_empty_message(channel_setup)
            )
            payload['summary']['brand_count'] = len(brands)
            payload['summary']['product_count'] = len(product_brand_map)
            payload['has_brands'] = True
            payload['brand_catalog'] = [
                {
                    'name': brand.name,
                    'product_count': len(brand.product_link_ids.filtered(lambda link: link.active and link.product_id)),
                }
                for brand in brands
            ]
            payload['active_filters'] = self._serialize_active_filters(normalized_filters)
            payload['filter_options'] = self._build_filter_options([], brands)
            return payload

        order_lines = self._get_commercial_sale_order_lines(
            date_from,
            date_to,
            list(product_brand_map.keys()),
        )
        filter_options = self._build_filter_options(order_lines, brands)
        filtered_lines = order_lines.filtered(lambda line: self._line_matches_filters(line, product_brand_map, normalized_filters))
        if not filtered_lines:
            payload = self._get_empty_commercial_hub_payload()
            payload['summary']['brand_count'] = len(brands)
            payload['summary']['product_count'] = len(product_brand_map)
            payload['has_brands'] = True
            payload['empty_message'] = 'No hay datos para los filtros seleccionados.'
            payload['brand_catalog'] = [
                {
                    'name': brand.name,
                    'product_count': len(brand.product_link_ids.filtered(lambda link: link.active and link.product_id)),
                }
                for brand in brands
            ]
            payload['active_filters'] = self._serialize_active_filters(normalized_filters)
            payload['filter_options'] = filter_options
            return payload

        month_starts, month_labels = self._get_recent_month_labels(date_to)
        month_amounts = {
            month_start: 0.0
            for month_start in month_starts
        }
        brand_amounts = defaultdict(float)
        brand_product_ids = defaultdict(set)
        portfolio_brand_map = {}
        order_ids = set()
        channel_map = {}
        customer_map = {}
        product_map = {}

        def _init_detail_bucket():
            return {
                'revenue': 0.0,
                'units': 0.0,
                'order_ids': set(),
                'partner_ids': set(),
                'channels': defaultdict(lambda: {
                    'name': '',
                    'revenue': 0.0,
                    'units': 0.0,
                    'order_ids': set(),
                    'partner_ids': set(),
                }),
                'customers': defaultdict(lambda: {
                    'name': '',
                    'revenue': 0.0,
                    'units': 0.0,
                    'order_ids': set(),
                }),
            }

        def _accumulate_detail(bucket, channel_name, partner, order, amount, quantity):
            bucket['revenue'] += amount
            bucket['units'] += quantity
            bucket['order_ids'].add(order.id)
            if partner:
                bucket['partner_ids'].add(partner.id)
                customer_entry = bucket['customers'][partner.id]
                customer_entry['name'] = partner.display_name
                customer_entry['revenue'] += amount
                customer_entry['units'] += quantity
                customer_entry['order_ids'].add(order.id)
            channel_key = channel_name or 'Sin canal'
            channel_entry = bucket['channels'][channel_key]
            channel_entry['name'] = channel_key
            channel_entry['revenue'] += amount
            channel_entry['units'] += quantity
            channel_entry['order_ids'].add(order.id)
            if partner:
                channel_entry['partner_ids'].add(partner.id)

        def _serialize_channel_rows(bucket):
            return sorted(
                [
                    {
                        'name': item['name'],
                        'pdv_count': len(item['partner_ids']),
                        'order_count': len(item['order_ids']),
                        'units': round(item['units'], 2),
                        'revenue': round(item['revenue'], 2),
                    }
                    for item in bucket['channels'].values()
                ],
                key=lambda item: item['revenue'],
                reverse=True,
            )[:8]

        def _serialize_customer_rows(bucket):
            return sorted(
                [
                    {
                        'name': item['name'],
                        'order_count': len(item['order_ids']),
                        'units': round(item['units'], 2),
                        'revenue': round(item['revenue'], 2),
                    }
                    for item in bucket['customers'].values()
                ],
                key=lambda item: item['revenue'],
                reverse=True,
            )[:8]

        def _build_detail_payload(title, subtitle, bucket, secondary_title='', secondary_rows=None):
            return {
                'title': title,
                'subtitle': subtitle,
                'currency_symbol': currency_symbol,
                'summary_cards': [
                    {'label': 'Venta', 'value': round(bucket['revenue'], 2), 'format': 'money'},
                    {'label': 'Unidades', 'value': round(bucket['units'], 2), 'format': 'count'},
                    {'label': 'Pedidos', 'value': len(bucket['order_ids']), 'format': 'count'},
                    {'label': 'PDVs', 'value': len(bucket['partner_ids']), 'format': 'count'},
                ],
                'channel_rows': _serialize_channel_rows(bucket),
                'secondary_title': secondary_title,
                'secondary_rows': secondary_rows or [],
                'customer_rows': _serialize_customer_rows(bucket),
            }

        for line in filtered_lines:
            order = line.order_id
            partner = order.partner_id
            commercial_partner = partner.commercial_partner_id or partner
            product = line.product_id
            if not order or not product:
                continue

            brand_info = product_brand_map.get(product.id)
            if not brand_info:
                continue

            amount = float(line.price_total or 0.0)
            quantity = float(line.product_uom_qty or 0.0)
            order_ids.add(order.id)
            channel_name = self._resolve_partner_channel(commercial_partner)

            if order.date_order:
                order_date = fields.Datetime.to_datetime(order.date_order).date()
                order_month = order_date.replace(day=1)
                if order_month in month_amounts:
                    month_amounts[order_month] += amount
            else:
                order_date = False

            brand_amounts[brand_info['brand_name']] += amount
            brand_product_ids[brand_info['brand_name']].add(product.id)

            portfolio_brand = portfolio_brand_map.setdefault(
                brand_info['brand_name'],
                {
                    'name': brand_info['brand_name'],
                    'revenue': 0.0,
                    'quantity_sold': 0.0,
                    'product_ids': set(),
                    'categories': {},
                    '_detail': _init_detail_bucket(),
                },
            )
            portfolio_brand['revenue'] += amount
            portfolio_brand['quantity_sold'] += quantity
            portfolio_brand['product_ids'].add(product.id)
            _accumulate_detail(portfolio_brand['_detail'], channel_name, partner, order, amount, quantity)
            category_key = product.categ_id.display_name or 'Sin categoria'
            portfolio_category = portfolio_brand['categories'].setdefault(
                category_key,
                {
                    'name': category_key,
                    'revenue': 0.0,
                    'quantity_sold': 0.0,
                    'product_ids': set(),
                    'products': {},
                    '_detail': _init_detail_bucket(),
                },
            )
            portfolio_category['revenue'] += amount
            portfolio_category['quantity_sold'] += quantity
            portfolio_category['product_ids'].add(product.id)
            _accumulate_detail(portfolio_category['_detail'], channel_name, partner, order, amount, quantity)
            portfolio_product = portfolio_category['products'].setdefault(
                product.id,
                {
                    'name': product.display_name,
                    'default_code': product.default_code or '',
                    'revenue': 0.0,
                    'quantity_sold': 0.0,
                    '_detail': _init_detail_bucket(),
                },
            )
            portfolio_product['revenue'] += amount
            portfolio_product['quantity_sold'] += quantity
            _accumulate_detail(portfolio_product['_detail'], channel_name, partner, order, amount, quantity)

            if commercial_partner:
                channel_entry = channel_map.setdefault(
                    commercial_partner.id,
                    {
                        'name': commercial_partner.display_name,
                        'order_ids': set(),
                        'total_amount': 0.0,
                    },
                )
                channel_entry['order_ids'].add(order.id)
                channel_entry['total_amount'] += amount

            if partner:
                customer_entry = customer_map.setdefault(
                    partner.id,
                    {
                        'name': partner.display_name,
                        'order_ids': set(),
                        'total_amount': 0.0,
                    },
                )
                customer_entry['order_ids'].add(order.id)
                customer_entry['total_amount'] += amount

            product_entry = product_map.setdefault(
                product.id,
                {
                    'product_id': product.id,
                    'name': product.display_name,
                    'default_code': product.default_code or '',
                    'category_name': product.categ_id.display_name or '',
                    'quantity_sold': 0.0,
                    'sales_amount': 0.0,
                    '_detail': _init_detail_bucket(),
                },
            )
            product_entry['quantity_sold'] += quantity
            product_entry['sales_amount'] += amount
            _accumulate_detail(product_entry['_detail'], channel_name, partner, order, amount, quantity)

        total_amount = round(sum(item['sales_amount'] for item in product_map.values()), 2)
        top_customers = sorted(
            [
                {
                    'partner_id': partner_id,
                    'name': item['name'],
                    'order_count': len(item['order_ids']),
                    'total_amount': round(item['total_amount'], 2),
                }
                for partner_id, item in customer_map.items()
            ],
            key=lambda item: item['total_amount'],
            reverse=True,
        )[:8]
        top_channels = sorted(
            [
                {
                    'name': item['name'],
                    'order_count': len(item['order_ids']),
                    'total_amount': round(item['total_amount'], 2),
                }
                for item in channel_map.values()
            ],
            key=lambda item: item['total_amount'],
            reverse=True,
        )[:8]
        top_products = sorted(
            [
                {
                    'product_id': item['product_id'],
                    'name': item['name'],
                    'default_code': item['default_code'],
                    'category_name': item['category_name'],
                    'quantity_sold': round(item['quantity_sold'], 2),
                    'sales_amount': round(item['sales_amount'], 2),
                    'detail': _build_detail_payload(
                        item['name'],
                        item['category_name'] or 'Producto',
                        item['_detail'],
                        secondary_title='Top PDVs',
                        secondary_rows=_serialize_customer_rows(item['_detail']),
                    ),
                }
                for item in product_map.values()
            ],
            key=lambda item: item['sales_amount'],
            reverse=True,
        )[:8]

        # Map brand names to their commercial brand database IDs
        brand_ids_map = {brand.name: brand.id for brand in brands}
        brand_mix = sorted(
            [
                {
                    'id': brand_ids_map.get(brand_name),
                    'name': brand_name,
                    'value': round(amount, 2),
                    'percentage': round((amount / total_amount) * 100, 2) if total_amount else 0.0,
                    'product_count': len(brand_product_ids.get(brand_name, set())),
                }
                for brand_name, amount in brand_amounts.items()
            ],
            key=lambda item: item['value'],
            reverse=True,
        )
        portfolio_rows = []
        for brand_name, brand_row in sorted(
            portfolio_brand_map.items(),
            key=lambda item: item[1]['revenue'],
            reverse=True,
        ):
            categories = []
            for category_name, category_row in sorted(
                brand_row['categories'].items(),
                key=lambda item: item[1]['revenue'],
                reverse=True,
            ):
                products = sorted(
                    [
                        {
                            'key': f"product_{product_id}",
                            'name': product_row['name'],
                            'default_code': product_row['default_code'],
                            'revenue': round(product_row['revenue'], 2),
                            'quantity_sold': round(product_row['quantity_sold'], 2),
                            'detail': _build_detail_payload(
                                product_row['name'],
                                category_name,
                                product_row['_detail'],
                                secondary_title='Top PDVs',
                                secondary_rows=_serialize_customer_rows(product_row['_detail']),
                            ),
                        }
                        for product_id, product_row in category_row['products'].items()
                    ],
                    key=lambda item: item['revenue'],
                    reverse=True,
                )
                category_secondary_rows = [
                    {
                        'name': item['name'],
                        'units': item['quantity_sold'],
                        'revenue': item['revenue'],
                    }
                    for item in products[:8]
                ]
                categories.append({
                    'key': f"category_{brand_name}_{category_name}",
                    'name': category_name,
                    'revenue': round(category_row['revenue'], 2),
                    'quantity_sold': round(category_row['quantity_sold'], 2),
                    'product_count': len(category_row['product_ids']),
                    'products': products,
                    'detail': _build_detail_payload(
                        category_name,
                        brand_name,
                        category_row['_detail'],
                        secondary_title='SKUs de la linea',
                        secondary_rows=category_secondary_rows,
                    ),
                })
            brand_secondary_rows = [
                {
                    'name': item['name'],
                    'sku_count': item['product_count'],
                    'units': item['quantity_sold'],
                    'revenue': item['revenue'],
                }
                for item in categories[:8]
            ]
            portfolio_rows.append({
                'key': f"brand_{brand_name}",
                'name': brand_name,
                'revenue': round(brand_row['revenue'], 2),
                'quantity_sold': round(brand_row['quantity_sold'], 2),
                'product_count': len(brand_row['product_ids']),
                'categories': categories,
                'detail': _build_detail_payload(
                    brand_name,
                    'Marca comercial',
                    brand_row['_detail'],
                    secondary_title='Lineas de portafolio',
                    secondary_rows=brand_secondary_rows,
                ),
            })

        return {
            'summary': {
                'sync_label': fields.Date.to_string(date_to),
                'period_label': '%s al %s' % (
                    fields.Date.to_string(date_from),
                    fields.Date.to_string(date_to),
                ),
                'total_amount': total_amount,
                'order_count': len(order_ids),
                'customer_count': len(channel_map),
                'point_count': len(customer_map),
                'product_count': len(product_map),
                'brand_count': len(brands),
                'average_ticket': round(total_amount / len(order_ids), 2) if order_ids else 0.0,
                'currency_symbol': self.env.company.currency_id.symbol or '$',
            },
            'has_brands': True,
            'empty_message': '',
            'revenue_series': [
                {
                    'label': month_labels[index],
                    'value': round(month_amounts[month_start], 2),
                }
                for index, month_start in enumerate(month_starts)
            ],
            'brand_mix': brand_mix,
            'brand_catalog': [
                {
                    'id': brand.id,
                    'name': brand.name,
                    'product_count': len(brand.product_link_ids.filtered(lambda link: link.active and link.product_id)),
                }
                for brand in brands
            ],
            'top_customers': top_customers,
            'top_channels': top_channels,
            'top_products': top_products,
            'portfolio_rows': portfolio_rows,
            'active_filters': self._serialize_active_filters(normalized_filters),
            'filter_options': filter_options,
        }

    @api.model
    def get_channel_dashboard_data(self, filters=None):
        normalized_filters = self._normalize_channel_filters(filters)
        date_from = normalized_filters['date_from']
        date_to = normalized_filters['date_to']
        brands, product_brand_map = self._get_commercial_brand_map()
        channel_setup = self._get_channel_setup_status()
        if not brands or not product_brand_map:
            return self._build_empty_channel_dashboard_payload(
                normalized_filters,
                brands=brands,
                product_brand_map=product_brand_map,
            )
        if not channel_setup['has_channels'] or not channel_setup['has_assignments']:
            payload = self._build_empty_channel_dashboard_payload(
                normalized_filters,
                brands=brands,
                product_brand_map=product_brand_map,
            )
            payload['empty_message'] = self._get_channel_empty_message(channel_setup)
            return payload

        period_lines = self._get_commercial_sale_order_lines(
            date_from,
            date_to,
            list(product_brand_map.keys()),
        )

        base_channels = set()
        base_categories = {}
        for line in period_lines:
            order = line.order_id
            partner = order.partner_id
            product = line.product_id
            if not order or not partner or not product:
                continue
            channel_name = self._resolve_partner_channel(partner)
            if channel_name:
                base_channels.add(channel_name)
            category = product.categ_id
            if category and category.id:
                base_categories[category.id] = category.display_name or category.name or 'Sin categoria'

        filter_options = {
            'periods': self._get_channel_period_options(),
            'channels': self._get_channel_filter_options(base_channels),
            'brands': self._get_brand_filter_options(brands),
            'categories': [
                {
                    'id': category_id,
                    'name': name,
                }
                for category_id, name in sorted(base_categories.items(), key=lambda item: item[1])
            ],
        }
        if not period_lines:
            return self._build_empty_channel_dashboard_payload(
                normalized_filters,
                filter_options=filter_options,
                brands=brands,
                product_brand_map=product_brand_map,
            )

        search_term = normalized_filters['search'].lower()
        selected_channel_names = self._get_selected_channel_names(normalized_filters)
        channel_rows = {}
        total_revenue = 0.0
        total_order_ids = set()
        total_point_ids = set()

        for line in period_lines:
            order = line.order_id
            partner = order.partner_id
            commercial_partner = partner.commercial_partner_id or partner
            product = line.product_id
            if not order or not partner or not product or not commercial_partner:
                continue

            brand_info = product_brand_map.get(product.id)
            if not brand_info:
                continue

            channel_name = self._resolve_partner_channel(partner)
            if not channel_name:
                continue
            category_name = product.categ_id.display_name or 'Sin categoria'
            if selected_channel_names and channel_name not in selected_channel_names:
                continue
            if normalized_filters['brand_ids'] and brand_info['brand_id'] not in normalized_filters['brand_ids']:
                continue
            if normalized_filters['category_ids'] and product.categ_id.id not in normalized_filters['category_ids']:
                continue

            if search_term:
                search_haystack = ' '.join([
                    partner.display_name or '',
                    commercial_partner.display_name or '',
                    product.display_name or '',
                    product.default_code or '',
                    brand_info['brand_name'],
                    category_name,
                    channel_name,
                ]).lower()
                if search_term not in search_haystack:
                    continue

            amount = float(line.price_total or 0.0)
            quantity = float(line.product_uom_qty or 0.0)
            order_date = fields.Datetime.to_datetime(order.date_order).date() if order.date_order else date_to

            row = channel_rows.setdefault(
                channel_name,
                {
                    'channel': channel_name,
                    'revenue': 0.0,
                    'units': 0.0,
                    'order_ids': set(),
                    'customer_ids': set(),
                    'point_ids': set(),
                    'brand_amounts': defaultdict(float),
                    'category_amounts': defaultdict(float),
                    'customer_rows': {},
                    'point_rows': {},
                    'product_rows': {},
                    'last_order_date': order_date,
                },
            )
            row['revenue'] += amount
            row['units'] += quantity
            row['order_ids'].add(order.id)
            row['customer_ids'].add(commercial_partner.id)
            row['point_ids'].add(partner.id)
            row['brand_amounts'][brand_info['brand_name']] += amount
            row['category_amounts'][category_name] += amount
            if order_date > row['last_order_date']:
                row['last_order_date'] = order_date

            customer_row = row['customer_rows'].setdefault(
                commercial_partner.id,
                {
                    'name': commercial_partner.display_name,
                    'revenue': 0.0,
                    'order_ids': set(),
                    'last_order_date': order_date,
                },
            )
            customer_row['revenue'] += amount
            customer_row['order_ids'].add(order.id)
            if order_date > customer_row['last_order_date']:
                customer_row['last_order_date'] = order_date

            point_row = row['point_rows'].setdefault(
                partner.id,
                {
                    'name': partner.display_name,
                    'revenue': 0.0,
                    'order_ids': set(),
                },
            )
            point_row['revenue'] += amount
            point_row['order_ids'].add(order.id)

            product_row = row['product_rows'].setdefault(
                product.id,
                {
                    'name': product.display_name,
                    'default_code': product.default_code or '',
                    'brand': brand_info['brand_name'],
                    'category': category_name,
                    'units': 0.0,
                    'revenue': 0.0,
                },
            )
            product_row['units'] += quantity
            product_row['revenue'] += amount

            total_revenue += amount
            total_order_ids.add(order.id)
            total_point_ids.add(partner.id)

        if not channel_rows:
            return self._build_empty_channel_dashboard_payload(
                normalized_filters,
                filter_options=filter_options,
                brands=brands,
                product_brand_map=product_brand_map,
            )

        rows = []
        for channel_name, row in sorted(
            channel_rows.items(),
            key=lambda item: item[1]['revenue'],
            reverse=True,
        ):
            order_count = len(row['order_ids'])
            point_count = len(row['point_ids'])
            revenue = round(row['revenue'], 2)
            top_brands = sorted(
                [
                    {
                        'name': brand_name,
                        'revenue': round(amount, 2),
                        'mix_pct': round((amount / revenue) * 100, 1) if revenue else 0.0,
                    }
                    for brand_name, amount in row['brand_amounts'].items()
                ],
                key=lambda item: item['revenue'],
                reverse=True,
            )[:6]
            top_customers = sorted(
                [
                    {
                        'name': customer['name'],
                        'revenue': round(customer['revenue'], 2),
                        'order_count': len(customer['order_ids']),
                        'last_order_label': fields.Date.to_string(customer['last_order_date']) if customer['last_order_date'] else '',
                    }
                    for customer in row['customer_rows'].values()
                ],
                key=lambda item: item['revenue'],
                reverse=True,
            )[:8]
            top_points = sorted(
                [
                    {
                        'name': point['name'],
                        'revenue': round(point['revenue'], 2),
                        'order_count': len(point['order_ids']),
                    }
                    for point in row['point_rows'].values()
                ],
                key=lambda item: item['revenue'],
                reverse=True,
            )[:8]
            top_products = sorted(
                [
                    {
                        'name': product['name'],
                        'default_code': product['default_code'],
                        'brand': product['brand'],
                        'category': product['category'],
                        'units': round(product['units'], 2),
                        'revenue': round(product['revenue'], 2),
                    }
                    for product in row['product_rows'].values()
                ],
                key=lambda item: item['revenue'],
                reverse=True,
            )[:8]
            top_categories = sorted(
                [
                    {
                        'name': category_name,
                        'revenue': round(amount, 2),
                        'mix_pct': round((amount / revenue) * 100, 1) if revenue else 0.0,
                    }
                    for category_name, amount in row['category_amounts'].items()
                ],
                key=lambda item: item['revenue'],
                reverse=True,
            )[:5]
            rows.append({
                'key': channel_name.lower().replace(' ', '_').replace('/', '_'),
                'channel': channel_name,
                'customer_count': len(row['customer_ids']),
                'point_count': point_count,
                'order_count': order_count,
                'units': round(row['units'], 2),
                'revenue': revenue,
                'mix_pct': round((revenue / total_revenue) * 100, 1) if total_revenue else 0.0,
                'average_ticket': round(revenue / order_count, 2) if order_count else 0.0,
                'brand_count': len(row['brand_amounts']),
                'last_order_label': fields.Date.to_string(row['last_order_date']) if row['last_order_date'] else '',
                'detail': {
                    'summary': {
                        'revenue': revenue,
                        'units': round(row['units'], 2),
                        'order_count': order_count,
                        'customer_count': len(row['customer_ids']),
                        'point_count': point_count,
                        'average_ticket': round(revenue / order_count, 2) if order_count else 0.0,
                        'brand_count': len(row['brand_amounts']),
                        'last_order_label': fields.Date.to_string(row['last_order_date']) if row['last_order_date'] else '',
                    },
                    'top_brands': top_brands,
                    'top_categories': top_categories,
                    'top_customers': top_customers,
                    'top_points': top_points,
                    'top_products': top_products,
                },
            })

        order_count = len(total_order_ids)
        return {
            'summary': {
                'sync_label': fields.Date.to_string(date_to),
                'period_label': '%s al %s' % (
                    fields.Date.to_string(date_from),
                    fields.Date.to_string(date_to),
                ),
                'currency_symbol': self.env.company.currency_id.symbol or '$',
            },
            'active_filters': self._serialize_active_filters(normalized_filters),
            'filter_options': filter_options,
            'summary_cards': [
                {'label': 'Canales activos', 'value': len(rows), 'type': 'count'},
                {'label': 'Revenue filtrado', 'value': round(total_revenue, 2), 'type': 'currency'},
                {'label': 'PDVs filtrados', 'value': len(total_point_ids), 'type': 'count'},
                {'label': 'Ticket promedio', 'value': round(total_revenue / order_count, 2) if order_count else 0.0, 'type': 'currency'},
            ],
            'rows': rows,
            'empty_message': '',
        }

    @api.model
    def get_coverage_dashboard_data(self, filters=None):
        normalized_filters = self._normalize_channel_filters(filters)
        date_from = normalized_filters['date_from']
        date_to = normalized_filters['date_to']
        currency_symbol = self.env.company.currency_id.symbol or '$'
        universe = self._get_coverage_universe(date_to - timedelta(days=365), date_to)
        brands, product_brand_map = self._get_commercial_brand_map()
        channel_setup = self._get_channel_setup_status()
        if not brands or not product_brand_map:
            payload = self._get_empty_coverage_dashboard_data()
            payload['summary'] = {
                'sync_label': fields.Date.to_string(date_to),
                'period_label': '%s al %s' % (
                    fields.Date.to_string(date_from),
                    fields.Date.to_string(date_to),
                ),
                'currency_symbol': currency_symbol,
            }
            payload['active_filters'] = self._serialize_active_filters(normalized_filters)
            payload['filter_options'] = self._build_filter_options([], brands)
            return payload
        if not channel_setup['has_channels'] or not channel_setup['has_assignments']:
            payload = self._get_empty_coverage_dashboard_data(
                self._get_channel_empty_message(channel_setup)
            )
            payload['summary'] = {
                'sync_label': fields.Date.to_string(date_to),
                'period_label': '%s al %s' % (
                    fields.Date.to_string(date_from),
                    fields.Date.to_string(date_to),
                ),
                'currency_symbol': currency_symbol,
            }
            payload['active_filters'] = self._serialize_active_filters(normalized_filters)
            payload['filter_options'] = self._build_filter_options([], brands)
            return payload

        order_lines = self._get_commercial_sale_order_lines(
            date_from,
            date_to,
            list(product_brand_map.keys()),
        )
        filter_options = self._build_filter_options(order_lines, brands)
        filtered_lines = order_lines.filtered(lambda line: self._line_matches_filters(line, product_brand_map, normalized_filters))
        if not filtered_lines:
            payload = self._get_empty_coverage_dashboard_data()
            payload['summary'] = {
                'sync_label': fields.Date.to_string(date_to),
                'period_label': '%s al %s' % (
                    fields.Date.to_string(date_from),
                    fields.Date.to_string(date_to),
                ),
                'currency_symbol': currency_symbol,
            }
            payload['active_filters'] = self._serialize_active_filters(normalized_filters)
            payload['filter_options'] = filter_options
            return payload

        channel_map = {}
        customer_map = {}
        sku_map = {}
        total_revenue = 0.0

        def _init_sku_detail_bucket():
            return {
                'revenue': 0.0,
                'units': 0.0,
                'order_ids': set(),
                'partner_ids': set(),
                'channel_rows': defaultdict(lambda: {
                    'name': '',
                    'partner_ids': set(),
                    'order_ids': set(),
                    'units': 0.0,
                    'revenue': 0.0,
                }),
                'pdv_rows': defaultdict(lambda: {
                    'name': '',
                    'order_ids': set(),
                    'units': 0.0,
                    'revenue': 0.0,
                }),
            }

        def _accumulate_sku_detail(bucket, channel_name, partner, order, amount, quantity):
            bucket['revenue'] += amount
            bucket['units'] += quantity
            bucket['order_ids'].add(order.id)
            bucket['partner_ids'].add(partner.id)
            channel_entry = bucket['channel_rows'][channel_name]
            channel_entry['name'] = channel_name
            channel_entry['partner_ids'].add(partner.id)
            channel_entry['order_ids'].add(order.id)
            channel_entry['units'] += quantity
            channel_entry['revenue'] += amount
            pdv_entry = bucket['pdv_rows'][partner.id]
            pdv_entry['name'] = partner.display_name
            pdv_entry['order_ids'].add(order.id)
            pdv_entry['units'] += quantity
            pdv_entry['revenue'] += amount

        def _serialize_sku_channel_rows(bucket):
            return sorted(
                [
                    {
                        'name': item['name'],
                        'pdv_count': len(item['partner_ids']),
                        'order_count': len(item['order_ids']),
                        'units': round(item['units'], 2),
                        'revenue': round(item['revenue'], 2),
                    }
                    for item in bucket['channel_rows'].values()
                ],
                key=lambda item: item['revenue'],
                reverse=True,
            )[:8]

        def _serialize_sku_pdv_rows(bucket):
            return sorted(
                [
                    {
                        'name': item['name'],
                        'order_count': len(item['order_ids']),
                        'units': round(item['units'], 2),
                        'revenue': round(item['revenue'], 2),
                    }
                    for item in bucket['pdv_rows'].values()
                ],
                key=lambda item: item['revenue'],
                reverse=True,
            )[:8]

        for line in filtered_lines:
            order = line.order_id
            product = line.product_id
            partner = order.partner_id.commercial_partner_id or order.partner_id
            if not order or not product or not partner:
                continue

            brand_info = product_brand_map.get(product.id)
            if not brand_info:
                continue

            amount = float(line.price_total or 0.0)
            quantity = float(line.product_uom_qty or 0.0)
            order_date = fields.Datetime.to_datetime(order.date_order).date() if order.date_order else date_to
            channel_name = self._resolve_partner_channel(partner)
            total_revenue += amount

            channel_entry = channel_map.setdefault(
                channel_name,
                {
                    'channel': channel_name,
                    'active_customer_ids': set(),
                    'order_ids': set(),
                    'revenue': 0.0,
                    'brand_amounts': defaultdict(float),
                },
            )
            channel_entry['active_customer_ids'].add(partner.id)
            channel_entry['order_ids'].add(order.id)
            channel_entry['revenue'] += amount
            channel_entry['brand_amounts'][brand_info['brand_name']] += amount

            customer_entry = customer_map.setdefault(
                partner.id,
                {
                    'name': partner.display_name,
                    'channel': channel_name,
                    'revenue': 0.0,
                    'order_ids': set(),
                    'product_ids': set(),
                    'brand_names': set(),
                    'product_amounts': defaultdict(float),
                    'last_order_date': order_date,
                    'months_active': set(),
                },
            )
            customer_entry['revenue'] += amount
            customer_entry['order_ids'].add(order.id)
            customer_entry['product_ids'].add(product.id)
            customer_entry['brand_names'].add(brand_info['brand_name'])
            customer_entry['product_amounts'][product.display_name] += amount
            customer_entry['months_active'].add(order_date.strftime('%Y-%m'))
            if order_date > customer_entry['last_order_date']:
                customer_entry['last_order_date'] = order_date

            sku_entry = sku_map.setdefault(
                product.id,
                {
                    'product_id': product.id,
                    'sku': product.display_name,
                    'brand': brand_info['brand_name'],
                    'revenue': 0.0,
                    'customer_ids': set(),
                    'channels': set(),
                    'quantity': 0.0,
                    'detail_bucket': _init_sku_detail_bucket(),
                },
            )
            sku_entry['revenue'] += amount
            sku_entry['customer_ids'].add(partner.id)
            sku_entry['channels'].add(channel_name)
            sku_entry['quantity'] += quantity
            _accumulate_sku_detail(sku_entry['detail_bucket'], channel_name, partner, order, amount, quantity)

        if not total_revenue:
            return self._get_empty_coverage_dashboard_data()

        active_customer_total = len(customer_map)
        ranked_customers = sorted(
            customer_map.items(),
            key=lambda item: item[1]['revenue'],
            reverse=True,
        )
        ranked_customer_ids = [customer_id for customer_id, _data in ranked_customers]
        a_cutoff = max(1, round(len(ranked_customer_ids) * 0.2))
        b_cutoff = max(a_cutoff + 1, round(len(ranked_customer_ids) * 0.5))
        abc_map = {}
        for index, customer_id in enumerate(ranked_customer_ids):
            if index < a_cutoff:
                abc_map[customer_id] = 'A'
            elif index < b_cutoff:
                abc_map[customer_id] = 'B'
            else:
                abc_map[customer_id] = 'C'

        coverage_by_channel = []
        matrix_brand_names = [brand.name for brand in brands]
        matrix_rows = []
        for channel_name, channel_data in sorted(
            channel_map.items(),
            key=lambda item: item[1]['revenue'],
            reverse=True,
        ):
            active_count = len(channel_data['active_customer_ids'])
            network_total = universe['by_channel'].get(channel_name)
            coverage_pct = round((active_count / network_total) * 100, 1) if network_total else 0.0
            white_space = max(network_total - active_count, 0) if network_total else 0
            avg_ticket = round(channel_data['revenue'] / active_count, 2) if active_count else 0.0
            coverage_by_channel.append({
                'channel': channel_name,
                'active': active_count,
                'network_total': network_total,
                'coverage_pct': coverage_pct,
                'white_space': white_space,
                'revenue': round(channel_data['revenue'], 2),
                'mix_pct': round((channel_data['revenue'] / total_revenue) * 100, 1),
                'avg_ticket': avg_ticket,
            })
            matrix_rows.append({
                'channel': channel_name,
                'total_revenue': round(channel_data['revenue'], 2),
                'cells': [
                    {
                        'brand': brand_name,
                        'revenue': round(channel_data['brand_amounts'].get(brand_name, 0.0), 2),
                    }
                    for brand_name in matrix_brand_names
                ],
            })

        sku_distribution = sorted(
            [
                {
                    'product_id': sku_data['product_id'],
                    'sku': sku_data['sku'],
                    'brand': sku_data['brand'],
                    'revenue': round(sku_data['revenue'], 2),
                    'pdv_count': len(sku_data['customer_ids']),
                    'pdv_pct': round((len(sku_data['customer_ids']) / active_customer_total) * 100, 1) if active_customer_total else 0.0,
                    'channels': len(sku_data['channels']),
                    'detail': {
                        'title': sku_data['sku'],
                        'subtitle': sku_data['brand'],
                        'currency_symbol': currency_symbol,
                        'summary_cards': [
                            {'label': 'Venta', 'value': round(sku_data['detail_bucket']['revenue'], 2), 'format': 'money'},
                            {'label': 'Unidades', 'value': round(sku_data['detail_bucket']['units'], 2), 'format': 'count'},
                            {'label': 'Pedidos', 'value': len(sku_data['detail_bucket']['order_ids']), 'format': 'count'},
                            {'label': 'PDVs', 'value': len(sku_data['detail_bucket']['partner_ids']), 'format': 'count'},
                        ],
                        'channel_rows': _serialize_sku_channel_rows(sku_data['detail_bucket']),
                        'secondary_title': 'Top PDVs',
                        'secondary_rows': _serialize_sku_pdv_rows(sku_data['detail_bucket']),
                        'customer_rows': _serialize_sku_pdv_rows(sku_data['detail_bucket']),
                    },
                }
                for sku_data in sku_map.values()
            ],
            key=lambda item: item['revenue'],
            reverse=True,
        )[:15]

        core_skus = [item['sku'] for item in sku_distribution[:5]]
        portfolio_holes_rows = []
        clients_at_risk = []
        ab_customers = [
            customer_data
            for customer_id, customer_data in ranked_customers
            if abc_map.get(customer_id) in ('A', 'B')
        ]
        for customer_id, customer_data in ranked_customers:
            if abc_map.get(customer_id) not in ('A', 'B'):
                continue
            present_skus = sorted(
                sku_name
                for sku_name in core_skus
                if sku_name in customer_data['product_amounts']
            )
            missing_skus = [sku_name for sku_name in core_skus if sku_name not in present_skus]
            days_since_last = (date_to - customer_data['last_order_date']).days if customer_data['last_order_date'] else 999
            top_product = ''
            if customer_data['product_amounts']:
                top_product = max(
                    customer_data['product_amounts'].items(),
                    key=lambda item: item[1],
                )[0]
            portfolio_holes_rows.append({
                'partner_id': customer_id,
                'name': customer_data['name'],
                'channel': customer_data['channel'],
                'abc': abc_map.get(customer_id, 'C'),
                'revenue': round(customer_data['revenue'], 2),
                'present': present_skus,
                'missing': missing_skus,
                'gap_count': len(missing_skus),
                'detail': {
                    'title': customer_data['name'],
                    'subtitle': 'Holes de portafolio',
                    'currency_symbol': currency_symbol,
                    'summary_cards': [
                        {'label': 'Venta', 'value': round(customer_data['revenue'], 2), 'format': 'money'},
                        {'label': 'SKUs presentes', 'value': len(present_skus), 'format': 'count'},
                        {'label': 'SKUs faltantes', 'value': len(missing_skus), 'format': 'count'},
                        {'label': 'ABC', 'value': abc_map.get(customer_id, 'C'), 'format': 'text'},
                    ],
                    'channel_rows': [
                        {
                            'name': customer_data['channel'],
                            'pdv_count': 1,
                            'order_count': len(customer_data['order_ids']),
                            'units': 0.0,
                            'revenue': round(customer_data['revenue'], 2),
                        }
                    ],
                    'secondary_title': 'Estado del portafolio core',
                    'secondary_rows': [
                        {
                            'name': sku_name,
                            'units': 0.0,
                            'order_count': 0,
                            'revenue': round(customer_data['product_amounts'].get(sku_name, 0.0), 2),
                            'status': 'Presente',
                        }
                        for sku_name in present_skus
                    ] + [
                        {
                            'name': sku_name,
                            'units': 0.0,
                            'order_count': 0,
                            'revenue': 0.0,
                            'status': 'Faltante',
                        }
                        for sku_name in missing_skus
                    ],
                    'customer_rows': [],
                },
            })

            if days_since_last >= 20 or len(missing_skus) >= 2:
                if days_since_last >= 60:
                    segment = 'Hibernando'
                    action = 'Reactivar cuenta con revisión de portafolio.'
                elif days_since_last >= 35:
                    segment = 'En riesgo'
                    action = 'Recuperar frecuencia y revisar surtido core.'
                elif days_since_last >= 20 and abc_map.get(customer_id) == 'A':
                    segment = 'No perderlo'
                    action = 'Atención inmediata del ejecutivo comercial.'
                else:
                    segment = 'Atender'
                    action = 'Cerrar huecos de portafolio en próxima gestión.'
                clients_at_risk.append({
                    'partner_id': customer_id,
                    'name': customer_data['name'],
                    'channel': customer_data['channel'],
                    'abc': abc_map.get(customer_id, 'C'),
                    'segment': segment,
                    'revenue': round(customer_data['revenue'], 2),
                    'days_since_last': days_since_last,
                    'months_active': len(customer_data['months_active']),
                    'top_product': top_product,
                    'action': action,
                })

        clients_at_risk.sort(key=lambda item: (item['days_since_last'], item['revenue']), reverse=True)
        portfolio_holes_rows.sort(key=lambda item: (item['gap_count'], item['revenue']), reverse=True)

        return {
            'summary': {
                'sync_label': fields.Date.to_string(date_to),
                'period_label': '%s al %s' % (
                    fields.Date.to_string(date_from),
                    fields.Date.to_string(date_to),
                ),
                'currency_symbol': self.env.company.currency_id.symbol or '$',
            },
            'active_filters': self._serialize_active_filters(normalized_filters),
            'filter_options': filter_options,
            'summary_cards': [
                {
                    'label': 'PDVs en universo',
                    'value': universe['total'],
                    'note': 'Partners con actividad comercial en Odoo',
                },
                {
                    'label': 'PDVs facturados YTD',
                    'value': active_customer_total,
                    'note': 'Clientes con venta en marcas activas',
                },
                {
                    'label': 'White space ponderado',
                    'value': sum(item['white_space'] for item in coverage_by_channel),
                    'note': 'Canales mapeados sin captura YTD',
                },
                {
                    'label': 'Clientes A/B con holes',
                    'value': len([item for item in portfolio_holes_rows if item['gap_count'] >= 2]),
                    'note': 'Cuentas con huecos sobre SKUs core',
                },
                {
                    'label': 'Clientes A/B en riesgo',
                    'value': len(clients_at_risk),
                    'note': 'Recencia o caída de cobertura',
                },
            ],
            'coverage_by_channel': coverage_by_channel,
            'pdv_universe': universe,
            'channel_brand_matrix': {
                'brands': matrix_brand_names,
                'rows': matrix_rows,
            },
            'sku_distribution': sku_distribution,
            'portfolio_holes': {
                'core_skus': core_skus,
                'rows': portfolio_holes_rows[:20],
            },
            'clients_at_risk': clients_at_risk[:20],
            'notes_sources': [
                {
                    'label': 'Odoo',
                    'detail': 'Revenue, clientes activos, recencia, SKUs y marcas desde sale.order.line, sale.order, res.partner y zrn_commercial.',
                },
                {
                    'label': 'Universo PDV',
                    'detail': 'Totales de universo derivados de partners y pedidos reales del ultimo ano movil.',
                },
                {
                    'label': 'White space y holes',
                    'detail': 'Se calculan como señal analítica. No representan visitas, rutas ni ejecución física en PDV.',
                },
            ],
        }
