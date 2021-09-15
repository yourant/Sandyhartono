# -*- coding: utf-8 -*-
{
    'name': "Secure and Encrypted REST API",

    'summary': "Secure and Encrypted REST API Using RSA Authentication",

    'description': "Secure and Encrypted REST API Using RSA Authentication",

    'author': "okkype@gmail.com",
    'website': "https://www.linkedin.com/in/okky-permana-sihipo/",
    'license': 'OPL-1',
    'currency': 'USD',
    'price': 100.0,

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'API',
    'version': '12.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'rsa'],

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
    
    'images': ['static/description/banner.png'],
}
