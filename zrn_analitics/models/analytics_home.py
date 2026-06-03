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
            universe_partner_ids.add(partner.id)
            by_channel[self._infer_coverage_channel(partner.display_name)].add(partner.id)
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
                universe_partner_ids.add(commercial_partner.id)
                by_channel[self._infer_coverage_channel(commercial_partner.display_name)].add(commercial_partner.id)
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
    def _get_empty_coverage_dashboard_data(self):
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
    def _get_empty_commercial_hub_payload(self):
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
            'empty_message': 'No hay marcas comerciales creadas en Zoraen Commercial.',
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
    def get_commercial_hub_payload(self):
        date_from, date_to = self._get_commercial_hub_period()
        brands, product_brand_map = self._get_commercial_brand_map()
        if not brands or not product_brand_map:
            return self._get_empty_commercial_hub_payload()

        order_lines = self._get_commercial_sale_order_lines(
            date_from,
            date_to,
            list(product_brand_map.keys()),
        )
        if not order_lines:
            payload = self._get_empty_commercial_hub_payload()
            payload['summary']['brand_count'] = len(brands)
            payload['summary']['product_count'] = len(product_brand_map)
            payload['has_brands'] = True
            payload['empty_message'] = 'Hay marcas creadas, pero aun no existen ventas para sus productos en el periodo.'
            payload['brand_catalog'] = [
                {
                    'name': brand.name,
                    'product_count': len(brand.product_link_ids.filtered(lambda link: link.active and link.product_id)),
                }
                for brand in brands
            ]
            return payload

        month_starts, month_labels = self._get_recent_month_labels(date_to)
        month_amounts = {
            month_start: 0.0
            for month_start in month_starts
        }
        brand_amounts = defaultdict(float)
        brand_product_ids = defaultdict(set)
        order_ids = set()
        channel_map = {}
        customer_map = {}
        product_map = {}

        for line in order_lines:
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

            if order.date_order:
                order_date = fields.Datetime.to_datetime(order.date_order).date()
                order_month = order_date.replace(day=1)
                if order_month in month_amounts:
                    month_amounts[order_month] += amount
            else:
                order_date = False

            brand_amounts[brand_info['brand_name']] += amount
            brand_product_ids[brand_info['brand_name']].add(product.id)

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
                },
            )
            product_entry['quantity_sold'] += quantity
            product_entry['sales_amount'] += amount

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
        }

    @api.model
    def get_coverage_dashboard_data(self):
        date_from, date_to = self._get_commercial_hub_period()
        universe = self._get_coverage_universe(date_to - timedelta(days=365), date_to)
        brands, product_brand_map = self._get_commercial_brand_map()
        if not brands or not product_brand_map:
            return self._get_empty_coverage_dashboard_data()

        order_lines = self._get_commercial_sale_order_lines(
            date_from,
            date_to,
            list(product_brand_map.keys()),
        )
        if not order_lines:
            return self._get_empty_coverage_dashboard_data()

        channel_map = {}
        customer_map = {}
        sku_map = {}
        total_revenue = 0.0

        for line in order_lines:
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
            channel_name = self._infer_coverage_channel(partner.display_name)
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
                },
            )
            sku_entry['revenue'] += amount
            sku_entry['customer_ids'].add(partner.id)
            sku_entry['channels'].add(channel_name)
            sku_entry['quantity'] += quantity

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
