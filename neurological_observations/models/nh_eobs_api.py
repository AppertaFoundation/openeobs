# -*- coding: utf-8 -*-
from openerp.models import Model


class NhEobsApi(Model):

    _name = 'nh.eobs.api'
    _inherit = 'nh.eobs.api'

    # TODO EOBS-981: Admin can set a list of 'active observations' in the UI
    _active_observations = [
        {
            'type': 'ews',
            'name': 'NEWS'
        },
        {
            'type': 'height',
            'name': 'Height'
        },
        {
            'type': 'weight',
            'name': 'Weight'
        },
        {
            'type': 'blood_product',
            'name': 'Blood Product'
        },
        {
            'type': 'blood_sugar',
            'name': 'Blood Sugar'
        },
        {
            'type': 'stools',
            'name': 'Bowel Open'
        },
        {
            'type': 'pbp',
            'name': 'Postural Blood Pressure'
        },
        {
            'type': 'neurological',
            'name': 'Neurological'
        }
    ]