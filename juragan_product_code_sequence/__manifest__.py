# -*- coding: utf-8 -*-
{
    'name': "Product Code Sequence",
    'summary': """Auto-generate default code for product based on selected sequence.""",
    'author': "Arkana Solusi Teknologi",
    'website': "https://www.arkana.co.id",
    'category': 'Warehouse',
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
        'data/ir_sequence.xml',

        # global action
        # 'views/action/action.xml',

        # view
        'views/common/res_config_settings.xml',

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