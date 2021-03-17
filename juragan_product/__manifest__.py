# -*- coding: utf-8 -*-
{
    'name': "Juragan Product",

    'summary': """
    """,

    'description': """
    """,

    'author': "Arkana",
    'website': "https://www.arkana.co.id",
    'category': 'Juragan',
    'version': '0.1',
    'depends': [
        'product',
        'stock',
        'juragan_webhook',
        'sale_management',
        'purchase',
        'sale_stock',
    ],
    'css': ['static/src/css/sale.css'],
    'data': [
        'security/ir.model.access.csv',
        'wizards/views/sale_cancel.xml',
        'wizards/views/request_pickup.xml',
        'views/marketplace_views.xml',
        'views/assets.xml',
        'views/product_views.xml',
        'views/order_views.xml',
        'views/server_views.xml',
        'data/cronjob.xml',
    ],
}
