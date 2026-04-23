# -*- coding: utf-8 -*-

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

from .base_controller import AutomatizationsBaseController
from ..application.customers.queries import CustomerQueryService
from ..domain.customers.query_fields import CUSTOMER_QUERY_FIELDS


class AutomatizationsCustomersController(AutomatizationsBaseController):
    @http.route(
        ['/api/automatizations/customers/query'],
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def query_customer(self, **kwargs):
        if not self._authenticate():
            return self._make_auth_error_response()

        criteria = self._extract_criteria()

        try:
            result = CustomerQueryService(request.env).query_customer(criteria)
        except ValidationError as error:
            return request.make_json_response({
                'success': False,
                'message': error.args[0],
                'criteria': criteria,
                'customer': None,
            }, status=400)

        return request.make_json_response({
            'success': True,
            'message': 'Consulta de cliente procesada correctamente.',
            'criteria': result['criteria'],
            'matched_fields': result['matched_fields'],
            'customer': result['customer'],
        })

    def _extract_criteria(self):
        payload = self._get_json_payload()
        candidate = payload.get('customer') or payload.get('criteria') or payload
        candidate = candidate if isinstance(candidate, dict) else {}
        return {
            field_name: candidate.get(field_name)
            for field_name in CUSTOMER_QUERY_FIELDS
        }
