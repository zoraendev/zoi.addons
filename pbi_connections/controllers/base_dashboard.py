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

    def _get_request_filters(self, request_filter_keys=None):
        payload = self._get_json_payload()
        filters = payload.get('filters') or payload or {}

        for key in (request_filter_keys or self._request_filter_keys):
            value = request.httprequest.args.get(key)
            if value not in (None, ''):
                filters[key] = value

        return filters

    @staticmethod
    def _normalize_token(token):
        token = (token or '').strip().strip('"').strip("'")
        if token.lower().startswith('bearer '):
            token = token[7:].strip()
        return token

    def _authenticate(self):
        token = self._normalize_token(
            request.httprequest.headers.get('Access-Token')
            or request.httprequest.headers.get('Authorization')
            or request.httprequest.args.get('token')
        )
        if not token:
            return None

        for model_name in self._auth_config_models:
            if model_name in request.env:
                if model_name == 'pbi_connections.api.config':
                    request.env[model_name].sudo()._sync_legacy_config()
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

    def _handle_service_request(
        self,
        method_name,
        success_message,
        error_message,
        extra_keys=None,
        extra_payload=None,
        service_model=None,
        request_filter_keys=None,
    ):
        filters = self._get_request_filters(request_filter_keys=request_filter_keys)
        # Incluye los filtros recibidos en la respuesta para depuración
        debug_payload = extra_payload.copy() if extra_payload else {}
        debug_payload['received_filters'] = filters

        if not self._authenticate():
            debug_payload['auth'] = 'failed'
            return self._make_error_response(self._auth_error_message, filters, status=401, extra_payload=debug_payload)

        try:
            service = request.env[service_model or self._service_model].sudo()
            report_data = getattr(service, method_name)(filters)
            return self._make_success_response(success_message, report_data, extra_keys=extra_keys)
        except ValidationError as error:
            debug_payload['exception'] = str(error)
            return self._make_error_response(error.args[0], filters, status=400, extra_payload=debug_payload)
        except Exception as error:
            debug_payload['exception'] = str(error)
            return self._make_error_response(f"{error_message} | Exception: {error}", filters, extra_payload=debug_payload)
