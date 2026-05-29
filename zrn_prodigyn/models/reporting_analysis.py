# -*- coding: utf-8 -*-

from odoo import fields, models

from .models import ZrnProdigynNavigationMixin


class ZrnProdigynReportingAnalysis(ZrnProdigynNavigationMixin, models.Model):
    _name = 'zrn_prodigyn.reporting.analysis'
    _description = 'Centro de reporteria y analisis'
    _order = 'sequence, id'

    name = fields.Char(string='Nombre', required=True, default='Reporteria y Analisis')
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

    def action_open_reporting_overview(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_reporting_analysis')

    def action_open_reporting_workspace(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_reporting_analysis_workspace')

    def action_open_reporting_executive(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_reporting_executive')

    def action_open_reporting_commercial(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_reporting_commercial')

    def action_open_reporting_channels(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_reporting_channels')

    def action_open_reporting_customers(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_reporting_customers')

    def action_open_reporting_skus(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_reporting_skus')

    def action_open_reporting_financial(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_reporting_financial')

    def action_open_reporting_margin(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_reporting_margin')

    def action_open_reporting_receivables(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_reporting_receivables')

    def action_open_reporting_operations(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_reporting_operations')

    def action_open_reporting_forecast(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_reporting_forecast')

    def action_open_reporting_stockouts(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_reporting_stockouts')

    def action_open_reporting_coverage(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_reporting_coverage')

    def action_open_reporting_velocity(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_reporting_velocity')

    def action_open_reporting_rrhh(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_reporting_rrhh')

    def action_open_reporting_media(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_reporting_media')

    def action_open_reporting_scenarios(self):
        self.ensure_one()
        return self._open_singleton_action('zrn_prodigyn.action_zrn_prodigyn_reporting_scenarios')
