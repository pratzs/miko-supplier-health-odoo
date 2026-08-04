# -*- coding: utf-8 -*-
{
    'name': 'Vendor Price Check & Supplier Audit (Miko)',
    'version': '16.0.1.0.0',
    'summary': 'Find products you cannot reorder and supplier prices that never apply',
    'description': """
Audits the buying side: products with no supplier at all, supplier price lines
that have expired or can never be reached, and minimum order quantities that
conflict with the rest of your setup.
""",
    'author': 'Tripster Developers',
    'website': 'https://tripsterdevelopers.com/odoo/',
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
