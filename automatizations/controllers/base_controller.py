# -*- coding: utf-8 -*-

import json

from odoo import http
from odoo.http import request


class AutomatizationsBaseController(http.Controller):
    """Controlador base con autenticacion por token compartido con pbi_connections."""

    _auth_config_models = (
        'pbi_connections.api.config',
        'advanced_metrics.api.config',
    )

    def _authenticate(self):
        """Valida el token enviado en headers o query string.

        Busca en los mismos modelos de configuracion que usa Power BI
        para mantener un unico token centralizado.
        """
        token = self._extract_token()
        if not token:
            return None

        for model_name in self._auth_config_models:
            if model_name in request.env:
                if model_name == 'pbi_connections.api.config':
                    request.env[model_name].sudo()._sync_legacy_config()
                config = request.env[model_name].sudo().search(
                    [('access_token', '=', token)], limit=1,
                )
                if config:
                    return config
        return None

    def _make_auth_error_response(self):
        return request.make_json_response({
            'success': False,
            'message': 'Acceso no autorizado: Token invalido o ausente. '
                       'Envia el token en la cabecera Access-Token, '
                       'Authorization: Bearer <token>, o como parametro ?token=<token>.',
        }, status=401)

    @staticmethod
    def _extract_token():
        token = (
            request.httprequest.headers.get('Access-Token')
            or request.httprequest.headers.get('Authorization')
            or request.httprequest.args.get('token')
        )
        token = (token or '').strip().strip('"').strip("'")
        if token.lower().startswith('bearer '):
            token = token[7:].strip()
        return token

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
