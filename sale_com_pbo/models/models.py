# -*- coding: utf-8 -*-

from odoo import models, fields, api


class account_invoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def action_invoice_paid(self):
        # lots of duplicate calls to action_invoice_paid, so we remove those already paid
        to_pay_invoices = self.filtered(lambda inv: inv.state != 'paid')
        for inv in to_pay_invoices:
            p = inv.partner_id
            while p.lnl_parent_id:
                self.env['lnl.com'].sudo().create({
                    'invoice_id': inv.id,
                    'amount': max(0, (p.lnl_parent_id.releg_pos - p.releg_pos)) * inv.amount_total / 100.0,
                    'pos': p.lnl_parent_id.releg_pos,
                    'partner_id': p.lnl_parent_id.id,
                    'down_partner_id': p.id,
                    'down_pos': p.releg_pos,
                    'paid_date': False,
                })
                p = p.lnl_parent_id
        super(account_invoice, self).action_invoice_paid()


class sale_com(models.Model):
    _name = 'lnl.com'

    invoice_id = fields.Many2one('account.invoice', readonly=True)
    create_date = fields.Datetime('Date')
    amount = fields.Float()
    pos = fields.Integer()
    partner_id = fields.Many2one('res.partner', index=True)
    down_partner_id = fields.Many2one('res.partner', index=True)
    down_pos = fields.Integer()
    src_partner_id = fields.Many2one(related='invoice_id.partner_id', readonly=True)
    src_amount = fields.Monetary(related='invoice_id.amount_total', readonly=True)
    currency_id = fields.Many2one(related='invoice_id.currency_id', readonly=True)

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

    releg_coms = fields.Monetary(compute='get_coms')
    releg_coms_amount = fields.Monetary(compute='get_coms')
    releg_coms_unpaid_amount = fields.Monetary(compute='get_coms')

    com_ids = fields.One2many('lnl.com', 'partner_id')
    invoice_ids = fields.One2many('account.invoice', 'partner_id')

    @api.depends('com_ids')
    def get_coms(self):
        for record in self:
            record.releg_coms_amount = sum(self.com_ids.mapped('amount'))
            record.releg_coms_unpaid_amount = sum(self.com_ids.filtered(lambda x: not x.paid_date).mapped('amount'))

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
        print('Get POS')
        for record in self:
            if record.releg_fixed_pos:
                record.releg_pos = record.releg_fixed_pos
            else:
                pos = 2
                if not record.vat:
                    amount_to_pos = record.releg_cap
                    if amount_to_pos < 500:
                        pos = 2
                    elif amount_to_pos < 2000:
                        pos = 3
                    elif amount_to_pos < 4000:
                        pos = 4
                    elif amount_to_pos < 8000:
                        pos = 5
                    else:  # amount_to_pos < 20000:
                        pos = 6
                else:
                    own = record.releg_cap
                    all_cap = sorted(record.child_ids.mapped('releg_cap'))

                    top1 = len(all_cap) >= 1 and all_cap[0] or 0
                    top2 = len(all_cap) >= 2 and all_cap[1] or 0
                    others = sum(all_cap[2:])

                    def is_com(own, top1, top2, others, amount):
                        # if 40/20/20 < amount or not
                        pc20 = amount * 0.2
                        pc40 = amount * 0.4
                        own = own > pc20 and pc20 or own
                        top1 = top1 > pc40 and pc40 or top1
                        top2 = top2 > pc40 and pc40 or top2
                        return (own + top1 + top2 + others) < amount

                    coms_rate = [(500, 2), (2000, 3), (4000, 4), (8000, 5), (20000, 6), (40000, 8), (80000, 10), (160000, 12), (320000, 14), (640000, 16), (10000000, 18)]
                    for amount, pos_pc in coms_rate:
                        if is_com(own, top1, top2, others, amount):
                            pos = pos_pc

                record.releg_pos = pos

    @api.depends('invoice_ids', 'invoice_ids.state')
    def get_ca_propre(self):
        print('CA Propre')
        for record in self:
            amounts = record.invoice_ids.filtered(lambda x: x.state == 'paid').mapped('amount_total')
            record.releg_cap = sum(amounts)

    # hack, when a com is create, it is because new invoice and so new cag
    # -> need to create com 0 too !
    @api.depends('com_ids', 'invoice_ids', 'invoice_ids.state')
    def get_ca_global(self):
        print('CA Global')
        for record in self:
            record.releg_cag = sum(record.lnl_child_ids.mapped('releg_cap')) + record.releg_cap
