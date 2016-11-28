# Part of Open eObs. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-
{
    'name': 'NH eObs Mental Health Defaults',
    'version': '0.1',
    'category': 'Clinical',
    'license': 'AGPL-3',
    'summary': '',
    'description': """     """,
    'author': 'Neova Health',
    'website': 'http://www.neovahealth.co.uk/',
    'depends': [
        'nh_eobs',
        'nh_eobs_mobile'
    ],
    'data': ['data/master_data.xml',
             'views/wardboard_view.xml',
             'views/ward_dashboard_view.xml',
             'views/static_include.xml',
             'views/mobile_override.xml',
             'security/ir.model.access.csv'
             ],
    'qweb': [],
    'application': True,
    'installable': True,
    'active': False,
}
