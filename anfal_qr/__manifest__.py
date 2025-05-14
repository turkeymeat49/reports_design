# -*- coding: utf-8 -*-
{
    "name": "Anfal Invoice",
    'author': 'Digital Harbor',
    'website': 'https://www.digital-harbor.net',
    "support": "support@digital-harbor.com",
    'version': '17.0',
    'category': "Accounting",
    "depends" : ["account","base", "sale_management", "anfal_sales_1"],
    "application" : True,
    "data" : [  
            'security/ir.model.access.csv',
            'views/account_move.xml',
            'report/paperformat.xml',
            'report/custom_layout.xml', 
            'report/contract_layout.xml', 
            'report/invoicing_base.xml',
            ],
    
    "external_dependencies": {
        "python": ["qrcode"],
    },

    'images': ['static/description/background.png', ],
    "auto_install":False,
    "installable" : True,

}
