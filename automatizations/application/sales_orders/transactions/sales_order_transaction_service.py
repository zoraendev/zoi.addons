# -*- coding: utf-8 -*-

from odoo.exceptions import ValidationError
from odoo.osv import expression

from ....domain.sales_orders.command_fields import SALES_ORDER_COMMAND_FIELDS
from ....domain.sales_orders.line_fields import SALES_ORDER_LINE_FIELDS


class SalesOrderTransactionService:
    """Crea pedidos automatizados a partir de payloads armados por el bot."""

    def __init__(self, env):
        self.env = env
        self.partner_model = env['res.partner'].sudo()
        self.product_model = env['product.product'].sudo()
        self.sale_order_model = env['sale.order'].sudo()

    def create_orders(self, payload_orders):
        payload_orders = payload_orders if isinstance(payload_orders, list) else []
        results = []

        for index, payload in enumerate(payload_orders, start=1):
            try:
                order = self._create_single_order(payload or {})
                results.append({
                    'index': index,
                    'success': True,
                    'message': 'Orden creada correctamente.',
                    'order': self._serialize_order(order),
                })
            except ValidationError as error:
                results.append({
                    'index': index,
                    'success': False,
                    'message': error.args[0],
                    'order': None,
                })
            except Exception as error:
                results.append({
                    'index': index,
                    'success': False,
                    'message': str(error),
                    'order': None,
                })

        return {
            'count': len(results),
            'created_count': len([item for item in results if item['success']]),
            'results': results,
        }

    def _create_single_order(self, payload):
        values = self._normalize_order_payload(payload)
        partner = self._resolve_partner(values)
        lines = values.pop('lines', [])

        if not lines:
            raise ValidationError('La orden debe incluir al menos una linea.')

        order_vals = {
            'partner_id': partner.id,
            'order_line': [self._build_order_line_values(line) for line in lines],
        }

        if values.get('pricelist_id') and self._has_order_field('pricelist_id'):
            order_vals['pricelist_id'] = values['pricelist_id']
        if values.get('payment_term_id') and self._has_order_field('payment_term_id'):
            order_vals['payment_term_id'] = values['payment_term_id']
        if values.get('warehouse_id') and self._has_order_field('warehouse_id'):
            order_vals['warehouse_id'] = values['warehouse_id']
        if values.get('client_order_ref') and self._has_order_field('client_order_ref'):
            order_vals['client_order_ref'] = values['client_order_ref']
        if values.get('note') and self._has_order_field('note'):
            order_vals['note'] = values['note']
        if values.get('requested_date') and self._has_order_field('commitment_date'):
            order_vals['commitment_date'] = values['requested_date']

        return self.sale_order_model.create(order_vals)

    def _normalize_order_payload(self, payload):
        payload = payload if isinstance(payload, dict) else {}
        normalized = {
            field_name: payload.get(field_name)
            for field_name in SALES_ORDER_COMMAND_FIELDS
        }
        normalized['lines'] = self._normalize_lines(payload.get('lines'))
        return normalized

    def _normalize_lines(self, lines):
        lines = lines if isinstance(lines, list) else []
        normalized_lines = []
        for line in lines:
            line = line if isinstance(line, dict) else {}
            normalized_lines.append({
                field_name: line.get(field_name)
                for field_name in SALES_ORDER_LINE_FIELDS
            })
        return normalized_lines

    def _resolve_partner(self, values):
        domain = []

        if values.get('customer_id'):
            domain = expression.AND([domain, [('id', '=', int(values['customer_id']))]])
        if values.get('customer_phone'):
            phone = self._normalize_phone(values['customer_phone'])
            phone_domain = ['|', ('automation_phone_normalized', '=', phone), ('automation_mobile_normalized', '=', phone)]
            domain = expression.AND([domain, phone_domain])
        if values.get('customer_email'):
            domain = expression.AND([domain, [('automation_email_normalized', '=', values['customer_email'].strip().lower())]])
        if values.get('customer_ref'):
            domain = expression.AND([domain, [('ref', '=ilike', values['customer_ref'])]])
        if values.get('automation_customer_uid'):
            domain = expression.AND([domain, [('automation_customer_uid', '=', values['automation_customer_uid'])]])

        if not domain:
            raise ValidationError(
                'Debes enviar un identificador de cliente para crear la orden: customer_id, customer_phone, customer_email, customer_ref o automation_customer_uid.'
            )

        partners = self.partner_model.search(domain, limit=2)
        if not partners:
            raise ValidationError('No se encontro un cliente valido para la orden.')
        if len(partners) > 1:
            raise ValidationError('La busqueda del cliente devolvio multiples resultados. Usa un identificador mas especifico.')
        return partners[0]

    def _build_order_line_values(self, line):
        product = self._resolve_product(line)
        quantity = line.get('product_uom_qty') or line.get('quantity') or 1
        try:
            quantity = float(quantity)
        except (TypeError, ValueError):
            raise ValidationError('Cada linea debe incluir una cantidad valida.')

        if quantity <= 0:
            raise ValidationError('La cantidad de cada linea debe ser mayor a cero.')

        discount = line.get('discount') or 0
        try:
            discount = float(discount)
        except (TypeError, ValueError):
            raise ValidationError('El descuento de la linea no es valido.')

        price_unit = line.get('price_unit')
        if price_unit in (None, ''):
            price_unit = product.lst_price
        else:
            try:
                price_unit = float(price_unit)
            except (TypeError, ValueError):
                raise ValidationError('El precio unitario de la linea no es valido.')

        line_vals = (0, 0, {
            'product_id': product.id,
            'name': line.get('name') or product.display_name,
            'product_uom_qty': quantity,
            'price_unit': price_unit,
            'discount': discount,
        })

        return line_vals

    def _resolve_product(self, line):
        domain = []

        if line.get('product_id'):
            domain = expression.AND([domain, [('id', '=', int(line['product_id']))]])
        if line.get('product_tmpl_id'):
            domain = expression.AND([domain, [('product_tmpl_id', '=', int(line['product_tmpl_id']))]])
        if line.get('default_code'):
            domain = expression.AND([domain, [('default_code', '=ilike', line['default_code'])]])
        if line.get('barcode'):
            domain = expression.AND([domain, [('barcode', '=ilike', line['barcode'])]])
        if line.get('name'):
            domain = expression.AND([domain, [('name', 'ilike', line['name'])]])

        if not domain:
            raise ValidationError(
                'Cada linea debe incluir un identificador de producto: product_id, product_tmpl_id, default_code, barcode o name.'
            )

        products = self.product_model.search(domain, limit=2)
        if not products:
            raise ValidationError('No se encontro un producto valido para una de las lineas.')
        if len(products) > 1:
            raise ValidationError('La busqueda de producto devolvio multiples resultados. Usa un identificador mas especifico.')
        return products[0]

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
            'currency_id': order.currency_id.id if order.currency_id else None,
            'currency_name': order.currency_id.name if order.currency_id else None,
            'date_order': order.date_order.isoformat() if order.date_order else None,
            'client_order_ref': order.client_order_ref if self._has_order_field('client_order_ref') else None,
            'note': order.note if self._has_order_field('note') else None,
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

    def _has_order_field(self, field_name):
        return field_name in self.sale_order_model._fields

    @staticmethod
    def _normalize_phone(value):
        return ''.join(char for char in str(value or '') if char.isdigit())
