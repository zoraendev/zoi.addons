# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.exceptions import UserError


class ZrnCommercialNavigationMixin:
    """
    Mixin para proveer métodos comunes de navegación y redirección
    a pantallas únicas del módulo comercial de Zoraen.
    """
    def _open_singleton_action(self, action_xmlid):
        self.ensure_one()
        action = self.env.ref(action_xmlid, raise_if_not_found=False)
        if not action:
            raise UserError('No se encontro la accion configurada para esta pantalla.')
        action_data = action.read()[0]
        # target='main' para recargar la pantalla principal y evitar popups
        action_data['target'] = 'main'
        return action_data

    def action_open_home(self):
        """
        Redirige al usuario al inicio de Zoraen Commercial.
        """
        return self._open_singleton_action('zrn_commercial.action_zrn_commercial_home')


class ZrnCommercialHome(ZrnCommercialNavigationMixin, models.Model):
    """
    Modelo del Dashboard o Inicio de Zoraen Commercial.
    Provee el punto de entrada principal del módulo comercial.
    """
    _name = 'zrn_commercial.home'
    _description = 'Centro principal de Zoraen Commercial'
    _order = 'sequence, id'

    name = fields.Char(string='Nombre', required=True, default='Zoraen Commercial')
    sequence = fields.Integer(string='Secuencia', default=10)
    page_key = fields.Selection(
        [
            ('overview', 'Resumen'),
        ],
        string='Pagina',
        required=True,
        default='overview',
    )
    brand_count = fields.Integer(compute='_compute_dashboard_counts')
    channel_count = fields.Integer(compute='_compute_dashboard_counts')
    prospect_count = fields.Integer(compute='_compute_dashboard_counts')
    opportunity_count = fields.Integer(compute='_compute_dashboard_counts')
    quotation_count = fields.Integer(compute='_compute_dashboard_counts')
    overdue_count = fields.Integer(compute='_compute_dashboard_counts')

    def _compute_dashboard_counts(self):
        brand_model = self.env['zrn_commercial.commercial.brand'].sudo()
        channel_model = self.env['zrn_commercial.commercial.channel'].sudo()
        lead_model = self.env['crm.lead'].sudo()
        order_model = self.env['sale.order'].sudo()
        today = fields.Date.today()
        for record in self:
            record.brand_count = brand_model.search_count([('active', '=', True)])
            record.channel_count = channel_model.search_count([('active', '=', True)])
            record.prospect_count = lead_model.search_count([('type', '=', 'lead'), ('active', '=', True)])
            record.opportunity_count = lead_model.search_count([('type', '=', 'opportunity'), ('active', '=', True)])
            record.quotation_count = order_model.search_count([('state', 'in', ['draft', 'sent'])])
            record.overdue_count = lead_model.search_count([
                ('type', '=', 'opportunity'),
                ('activity_date_deadline', '<', today),
                ('active', '=', True),
            ])

    def action_open_brands(self):
        """
        Abre la vista de listado de marcas comerciales.
        """
        self.ensure_one()
        return self._open_singleton_action('zrn_commercial.action_zrn_commercial_brands')

    def action_open_channels(self):
        """
        Abre la vista de listado de canales comerciales.
        """
        self.ensure_one()
        return self._open_singleton_action('zrn_commercial.action_zrn_commercial_channels')

    def action_open_portfolio(self):
        """
        Abre la vista de portafolio comercial (marcador de posición).
        """
        self.ensure_one()
        return self._open_singleton_action('zrn_commercial.action_zrn_commercial_portfolio')

    def action_open_pricing(self):
        """
        Abre la vista de pricing comercial (marcador de posición).
        """
        self.ensure_one()
        return self._open_singleton_action('zrn_commercial.action_zrn_commercial_pricing')

    def action_open_prospects(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_commercial.action_zrn_commercial_prospects')

    def action_open_opportunities(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_commercial.action_zrn_commercial_opportunities')

    def action_open_customers(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_commercial.action_zrn_commercial_customers')

    def action_open_quotations(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_commercial.action_zrn_commercial_quotations')

    def action_open_reports(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_commercial.action_zrn_commercial_reports_pipeline')


class ZrnCommercialPortfolio(ZrnCommercialNavigationMixin, models.Model):
    """
    Modelo de marcador de posición para el workspace de Portafolio.
    """
    _name = 'zrn_commercial.portfolio'
    _description = 'Workspace del Portafolio Comercial'

    name = fields.Char(string='Nombre', required=True, default='Portafolio Comercial')


class ZrnCommercialPricing(ZrnCommercialNavigationMixin, models.Model):
    """
    Modelo de marcador de posición para el workspace de Pricing.
    """
    _name = 'zrn_commercial.pricing'
    _description = 'Workspace de Pricing Comercial'

    name = fields.Char(string='Nombre', required=True, default='Pricing Comercial')
