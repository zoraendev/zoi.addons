# -*- coding: utf-8 -*-

import re

from odoo.exceptions import ValidationError
from odoo.osv import expression

from ....domain.customers.query_fields import CUSTOMER_QUERY_FIELDS
from ..services import CustomerProfileService


class CustomerQueryService:
    """Resuelve consultas genericas de customers a partir de criterios opcionales."""

    def __init__(self, env):
        self.env = env
        self.partner_model = env['res.partner'].sudo()
        self.profile_service = CustomerProfileService(env)

    def query_customer(self, criteria):
        normalized_criteria = self._normalize_criteria(criteria)
        provided_fields = {
            field_name: value
            for field_name, value in normalized_criteria.items()
            if value not in (None, '', [])
        }

        if not provided_fields:
            raise ValidationError('Debes enviar al menos un criterio de consulta del cliente.')

        partners = self.partner_model.search(
            self._build_domain(provided_fields),
            limit=25,
        )
        partner = self._resolve_unique_partner(partners)

        if not partner:
            return {
                'criteria': normalized_criteria,
                'matched_fields': list(provided_fields.keys()),
                'customer': None,
            }

        return {
            'criteria': normalized_criteria,
            'matched_fields': list(provided_fields.keys()),
            'customer': self._serialize_customer(partner),
        }

    def _normalize_criteria(self, criteria):
        criteria = criteria if isinstance(criteria, dict) else {}
        normalized = {}
        for field_name in CUSTOMER_QUERY_FIELDS:
            raw_value = criteria.get(field_name)
            if field_name in {'phone', 'mobile'}:
                normalized[field_name] = self._normalize_phone(raw_value)
            elif field_name in {'email'}:
                normalized[field_name] = (raw_value or '').strip().lower() or None
            else:
                normalized[field_name] = (raw_value or '').strip() or None
        return normalized

    def _build_domain(self, provided_fields):
        domain = []
        for field_name, value in provided_fields.items():
            resolver = getattr(self, f'_domain_for_{field_name}', None)
            if resolver:
                domain = expression.AND([domain, resolver(value)])
        return domain

    def _domain_for_phone(self, value):
        return ['|', ('automation_phone_normalized', '=', value), ('automation_mobile_normalized', '=', value)]

    def _domain_for_mobile(self, value):
        return ['|', ('automation_mobile_normalized', '=', value), ('automation_phone_normalized', '=', value)]

    def _domain_for_email(self, value):
        return [('automation_email_normalized', '=', value)]

    def _domain_for_vat(self, value):
        return [('vat', '=ilike', value)]

    def _domain_for_ref(self, value):
        return [('ref', '=ilike', value)]

    def _domain_for_name(self, value):
        return [('name', '=ilike', value)]

    def _domain_for_display_name(self, value):
        return [('display_name', '=ilike', value)]

    def _domain_for_automation_customer_uid(self, value):
        return [('automation_customer_uid', '=', value)]

    def _domain_for_automation_customer_alias(self, value):
        return [('automation_customer_alias', '=ilike', value)]

    def _serialize_customer(self, partner):
        profile = self.profile_service.build_profile(partner).to_dict()
        return {
            'id': partner.id,
            'name': partner.name,
            'display_name': partner.display_name,
            'email': partner.email,
            'phone': partner.phone,
            'mobile': partner.mobile,
            'street': partner.street,
            'street2': partner.street2,
            'city': partner.city,
            'state_id': partner.state_id.id if partner.state_id else None,
            'state_name': partner.state_id.name if partner.state_id else None,
            'country_id': partner.country_id.id if partner.country_id else None,
            'country_name': partner.country_id.name if partner.country_id else None,
            'zip': partner.zip,
            'vat': partner.vat,
            'ref': partner.ref,
            'lang': partner.lang,
            'company_type': partner.company_type,
            'is_company': partner.is_company,
            'active': partner.active,
            'customer_rank': getattr(partner, 'customer_rank', 0),
            'commercial_partner_id': partner.commercial_partner_id.id,
            'commercial_partner_name': partner.commercial_partner_id.name,
            'automation_customer_uid': partner.automation_customer_uid,
            'automation_customer_alias': partner.automation_customer_alias,
            'automation_customer_fingerprint': partner.automation_customer_fingerprint,
            'automation_phone_normalized': partner.automation_phone_normalized,
            'automation_mobile_normalized': partner.automation_mobile_normalized,
            'automation_email_normalized': partner.automation_email_normalized,
            'profile': profile,
        }

    def _resolve_unique_partner(self, partners):
        if not partners:
            return None
        if len(partners) == 1:
            return partners[0].commercial_partner_id

        commercial_partners = partners.mapped('commercial_partner_id')
        if len(commercial_partners) == 1:
            return commercial_partners[0]

        raise ValidationError(
            'La consulta devolvio multiples clientes. Envia un criterio mas especifico, de preferencia el numero de telefono.'
        )

    @staticmethod
    def _normalize_phone(value):
        normalized = re.sub(r'[^0-9]+', '', (value or '').strip())
        return normalized or None
