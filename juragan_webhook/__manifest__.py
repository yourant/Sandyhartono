# -*- coding: utf-8 -*-
{
    'name': "Juragan Webhook",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Arkana",
    'website': "https://arkana.co.id",

    'category': 'Juragan',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'auth_oauth',
        'web_notify',
        'rsa',
        'rsa_api',
    ],

    # always loaded
    'data': [
        # group
        'security/res_groups.xml',

        # data
        'data/ir_cron.xml',
        'data/ir_config.xml',
        'data/webhook_server.xml',

        # global action
        'views/action.xml',

        # view
        'views/views.xml',
        # 'views/remote_views.xml',
        'views/templates.xml',

        # wizard

        # report paperformat

        # report template

        # report action

        # assets

        # onboarding action

        # action menu

        # action onboarding

        # menu
        'views/menu.xml',

        # security
        'security/ir.model.access.csv',

        # data
    ],
    
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
