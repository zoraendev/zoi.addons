# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError


class ZrnCommercialNavigationMixin:
    """
    Mixin para proveer métodos comunes de navegación y redirección
    a pantallas únicas del módulo comercial de Zoraen.
    
    Permite abrir vistas de formulario en modo "singleton" de forma directa
    sin abrir popups innecesarios al forzar el target en 'main'.
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
    Consolida las métricas clave y las listas de registros recientes para el layout.
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
    
    # Métricas superiores de Quickstats (Conteo global)
    brand_count = fields.Integer(compute='_compute_dashboard_counts')
    channel_count = fields.Integer(compute='_compute_dashboard_counts')
    product_channel_count = fields.Integer(compute='_compute_dashboard_counts')
    prospect_count = fields.Integer(compute='_compute_dashboard_counts')
    opportunity_count = fields.Integer(compute='_compute_dashboard_counts')
    quotation_count = fields.Integer(compute='_compute_dashboard_counts')
    overdue_count = fields.Integer(compute='_compute_dashboard_counts')

    # Relaciones y contadores para los 4 paneles principales del dashboard
    # Limitados a los 7 registros más recientes
    recent_prospect_ids = fields.Many2many(
        'crm.lead',
        relation='zrn_commercial_home_prospect_rel',
        column1='home_id',
        column2='lead_id',
        string='Ultimos prospectos',
        compute='_compute_home_panels',
        readonly=True,
    )
    recent_prospect_count = fields.Integer(
        string='Prospectos recientes',
        compute='_compute_home_panels',
        readonly=True,
    )
    recent_opportunity_ids = fields.Many2many(
        'crm.lead',
        relation='zrn_commercial_home_opportunity_rel',
        column1='home_id',
        column2='lead_id',
        string='Ultimas oportunidades',
        compute='_compute_home_panels',
        readonly=True,
    )
    recent_opportunity_count = fields.Integer(
        string='Oportunidades recientes',
        compute='_compute_home_panels',
        readonly=True,
    )
    recent_brand_ids = fields.Many2many(
        'zrn_commercial.commercial.brand',
        relation='zrn_commercial_home_brand_rel',
        column1='home_id',
        column2='brand_id',
        string='Marcas activas',
        compute='_compute_home_panels',
        readonly=True,
    )
    recent_brand_count = fields.Integer(
        string='Marcas recientes',
        compute='_compute_home_panels',
        readonly=True,
    )
    recent_channel_ids = fields.Many2many(
        'zrn_commercial.commercial.channel',
        relation='zrn_commercial_home_channel_rel',
        column1='home_id',
        column2='channel_id',
        string='Canales activos',
        compute='_compute_home_panels',
        readonly=True,
    )
    recent_channel_count = fields.Integer(
        string='Canales recientes',
        compute='_compute_home_panels',
        readonly=True,
    )

    def _compute_dashboard_counts(self):
        """
        Calcula contadores globales de marcas, canales, prospectos, oportunidades
        y cotizaciones para mostrarlos en la barra superior de métricas del dashboard.
        """
        brand_model = self.env['zrn_commercial.commercial.brand'].sudo()
        channel_model = self.env['zrn_commercial.commercial.channel'].sudo()
        product_channel_model = self.env['zrn_commercial.product.channel'].sudo()
        lead_model = self.env['crm.lead'].sudo()
        order_model = self.env['sale.order'].sudo()
        today = fields.Date.today()
        for record in self:
            record.brand_count = brand_model.search_count([('active', '=', True)])
            record.channel_count = channel_model.search_count([('active', '=', True)])
            record.product_channel_count = product_channel_model.search_count([('active', '=', True)])
            record.prospect_count = lead_model.search_count([('type', '=', 'lead'), ('active', '=', True)])
            record.opportunity_count = lead_model.search_count([('type', '=', 'opportunity'), ('active', '=', True)])
            record.quotation_count = order_model.search_count([('state', 'in', ['draft', 'sent'])])
            record.overdue_count = lead_model.search_count([
                ('type', '=', 'opportunity'),
                ('activity_date_deadline', '<', today),
                ('active', '=', True),
            ])

    # Métricas de redirección a las vistas principales (Lista/Kanban)
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

    def action_open_product_channels(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_commercial.action_zrn_commercial_product_channels')

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

    @api.depends_context('company')
    def _compute_home_panels(self):
        """
        Carga los 7 registros más recientes para cada una de las 4 secciones principales.
        Esto permite mostrar una previsualización rápida en formato tabla en el dashboard.
        """
        lead_model = self.env['crm.lead'].sudo()
        brand_model = self.env['zrn_commercial.commercial.brand'].sudo()
        channel_model = self.env['zrn_commercial.commercial.channel'].sudo()
        
        # Consultas de registros ordenando por fecha de creación desc
        prospects = lead_model.search(
            [('type', '=', 'lead'), ('active', '=', True)],
            order='create_date desc, id desc',
            limit=7,
        )
        opportunities = lead_model.search(
            [('type', '=', 'opportunity'), ('active', '=', True)],
            order='create_date desc, id desc',
            limit=7,
        )
        brands = brand_model.search(
            [('active', '=', True)],
            order='name',
            limit=7,
        )
        channels = channel_model.search(
            [('active', '=', True)],
            order='name',
            limit=7,
        )
        
        for record in self:
            record.recent_prospect_ids = prospects
            record.recent_prospect_count = len(prospects)
            record.recent_opportunity_ids = opportunities
            record.recent_opportunity_count = len(opportunities)
            record.recent_brand_ids = brands
            record.recent_brand_count = len(brands)
            record.recent_channel_ids = channels
            record.recent_channel_count = len(channels)

    def get_home_chart_payload(self):
        """
        Construye el payload de datos JSON para alimentar las gráficas ECharts.
        Retorna la información formateada y agrupada para los 4 paneles principales:
        
        - prospects: Agrupado por Etapa del Lead
        - opportunities: Agrupado por Etapa de Oportunidad
        - brands: Comparativa multiserie (Oportunidades vs Cotizaciones) por marca
        - channels: Comparativa multiserie (Oportunidades vs Clientes) por canal
        """
        self.ensure_one()
        lead_model = self.env['crm.lead'].sudo()
        brand_model = self.env['zrn_commercial.commercial.brand'].sudo()
        channel_model = self.env['zrn_commercial.commercial.channel'].sudo()
        
        # Agrupación de Prospectos
        prospect_groups = lead_model.read_group(
            [('type', '=', 'lead'), ('active', '=', True)],
            ['stage_id'],
            ['stage_id'],
        )
        # Agrupación de Oportunidades
        opportunity_groups = lead_model.read_group(
            [('type', '=', 'opportunity'), ('active', '=', True)],
            ['stage_id'],
            ['stage_id'],
        )
        
        # Obtener primeras 10 marcas y canales para las gráficas comparativas
        brands = brand_model.search([('active', '=', True)], order='name', limit=10)
        channels = channel_model.search([('active', '=', True)], order='name', limit=10)
        
        return {
            'prospects': {
                'labels': [
                    g['stage_id'][1] if g['stage_id'] else 'Sin etapa'
                    for g in prospect_groups
                ],
                'values': [g['stage_id_count'] for g in prospect_groups],
                'series_label': 'Prospectos',
            },
            'opportunities': {
                'labels': [
                    g['stage_id'][1] if g['stage_id'] else 'Sin etapa'
                    for g in opportunity_groups
                ],
                'values': [g['stage_id_count'] for g in opportunity_groups],
                'series_label': 'Oportunidades',
            },
            'brands': {
                'labels': brands.mapped('name'),
                'series': [
                    {'name': 'Oportunidades', 'data': [b.opportunity_count for b in brands]},
                    {'name': 'Cotizaciones', 'data': [b.quotation_count for b in brands]},
                ],
            },
            'channels': {
                'labels': channels.mapped('name'),
                'series': [
                    {'name': 'Oportunidades', 'data': [c.opportunity_count for c in channels]},
                    {'name': 'Clientes', 'data': [c.partner_count for c in channels]},
                ],
            },
        }


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
