from odoo import api, fields, models


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
    def get_sales_orders_report_rows(self, filters=None, limit=500):
        filters = filters or {}
        sale_line_model = self.env.get('sale.order.line')
        stock_quant_model = self.env.get('stock.quant')
        if not sale_line_model or not stock_quant_model:
            return []

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

        order_lines = sale_line_model.search(domain, order='order_id.commitment_date desc, id desc', limit=limit)
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
