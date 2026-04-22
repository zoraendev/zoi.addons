# -*- coding: utf-8 -*-
# from odoo import http


# class Automatizations(http.Controller):
#     @http.route('/automatizations/automatizations', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/automatizations/automatizations/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('automatizations.listing', {
#             'root': '/automatizations/automatizations',
#             'objects': http.request.env['automatizations.automatizations'].search([]),
#         })

#     @http.route('/automatizations/automatizations/objects/<model("automatizations.automatizations"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('automatizations.object', {
#             'object': obj
#         })

