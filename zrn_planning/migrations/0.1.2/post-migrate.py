# -*- coding: utf-8 -*-

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    lines = env['zrn_planning.mfg.plan.line'].search([
        ('plan_id.planning_basis', '!=', 'mixed'),
    ])
    lines._sync_supplies_from_bom()
