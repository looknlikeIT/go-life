# -*- coding: utf-8 -*-
{
    'name': "sale_com_pbo",
    'summary': """Sale coms""",
    'description': """Sale coms""",
    'author': "pbo",
    'category': 'Uncategorized',
    'version': '0.1',
    'depends': ['sale_management', 'account', 'sale_coupon'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        # 'views/templates.xml',
    ],
    'demo': [
        'data/demo.xml',
        'data/data.xml',
    ]
}
