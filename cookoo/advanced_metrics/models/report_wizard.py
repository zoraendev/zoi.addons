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
    report_line_ids = fields.One2many(
        'advanced_metrics.report.wizard.line',
        'wizard_id',
        string='Lineas de reporte',
    )

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
