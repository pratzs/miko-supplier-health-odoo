# Miko Supplier Health for Odoo

Finds products that cannot actually be reordered, and supplier price lines Odoo can
never select.

| | |
|---|---|
| Series | 14.0 to 19.0 |
| Price | USD 29, licence OPL-1 |
| Depends | `purchase` |
| Tests | 16 per series, 6/6 certified |
| Colour | Miko mark in damson `#8C7CB8` to `#524285` |

## The differentiator

Odoo takes the FIRST supplier line that fits, ordered by `sequence` then
`min_qty` descending. A line behind one already covering the same ground is dead:
priced, apparently live, never used. This reproduces that ordering and names the
winner.

## Version trap unique to this app

**`product.supplierinfo.partner_id` is called `name` before Odoo 16.** The field is
held in one `SUPPLIER_FIELD` constant which the build script swaps for 14/15,
because `@api.depends` needs a literal at class-definition time. Views and tests
resolve it too.

## Bug worth remembering

A supplier line with **no price is reachable, not expired**. Excluding it from the
reachable set made a priced-at-zero supplier report as "every line expired", which
points the buyer at entirely the wrong problem.

Full store runbook: `Apps/miko-catalog-health-odoo/PUBLISHING.md`.
