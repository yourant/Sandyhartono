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
    'depends': ['base', 'auth_oauth', 'web_notify'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'data/ir_config.xml',
        'views/action.xml',
        'views/views.xml',
        'views/menu.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
