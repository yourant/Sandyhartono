# -*- coding: utf-8 -*-
{
    'name': "Firebase Cloud Messaging: Push Notification",
    'summary': """Push notification with Firebase Cloud Messaging""",
    'author': "Arkana Solusi Teknologi",
    'website': "https://www.arkana.co.id",
    'category': 'User Interface',
    'version': '0.1.0',
    'depends': [
        # odoo addons
        'base',
        'base_setup',
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
        'views/common/res_config_settings.xml',
        'views/template/website_template_firebase.xml',

        # wizard

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
