# -*- coding: utf-8 -*-

import re
import uuid

from odoo import api, fields, models

from ..application.customers.services import CustomerProfileService


class ResPartner(models.Model):
    _inherit = 'res.partner'

    automation_customer_uid = fields.Char(
        string='Automation Customer UID',
        copy=False,
        readonly=True,
        default=lambda self: str(uuid.uuid4()),
        index=True,
        help='Identificador estable que permite al bot reconocer al cliente.',
    )
    automation_customer_alias = fields.Char(
        string='Automation Customer Alias',
        help='Alias opcional para mejorar el reconocimiento del cliente por automatizaciones.',
    )
    automation_customer_fingerprint = fields.Char(
        string='Automation Customer Fingerprint',
        compute='_compute_automation_customer_fingerprint',
        store=True,
        index=True,
        help='Huella de busqueda normalizada usada para reconocimiento automatizado.',
    )
    automation_phone_normalized = fields.Char(
        string='Automation Phone Normalized',
        compute='_compute_automation_contact_normalized',
        store=True,
        index=True,
        help='Telefono normalizado para consultas automatizadas.',
    )
    automation_mobile_normalized = fields.Char(
        string='Automation Mobile Normalized',
        compute='_compute_automation_contact_normalized',
        store=True,
        index=True,
        help='Movil normalizado para consultas automatizadas.',
    )
    automation_email_normalized = fields.Char(
        string='Automation Email Normalized',
        compute='_compute_automation_contact_normalized',
        store=True,
        index=True,
        help='Correo normalizado para consultas automatizadas.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if not values.get('automation_customer_uid'):
                values['automation_customer_uid'] = str(uuid.uuid4())
        return super().create(vals_list)

    @api.depends(
        'name',
        'display_name',
        'email',
        'phone',
        'mobile',
        'vat',
        'ref',
        'lang',
        'active',
        'automation_customer_uid',
        'automation_customer_alias',
        'commercial_partner_id.name',
        'commercial_partner_id.vat',
        'commercial_partner_id.ref',
    )
    def _compute_automation_customer_fingerprint(self):
        service = CustomerProfileService(self.env)
        for partner in self:
            partner.automation_customer_fingerprint = service.build_fingerprint_value(partner)

    @api.depends('phone', 'mobile', 'email')
    def _compute_automation_contact_normalized(self):
        for partner in self:
            partner.automation_phone_normalized = self._normalize_phone_value(partner.phone)
            partner.automation_mobile_normalized = self._normalize_phone_value(partner.mobile)
            partner.automation_email_normalized = (partner.email or '').strip().lower()

    def get_automation_customer_profile(self):
        self.ensure_one()
        return CustomerProfileService(self.env).build_profile(self).to_dict()

    def get_automation_customer_profiles(self):
        return CustomerProfileService(self.env).build_profiles(self)

    @staticmethod
    def _normalize_phone_value(value):
        return re.sub(r'[^0-9]+', '', (value or '').strip())
