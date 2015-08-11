# -*- encoding: utf-8 -*-
{
    'name': 'NH eObs Backup',
    'version': '0.1',
    'category': 'Clinical',
    'license': 'AGPL-3',
    'summary': '',
    'description': """ Automatic backups for NHClinical """,
    'author': 'Neova Health',
    'website': 'http://www.neovahealth.co.uk/',
    'depends': ['nh_eobs'],
    'data': ['data/cron.xml',
             'views/config_view.xml'],
    'qweb': [],
    'application': True,
    'installable': True,
    'active': False,
}