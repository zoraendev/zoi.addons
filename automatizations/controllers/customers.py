# -*- coding: utf-8 -*-

import json

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

from ..application.customers.queries import CustomerQueryService
from ..domain.customers.query_fields import CUSTOMER_QUERY_FIELDS


class AutomatizationsCustomersController(http.Controller):
    @http.route(
        ['/api/automatizations/customers/query'],
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def query_customer(self, **kwargs):
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
