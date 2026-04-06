from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AdvancedMetricsReportWizard(models.TransientModel):
    _name = 'advanced_metrics.report.wizard'
    _description = 'Asistente de reporte de ventas e inventario'

    fecha_entrega_desde = fields.Date(string='Fecha de entrega desde')
    fecha_entrega_hasta = fields.Date(string='Fecha de entrega hasta')
    cliente_id = fields.Many2one(
        'res.partner',
        string='Cliente',
    )
    numero_orden_venta = fields.Char(string='Numero de orden de venta')
    producto = fields.Char(string='Producto')
    cantidad_vendida_min = fields.Float(string='Cantidad vendida minima')
    cantidad_vendida_max = fields.Float(string='Cantidad vendida maxima')
    inventario_disponible_min = fields.Float(string='Inventario disponible minimo')
    inventario_disponible_max = fields.Float(string='Inventario disponible maximo')
    report_line_ids = fields.One2many(
        'advanced_metrics.report.wizard.line',
        'wizard_id',
        string='Lineas de reporte',
    )

    @api.model
    def get_sales_orders_report_rows(self, filters=None):
        filters = filters or {}
        if 'sale.order.line' not in self.env or 'stock.quant' not in self.env:
            return []

        sale_line_model = self.env['sale.order.line']
        stock_quant_model = self.env['stock.quant']

        domain = [
            ('order_id.state', 'in', ['sale', 'done']),
            ('display_type', '=', False),
        ]

        fecha_desde = filters.get('fecha_entrega_desde')
        fecha_hasta = filters.get('fecha_entrega_hasta')
        cliente_id = filters.get('cliente_id')
        cliente_nombre = filters.get('cliente_nombre')

        if fecha_desde:
            domain.append(('order_id.commitment_date', '>=', fecha_desde))
        if fecha_hasta:
            domain.append(('order_id.commitment_date', '<=', f'{fecha_hasta} 23:59:59'))
        if cliente_id:
            domain.append(('order_partner_id', '=', int(cliente_id)))
        elif cliente_nombre:
            domain.append(('order_partner_id.name', 'ilike', cliente_nombre))

        order_lines = sale_line_model.search(domain, order='order_id.commitment_date desc, id desc', limit=500)
        product_ids = order_lines.mapped('product_id').ids

        qty_by_product_id = {}
        if product_ids:
            grouped_quants = stock_quant_model.read_group(
                [('product_id', 'in', product_ids), ('location_id.usage', '=', 'internal')],
                ['product_id', 'quantity:sum'],
                ['product_id'],
            )
            qty_by_product_id = {
                item['product_id'][0]: item.get('quantity', 0.0)
                for item in grouped_quants
                if item.get('product_id')
            }

        rows = []
        for line in order_lines:
            available_qty = qty_by_product_id.get(line.product_id.id, 0.0)
            rows.append({
                'fecha_entrega': line.order_id.commitment_date.date().isoformat() if line.order_id.commitment_date else '',
                'cliente': line.order_partner_id.display_name or '',
                'numero_orden_venta': line.order_id.name or '',
                'producto': line.product_id.display_name or '',
                'cantidad_vendida': line.product_uom_qty,
                'inventario_disponible': available_qty,
                'cantidad_sugerida_producir': 0.0,
            })

        return rows

    @api.model
    def _normalize_top_products_filters(self, filters=None):
        filters = filters or {}

        raw_date_from = (
            filters.get('dateFrom')
            or filters.get('date_from')
            or filters.get('fecha_entrega_desde')
        )
        raw_date_to = (
            filters.get('dateTo')
            or filters.get('date_to')
            or filters.get('fecha_entrega_hasta')
        )
        raw_limit = filters.get('limit', 10)

        try:
            limit = int(raw_limit or 10)
        except (TypeError, ValueError):
            raise ValidationError('El filtro "limit" debe ser un numero entero.')

        if limit <= 0:
            raise ValidationError('El filtro "limit" debe ser mayor que cero.')

        normalized_filters = {
            'dateFrom': None,
            'dateTo': None,
            'limit': min(limit, 100),
        }

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
    def _get_generated_at_iso(self):
        generated_at = fields.Datetime.now()
        if isinstance(generated_at, str):
            generated_at = fields.Datetime.to_datetime(generated_at)
        return generated_at.replace(microsecond=0).isoformat() + 'Z'

    @api.model
    def _get_current_stock_by_product(self, product_ids):
        if 'stock.quant' not in self.env or not product_ids:
            return {}

        stock_quant_model = self.env['stock.quant']

        grouped_quants = stock_quant_model.read_group(
            [('product_id', 'in', product_ids), ('location_id.usage', '=', 'internal')],
            ['product_id', 'quantity:sum'],
            ['product_id'],
        )
        return {
            item['product_id'][0]: float(item.get('quantity', 0.0))
            for item in grouped_quants
            if item.get('product_id')
        }

    @api.model
    def get_top_products_report_data(self, filters=None):
        normalized_filters = self._normalize_top_products_filters(filters)
        if 'sale.order.line' not in self.env:
            raise ValidationError('El modelo de lineas de venta no esta disponible en esta instancia.')

        sale_line_model = self.env['sale.order.line']

        domain = [
            ('order_id.state', 'in', ['sale', 'done']),
            ('display_type', '=', False),
            ('product_id', '!=', False),
        ]

        if normalized_filters['dateFrom']:
            domain.append(('order_id.date_order', '>=', f"{normalized_filters['dateFrom']} 00:00:00"))
        if normalized_filters['dateTo']:
            domain.append(('order_id.date_order', '<=', f"{normalized_filters['dateTo']} 23:59:59"))

        order_lines = sale_line_model.search(domain, order='id desc')
        product_ids = order_lines.mapped('product_id').ids
        stock_by_product = self._get_current_stock_by_product(product_ids)

        aggregated_data = {}
        for line in order_lines:
            product = line.product_id
            if not product:
                continue

            quantity_sold = float(line.product_uom_qty or 0.0)
            if quantity_sold <= 0:
                continue

            sales_amount = float(line.price_subtotal or 0.0)
            unit_cost = float(
                getattr(line, 'purchase_price', 0.0)
                or getattr(product, 'standard_price', 0.0)
                or 0.0
            )
            margin_amount = sales_amount - (quantity_sold * unit_cost)

            item = aggregated_data.setdefault(product.id, {
                'productId': product.id,
                'productName': product.display_name or '',
                'sku': product.default_code or '',
                'categoryName': product.categ_id.display_name or '',
                'quantitySold': 0.0,
                'salesAmount': 0.0,
                'currentStock': float(stock_by_product.get(product.id, 0.0)),
                'marginAmount': 0.0,
            })
            item['quantitySold'] += quantity_sold
            item['salesAmount'] += sales_amount
            item['marginAmount'] += margin_amount

        data = sorted(
            aggregated_data.values(),
            key=lambda row: (row['quantitySold'], row['salesAmount']),
            reverse=True,
        )[:normalized_filters['limit']]

        for item in data:
            item['quantitySold'] = round(item['quantitySold'], 2)
            item['salesAmount'] = round(item['salesAmount'], 2)
            item['currentStock'] = round(item['currentStock'], 2)
            item['marginAmount'] = round(item['marginAmount'], 2)
            item['marginPercent'] = round(
                (item['marginAmount'] / item['salesAmount']) * 100,
                2,
            ) if item['salesAmount'] else 0.0
            item['inventoryTurnover'] = round(
                item['quantitySold'] / item['currentStock'],
                2,
            ) if item['currentStock'] > 0 else 0.0

        return {
            'generatedAt': self._get_generated_at_iso(),
            'filters': normalized_filters,
            'data': data,
        }

    def action_generate_report(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Advanced Metrics',
                'message': 'La logica de generacion del reporte se implementara despues.',
                'type': 'warning',
                'sticky': False,
            },
        }


class AdvancedMetricsReportWizardLine(models.TransientModel):
    _name = 'advanced_metrics.report.wizard.line'
    _description = 'Linea del reporte de ventas e inventario'
    _order = 'fecha_entrega desc, id desc'

    wizard_id = fields.Many2one(
        'advanced_metrics.report.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    fecha_entrega = fields.Date(string='Fecha de entrega')
    cliente_id = fields.Many2one('res.partner', string='Cliente')
    numero_orden_venta = fields.Char(string='Numero de orden de venta')
    producto = fields.Char(string='Producto')
    cantidad_vendida = fields.Float(string='Cantidad vendida')
    inventario_disponible = fields.Float(string='Inventario disponible de producto terminado')
    cantidad_sugerida_producir = fields.Float(
        string='Cantidad sugerida a producir',
        default=0.0,
    )
