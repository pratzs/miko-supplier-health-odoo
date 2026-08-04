# -*- coding: utf-8 -*-
"""Supplier line reachability and buying-side faults.

Odoo picks a supplier line the same way it picks a pricelist rule: it walks them
in a fixed order and takes the FIRST one that fits. A line sitting behind another
that already covers every case it would cover is dead. It has a price on it, it
looks live, and no purchase order has ever used it.

`product.supplierinfo._order` is `sequence, min_qty desc, price, id`, so a line is
reached before another when it has a lower sequence, or the same sequence and a
higher minimum quantity.

Everything here is arithmetic on values already in the database. No network.
"""

SUPPLIER_LINE_STATUS = [
    ('ok', 'Can be used'),
    ('unreachable', 'Never used'),
    ('expired', 'Expired'),
    ('future', 'Not started yet'),
    ('no_price', 'No price'),
]

PRODUCT_SUPPLY_STATUS = [
    ('ok', 'Can be reordered'),
    ('no_supplier', 'No supplier at all'),
    ('all_expired', 'Every supplier line has expired'),
    ('no_price', 'Supplier has no price'),
    ('na', 'Not purchased'),
]


def line_sort_key(line):
    """Reproduce Odoo's own ordering so reachability is judged the way Odoo buys."""
    return (
        line.get('sequence') or 0,
        -(line.get('min_qty') or 0.0),
        line.get('price') or 0.0,
        line.get('id') or 0,
    )


def same_supply_target(a, b):
    """Same supplier, same product, same company.

    Only exact matches count. A line on the template and a line on one variant do
    overlap, but proving it needs the variant set walked, and a wrong answer would
    condemn a line that is genuinely used.
    """
    return (
        a.get('partner_id') == b.get('partner_id')
        and a.get('product_tmpl_id') == b.get('product_tmpl_id')
        and a.get('product_id') == b.get('product_id')
        and a.get('company_id') == b.get('company_id')
    )


def dates_cover(outer, inner):
    """Does `outer`'s validity window contain the whole of `inner`'s?"""
    o_start, o_end = outer.get('date_start'), outer.get('date_end')
    i_start, i_end = inner.get('date_start'), inner.get('date_end')
    if o_start and (not i_start or i_start < o_start):
        return False
    if o_end and (not i_end or i_end > o_end):
        return False
    return True


def find_unreachable(lines):
    """Return {line_id: shadowing_line_id} for lines Odoo can never select.

    A line is unreachable when an earlier line, for the same supplier and product,
    is reached at a quantity at least as low and is valid across at least the same
    dates. Odoo returns the earlier one every time.
    """
    ordered = sorted(lines, key=line_sort_key)
    dead = {}
    for i, line in enumerate(ordered):
        for earlier in ordered[:i]:
            if earlier['id'] in dead:
                continue  # a dead line cannot shadow anything
            if not same_supply_target(earlier, line):
                continue
            # Ordering is min_qty DESCENDING, so an earlier line is reached at a
            # lower quantity only when its own threshold is lower or equal.
            if (earlier.get('min_qty') or 0.0) > (line.get('min_qty') or 0.0):
                continue
            if not dates_cover(earlier, line):
                continue
            dead[line['id']] = earlier['id']
            break
    return dead


def classify_supply(purchasable, lines_status):
    """Judge a product's ability to actually be reordered.

    `lines_status` is the list of statuses of its supplier lines.
    """
    if not purchasable:
        return 'na'
    if not lines_status:
        return 'no_supplier'

    # A line with no price is still REACHABLE, it is simply priceless. Excluding
    # it from the reachable set made a priced-but-zero supplier look like an
    # expired one, which points the buyer at the wrong problem entirely.
    reachable = [s for s in lines_status if s in ('ok', 'future', 'no_price')]
    if not reachable:
        # Everything is expired or shadowed. Either way nothing can be bought.
        return 'all_expired'
    if all(s == 'no_price' for s in reachable):
        return 'no_price'
    return 'ok'
