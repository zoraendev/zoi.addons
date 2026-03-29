from odoo import fields, models


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
