# -*- coding: utf-8 -*-
# from odoo import http


# class AdvancedMetrics(http.Controller):
#     @http.route('/advanced_metrics/advanced_metrics', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/advanced_metrics/advanced_metrics/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('advanced_metrics.listing', {
#             'root': '/advanced_metrics/advanced_metrics',
#             'objects': http.request.env['advanced_metrics.advanced_metrics'].search([]),
#         })

#     @http.route('/advanced_metrics/advanced_metrics/objects/<model("advanced_metrics.advanced_metrics"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('advanced_metrics.object', {
#             'object': obj
#         })

