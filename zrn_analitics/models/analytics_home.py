# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.exceptions import UserError


class ZrnAnalyticsNavigationMixin:
    def _open_singleton_action(self, action_xmlid):
        self.ensure_one()
        action = self.env.ref(action_xmlid, raise_if_not_found=False)
        if not action:
            raise UserError('No se encontro la accion configurada para esta pantalla.')
        action_data = action.read()[0]
        action_data['target'] = 'main'
        return action_data

    def action_open_home(self):
        return self._open_singleton_action('zrn_analitics.action_zrn_analitics_home')

    def action_open_workspace(self):
        return self._open_singleton_action('zrn_analitics.action_zrn_analitics_workspace')

    def action_open_scenarios(self):
        return self._open_singleton_action('zrn_analitics.action_zrn_analitics_scenarios')

    def action_open_hubs_client(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'name': 'Hubs',
            'tag': 'zrn_analitics.hubs',
            'target': 'main',
        }

    def action_open_button_1(self):
        return self.action_open_home()

    def action_open_button_2(self):
        return self.action_open_workspace()

    def action_open_button_3(self):
        return self.action_open_scenarios()

    def action_open_button_4(self):
        return self.action_open_workspace()

    def action_open_button_5(self):
        return self.action_open_workspace()


class ZrnAnalyticsHome(ZrnAnalyticsNavigationMixin, models.Model):
    _name = 'zrn_analitics.home'
    _description = 'Centro principal de Zoraen Analytics'
    _order = 'sequence, id'

    name = fields.Char(string='Nombre', required=True, default='Zoraen Analytics')
    sequence = fields.Integer(string='Secuencia', default=10)
    page_key = fields.Selection(
        [
            ('overview', 'Resumen'),
            ('workspace', 'Workspace'),
            ('scenarios', 'Escenarios'),
        ],
        string='Pagina',
        required=True,
        default='overview',
    )

    def action_open_hubs(self):
        self.ensure_one()
        return self.action_open_hubs_client()

    def action_open_dashboards(self):
        self.ensure_one()
        return self.action_open_workspace()

    def action_open_processing(self):
        self.ensure_one()
        return self.action_open_workspace()

    def action_open_scenarios(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_analitics.action_zrn_analitics_scenarios')
