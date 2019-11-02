# -*- coding: utf-8 -*-
from odoo import http

# class SaleComPbo(http.Controller):
#     @http.route('/sale_com_pbo/sale_com_pbo/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/sale_com_pbo/sale_com_pbo/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('sale_com_pbo.listing', {
#             'root': '/sale_com_pbo/sale_com_pbo',
#             'objects': http.request.env['sale_com_pbo.sale_com_pbo'].search([]),
#         })

#     @http.route('/sale_com_pbo/sale_com_pbo/objects/<model("sale_com_pbo.sale_com_pbo"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('sale_com_pbo.object', {
#             'object': obj
#         })