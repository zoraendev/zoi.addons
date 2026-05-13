# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.exceptions import UserError


class ZrnProdigynNavigationMixin:
    def _open_singleton_action(self, action_xmlid):
        self.ensure_one()
        action = self.env.ref(action_xmlid, raise_if_not_found=False)
        if not action:
            raise UserError('No se encontro la accion configurada para esta pantalla.')
        return action.read()[0]

    def action_open_home(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_inicio')


class ZrnProdigynInicio(ZrnProdigynNavigationMixin, models.Model):
    _name = 'zrn_prodigyn.inicio'
    _description = 'Pantalla principal de Prodigyn'

    name = fields.Char(string='Nombre', required=True, default='Prodigyn')

    def action_open_production_planning(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_production_planning')

    def action_open_purchase_planning(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_purchase_planning')

    def action_open_delivery_planning(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_delivery_planning')


class ZrnProdigynProductionPlanning(ZrnProdigynNavigationMixin, models.Model):
    _name = 'zrn_prodigyn.production.planning'
    _description = 'Planeacion de produccion y fabricacion'

    name = fields.Char(string='Nombre', required=True, default='Planeacion de produccion/fabricacion')


class ZrnProdigynPurchasePlanning(ZrnProdigynNavigationMixin, models.Model):
    _name = 'zrn_prodigyn.purchase.planning'
    _description = 'Planeacion de insumos y compras'

    name = fields.Char(string='Nombre', required=True, default='Planeacion de Insumos / Compras')


class ZrnProdigynDeliveryPlanning(ZrnProdigynNavigationMixin, models.Model):
    _name = 'zrn_prodigyn.delivery.planning'
    _description = 'Planeacion de entregas'

    name = fields.Char(string='Nombre', required=True, default='Planeacion de Entregas')
