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
        'sale_stock',
        'juragan_fcm_notify',
        'juragan_product_code_sequence',
        'juragan_pricelist_datetime',
    ],
    'css': ['static/src/css/sale.css'],
   
    'data': [
        # group
        'security/res_groups.xml',

        # data

        # global action
        'views/action.xml',

        # view
        'views/assets.xml',
        'views/server_views.xml',
        'views/marketplace_views.xml',
        'views/product_views.xml',
        'views/order_views.xml',
        'views/stock_distribution_views.xml',
        'views/order_component_config.xml',
        'views/juragan_campaign.xml',

        # wizard        
        'wizards/views/popup_view.xml',
        'wizards/views/qty_available.xml',
        'wizards/views/request_pickup.xml',
        'wizards/views/confirm_shipping.xml',
        'wizards/views/sale_cancel.xml',
        'wizards/views/warehouse_config_wizard.xml',
        'wizards/views/mapping_master.xml',

        # report paperformat

        # report template

        # report action

        # assets

        # onboarding action

        # action menu

        # action onboarding

        # menu

        # security
        'security/ir.model.access.csv',
        'security/ir.rule.csv',

        # data
    ],
}