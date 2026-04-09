# -*- coding: utf-8 -*-
# from odoo import http


# class PbiConnections(http.Controller):
#     @http.route('/pbi_connections/pbi_connections', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/pbi_connections/pbi_connections/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('pbi_connections.listing', {
#             'root': '/pbi_connections/pbi_connections',
#             'objects': http.request.env['pbi_connections.pbi_connections'].search([]),
#         })

#     @http.route('/pbi_connections/pbi_connections/objects/<model("pbi_connections.pbi_connections"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('pbi_connections.object', {
#             'object': obj
#         })

