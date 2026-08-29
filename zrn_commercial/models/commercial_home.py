# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.exceptions import UserError


class ZrnCommercialNavigationMixin:
    def _open_singleton_action(self, action_xmlid):
        self.ensure_one()
        action = self.env.ref(action_xmlid, raise_if_not_found=False)
        if not action:
            raise UserError('No se encontro la accion configurada para esta pantalla.')
        action_data = action.read()[0]
        action_data['target'] = 'main'
        return action_data

    def action_open_home(self):
        return self._open_singleton_action('zrn_commercial.action_zrn_commercial_home')


class ZrnCommercialHome(ZrnCommercialNavigationMixin, models.Model):
    _name = 'zrn_commercial.home'
    _description = 'Inicio de Zoraen Commercial'
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
        return self._open_singleton_action('zrn_commercial.action_zrn_commercial_brands')

    def action_open_channels(self):
        return self._open_singleton_action('zrn_commercial.action_zrn_commercial_channels')
