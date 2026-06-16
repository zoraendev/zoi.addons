# -*- coding: utf-8 -*-

from odoo import models
from odoo.osv import expression


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def _get_gather_domain(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False):
        domain = super()._get_gather_domain(
            product_id,
            location_id,
            lot_id=lot_id,
            package_id=package_id,
            owner_id=owner_id,
            strict=strict,
        )
        if not lot_id:
            domain = expression.AND([domain, ['|', ('lot_id', '=', False), ('lot_id.active', '=', True)]])
        return domain
