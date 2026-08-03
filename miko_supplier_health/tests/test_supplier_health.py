# -*- coding: utf-8 -*-
"""Supplier Health tests.

Same two obligations as the rest of the family: catch every product that genuinely
cannot be bought, and stay completely silent on the ones that are fine.
"""
from odoo.tests import TransactionCase, tagged

from ..models.supplier_check import find_unreachable, classify_supply


@tagged('post_install', '-at_install')
class TestSupplierLogic(TransactionCase):

    def _line(self, lid, **kw):
        base = {'id': lid, 'partner_id': 5, 'product_tmpl_id': 7, 'product_id': False,
                'company_id': 1, 'min_qty': 0.0, 'price': 10.0, 'sequence': 10,
                'date_start': None, 'date_end': None}
        base.update(kw)
        return base

    def test_a_duplicate_line_can_never_be_used(self):
        self.assertEqual(len(find_unreachable([self._line(1), self._line(2)])), 1)

    def test_quantity_breaks_all_survive(self):
        lines = [self._line(1, min_qty=0), self._line(2, min_qty=50),
                 self._line(3, min_qty=200)]
        self.assertEqual(find_unreachable(lines), {})

    def test_a_lower_sequence_wins(self):
        dead = find_unreachable([self._line(1, sequence=5), self._line(2, sequence=20)])
        self.assertIn(2, dead, 'sequence orders supplier lines before anything else')

    def test_different_suppliers_never_shadow_each_other(self):
        lines = [self._line(1, partner_id=5), self._line(2, partner_id=9)]
        self.assertEqual(find_unreachable(lines), {})

    def test_different_companies_never_shadow_each_other(self):
        lines = [self._line(1, company_id=1), self._line(2, company_id=2)]
        self.assertEqual(find_unreachable(lines), {})

    def test_a_priceless_line_is_reachable_not_expired(self):
        """A zero price is a line that WILL be used and raise a PO at nothing.

        Treating it as unreachable pointed the buyer at the wrong problem.
        """
        self.assertEqual(classify_supply(True, ['no_price']), 'no_price')
        self.assertEqual(classify_supply(True, ['no_price', 'ok']), 'ok')

    def test_supply_classification(self):
        self.assertEqual(classify_supply(True, []), 'no_supplier')
        self.assertEqual(classify_supply(True, ['expired']), 'all_expired')
        self.assertEqual(classify_supply(True, ['unreachable']), 'all_expired')
        self.assertEqual(classify_supply(True, ['expired', 'ok']), 'ok')
        self.assertEqual(classify_supply(True, ['future']), 'ok')

    def test_a_product_nobody_buys_is_never_flagged(self):
        self.assertEqual(classify_supply(False, []), 'na')


@tagged('post_install', '-at_install')
class TestSupplierRecords(TransactionCase):

    def setUp(self):
        # Instance level: cls.env in setUpClass needs Odoo 15+, and this supports 14.
        super().setUp()
        self.vendor = self.env['res.partner'].create(
            {'name': 'Northline Supplies', 'supplier_rank': 1})

    def _product(self, name, **kw):
        return self.env['product.template'].create(dict(name=name, **kw))

    def _line(self, product, **kw):
        # `name` up to Odoo 15, `partner_id` from 16.
        info = self.env['product.supplierinfo']
        supplier_field = 'partner_id' if 'partner_id' in info._fields else 'name'
        vals = {supplier_field: self.vendor.id, 'price': 10.0}
        vals.update(kw)
        if 'product_tmpl_id' in info._fields:
            vals['product_tmpl_id'] = product.id
        return info.create(vals)

    def test_a_purchasable_product_with_no_supplier_is_flagged(self):
        p = self._product('Orphan', purchase_ok=True)
        p._compute_supply_health()
        self.assertEqual(p.sh_supply_status, 'no_supplier')
        self.assertFalse(p.sh_is_healthy)

    def test_a_product_nobody_buys_is_not_flagged(self):
        p = self._product('Made in house', purchase_ok=False)
        p._compute_supply_health()
        self.assertEqual(p.sh_supply_status, 'na')
        self.assertTrue(p.sh_is_healthy)

    def test_a_product_with_a_usable_line_passes(self):
        p = self._product('Buyable', purchase_ok=True)
        self._line(p, price=4.20, delay=7)
        p.invalidate_recordset() if hasattr(p, 'invalidate_recordset') else None
        p._compute_supply_health()
        self.assertEqual(p.sh_supply_status, 'ok')
        self.assertEqual(p.sh_lead_time, 7)

    def test_an_expired_line_is_reported_as_expired(self):
        p = self._product('Stale', purchase_ok=True)
        line = self._line(p, date_end='2020-12-31')
        line._compute_supplier_line_health()
        self.assertEqual(line.sh_line_status, 'expired')

    def test_a_future_line_is_reported_as_not_started(self):
        p = self._product('Upcoming', purchase_ok=True)
        line = self._line(p, date_start='2099-01-01')
        line._compute_supplier_line_health()
        self.assertEqual(line.sh_line_status, 'future')

    def test_a_priceless_line_is_reported(self):
        p = self._product('Free from vendor', purchase_ok=True)
        line = self._line(p, price=0.0)
        line._compute_supplier_line_health()
        self.assertEqual(line.sh_line_status, 'no_price')

    def test_a_duplicate_line_on_real_records_is_flagged(self):
        p = self._product('Doubled', purchase_ok=True)
        a = self._line(p, price=10.0)
        b = self._line(p, price=12.0)
        (a | b)._compute_supplier_line_health()
        self.assertIn('unreachable', (a.sh_line_status, b.sh_line_status),
                      'one of two identical supplier lines can never be used')

    def test_rescans_return_notifications(self):
        self.assertEqual(
            self.env['product.template'].action_supply_health_rescan()['tag'],
            'display_notification')
        self.assertEqual(
            self.env['product.supplierinfo'].action_supplier_lines_rescan()['tag'],
            'display_notification')
