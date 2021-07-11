# -*- coding: utf-8 -*-
{
    'name': "Pricelist by Datetime",
    'summary': """Manage the pricelist by Date, by Time or by Week Days""",
    'author': "Arkana Solusi Teknologi",
    'website': "https://www.arkana.co.id",
    'category': 'Sales',
    'version': '0.1.0',
    'depends': [
        # odoo addons
        'base',
        'product',
        # third party addons

        # developed addons
    ],

    # always loaded
    'data': [
        # group
        # 'security/res_groups.xml',

        # data

        # global action
        # 'views/action/action.xml',

        # view
        'views/common/product_pricelist.xml',

        # wizard

        # report paperformat
        # 'data/report_paperformat.xml',

        # report template
        # 'views/report/report_template_model_name.xml',

        # report action
        # 'views/action/action_report.xml',

        # assets
        # 'views/assets.xml',

        # onboarding action
        # 'views/action/action_onboarding.xml',

        # action menu
        # 'views/action/action_menu.xml',

        # action onboarding
        # 'views/action/action_onboarding.xml',

        # menu
        # 'views/menu.xml',

        # security
        # 'security/ir.model.access.csv',
        # 'security/ir.rule.csv',

        # data
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}