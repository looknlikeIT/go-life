# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class SaleCouponProgram(models.Model):
    _inherit = 'sale.coupon.program'

    level_up = fields.Many2one('res.partner')


class sale_order(models.Model):
    _inherit = 'sale.order'

    def _prepare_invoice(self):
        invoice_vals = super(sale_order, self)._prepare_invoice()
        promo_lvl_up = self.code_promo_program_id.level_up.id  # Promotion Programs
        coupon_lvl_up = self.applied_coupon_ids.mapped('program_id.level_up')  # Coupon Programs
        coupon_lvl_up = coupon_lvl_up and coupon_lvl_up[0].id
        invoice_vals['lnl_parent_id'] = promo_lvl_up or coupon_lvl_up or self.partner_id.lnl_parent_id.id

        if not self.partner_id.lnl_parent_id and (promo_lvl_up or coupon_lvl_up):
            self.partner_id.lnl_parent_id = promo_lvl_up or coupon_lvl_up
        return invoice_vals


class account_invoice(models.Model):
    _inherit = 'account.invoice'

    lnl_parent_id = fields.Many2one('res.partner')

    @api.multi
    def action_invoice_paid(self):
        # lots of duplicate calls to action_invoice_paid, so we remove those already paid
        to_pay_invoices = self.filtered(lambda inv: inv.state != 'paid')
        for inv in to_pay_invoices:
            # compute hierarchy and pos before recompute cap
            hierarchy = [(inv.partner_id, inv.partner_id.releg_pos)]
            parent = inv.lnl_parent_id
            while parent:
                hierarchy.append((parent, parent.releg_pos))
                parent = parent.lnl_parent_id

            if inv.type == 'out_invoice':
                down_pos = 0
                down_p = self.env['res.partner']
                for p, p_pos in hierarchy:
                    pos = max(p_pos - down_pos, 0) if down_p else p_pos
                    print("pay %s of com for %s" % (pos * inv.amount_untaxed / 100.0, p.id))
                    self.env['lnl.com'].sudo().create({
                        'invoice_id': inv.id,
                        'amount': pos * inv.amount_untaxed / 100.0,
                        'partner_id': p.id,
                        'pos': p_pos,
                        'down_partner_id': down_p.id,
                        'down_pos': down_pos,
                        'paid_date': False,
                    })
                    down_p = p
                    down_pos = p_pos
            elif inv.type == 'out_refund':
                coms = self.env['lnl.com'].search([('invoice_id', '=', inv.origin)])
                for c in coms:
                    print("refund %s of com for %s" % (c.amount * -1, c.partner_id.id))
                    if c.partner_id.vat:
                        c.copy({
                            'invoice_id': inv.id,
                            'amount': c.partner_id.vat and (c.amount * -1) or 0,
                            'note': 'refund of %s (com %s) - vat %s' % (inv.origin, c.id, c.partner_id.vat or 'N/A'),
                        })

        super(account_invoice, self).action_invoice_paid()


class sale_com(models.Model):
    _name = 'lnl.com'
    _description = 'Coms'

    invoice_id = fields.Many2one('account.invoice', readonly=True)
    create_date = fields.Datetime('Date')
    amount = fields.Float()
    pos = fields.Integer()
    partner_id = fields.Many2one('res.partner', string="Partner", index=True)
    down_partner_id = fields.Many2one('res.partner', index=True)
    down_pos = fields.Integer()
    src_partner_id = fields.Many2one(related='invoice_id.partner_id', string="Partner Src", readonly=True)
    src_amount = fields.Monetary(related='invoice_id.amount_untaxed', readonly=True)
    currency_id = fields.Many2one(related='invoice_id.currency_id', readonly=True)
    group_id = fields.Many2one('lnl.com.group', index=True, copy=False)

    paid_date = fields.Datetime(default=False, copy=False)
    note = fields.Text()


class sale_com_group(models.Model):
    _name = 'lnl.com.group'

    amount = fields.Float()
    com_ids = fields.One2many('lnl.com', 'group_id')
    partner_id = fields.Many2one('res.partner', index=True)
    paid_date = fields.Datetime(default=False)


class res_partner(models.Model):
    _inherit = 'res.partner'

    lnl_parent_id = fields.Many2one('res.partner')
    lnl_child_ids = fields.One2many('res.partner', compute='get_childs')
    lnl_direct_child_ids = fields.One2many('res.partner', compute='get_childs')

    releg_pos = fields.Float(compute='get_position')
    releg_fixed_pos = fields.Float('Fixed Position')

    releg_cap = fields.Monetary(compute='get_ca_propre', store=True)
    releg_cag = fields.Monetary(compute='get_ca_global', store=True)

    releg_coms_amount = fields.Monetary(compute='get_coms')
    releg_coms_unpaid_amount = fields.Monetary(compute='get_coms')

    com_ids = fields.One2many('lnl.com', 'partner_id')
    invoice_ids = fields.One2many('account.invoice', 'partner_id')

    @api.depends('com_ids')
    def get_coms(self):
        for record in self:
            record.releg_coms_amount = sum(record.com_ids.mapped('amount'))
            record.releg_coms_unpaid_amount = sum(record.com_ids.filtered(lambda x: not x.paid_date).mapped('amount'))

    def get_childs(self):
        for record in self:
            if record.id:
                record.lnl_child_ids = self.env['res.partner'].search([
                    ('lnl_parent_id', 'child_of', record.id), ('id', '!=', record.id)
                ])
                record.lnl_direct_child_ids = self.env['res.partner'].search([
                    ('lnl_parent_id', '=', record.id), ('id', '!=', record.id)
                ])

    @api.depends('invoice_ids')
    def get_position(self):
        for record in self:
            if record.releg_fixed_pos:
                record.releg_pos = record.releg_fixed_pos
            else:
                pos = 2
                if not record.vat:
                    amount_to_pos = record.releg_cag
                    if amount_to_pos > 499:
                        pos = 3
                    if amount_to_pos > 1999:
                        pos = 4
                    if amount_to_pos > 3999:
                        pos = 5
                    if amount_to_pos > 7999:
                        pos = 6
                else:
                    own = record.releg_cap
                    all_cag = record.lnl_direct_child_ids.sorted('releg_cag', True).mapped('releg_cag')
                    top1 = len(all_cag) >= 1 and all_cag[0] or 0
                    top2 = len(all_cag) >= 2 and all_cag[1] or 0
                    others = sum(all_cag[2:])

                    def is_com(own, top1, top2, others, amount, next_amount):
                        top1 = top1 * 0.4
                        top2 = top2 * 0.4
                        # if 40/40/20 < amount or not
                        pc40 = next_amount * 0.4
                        own = own  # > pc20 and pc20 or own
                        top1 = min(top1, pc40)
                        top2 = min(top2, pc40)

                        _logger.info("coms for %s: pc40 %s, top1: %s, top2: %s, own: %s, other: %s " % (record.id, pc40, top1, top2, own, others))
                        _logger.info("coms: own + top1 + top2 + others > amount =>  %s > %s" % ((own + top1 + top2 + others), amount - 1))
                        return (own + top1 + top2 + others) > amount - 1

                    # (500, 3, 2000) -> Si min(40% top_1, 40% 2000) + min(40% top_2, 40% 2000) + cap > 499 => check next level
                    coms_rate = [(500, 3, 2000), (2000, 4, 4000), (4000, 5, 8000), (8000, 6, 20000), (20000, 8, 40000), (40000, 10, 80000), (80000, 12, 160000), (160000, 14, 320000), (320000, 16, 640000), (640000, 18, 1280000)]
                    for amount, pos_pc, next_amount in coms_rate:
                        if is_com(own, top1, top2, others, amount, next_amount):
                            pos = pos_pc
                        else:
                            break

                record.releg_pos = pos

    @api.depends('invoice_ids', 'invoice_ids.state')
    def get_ca_propre(self):
        for record in self:
            amounts = record.invoice_ids.filtered(lambda x: x.state == 'paid').mapped('amount_untaxed')
            record.releg_cap = sum(amounts)

    # hack, when a com is create, it is because new invoice and so new cag
    # -> need to create com 0 too !
    @api.depends('com_ids', 'invoice_ids', 'invoice_ids.state')
    def get_ca_global(self):
        for record in self:
            record.releg_cag = sum(record.lnl_child_ids.mapped('releg_cap')) + record.releg_cap
