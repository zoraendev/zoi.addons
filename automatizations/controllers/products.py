# -*- coding: utf-8 -*-

import json

from odoo import http
from odoo.http import request

from ..application.products.queries import ProductCatalogQueryService
from ..domain.products.query_fields import PRODUCT_QUERY_FIELDS


class AutomatizationsProductsController(http.Controller):
    """Endpoints de catalogo y consultas comerciales de productos."""

    @http.route(
        ['/api/automatizations/products/query'],
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def query_products(self, **kwargs):
        criteria = self._extract_criteria()
        result = ProductCatalogQueryService(request.env).query_products(criteria)
        return request.make_json_response({
            'success': True,
            'message': 'Consulta de productos procesada correctamente.',
            'criteria': result['criteria'],
            'matched_fields': result['matched_fields'],
            'count': result['count'],
            'products': result['products'],
        })

    def _extract_criteria(self):
        payload = self._get_json_payload()
        candidate = payload.get('product') or payload.get('products') or payload.get('criteria') or payload
        candidate = candidate if isinstance(candidate, dict) else {}
        return {
            field_name: candidate.get(field_name)
            for field_name in PRODUCT_QUERY_FIELDS
        }

    @staticmethod
    def _get_json_payload():
        raw_body = request.httprequest.data
        if not raw_body:
            return {}
        try:
            payload = json.loads(raw_body.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}
