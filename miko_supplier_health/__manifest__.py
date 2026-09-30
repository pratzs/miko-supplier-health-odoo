# -*- coding: utf-8 -*-
{
    'name': 'Audit Supplier Prices: Vendor Price Check (Miko)',
    'version': '19.0.1.0.1',
    'summary': 'Supplier audit and vendor pricelist check: find products you cannot reorder and supplier price lines (supplier pricelist) that never apply',
    'description': """
Audits the buying side: products with no supplier at all, supplier price lines
that have expired or can never be reached, and minimum order quantities that
conflict with the rest of your setup.
""",
    'author': 'Tripster Developers',
    'website': 'https://miko.co.nz/odoo/vendor-price-check',
    'category': 'Purchases',
    'license': 'OPL-1',
    'depends': ['purchase'],
    'data': [
        'views/miko_supplier_health_views.xml',
    ],
    'price': 29.00,
    'currency': 'USD',
    'images': ['images/banner.gif', 'images/banner.png'],
    'application': True,
    'installable': True,
    'support': 'support@tripsterdevelopers.com',
}
