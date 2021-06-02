# -*- coding: utf-8 -*-
{
    'name': "RSA Login",

    'summary': "Encrypt and login Odoo using RSA Token",

    'description': """
        Encrypt and login Odoo using RSA
        1. [SERVER_URL]/rsa/pem/public : to get public_key.pem
        2. [SERVER_URL]/rsa/encrypt/<string:data> : to encrypt data
        3. [SERVER_URL]/web/login/rsa/<string:rsa_token> : to login using rsa token
    """,

    'author': "okkype@sihipo.net",
    'website': "https://sihipo.net/",
    'license': 'OPL-1',
    'currency': 'USD',
    'price': 50.0,

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/function.xml',
        'views/views.xml',
        'views/templates.xml',
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
}
