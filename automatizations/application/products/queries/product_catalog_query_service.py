# -*- coding: utf-8 -*-

import unicodedata

from odoo.osv import expression

from ....domain.products.query_fields import PRODUCT_QUERY_FIELDS


class ProductCatalogQueryService:
    """Resuelve consultas genericas del catalogo de productos."""

    def __init__(self, env):
        self.env = env
        self.product_model = env['product.product'].sudo()

    def query_products(self, criteria):
        normalized_criteria = self._normalize_criteria(criteria)
        limit = normalized_criteria.pop('limit', 80)
        provided_fields = {
            field_name: value
            for field_name, value in normalized_criteria.items()
            if value not in (None, '', [])
        }
        db_filters = {
            field_name: value
            for field_name, value in provided_fields.items()
            if field_name != 'name'
        }

        products = self.product_model.search(
            self._build_domain(db_filters),
            limit=self._build_search_limit(limit, provided_fields),
            order='name asc, id asc',
        )
        products = self._apply_python_filters(products, provided_fields, limit)

        return {
            'criteria': normalized_criteria,
            'matched_fields': list(provided_fields.keys()),
            'count': len(products),
            'products': [self._serialize_product(product) for product in products],
        }

    def _normalize_criteria(self, criteria):
        criteria = criteria if isinstance(criteria, dict) else {}
        normalized = {}

        for field_name in PRODUCT_QUERY_FIELDS:
            raw_value = criteria.get(field_name)

            if field_name in {'id', 'product_id', 'product_tmpl_id', 'category_id', 'categ_id', 'limit'}:
                normalized[field_name] = self._normalize_int(raw_value)
            elif field_name in {'price_min', 'price_max'}:
                normalized[field_name] = self._normalize_float(raw_value)
            elif field_name in {'available_only', 'sale_ok', 'active'}:
                normalized[field_name] = self._normalize_bool(raw_value)
            else:
                normalized[field_name] = (raw_value or '').strip() or None

        if normalized.get('limit') is None:
            normalized['limit'] = 80
        normalized['limit'] = max(1, min(normalized['limit'], 200))
        return normalized

    def _build_domain(self, provided_fields):
        domain = []
        for field_name, value in provided_fields.items():
            resolver = getattr(self, f'_domain_for_{field_name}', None)
            if resolver:
                domain = expression.AND([domain, resolver(value)])
        return domain

    def _domain_for_id(self, value):
        return [('id', '=', value)]

    def _domain_for_product_id(self, value):
        return [('id', '=', value)]

    def _domain_for_product_tmpl_id(self, value):
        return [('product_tmpl_id', '=', value)]

    def _domain_for_default_code(self, value):
        return [('default_code', '=ilike', value)]

    def _domain_for_barcode(self, value):
        return [('barcode', '=ilike', value)]

    def _domain_for_category_id(self, value):
        return [('categ_id', '=', value)]

    def _domain_for_categ_id(self, value):
        return [('categ_id', '=', value)]

    def _domain_for_price_min(self, value):
        return [('lst_price', '>=', value)]

    def _domain_for_price_max(self, value):
        return [('lst_price', '<=', value)]

    def _domain_for_created_from(self, value):
        return [('create_date', '>=', value)]

    def _domain_for_created_to(self, value):
        return [('create_date', '<=', value)]

    def _domain_for_available_only(self, value):
        if not value or not self._has_field('qty_available'):
            return []
        return [('qty_available', '>', 0)]

    def _domain_for_sale_ok(self, value):
        return [('sale_ok', '=', value)]

    def _domain_for_active(self, value):
        return [('active', '=', value)]

    def _serialize_product(self, product):
        template = product.product_tmpl_id
        return {
            'id': product.id,
            'product_tmpl_id': template.id,
            'name': product.display_name,
            'internal_name': product.name,
            'default_code': product.default_code,
            'barcode': product.barcode,
            'description': template.description,
            'description_sale': template.description_sale,
            'list_price': product.lst_price,
            'standard_price': self._read_field(product, 'standard_price', 0.0),
            'qty_available': self._read_field(product, 'qty_available', 0.0),
            'virtual_available': self._read_field(product, 'virtual_available', 0.0),
            'uom_id': product.uom_id.id if product.uom_id else None,
            'uom_name': product.uom_id.name if product.uom_id else None,
            'categ_id': product.categ_id.id if product.categ_id else None,
            'categ_name': product.categ_id.name if product.categ_id else None,
            'sale_ok': bool(self._read_field(product, 'sale_ok', False)),
            'purchase_ok': bool(self._read_field(product, 'purchase_ok', False)),
            'active': bool(product.active),
            'type': self._read_field(product, 'type'),
            'detailed_type': self._read_field(product, 'detailed_type'),
            'create_date': product.create_date.isoformat() if product.create_date else None,
            'write_date': product.write_date.isoformat() if product.write_date else None,
            'product_variant_count': template.product_variant_count,
            'product_template_name': template.name,
        }

    def _has_field(self, field_name):
        return field_name in self.product_model._fields

    def _read_field(self, record, field_name, default=None):
        if field_name not in record._fields:
            return default
        return record[field_name]

    def _apply_python_filters(self, products, provided_fields, limit):
        filtered_products = products
        if provided_fields.get('name'):
            filtered_products = filtered_products.filtered(
                lambda product: self._matches_name(product, provided_fields['name'])
            )
        return filtered_products[:limit]

    def _matches_name(self, product, query):
        normalized_query = self._normalize_text(query)
        if not normalized_query:
            return True

        candidates = [
            product.name,
            product.display_name,
            product.default_code,
            product.barcode,
            product.product_tmpl_id.name,
            product.product_tmpl_id.description_sale,
        ]

        return any(
            normalized_query in self._normalize_text(candidate)
            for candidate in candidates
            if candidate
        )

    @staticmethod
    def _build_search_limit(limit, provided_fields):
        if 'name' not in provided_fields:
            return limit
        return min(max(limit * 5, 100), 500)

    @staticmethod
    def _normalize_text(value):
        value = (value or '').strip().lower()
        if not value:
            return ''
        value = unicodedata.normalize('NFKD', value)
        value = ''.join(char for char in value if not unicodedata.combining(char))
        return ' '.join(value.split())

    @staticmethod
    def _normalize_int(value):
        if value in (None, ''):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize_float(value):
        if value in (None, ''):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize_bool(value):
        if value in (None, ''):
            return None
        if isinstance(value, bool):
            return value
        normalized = str(value).strip().lower()
        if normalized in {'true', '1', 'yes', 'si'}:
            return True
        if normalized in {'false', '0', 'no'}:
            return False
        return None
