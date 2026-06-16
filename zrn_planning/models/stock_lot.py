# -*- coding: utf-8 -*-

from odoo import api, fields, models


class StockLot(models.Model):
    _inherit = 'stock.lot'

    active = fields.Boolean(default=True)
    zrn_location_names = fields.Char(string='Ubicaciones internas', compute='_compute_zrn_location_names')
    zrn_oldest_in_date = fields.Datetime(string='Primera entrada', compute='_compute_zrn_oldest_in_date', store=True)

    @api.depends('quant_ids.quantity', 'quant_ids.in_date', 'quant_ids.location_id')
    def _compute_zrn_location_names(self):
        for lot in self:
            internal_quants = lot.quant_ids.filtered(
                lambda quant: quant.quantity > 0 and (
                    quant.location_id.usage == 'internal' or (
                        quant.location_id.usage == 'transit' and quant.location_id.company_id
                    )
                )
            )
            location_names = internal_quants.mapped('location_id.complete_name')
            lot.zrn_location_names = ', '.join(sorted(set(location_names))) if location_names else False

    @api.depends('quant_ids.quantity', 'quant_ids.in_date', 'quant_ids.location_id')
    def _compute_zrn_oldest_in_date(self):
        for lot in self:
            internal_quants = lot.quant_ids.filtered(
                lambda quant: quant.quantity > 0 and (
                    quant.location_id.usage == 'internal' or (
                        quant.location_id.usage == 'transit' and quant.location_id.company_id
                    )
                )
            )
            incoming_dates = [quant.in_date for quant in internal_quants if quant.in_date]
            lot.zrn_oldest_in_date = min(incoming_dates) if incoming_dates else False
