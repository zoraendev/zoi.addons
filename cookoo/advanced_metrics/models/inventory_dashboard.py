# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AdvancedMetricsInventoryDashboard(models.AbstractModel):
    _name = 'advanced_metrics.inventory.dashboard'
    _description = 'Servicio del dashboard de inventario'

    @api.model
    def _normalize_date_range_filters(self, filters=None):
        filters = filters or {}
        normalized_filters = {
            'dateFrom': None,
            'dateTo': None,
        }

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
    def _parse_optional_integer(self, value, label):
        if value in (None, False, '', 'null', 'None'):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValidationError(f'El filtro "{label}" debe ser un numero entero.')

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
    def _normalize_top_products_filters(self, filters=None):
        filters = filters or {}
        normalized_filters = self._normalize_date_range_filters(filters)
        normalized_filters['limit'] = self._parse_positive_integer(filters.get('limit'), 'limit', 10, max_value=100)
        return normalized_filters

    @api.model
    def _normalize_products_sales_filters(self, filters=None):
        filters = filters or {}
        normalized_filters = self._normalize_date_range_filters(filters)
        normalized_filters.update({
            'warehouseId': self._parse_optional_integer(filters.get('warehouseId'), 'warehouseId'),
            'categoryId': self._parse_optional_integer(filters.get('categoryId'), 'categoryId'),
        })
        return normalized_filters

    @api.model
    def _normalize_sales_trend_filters(self, filters=None):
        filters = filters or {}
        normalized_filters = self._normalize_products_sales_filters(filters)
        normalized_filters['groupBy'] = (filters.get('groupBy') or 'day').strip().lower()

        if normalized_filters['groupBy'] not in ('day', 'week', 'month'):
            raise ValidationError('El filtro "groupBy" debe ser day, week o month.')

        return normalized_filters

    @api.model
    def _normalize_dead_products_filters(self, filters=None):
        filters = filters or {}
        return {
            'daysWithoutMovement': self._parse_positive_integer(
                filters.get('daysWithoutMovement') or filters.get('days_without_movement'),
                'daysWithoutMovement',
                60,
                allow_zero=True,
            ),
            'warehouseId': self._parse_optional_integer(filters.get('warehouseId'), 'warehouseId'),
        }

    @api.model
    def _normalize_high_rotation_filters(self, filters=None):
        filters = filters or {}
        normalized_filters = self._normalize_date_range_filters(filters)
        normalized_filters.update({
            'warehouseId': self._parse_optional_integer(filters.get('warehouseId'), 'warehouseId'),
            'limit': self._parse_positive_integer(filters.get('limit'), 'limit', 10, max_value=100),
        })
        return normalized_filters

    @api.model
    def _normalize_weekly_plan_filters(self, filters=None):
        filters = filters or {}
        normalized_filters = self._normalize_date_range_filters(filters)
        for key in ('cliente_id', 'cliente_nombre', 'fecha_entrega_desde', 'fecha_entrega_hasta'):
            value = filters.get(key)
            if value not in (None, ''):
                normalized_filters[key] = value
        return normalized_filters

    @api.model
    def _get_generated_at_iso(self):
        generated_at = fields.Datetime.now()
        if isinstance(generated_at, str):
            generated_at = fields.Datetime.to_datetime(generated_at)
        return generated_at.replace(microsecond=0).isoformat() + 'Z'

    @api.model
    def _get_period_bucket(self, sale_date, group_by):
        if group_by == 'week':
            sale_date = sale_date - timedelta(days=sale_date.weekday())
        elif group_by == 'month':
            sale_date = sale_date.replace(day=1)
        return sale_date.isoformat()

    @api.model
    def _build_period_summary(self):
        return {
            'last7Days': {'quantitySold': 0.0, 'salesAmount': 0.0},
            'last15Days': {'quantitySold': 0.0, 'salesAmount': 0.0},
            'last30Days': {'quantitySold': 0.0, 'salesAmount': 0.0},
        }

    @api.model
    def _get_sellable_product_domain(self, category_id=None):
        domain = [
            ('sale_ok', '=', True),
            ('active', '=', True),
        ]

        if 'detailed_type' in self.env['product.product']._fields:
            domain.append(('detailed_type', 'in', ['product', 'consu']))
        elif 'type' in self.env['product.product']._fields:
            domain.append(('type', 'in', ['product', 'consu']))

        if category_id:
            domain.append(('categ_id', 'child_of', category_id))

        return domain

    @api.model
    def _get_sellable_product_ids(self, product_ids=None, category_id=None):
        if 'product.product' not in self.env:
            return []

        domain = self._get_sellable_product_domain(category_id=category_id)
        if product_ids:
            domain.append(('id', 'in', list(product_ids)))

        return self.env['product.product'].search(domain).ids

    @api.model
    def _get_stock_quant_domain(self, product_ids=None, warehouse_id=None, category_id=None):
        domain = [
            ('location_id.usage', '=', 'internal'),
            ('product_id.sale_ok', '=', True),
        ]

        if 'detailed_type' in self.env['product.product']._fields:
            domain.append(('product_id.detailed_type', 'in', ['product', 'consu']))
        elif 'type' in self.env['product.product']._fields:
            domain.append(('product_id.type', 'in', ['product', 'consu']))

        if product_ids:
            domain.append(('product_id', 'in', list(product_ids)))
        if category_id:
            domain.append(('product_id.categ_id', 'child_of', category_id))
        if warehouse_id:
            warehouse = self.env['stock.warehouse'].browse(warehouse_id)
            if not warehouse.exists():
                raise ValidationError('El almacen indicado no existe.')
            domain.append(('location_id', 'child_of', warehouse.lot_stock_id.id))

        return domain

    @api.model
    def _get_current_stock_by_product(self, product_ids, warehouse_id=None, category_id=None):
        if 'stock.quant' not in self.env or not product_ids:
            return {}

        grouped_quants = self.env['stock.quant'].read_group(
            self._get_stock_quant_domain(product_ids=product_ids, warehouse_id=warehouse_id, category_id=category_id),
            ['product_id', 'quantity:sum'],
            ['product_id'],
        )
        return {
            item['product_id'][0]: float(item.get('quantity', 0.0))
            for item in grouped_quants
            if item.get('product_id')
        }

    @api.model
    def _get_stocked_product_ids(self, warehouse_id=None, category_id=None):
        if 'stock.quant' not in self.env:
            return []

        grouped_quants = self.env['stock.quant'].read_group(
            self._get_stock_quant_domain(warehouse_id=warehouse_id, category_id=category_id),
            ['product_id'],
            ['product_id'],
        )
        return [item['product_id'][0] for item in grouped_quants if item.get('product_id')]

    @api.model
    def _get_last_sale_date_by_product(self, product_ids, warehouse_id=None):
        if 'sale.order.line' not in self.env or not product_ids:
            return {}

        domain = [
            ('order_id.state', 'in', ['sale', 'done']),
            ('display_type', '=', False),
            ('product_id', 'in', list(product_ids)),
        ]
        if warehouse_id:
            domain.append(('order_id.warehouse_id', '=', warehouse_id))

        last_sale_dates = {}
        lines = self.env['sale.order.line'].search(domain, order='id desc')

        for line in lines:
            product_id = line.product_id.id
            order_date = fields.Datetime.to_datetime(line.order_id.date_order) if line.order_id.date_order else None
            existing_date = last_sale_dates.get(product_id)
            if order_date and (not existing_date or order_date.date().isoformat() > existing_date):
                last_sale_dates[product_id] = order_date.date().isoformat()
            elif product_id not in last_sale_dates:
                last_sale_dates[product_id] = ''

        return last_sale_dates

    @api.model
    def _get_movement_status(self, quantity_sold, inventory_turnover):
        if quantity_sold <= 0:
            return 'no_movement'
        if inventory_turnover >= 5 or quantity_sold >= 50:
            return 'high_rotation'
        if inventory_turnover >= 2 or quantity_sold >= 10:
            return 'medium_rotation'
        return 'low_rotation'

    @api.model
    def _get_stock_status(self, current_stock, quantity_sold):
        if current_stock <= 0:
            return 'out_of_stock'
        if quantity_sold > 0 and current_stock <= max(quantity_sold * 0.1, 1):
            return 'low'
        if quantity_sold > 0 and current_stock >= quantity_sold * 2:
            return 'overstock'
        return 'normal'

    @api.model
    def _get_sale_order_line_domain(self, *, date_from=None, date_to=None, warehouse_id=None, category_id=None):
        domain = [
            ('order_id.state', 'in', ['sale', 'done']),
            ('display_type', '=', False),
            ('product_id', '!=', False),
            ('product_id.sale_ok', '=', True),
        ]

        if 'detailed_type' in self.env['product.product']._fields:
            domain.append(('product_id.detailed_type', 'in', ['product', 'consu']))
        elif 'type' in self.env['product.product']._fields:
            domain.append(('product_id.type', 'in', ['product', 'consu']))

        if date_from:
            domain.append(('order_id.date_order', '>=', f"{date_from} 00:00:00"))
        if date_to:
            domain.append(('order_id.date_order', '<=', f"{date_to} 23:59:59"))
        if warehouse_id:
            domain.append(('order_id.warehouse_id', '=', warehouse_id))
        if category_id:
            domain.append(('product_id.categ_id', 'child_of', category_id))

        return domain

    @api.model
    def get_top_products_report_data(self, filters=None):
        normalized_filters = self._normalize_top_products_filters(filters)
        if 'sale.order.line' not in self.env:
            raise ValidationError('El modelo de lineas de venta no esta disponible en esta instancia.')

        order_lines = self.env['sale.order.line'].search(
            self._get_sale_order_line_domain(
                date_from=normalized_filters['dateFrom'],
                date_to=normalized_filters['dateTo'],
            ),
            order='id desc',
        )
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

    @api.model
    def get_products_sales_report_data(self, filters=None):
        normalized_filters = self._normalize_products_sales_filters(filters)
        if 'sale.order.line' not in self.env or 'product.product' not in self.env:
            raise ValidationError('Los modelos requeridos para obtener ventas por producto no estan disponibles.')

        order_lines = self.env['sale.order.line'].search(
            self._get_sale_order_line_domain(
                date_from=normalized_filters['dateFrom'],
                date_to=normalized_filters['dateTo'],
                warehouse_id=normalized_filters['warehouseId'],
                category_id=normalized_filters['categoryId'],
            ),
            order='id desc',
        )
        sale_product_ids = set(order_lines.mapped('product_id').ids)
        stocked_product_ids = set(self._get_stocked_product_ids(
            warehouse_id=normalized_filters['warehouseId'],
            category_id=normalized_filters['categoryId'],
        ))
        product_ids = self._get_sellable_product_ids(
            sale_product_ids | stocked_product_ids,
            category_id=normalized_filters['categoryId'],
        )

        if not product_ids:
            return {
                'generatedAt': self._get_generated_at_iso(),
                'filters': normalized_filters,
                'data': [],
            }

        products = self.env['product.product'].browse(product_ids).exists()
        stock_by_product = self._get_current_stock_by_product(
            product_ids,
            warehouse_id=normalized_filters['warehouseId'],
            category_id=normalized_filters['categoryId'],
        )
        last_sale_date_by_product = self._get_last_sale_date_by_product(
            product_ids,
            warehouse_id=normalized_filters['warehouseId'],
        )

        aggregated_data = {
            product.id: {
                'productId': product.id,
                'productName': product.display_name or '',
                'sku': product.default_code or '',
                'categoryName': product.categ_id.display_name or '',
                'quantitySold': 0.0,
                'salesAmount': 0.0,
                'costAmount': 0.0,
                'marginAmount': 0.0,
                'marginPercent': 0.0,
                'currentStock': round(float(stock_by_product.get(product.id, 0.0)), 2),
                'averageStock': round(float(stock_by_product.get(product.id, 0.0)), 2),
                'inventoryTurnover': 0.0,
                'lastSaleDate': last_sale_date_by_product.get(product.id, ''),
                'movementStatus': 'no_movement',
                'stockStatus': 'normal',
            }
            for product in products
        }

        for line in order_lines:
            product = line.product_id
            if not product or product.id not in aggregated_data:
                continue

            quantity_sold = float(getattr(line, 'qty_delivered', 0.0) or line.product_uom_qty or 0.0)
            sales_amount = float(line.price_subtotal or 0.0)
            unit_cost = float(
                getattr(line, 'purchase_price', 0.0)
                or getattr(product, 'standard_price', 0.0)
                or 0.0
            )
            cost_amount = quantity_sold * unit_cost
            margin_amount = sales_amount - cost_amount

            item = aggregated_data[product.id]
            item['quantitySold'] += quantity_sold
            item['salesAmount'] += sales_amount
            item['costAmount'] += cost_amount
            item['marginAmount'] += margin_amount

        data = []
        for item in aggregated_data.values():
            item['quantitySold'] = round(item['quantitySold'], 2)
            item['salesAmount'] = round(item['salesAmount'], 2)
            item['costAmount'] = round(item['costAmount'], 2)
            item['marginAmount'] = round(item['marginAmount'], 2)
            item['marginPercent'] = round(
                (item['marginAmount'] / item['salesAmount']) * 100,
                2,
            ) if item['salesAmount'] else 0.0
            item['inventoryTurnover'] = round(
                item['quantitySold'] / item['averageStock'],
                2,
            ) if item['averageStock'] > 0 else 0.0
            item['movementStatus'] = self._get_movement_status(item['quantitySold'], item['inventoryTurnover'])
            item['stockStatus'] = self._get_stock_status(item['currentStock'], item['quantitySold'])
            data.append(item)

        data.sort(key=lambda row: (-row['quantitySold'], -row['salesAmount'], row['productName']))

        return {
            'generatedAt': self._get_generated_at_iso(),
            'filters': normalized_filters,
            'data': data,
        }

    @api.model
    def get_sales_trend_report_data(self, filters=None):
        normalized_filters = self._normalize_sales_trend_filters(filters)
        if 'sale.order.line' not in self.env:
            raise ValidationError('El modelo de lineas de venta no esta disponible en esta instancia.')

        order_lines = self.env['sale.order.line'].search(
            self._get_sale_order_line_domain(
                date_from=normalized_filters['dateFrom'],
                date_to=normalized_filters['dateTo'],
                warehouse_id=normalized_filters['warehouseId'],
            ),
            order='id desc',
        )
        grouped_data = {}
        period_summary = self._build_period_summary()
        anchor_date = (
            fields.Date.to_date(normalized_filters['dateTo'])
            if normalized_filters['dateTo']
            else fields.Date.to_date(fields.Date.context_today(self))
        )

        for line in order_lines:
            order_datetime = fields.Datetime.to_datetime(line.order_id.date_order) if line.order_id.date_order else None
            if not order_datetime:
                continue

            sale_date = order_datetime.date()
            bucket = self._get_period_bucket(sale_date, normalized_filters['groupBy'])
            quantity_sold = float(getattr(line, 'qty_delivered', 0.0) or line.product_uom_qty or 0.0)
            sales_amount = float(line.price_subtotal or 0.0)

            item = grouped_data.setdefault(bucket, {
                'date': bucket,
                'quantitySold': 0.0,
                'salesAmount': 0.0,
            })
            item['quantitySold'] += quantity_sold
            item['salesAmount'] += sales_amount

            for label, days in (('last7Days', 7), ('last15Days', 15), ('last30Days', 30)):
                window_start = anchor_date - timedelta(days=days - 1)
                if window_start <= sale_date <= anchor_date:
                    period_summary[label]['quantitySold'] += quantity_sold
                    period_summary[label]['salesAmount'] += sales_amount

        data = []
        for bucket in sorted(grouped_data.keys()):
            row = grouped_data[bucket]
            row['quantitySold'] = round(row['quantitySold'], 2)
            row['salesAmount'] = round(row['salesAmount'], 2)
            data.append(row)

        for summary in period_summary.values():
            summary['quantitySold'] = round(summary['quantitySold'], 2)
            summary['salesAmount'] = round(summary['salesAmount'], 2)

        return {
            'generatedAt': self._get_generated_at_iso(),
            'filters': normalized_filters,
            'data': data,
            'periodSummary': period_summary,
        }

    @api.model
    def get_dead_products_report_data(self, filters=None):
        normalized_filters = self._normalize_dead_products_filters(filters)
        if 'product.product' not in self.env or 'stock.quant' not in self.env:
            raise ValidationError('Los modelos requeridos para obtener productos sin movimiento no estan disponibles.')

        product_ids = self._get_stocked_product_ids(warehouse_id=normalized_filters['warehouseId'])
        if not product_ids:
            return {
                'generatedAt': self._get_generated_at_iso(),
                'filters': normalized_filters,
                'data': [],
            }

        products = self.env['product.product'].browse(product_ids).exists()
        stock_by_product = self._get_current_stock_by_product(
            product_ids,
            warehouse_id=normalized_filters['warehouseId'],
        )
        last_sale_date_by_product = self._get_last_sale_date_by_product(
            product_ids,
            warehouse_id=normalized_filters['warehouseId'],
        )
        anchor_date = fields.Date.to_date(fields.Date.context_today(self))

        data = []
        for product in products:
            current_stock = round(float(stock_by_product.get(product.id, 0.0)), 2)
            if current_stock <= 0:
                continue

            last_sale_date = last_sale_date_by_product.get(product.id, '')
            if last_sale_date:
                reference_date = fields.Date.to_date(last_sale_date)
            else:
                created_at = fields.Datetime.to_datetime(product.create_date) if product.create_date else None
                reference_date = created_at.date() if created_at else None

            days_without_movement = (
                max((anchor_date - reference_date).days, 0)
                if reference_date
                else normalized_filters['daysWithoutMovement']
            )

            if days_without_movement < normalized_filters['daysWithoutMovement']:
                continue

            data.append({
                'productId': product.id,
                'productName': product.display_name or '',
                'sku': product.default_code or '',
                'categoryName': product.categ_id.display_name or '',
                'currentStock': current_stock,
                'lastSaleDate': last_sale_date,
                'daysWithoutMovement': days_without_movement,
                'movementStatus': 'no_movement',
            })

        data.sort(key=lambda row: (-row['daysWithoutMovement'], -row['currentStock'], row['productName']))

        return {
            'generatedAt': self._get_generated_at_iso(),
            'filters': normalized_filters,
            'data': data,
        }

    @api.model
    def get_high_rotation_products_report_data(self, filters=None):
        normalized_filters = self._normalize_high_rotation_filters(filters)
        products_sales_report = self.get_products_sales_report_data(normalized_filters)

        if normalized_filters['dateFrom'] and normalized_filters['dateTo']:
            period_days = max(
                (fields.Date.to_date(normalized_filters['dateTo']) - fields.Date.to_date(normalized_filters['dateFrom'])).days + 1,
                1,
            )
        else:
            period_days = 30

        data = []
        for item in products_sales_report.get('data', []):
            if item.get('movementStatus') != 'high_rotation':
                continue

            quantity_sold = float(item.get('quantitySold', 0.0) or 0.0)
            current_stock = float(item.get('currentStock', 0.0) or 0.0)
            average_stock = float(item.get('averageStock', current_stock) or 0.0)
            inventory_turnover = float(item.get('inventoryTurnover', 0.0) or 0.0)
            average_daily_sales = quantity_sold / period_days if period_days > 0 else 0.0
            days_of_coverage = int(round(current_stock / average_daily_sales)) if average_daily_sales > 0 else 0

            data.append({
                'productId': item.get('productId'),
                'productName': item.get('productName', ''),
                'sku': item.get('sku', ''),
                'quantitySold': round(quantity_sold, 2),
                'currentStock': round(current_stock, 2),
                'averageStock': round(average_stock, 2),
                'inventoryTurnover': round(inventory_turnover, 2),
                'daysOfCoverage': max(days_of_coverage, 0),
                'movementStatus': 'high_rotation',
            })

        data.sort(key=lambda row: (-row['inventoryTurnover'], -row['quantitySold'], row['productName']))

        return {
            'generatedAt': self._get_generated_at_iso(),
            'filters': normalized_filters,
            'data': data[:normalized_filters['limit']],
        }

    @api.model
    def get_weekly_production_plan_report_data(self, filters=None):
        filters = filters or {}
        normalized_filters = self._normalize_weekly_plan_filters(filters)
        wizard_filters = dict(filters)

        if normalized_filters.get('dateFrom'):
            wizard_filters['dateFrom'] = normalized_filters['dateFrom']
            wizard_filters['fecha_entrega_desde'] = normalized_filters['dateFrom']
        if normalized_filters.get('dateTo'):
            wizard_filters['dateTo'] = normalized_filters['dateTo']
            wizard_filters['fecha_entrega_hasta'] = normalized_filters['dateTo']

        rows = self.env['advanced_metrics.report.wizard'].sudo().get_sales_orders_report_rows(wizard_filters)
        return {
            'generatedAt': self._get_generated_at_iso(),
            'filters': wizard_filters,
            'data': rows,
        }
