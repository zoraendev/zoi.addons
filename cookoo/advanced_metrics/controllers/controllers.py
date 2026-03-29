# -*- coding: utf-8 -*-
import json

from odoo import http
from odoo.http import request


class AdvancedMetricsController(http.Controller):
	@http.route('/advanced_metrics/report/generate', type='http', auth='user', methods=['POST'], csrf=False)
	def generate_sales_orders_report(self, **kwargs):
		payload = {}
		raw_body = request.httprequest.data
		if raw_body:
			try:
				payload = json.loads(raw_body.decode('utf-8'))
			except (ValueError, UnicodeDecodeError):
				payload = {}

		return request.make_json_response({
			'success': True,
			'message': 'Solicitud de reporte recibida correctamente.',
			'payload': payload,
		})

