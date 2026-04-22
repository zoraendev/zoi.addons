# -*- coding: utf-8 -*-

import re
import uuid

from ....domain.customers.constants import CUSTOMER_IDENTIFIER_PRIORITY
from ....domain.customers.schemas import CustomerIdentifier, CustomerProfile


class CustomerProfileService:
    """Construye el perfil canonico que usara el bot para reconocer clientes."""

    def __init__(self, env):
        self.env = env

    def build_profile(self, partner):
        commercial_partner = partner.commercial_partner_id
        customer_uid = partner.automation_customer_uid or str(uuid.uuid4())
        identifiers = self._build_identifiers(partner, commercial_partner)
        search_terms = self._build_search_terms(partner, commercial_partner, identifiers)
        fingerprint = self._build_fingerprint(search_terms)

        return CustomerProfile(
            partner_id=partner.id,
            commercial_partner_id=commercial_partner.id,
            customer_uid=customer_uid,
            display_name=partner.display_name or partner.name or '',
            legal_name=commercial_partner.name or partner.name or '',
            alias=partner.automation_customer_alias or partner.name or '',
            fingerprint=fingerprint,
            identifiers=identifiers,
            search_terms=search_terms,
            email=(partner.email or '').strip(),
            phone=(partner.phone or '').strip(),
            mobile=(partner.mobile or '').strip(),
            vat=(commercial_partner.vat or '').strip(),
            ref=(commercial_partner.ref or '').strip(),
            lang=(partner.lang or '').strip(),
            is_company=bool(commercial_partner.is_company),
            active=bool(partner.active),
            customer_rank=int(getattr(commercial_partner, 'customer_rank', 0) or 0),
        )

    def build_profiles(self, partners):
        return [self.build_profile(partner).to_dict() for partner in partners]

    def build_fingerprint_value(self, partner):
        return self.build_profile(partner).fingerprint

    def _build_identifiers(self, partner, commercial_partner):
        raw_identifiers = [
            ('customer_uid', partner.automation_customer_uid),
            ('email', partner.email),
            ('phone', partner.phone),
            ('mobile', partner.mobile),
            ('vat', commercial_partner.vat),
            ('reference', commercial_partner.ref),
            ('name', commercial_partner.name),
            ('alias', partner.automation_customer_alias),
        ]

        identifiers = []
        seen_keys = set()
        for identifier_type, raw_value in raw_identifiers:
            normalized_value = self._normalize_identifier(identifier_type, raw_value)
            if not normalized_value:
                continue

            dedupe_key = (identifier_type, normalized_value)
            if dedupe_key in seen_keys:
                continue

            seen_keys.add(dedupe_key)
            identifiers.append(
                CustomerIdentifier(
                    identifier_type=identifier_type,
                    raw_value=(raw_value or '').strip(),
                    normalized_value=normalized_value,
                    priority=CUSTOMER_IDENTIFIER_PRIORITY.get(identifier_type, 0),
                )
            )

        identifiers.sort(key=lambda item: item.priority, reverse=True)
        return identifiers

    def _build_search_terms(self, partner, commercial_partner, identifiers):
        values = [
            partner.name,
            partner.display_name,
            partner.automation_customer_alias,
            commercial_partner.name,
            commercial_partner.ref,
            commercial_partner.vat,
            partner.email,
            partner.phone,
            partner.mobile,
        ]
        values.extend(identifier.normalized_value for identifier in identifiers)

        terms = []
        seen_terms = set()
        for value in values:
            normalized = self._normalize_term(value)
            if not normalized or normalized in seen_terms:
                continue
            seen_terms.add(normalized)
            terms.append(normalized)
        return terms

    def _build_fingerprint(self, search_terms):
        return '|'.join(search_terms[:10])

    def _normalize_identifier(self, identifier_type, value):
        value = (value or '').strip()
        if not value:
            return ''
        if identifier_type in {'phone', 'mobile'}:
            return re.sub(r'[^0-9]+', '', value)
        if identifier_type in {'vat', 'reference', 'customer_uid'}:
            return re.sub(r'[^a-z0-9]+', '', value.lower())
        return self._normalize_term(value)

    def _normalize_term(self, value):
        value = (value or '').strip().lower()
        if not value:
            return ''
        value = re.sub(r'\s+', ' ', value)
        return value
