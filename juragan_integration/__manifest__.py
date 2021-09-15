# -*- coding: utf-8 -*-
{
    'name': "IZI Integration Package",

    'summary': "IZI Integration Package",

    'description': "IZI Integration Package",

    'author': "Arkana",
    'website': "https://www.arkana.co.id",
    'category': 'Juragan',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'juragan_fcm_notify',
        'juragan_pricelist_datetime',
        'juragan_product',
        'juragan_product_code_sequence',
        'juragan_webhook',
        'rsa',
        'rsa_api',
        'web_notify',
    ],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
