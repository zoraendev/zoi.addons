# -*- coding: utf-8 -*-
import json

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request


class BaseDashboardController(http.Controller):
    _service_model = None
    _request_filter_keys = ()
    _auth_error_message = 'Acceso no autorizado: Token invalido o ausente en las cabeceras o en la URL.'
    _auth_config_models = (
        'pbi_connections.api.config',
        'advanced_metrics.api.config',
    )

    @staticmethod
    def _get_json_payload():
        payload = {}
        raw_body = request.httprequest.data
        if raw_body:
            try:
                payload = json.loads(raw_body.decode('utf-8'))
            except (ValueError, UnicodeDecodeError):
                payload = {}
        return payload if isinstance(payload, dict) else {}

    def _get_request_filters(self):
        payload = self._get_json_payload()
        filters = payload.get('filters') or payload or {}

        for key in self._request_filter_keys:
            value = request.httprequest.args.get(key)
            if value not in (None, ''):
                filters[key] = value

        return filters

    def _authenticate(self):
        token = (
            request.httprequest.headers.get('Access-Token')
            or request.httprequest.headers.get('Authorization')
            or request.httprequest.args.get('token')
        )
        if token and token.startswith('Bearer '):
            token = token[7:]
        if not token:
            return None

        for model_name in self._auth_config_models:
            if model_name in request.env:
                config_record = request.env[model_name].sudo().search([('access_token', '=', token)], limit=1)
                if config_record:
                    return config_record
        return None

    @staticmethod
    def _make_success_response(message, report_data, extra_keys=None):
        response = {
            'success': True,
            'message': message,
            'generatedAt': report_data.get('generatedAt'),
            'filters': report_data.get('filters', {}),
            'data': report_data.get('data', []),
        }
        for key in extra_keys or []:
            response[key] = report_data.get(key, {})
        return request.make_json_response(response)

    @staticmethod
    def _make_error_response(message, filters, status=500, extra_payload=None):
        response = {
            'success': False,
            'message': message,
            'generatedAt': None,
            'filters': filters or {},
            'data': [],
        }
        if extra_payload:
            response.update(extra_payload)
        return request.make_json_response(response, status=status)

    def _handle_service_request(self, method_name, success_message, error_message, extra_keys=None, extra_payload=None):
        if not self._authenticate():
            return self._make_error_response(self._auth_error_message, {}, status=401)

        filters = self._get_request_filters()

        try:
            service = request.env[self._service_model].sudo()
            report_data = getattr(service, method_name)(filters)
            return self._make_success_response(success_message, report_data, extra_keys=extra_keys)
        except ValidationError as error:
            return self._make_error_response(error.args[0], filters, status=400, extra_payload=extra_payload)
        except Exception:
            return self._make_error_response(error_message, filters, extra_payload=extra_payload)
