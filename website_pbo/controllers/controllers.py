# -*- coding: utf-8 -*-

from odoo import http
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request
from odoo.osv import expression
from odoo.addons.portal.controllers.portal import get_records_pager


class WebsiteSale(WebsiteSale):

    @http.route()
    def shop(self, page=0, category=None, search='', ppg=False, **post):
        response = super(WebsiteSale, self).shop(page=page, category=category, search=search, **post)

        Product = request.env['product.template'].with_context(bin_size=True)
        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [[int(x) for x in v.split("-")] for v in attrib_list if v]

        # compute in all case for min/max value of price slider

        domain = request.website.sale_product_domain()
        domain += self._get_search_domain(search, category, attrib_values, **dict(filter_price=False))

        min_price = Product.read_group(
            domain, ['min:min(list_price)'], []
        )[0]['min'] or 0
        max_price = Product.read_group(
            domain, ['max:max(list_price)'], []
        )[0]['max'] or 10000

        if min_price == max_price:
            max_price += 1

        # save in session for pager on product page
        domain = request.website.sale_product_domain()
        domain += self._get_search_domain(search, category, attrib_values, **dict(filter_price=True))
        products = Product.search(domain, limit=100, order=self._get_search_order(post))
        request.session['history_products'] = products.ids[:]

        response.qcontext['slider_min_price'] = min_price
        response.qcontext['slider_max_price'] = max_price
        curminprice, curmaxprice = (request.params.get('price') or '-').split('-')
        response.qcontext['current_min_price'] = curminprice or min_price
        response.qcontext['current_max_price'] = curmaxprice or max_price
        return response

    @http.route()
    def product(self, product, category='', search='', **kwargs):
        history = request.session.get('history_products', [])
        res = super(WebsiteSale, self).product(product, category, search, **kwargs)
        res.qcontext.update(
            get_records_pager(history, product)
        )

        return res

    def _get_search_domain(self, search, category, attrib_values, **kw):
        domain = super(WebsiteSale, self)._get_search_domain(search, category, attrib_values)

        if request.params.get('price') and kw.get('filter_price', True):
            minprice, maxprice = request.params['price'].split('-')
            domain = expression.AND([[('lst_price', '>=', minprice), ('lst_price', '<=', maxprice)], domain])
        return domain
