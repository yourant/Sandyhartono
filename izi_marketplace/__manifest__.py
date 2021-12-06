# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
# noinspection PyUnresolvedReferences,SpellCheckingInspection
{
    "name": """IZI Marketplace""",
    "summary": """Base Module for Marketplace Integration""",
    "category": "Sales",
    "version": "11.0.0.9.0",
    "development_status": "Alpha",  # Options: Alpha|Beta|Production/Stable|Mature
    "auto_install": False,
    "installable": True,
    "application": True,
    "sequence": -100,
    "author": "IZI PT Solusi Usaha Mudah",
    "support": "admin@iziapp.id",
    "website": "https://www.iziapp.id",
    "license": "OPL-1",
    # "images": [
    #     'images/main_screenshot.png'
    # ],

    # "price": 10.00,
    # "currency": "USD",

    "depends": [
        # odoo addons
        'base',
        'sale_management',
        'stock',
        'delivery',
        # third party addons
        'web_widget_image_url',
        'web_notify',

        # developed addons
    ],
    "data": [
        # group
        'security/res_groups.xml',

        # data
        'data/functions.xml',
        'data/product.xml',

        # global action
        'views/action/action.xml',

        # view
        'views/common/mp_account.xml',
        'views/common/mp_token.xml',
        'views/common/mp_product.xml',
        'views/common/mp_map_product.xml',
        'views/common/mp_map_product_line.xml',
        'views/common/product_template.xml',
        'views/common/sale_order.xml',
        'views/common/order_component_config.xml',

        # wizard
        'views/wizard/wiz_mp_order.xml',
        # report paperformat
        # 'data/report_paperformat.xml',

        # report template
        # 'views/report/report_template_model_name.xml',

        # report action
        # 'views/action/action_report.xml',

        # assets
        'views/assets.xml',

        # onboarding action
        # 'views/action/action_onboarding.xml',

        # action menu
        'views/action/action_menu.xml',

        # action onboarding
        # 'views/action/action_onboarding.xml',

        # menu
        'views/menu.xml',

        # security
        'security/ir.model.access.csv',
        # 'security/ir.rule.csv',

        # data
    ],
    "demo": [
        # 'demo/demo.xml',
    ],
    "qweb": [
        # "static/src/xml/{QWEBFILE1}.xml",
    ],

    "post_load": None,
    # "pre_init_hook": "pre_init_hook",
    # "post_init_hook": "post_init_hook",
    "uninstall_hook": None,

    "external_dependencies": {"python": [], "bin": []},
    # "live_test_url": "",
    # "demo_title": "{MODULE_NAME}",
    # "demo_addons": [
    # ],
    # "demo_addons_hidden": [
    # ],
    # "demo_url": "DEMO-URL",
    # "demo_summary": "{SHORT_DESCRIPTION_OF_THE_MODULE}",
    # "demo_images": [
    #    "images/MAIN_IMAGE",
    # ]
}
