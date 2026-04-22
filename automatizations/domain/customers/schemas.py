# -*- coding: utf-8 -*-

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class CustomerIdentifier:
    identifier_type: str
    raw_value: str
    normalized_value: str
    priority: int

    def to_dict(self):
        return {
            'type': self.identifier_type,
            'value': self.raw_value,
            'normalized_value': self.normalized_value,
            'priority': self.priority,
        }


@dataclass(frozen=True)
class CustomerProfile:
    partner_id: int
    commercial_partner_id: int
    customer_uid: str
    display_name: str
    legal_name: str
    alias: str
    fingerprint: str
    identifiers: list = field(default_factory=list)
    search_terms: list = field(default_factory=list)
    email: str = ''
    phone: str = ''
    mobile: str = ''
    vat: str = ''
    ref: str = ''
    lang: str = ''
    is_company: bool = False
    active: bool = True
    customer_rank: int = 0

    def to_dict(self):
        values = asdict(self)
        values['identifiers'] = [identifier.to_dict() for identifier in self.identifiers]
        return values
