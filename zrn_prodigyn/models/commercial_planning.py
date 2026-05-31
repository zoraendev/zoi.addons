# -*- coding: utf-8 -*-

from odoo import fields, models

from .models import ZrnProdigynNavigationMixin


class ZrnProdigynCommercialPlanning(ZrnProdigynNavigationMixin, models.Model):
    _name = 'zrn_prodigyn.commercial.planning'
    _description = 'Centro de planeacion comercial'
    _order = 'sequence, id'

    name = fields.Char(string='Nombre', required=True, default='Planeacion Comercial')
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

    def action_open_commercial_overview(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_commercial_planning')

    def action_open_commercial_workspace(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_commercial_planning_workspace')

    def action_open_commercial_brands(self):
        self.ensure_one()
        action = self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_commercial_brands')
        action.pop('res_id', None)
        action.pop('res_ids', None)
        action_context = dict(self.env.context)
        action_context.pop('active_id', None)
        action_context.pop('active_ids', None)
        action_context.pop('active_model', None)
        action['context'] = action_context
        return action

    def action_open_commercial_portfolio(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_commercial_portfolio')

    def action_open_commercial_customers(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_commercial_customers')

    def action_open_commercial_channels(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_commercial_channels')

    def action_open_commercial_campaigns(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_commercial_campaigns')

    def action_open_commercial_pricing(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_commercial_pricing')

    def action_open_commercial_targets(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_commercial_targets')

    def action_open_commercial_calendar(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_commercial_calendar')
