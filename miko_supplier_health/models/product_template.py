# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

from .supplier_check import classify_supply, PRODUCT_SUPPLY_STATUS


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    sh_supply_status = fields.Selection(
        PRODUCT_SUPPLY_STATUS, string='Supply Check',
        compute='_compute_supply_health', store=True, index=True,
        help="Whether this product can actually be reordered. A product marked as "
             "purchasable with no usable supplier line cannot be bought at all, and "
             "Odoo does not warn you until you try.")
    sh_lead_time = fields.Integer(
        string='Best Lead Time', compute='_compute_supply_health', store=True,
        help="Shortest delivery lead time across the usable supplier lines.")
    sh_is_healthy = fields.Boolean(
        string='Supply OK', compute='_compute_supply_health', store=True, index=True)

    @api.depends('seller_ids', 'seller_ids.sh_line_status', 'seller_ids.delay',
                 'purchase_ok')
    def _compute_supply_health(self):
        for tmpl in self:
            purchasable = tmpl.purchase_ok if 'purchase_ok' in tmpl._fields else True
            lines = tmpl.seller_ids
            status = classify_supply(purchasable, lines.mapped('sh_line_status'))
            usable = lines.filtered(lambda l: l.sh_line_status in ('ok', 'future'))
            delays = [l.delay for l in usable if l.delay]
            tmpl.sh_supply_status = status
            tmpl.sh_lead_time = min(delays) if delays else 0
            # 'na' is not a fault: a product nobody buys needs no supplier.
            tmpl.sh_is_healthy = status in ('ok', 'na')

    @api.model
    def action_supply_health_rescan(self):
        products = self.search([])
        CHUNK = 2000
        for start in range(0, len(products), CHUNK):
            products[start:start + CHUNK]._compute_supply_health()
        if hasattr(products, 'flush_recordset'):
            products.flush_recordset()
        else:
            products.flush()
        bad = len(products.filtered(lambda p: not p.sh_is_healthy))
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {
                'title': _('Supply checked'),
                'message': _('%(total)s products checked, %(bad)s that cannot be reordered.') % {
                    'total': len(products), 'bad': bad},
                'type': 'warning' if bad else 'success', 'sticky': False,
            },
        }
