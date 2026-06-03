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

    def action_open_brands(self):
        """
        Abre la vista de listado de marcas comerciales.
        """
        self.ensure_one()
        return self._open_singleton_action('zrn_commercial.action_zrn_commercial_brands')

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
