# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PbiConnectionsCustomerDashboard(models.AbstractModel):
    _name = 'pbi_connections.customer.dashboard'
    _description = 'Servicio del dashboard de clientes para PBI Connections'

    @api.model
    def _normalize_date_range_filters(self, filters=None):
        filters = filters or {}
        normalized_filters = {
            'dateFrom': None,
            'dateTo': None,
        }

        raw_date_from = filters.get('dateFrom') or filters.get('date_from')
        raw_date_to = filters.get('dateTo') or filters.get('date_to')

        try:
            if raw_date_from:
                normalized_filters['dateFrom'] = fields.Date.to_date(raw_date_from).isoformat()
            if raw_date_to:
                normalized_filters['dateTo'] = fields.Date.to_date(raw_date_to).isoformat()
        except (TypeError, ValueError):
            raise ValidationError('Los filtros de fecha deben usar el formato YYYY-MM-DD.')

        if (
            normalized_filters['dateFrom']
            and normalized_filters['dateTo']
            and normalized_filters['dateFrom'] > normalized_filters['dateTo']
        ):
            raise ValidationError('El filtro "dateFrom" no puede ser mayor que "dateTo".')

        return normalized_filters

    @api.model
    def _parse_positive_integer(self, value, label, default, *, allow_zero=False, max_value=None):
        if value in (None, False, '', 'null', 'None'):
            value = default

        try:
            parsed_value = int(value)
        except (TypeError, ValueError):
            raise ValidationError(f'El filtro "{label}" debe ser un numero entero.')

        if allow_zero:
            if parsed_value < 0:
                raise ValidationError(f'El filtro "{label}" no puede ser negativo.')
        elif parsed_value <= 0:
            raise ValidationError(f'El filtro "{label}" debe ser mayor que cero.')

        if max_value is not None:
            parsed_value = min(parsed_value, max_value)

        return parsed_value

    @api.model
    def _normalize_frequent_customers_filters(self, filters=None):
        filters = filters or {}
        normalized_filters = self._normalize_date_range_filters(filters)
        normalized_filters.update({
            'top': self._parse_positive_integer(filters.get('top') or filters.get('limit'), 'top', 10, max_value=100),
            'sortBy': (filters.get('sortBy') or 'totalOrders').strip(),
        })

        allowed_sort_fields = {
            'totalOrders',
            'totalAmount',
            'averageOrderValue',
            'averageDaysBetweenOrders',
            'lastOrderDate',
            'daysWithoutPurchase',
            'customerName',
        }
        if normalized_filters['sortBy'] not in allowed_sort_fields:
            raise ValidationError(
                'El filtro "sortBy" debe ser uno de estos valores: '
                'totalOrders, totalAmount, averageOrderValue, averageDaysBetweenOrders, '
                'lastOrderDate, daysWithoutPurchase o customerName.'
            )

        return normalized_filters

    @api.model
    def _normalize_inactive_customers_filters(self, filters=None):
        filters = filters or {}
        return {
            'inactiveDays': self._parse_positive_integer(
                filters.get('inactiveDays') or filters.get('inactive_days'),
                'inactiveDays',
                60,
                allow_zero=True,
            ),
            'top': self._parse_positive_integer(filters.get('top') or filters.get('limit'), 'top', 50, max_value=100),
        }

    @api.model
    def _normalize_customer_value_filters(self, filters=None):
        filters = filters or {}
        normalized_filters = self._normalize_date_range_filters(filters)
        normalized_filters.update({
            'top': self._parse_positive_integer(filters.get('top') or filters.get('limit'), 'top', 20, max_value=100),
            'sortBy': (filters.get('sortBy') or 'totalAmount').strip(),
        })

        allowed_sort_fields = {
            'totalAmount',
            'totalOrders',
            'averageOrderValue',
            'ltvBasic',
            'firstOrderDate',
            'lastOrderDate',
            'customerName',
        }
        if normalized_filters['sortBy'] not in allowed_sort_fields:
            raise ValidationError(
                'El filtro "sortBy" debe ser uno de estos valores: '
                'totalAmount, totalOrders, averageOrderValue, ltvBasic, '
                'firstOrderDate, lastOrderDate o customerName.'
            )

        return normalized_filters

    @api.model
    def _get_generated_at_iso(self):
        generated_at = fields.Datetime.now()
        if isinstance(generated_at, str):
            generated_at = fields.Datetime.to_datetime(generated_at)
        return generated_at.replace(microsecond=0).isoformat() + 'Z'

    @api.model
    def _get_average_days_between_orders(self, order_datetimes):
        valid_dates = sorted(date for date in order_datetimes if date)
        if len(valid_dates) <= 1:
            return 0

        intervals = []
        previous_date = valid_dates[0]
        for current_date in valid_dates[1:]:
            delta_days = (current_date - previous_date).total_seconds() / 86400.0
            intervals.append(max(delta_days, 0.0))
            previous_date = current_date

        return int(round(sum(intervals) / len(intervals))) if intervals else 0

    @api.model
    def _get_customer_type(self, total_orders, average_days_between_orders):
        if total_orders >= 5:
            return 'recurring'
        if total_orders >= 2 and average_days_between_orders <= 30:
            return 'recurring'
        if total_orders >= 2:
            return 'occasional'
        return 'new'

    @api.model
    def _get_sale_orders(self, date_from=None, date_to=None):
        if 'sale.order' not in self.env:
            raise ValidationError('El modelo de ordenes de venta no esta disponible en esta instancia.')

        domain = [
            ('state', 'in', ['sale', 'done']),
            ('partner_id', '!=', False),
        ]
        if date_from:
            domain.append(('date_order', '>=', f"{date_from} 00:00:00"))
        if date_to:
            domain.append(('date_order', '<=', f"{date_to} 23:59:59"))

        return self.env['sale.order'].search(domain, order='date_order asc, id asc')

    @api.model
    def _aggregate_orders_by_customer(self, orders):
        aggregated_data = {}

        for order in orders:
            partner = order.partner_id.commercial_partner_id
            if not partner:
                continue

            order_datetime = fields.Datetime.to_datetime(order.date_order) if order.date_order else None
            item = aggregated_data.setdefault(partner.id, {
                'customerId': partner.id,
                'customerName': partner.display_name or '',
                'customerCode': partner.ref or '',
                'totalOrders': 0,
                'totalAmount': 0.0,
                '_first_order_datetime': None,
                '_last_order_datetime': None,
                '_order_datetimes': [],
            })

            item['totalOrders'] += 1
            item['totalAmount'] += float(order.amount_total or 0.0)

            if order_datetime:
                item['_order_datetimes'].append(order_datetime)
                if not item['_first_order_datetime'] or order_datetime < item['_first_order_datetime']:
                    item['_first_order_datetime'] = order_datetime
                if not item['_last_order_datetime'] or order_datetime > item['_last_order_datetime']:
                    item['_last_order_datetime'] = order_datetime

        return aggregated_data

    @api.model
    def _build_customer_metrics(self, aggregated_item, anchor_date=None):
        order_datetimes = aggregated_item.get('_order_datetimes', [])
        total_orders = aggregated_item.get('totalOrders', 0)
        total_amount = round(float(aggregated_item.get('totalAmount', 0.0) or 0.0), 2)
        average_order_value = round(total_amount / total_orders, 2) if total_orders else 0.0
        average_days_between_orders = self._get_average_days_between_orders(order_datetimes)

        first_order_datetime = aggregated_item.get('_first_order_datetime')
        last_order_datetime = aggregated_item.get('_last_order_datetime')
        first_order_date = first_order_datetime.date().isoformat() if first_order_datetime else ''
        last_order_date = last_order_datetime.date().isoformat() if last_order_datetime else ''
        days_without_purchase = 0
        if anchor_date and last_order_datetime:
            days_without_purchase = max((anchor_date - last_order_datetime.date()).days, 0)

        return {
            'customerId': aggregated_item.get('customerId'),
            'customerName': aggregated_item.get('customerName', ''),
            'customerCode': aggregated_item.get('customerCode', ''),
            'totalOrders': total_orders,
            'totalAmount': total_amount,
            'averageOrderValue': average_order_value,
            'averageDaysBetweenOrders': average_days_between_orders,
            'firstOrderDate': first_order_date,
            'lastOrderDate': last_order_date,
            'daysWithoutPurchase': days_without_purchase,
            'customerType': self._get_customer_type(total_orders, average_days_between_orders),
        }

    @api.model
    def get_frequent_customers_report_data(self, filters=None):
        normalized_filters = self._normalize_frequent_customers_filters(filters)
        orders = self._get_sale_orders(
            date_from=normalized_filters['dateFrom'],
            date_to=normalized_filters['dateTo'],
        )
        anchor_date = (
            fields.Date.to_date(normalized_filters['dateTo'])
            if normalized_filters['dateTo']
            else fields.Date.to_date(fields.Date.context_today(self))
        )

        data = []
        for item in self._aggregate_orders_by_customer(orders).values():
            metrics = self._build_customer_metrics(item, anchor_date=anchor_date)
            data.append({
                'customerId': metrics['customerId'],
                'customerName': metrics['customerName'],
                'customerCode': metrics['customerCode'],
                'totalOrders': metrics['totalOrders'],
                'totalAmount': metrics['totalAmount'],
                'averageOrderValue': metrics['averageOrderValue'],
                'averageDaysBetweenOrders': metrics['averageDaysBetweenOrders'],
                'lastOrderDate': metrics['lastOrderDate'],
                'daysWithoutPurchase': metrics['daysWithoutPurchase'],
                'customerType': metrics['customerType'],
            })

        sort_by = normalized_filters['sortBy']
        if sort_by == 'customerName':
            data.sort(key=lambda row: (row['customerName'] or '').lower())
        elif sort_by == 'lastOrderDate':
            data.sort(
                key=lambda row: (row['lastOrderDate'] or '', row['totalOrders'], row['totalAmount']),
                reverse=True,
            )
        elif sort_by in ('averageDaysBetweenOrders', 'daysWithoutPurchase'):
            data.sort(key=lambda row: (
                row.get(sort_by, 0),
                -(row.get('totalOrders', 0)),
                -(row.get('totalAmount', 0.0)),
                (row.get('customerName') or '').lower(),
            ))
        else:
            data.sort(
                key=lambda row: (
                    row.get(sort_by, 0),
                    row.get('totalAmount', 0.0),
                    row.get('totalOrders', 0),
                    (row.get('customerName') or '').lower(),
                ),
                reverse=True,
            )

        return {
            'generatedAt': self._get_generated_at_iso(),
            'filters': normalized_filters,
            'data': data[:normalized_filters['top']],
        }

    @api.model
    def get_inactive_customers_report_data(self, filters=None):
        normalized_filters = self._normalize_inactive_customers_filters(filters)
        orders = self._get_sale_orders()
        anchor_date = fields.Date.to_date(fields.Date.context_today(self))

        data = []
        for item in self._aggregate_orders_by_customer(orders).values():
            metrics = self._build_customer_metrics(item, anchor_date=anchor_date)
            if metrics['daysWithoutPurchase'] < normalized_filters['inactiveDays']:
                continue

            data.append({
                'customerId': metrics['customerId'],
                'customerName': metrics['customerName'],
                'customerCode': metrics['customerCode'],
                'lastOrderDate': metrics['lastOrderDate'],
                'daysWithoutPurchase': metrics['daysWithoutPurchase'],
                'totalOrdersHistorical': metrics['totalOrders'],
                'totalHistoricalAmount': metrics['totalAmount'],
                'averageOrderValue': metrics['averageOrderValue'],
                'customerType': 'inactive',
            })

        data.sort(
            key=lambda row: (
                row.get('daysWithoutPurchase', 0),
                row.get('totalOrdersHistorical', 0),
                row.get('totalHistoricalAmount', 0.0),
                (row.get('customerName') or '').lower(),
            ),
            reverse=True,
        )

        return {
            'generatedAt': self._get_generated_at_iso(),
            'filters': normalized_filters,
            'data': data[:normalized_filters['top']],
        }

    @api.model
    def get_customer_value_report_data(self, filters=None):
        normalized_filters = self._normalize_customer_value_filters(filters)
        orders = self._get_sale_orders(
            date_from=normalized_filters['dateFrom'],
            date_to=normalized_filters['dateTo'],
        )

        data = []
        for item in self._aggregate_orders_by_customer(orders).values():
            metrics = self._build_customer_metrics(item)
            data.append({
                'customerId': metrics['customerId'],
                'customerName': metrics['customerName'],
                'customerCode': metrics['customerCode'],
                'totalOrders': metrics['totalOrders'],
                'totalAmount': metrics['totalAmount'],
                'averageOrderValue': metrics['averageOrderValue'],
                'ltvBasic': metrics['totalAmount'],
                'firstOrderDate': metrics['firstOrderDate'],
                'lastOrderDate': metrics['lastOrderDate'],
                'customerType': metrics['customerType'],
            })

        sort_by = normalized_filters['sortBy']
        if sort_by == 'customerName':
            data.sort(key=lambda row: (row['customerName'] or '').lower())
        elif sort_by in ('firstOrderDate', 'lastOrderDate'):
            data.sort(
                key=lambda row: (
                    row.get(sort_by, ''),
                    row.get('totalAmount', 0.0),
                    row.get('totalOrders', 0),
                ),
                reverse=True,
            )
        else:
            data.sort(
                key=lambda row: (
                    row.get(sort_by, 0),
                    row.get('totalAmount', 0.0),
                    row.get('totalOrders', 0),
                    (row.get('customerName') or '').lower(),
                ),
                reverse=True,
            )

        return {
            'generatedAt': self._get_generated_at_iso(),
            'filters': normalized_filters,
            'data': data[:normalized_filters['top']],
        }
