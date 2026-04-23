# -*- coding: utf-8 -*-

from odoo.exceptions import ValidationError
from odoo.osv import expression

from ....domain.sales_orders.query_fields import SALES_ORDER_QUERY_FIELDS


class SalesOrderQueryService:
    """Consulta pedidos existentes para que el bot pueda verificar estados y borradores."""

    def __init__(self, env):
        self.env = env
        self.sale_order_model = env['sale.order'].sudo()

    def query_orders(self, criteria):
        normalized = self._normalize_criteria(criteria)
        provided = {
            key: value
            for key, value in normalized.items()
            if value not in (None, '', [])
        }

        if not provided:
            raise ValidationError(
                'Debes enviar al menos un criterio de consulta: '
                'order_id, name, partner_id, partner_phone, state, date_from o date_to.'
            )

        domain = self._build_domain(provided)
        orders = self.sale_order_model.search(domain, limit=50, order='date_order desc')

        return {
            'criteria': normalized,
            'matched_fields': list(provided.keys()),
            'count': len(orders),
            'orders': [self._serialize_order(order) for order in orders],
        }

    def _normalize_criteria(self, criteria):
        criteria = criteria if isinstance(criteria, dict) else {}
        normalized = {}
        for field_name in SALES_ORDER_QUERY_FIELDS:
            raw_value = criteria.get(field_name)
            if field_name in {'order_id', 'partner_id'}:
                normalized[field_name] = self._to_int(raw_value)
            else:
                normalized[field_name] = (raw_value or '').strip() or None
        return normalized

    def _build_domain(self, provided):
        domain = []

        if provided.get('order_id'):
            domain = expression.AND([domain, [('id', '=', provided['order_id'])]])

        if provided.get('name'):
            domain = expression.AND([domain, [('name', 'ilike', provided['name'])]])

        if provided.get('partner_id'):
            domain = expression.AND([domain, [('partner_id', '=', provided['partner_id'])]])

        if provided.get('partner_phone'):
            phone = self._normalize_phone(provided['partner_phone'])
            domain = expression.AND([domain, [
                '|',
                ('partner_id.phone', 'ilike', phone),
                ('partner_id.mobile', 'ilike', phone),
            ]])

        if provided.get('state'):
            domain = expression.AND([domain, [('state', '=', provided['state'])]])

        if provided.get('date_from'):
            domain = expression.AND([domain, [('date_order', '>=', provided['date_from'])]])

        if provided.get('date_to'):
            domain = expression.AND([domain, [('date_order', '<=', provided['date_to'])]])

        return domain

    def _serialize_order(self, order):
        return {
            'id': order.id,
            'name': order.name,
            'state': order.state,
            'partner_id': order.partner_id.id,
            'partner_name': order.partner_id.display_name,
            'amount_untaxed': order.amount_untaxed,
            'amount_tax': order.amount_tax,
            'amount_total': order.amount_total,
            'currency_name': order.currency_id.name if order.currency_id else None,
            'date_order': order.date_order.isoformat() if order.date_order else None,
            'client_order_ref': order.client_order_ref if 'client_order_ref' in order._fields else None,
            'lines': [
                {
                    'id': line.id,
                    'product_id': line.product_id.id,
                    'product_name': line.product_id.display_name,
                    'default_code': line.product_id.default_code,
                    'quantity': line.product_uom_qty,
                    'price_unit': line.price_unit,
                    'discount': line.discount,
                    'price_subtotal': line.price_subtotal,
                    'price_total': line.price_total,
                }
                for line in order.order_line
            ],
        }

    @staticmethod
    def _to_int(value):
        if value in (None, ''):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize_phone(value):
        return ''.join(char for char in str(value or '') if char.isdigit())
