# -*- coding: utf-8 -*-
import datetime

from odoo import api, fields, models, _

from .supplier_check import find_unreachable, SUPPLIER_LINE_STATUS


# product.supplierinfo names the supplier `name` up to Odoo 15 and `partner_id`
# from 16. @api.depends needs a literal at class-definition time, so the name is
# held in one constant and the build script swaps this single line for the older
# series rather than scattering version checks through the file.
SUPPLIER_FIELD = 'name'


def as_date(value):
    """Coerce a validity bound to a plain date.

    These fields are a Date on some Odoo series and a Datetime on others, and
    comparing the two raises TypeError. Learned on Margin Health.
    """
    if not value:
        return None
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    return fields.Date.to_date(value)


class ProductSupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    sh_line_status = fields.Selection(
        SUPPLIER_LINE_STATUS, string='Line Check', compute='_compute_supplier_line_health',
        store=True, index=True,
        help="Whether Odoo can ever select this line. It takes the FIRST line that "
             "fits, so a line behind one already covering the same ground is dead.")
    sh_shadowed_by = fields.Many2one(
        'product.supplierinfo', string='Beaten by',
        compute='_compute_supplier_line_health', store=True,
        help="The line Odoo uses instead of this one, every time.")

    @api.depends(SUPPLIER_FIELD, 'product_tmpl_id', 'product_id', 'company_id',
                 'min_qty', 'price', 'sequence', 'date_start', 'date_end')
    def _compute_supplier_line_health(self):
        today = fields.Date.context_today(self)

        # Reachability depends on the other lines for the same supplier and
        # product, so siblings are loaded once for the whole batch.
        partners = {l[SUPPLIER_FIELD].id for l in self if l[SUPPLIER_FIELD]}
        siblings = []
        if partners:
            for it in self.env['product.supplierinfo'].search(
                    [(SUPPLIER_FIELD, 'in', list(partners))]):
                siblings.append({
                    'id': it.id,
                    'partner_id': it[SUPPLIER_FIELD].id,
                    'product_tmpl_id': it.product_tmpl_id.id,
                    'product_id': it.product_id.id,
                    'company_id': it.company_id.id,
                    'min_qty': it.min_qty,
                    'price': it.price,
                    'sequence': it.sequence,
                    'date_start': as_date(it.date_start),
                    'date_end': as_date(it.date_end),
                })
        dead = find_unreachable(siblings) if siblings else {}

        for line in self:
            end, start = as_date(line.date_end), as_date(line.date_start)
            status, shadow = 'ok', False
            if end and end < today:
                status = 'expired'
            elif start and start > today:
                status = 'future'
            elif line.id in dead:
                status, shadow = 'unreachable', dead[line.id]
            elif not line.price:
                # A zero price is not a bargain, it is a purchase order that will
                # be raised at nothing and queried by the supplier.
                status = 'no_price'
            line.sh_line_status = status
            line.sh_shadowed_by = shadow

    @api.model
    def action_supplier_lines_rescan(self):
        lines = self.search([])
        CHUNK = 2000
        for start in range(0, len(lines), CHUNK):
            lines[start:start + CHUNK]._compute_supplier_line_health()
        if hasattr(lines, 'flush_recordset'):
            lines.flush_recordset()
        else:
            lines.flush()
        dead = len(lines.filtered(lambda l: l.sh_line_status == 'unreachable'))
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {
                'title': _('Supplier lines checked'),
                'message': _('%(total)s lines checked, %(dead)s that can never be used.') % {
                    'total': len(lines), 'dead': dead},
                'type': 'warning' if dead else 'success', 'sticky': False,
            },
        }
