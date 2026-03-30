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

		filters = payload.get('filters') or {}
		rows = request.env['advanced_metrics.report.wizard'].sudo().get_sales_orders_report_rows(filters)
		total_rows = len(rows)

		return request.make_json_response({
			'success': True,
			'message': (
				f'Se encontraron {total_rows} resultados.'
				if total_rows
				else 'No se encontraron resultados con los filtros seleccionados.'
			),
			'rows': rows,
			'count': total_rows,
		})

	@http.route('/api/advanced_metrics/sales_inventory', type='http', auth='public', methods=['GET'], csrf=False)
	def get_sales_inventory_api(self, token=None, **kwargs):
		if not token:
			return request.make_response(json.dumps({'error': 'Unauthorized: Token is missing'}), headers=[('Content-Type', 'application/json')], status=401)

		config = request.env['advanced_metrics.api.config'].sudo().search([('access_token', '=', token)], limit=1)
		if not config:
			return request.make_response(json.dumps({'error': 'Unauthorized: Invalid token'}), headers=[('Content-Type', 'application/json')], status=401)

		limit = config.record_limit or 5000
		try:
			# Use sudo to run the extraction under system privileges but restricted by the token logic limits
			rows = request.env['advanced_metrics.report.wizard'].sudo().get_sales_orders_report_rows(filters={}, limit=limit)
			return request.make_response(json.dumps({'data': rows}), headers=[('Content-Type', 'application/json')])
		except Exception as e:
			return request.make_response(json.dumps({'error': f'Internal Error: {str(e)}'}), headers=[('Content-Type', 'application/json')], status=500)


