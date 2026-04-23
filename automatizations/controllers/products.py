# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request

from .base_controller import AutomatizationsBaseController
from ..application.products.queries import ProductCatalogQueryService
from ..domain.products.query_fields import PRODUCT_QUERY_FIELDS


class AutomatizationsProductsController(AutomatizationsBaseController):
    """Endpoints de catalogo y consultas comerciales de productos."""

    @http.route(
        ['/api/automatizations/products/query'],
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def query_products(self, **kwargs):
        if not self._authenticate():
            return self._make_auth_error_response()

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
