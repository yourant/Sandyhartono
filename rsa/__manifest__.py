# -*- coding: utf-8 -*-
{
    'name': "RSA Login",

    'summary': "Encrypt and login Odoo using RSA Token",

    'description': "Encrypt and login Odoo using RSA Token",

    'author': "okkype@gmail.com",
    'website': "https://www.linkedin.com/in/okky-permana-sihipo/",
    'license': 'OPL-1',
    'currency': 'USD',
    'price': 100.0,

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'API',
    'version': '12.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/function.xml',
        'views/views.xml',
        'views/templates.xml',
        'data/ir_cron.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    
    "external_dependencies": {
        "python": [
            "Cryptodome",
        ],
        "bin": [],
    },
    
    'images': ['static/description/banner.png'],
}
