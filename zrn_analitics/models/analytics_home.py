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
        return self.env['sale.order.line'].search(domain, order='order_id.date_order asc, id asc')

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
                    'name': item['name'],
                    'order_count': len(item['order_ids']),
                    'total_amount': round(item['total_amount'], 2),
                }
                for item in customer_map.values()
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
        brand_mix = sorted(
            [
                {
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
            'top_customers': top_customers,
            'top_channels': top_channels,
            'top_products': top_products,
        }
