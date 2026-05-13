# -*- coding: utf-8 -*-

from odoo import fields, models


class ZrnProdigynInicio(models.Model):
    _name = 'zrn_prodigyn.inicio'
    _description = 'Pantalla principal de Prodigyn'

    name = fields.Char(string='Nombre', required=True, default='Prodigyn')
