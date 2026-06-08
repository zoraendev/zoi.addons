# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.exceptions import UserError


class ZrnPlanningNavigationMixin:
    def _open_singleton_action(self, action_xmlid):
        self.ensure_one()
        action = self.env.ref(action_xmlid, raise_if_not_found=False)
        if not action:
            raise UserError('No se encontro la accion configurada para esta pantalla.')
        action_data = action.read()[0]
        action_data['target'] = 'main'
        return action_data

    def action_open_home(self):
        return self._open_singleton_action('zrn_planning.action_zrn_planning_home')

    def action_open_button_1(self):
        return self._open_singleton_action('zrn_planning.action_zrn_planning_home')

    def action_open_button_2(self):
        return self._open_singleton_action('zrn_planning.action_zrn_planning_home')

    def action_open_button_3(self):
        return self._open_singleton_action('zrn_planning.action_zrn_planning_home')

    def action_open_button_4(self):
        return self._open_singleton_action('zrn_planning.action_zrn_planning_home')

    def action_open_button_5(self):
        return self._open_singleton_action('zrn_planning.action_zrn_planning_delivery_planning')


class ZrnPlanningHome(ZrnPlanningNavigationMixin, models.Model):
    _name = 'zrn_planning.home'
    _description = 'Centro principal de Zoraen Planning'
    _order = 'sequence, id'

    name = fields.Char(string='Nombre', required=True, default='Zoraen Planning')
    sequence = fields.Integer(string='Secuencia', default=10)
    page_key = fields.Selection(
        [
            ('overview', 'Resumen'),
        ],
        string='Pagina',
        required=True,
        default='overview',
    )

    def action_open_production_planning(self):
        self.ensure_one()
        wizard = self.env['zrn_planning.production.planning.wizard'].create({})
        return wizard.action_open_filters()

    def action_open_supply_planning(self):
        self.ensure_one()
        wizard = self.env['zrn_planning.purchase.planning.wizard'].create({})
        return wizard.action_open_filters()

    def action_open_logistics_planning(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_planning.action_zrn_planning_delivery_planning')


class ZrnPlanningProductionPlanning(ZrnPlanningNavigationMixin, models.Model):
    _name = 'zrn_planning.production.planning'
    _description = 'Planeacion de produccion y fabricacion'
    _order = 'sequence, id'

    name = fields.Char(string='Nombre', required=True, default='Planeacion de produccion/fabricacion')
    sequence = fields.Integer(string='Secuencia', default=10)
    page_key = fields.Selection(
        [
            ('overview', 'Resumen'),
            ('workspace', 'Workspace'),
        ],
        string='Pagina',
        required=True,
        default='overview',
    )

    def action_open_sale_order_filters(self):
        self.ensure_one()
        wizard = self.env['zrn_planning.production.planning.wizard'].create({})
        return wizard.action_open_filters()

    def action_open_supply_filters(self):
        self.ensure_one()
        wizard = self.env['zrn_planning.purchase.planning.wizard'].create({})
        return wizard.action_open_filters()


class ZrnPlanningPurchasePlanning(ZrnPlanningNavigationMixin, models.Model):
    _name = 'zrn_planning.purchase.planning'
    _description = 'Planeacion de insumos y compras'

    name = fields.Char(string='Nombre', required=True, default='Planeacion de Abastecimiento')


class ZrnPlanningDeliveryPlanning(ZrnPlanningNavigationMixin, models.Model):
    _name = 'zrn_planning.delivery.planning'
    _description = 'Planeacion de entregas'

    name = fields.Char(string='Nombre', required=True, default='Planeacion Logistica')
