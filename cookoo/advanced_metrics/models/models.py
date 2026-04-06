from odoo import _, fields, models


class AdvancedMetricsInicio(models.Model):
    _name = 'advanced_metrics.inicio'
    _description = 'Pantalla principal de Advanced Metrics'

    name = fields.Char(string='Nombre', required=True)
    show_dashboard = fields.Boolean(string='Mostrar dashboard', default=True)
    client_validation_state = fields.Selection(
        [
            ('ok', 'Activo'),
            ('payment_due', 'Pago pendiente'),
            ('inactive', 'Inactivo'),
            ('error', 'Error'),
        ],
        string='Estado de validacion del cliente',
        default='ok',
    )
    client_status_code = fields.Char(string='Codigo de estado del cliente')
    support_url = fields.Char(string='URL de soporte', default='https://www.zoraen.com')
    client_status_title = fields.Char(
        string='Titulo de estado del cliente',
        default='Metricas disponibles',
    )
    client_status_message = fields.Text(
        string='Mensaje de estado del cliente',
        default='La instancia esta lista para consultar los reportes y endpoints de BI.',
    )

    def action_request_support(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': self.support_url or 'https://www.zoraen.com',
            'target': 'new',
        }

    def action_open_sales_report(self):
        self.ensure_one()
        return self.env.ref('advanced_metrics.action_advanced_metrics_report_wizard').read()[0]

    def action_open_api_config(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Advanced Metrics'),
                'message': _('La configuracion de credenciales Power BI se habilitara en un siguiente paso.'),
                'type': 'info',
                'sticky': False,
            },
        }


class AdvancedMetricsRegistro(models.Model):
    _name = 'advanced_metrics.registro'
    _description = 'Registro de Advanced Metrics'

    name = fields.Char(string='Nombre', required=True)
    descripcion = fields.Text(string='Descripción')