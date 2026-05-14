# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.exceptions import UserError


class ZrnProdigynNavigationMixin:
    def _open_singleton_action(self, action_xmlid):
        self.ensure_one()
        action = self.env.ref(action_xmlid, raise_if_not_found=False)
        if not action:
            raise UserError('No se encontro la accion configurada para esta pantalla.')
        action_data = action.read()[0]
        action_data['_noBreadcrumbs'] = True
        return action_data

    def action_open_home(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_inicio')

    def action_open_button_1(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_production_planning')

    def action_open_button_2(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_purchase_planning')

    def action_open_button_3(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_delivery_planning')

    def action_open_button_4(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_internal_tool_4')

    def action_open_button_5(self):
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_internal_tool_5')

    def action_open_support(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'name': 'Open Support',
            'url': 'https://adm.zoraen.com/support?tkn=cualquier_cosa_por_ahora',
            'target': 'new',
        }

    def action_open_prodigyn_go(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'name': 'Prodigyn Go',
            'url': 'https://prodigyn.zoraen.com/go?tkn=cualquier_cosa_por_ahora',
            'target': 'new',
        }


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

    def action_open_sale_order_filters(self):
        self.ensure_one()
        wizard = self.env['zrn_prodigyn.production.planning.wizard'].create({})
        return wizard.action_open_filters()


class ZrnProdigynPurchasePlanning(ZrnProdigynNavigationMixin, models.Model):
    _name = 'zrn_prodigyn.purchase.planning'
    _description = 'Planeacion de insumos y compras'

    name = fields.Char(string='Nombre', required=True, default='Planeacion de Insumos / Compras')


class ZrnProdigynDeliveryPlanning(ZrnProdigynNavigationMixin, models.Model):
    _name = 'zrn_prodigyn.delivery.planning'
    _description = 'Planeacion de entregas'

    name = fields.Char(string='Nombre', required=True, default='Planeacion de Entregas')


class ZrnProdigynInternalTool(ZrnProdigynNavigationMixin, models.Model):
    _name = 'zrn_prodigyn.internal.tool'
    _description = 'Herramienta interna de Prodigyn'

    name = fields.Char(string='Nombre', required=True)
