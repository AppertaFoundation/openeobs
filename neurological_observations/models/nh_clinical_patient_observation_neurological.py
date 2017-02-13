# -*- coding: utf-8 -*-
from openerp import models, api
from openerp.addons.nh_observations import fields as obs_fields


class NhClinicalPatientObservationNeurological(models.Model):

    _name = 'nh.clinical.patient.observation.neurological'
    _inherit = 'nh.clinical.patient.observation.gcs'

    _pupil_size_selection = [
        ['8', '8mm'],
        ['7', '7mm'],
        ['6', '6mm'],
        ['5', '5mm'],
        ['4', '4mm'],
        ['3', '3mm'],
        ['2', '2mm'],
        ['1', '1mm'],
        ['not observable', 'Not Observable']
    ]
    _pupil_reaction_selection = [
        ('+', '+'),
        ('-', '-'),
        ('not testable', 'Not Testable')
    ]
    _limb_movement_selection = [
        ('normal power', 'Normal Power'),
        ('mild weakness', 'Mild Weakness'),
        ('severe weakness', 'Severe Weakness'),
        ('spastic flexion', 'Spastic Flexion'),
        ('extension', 'Extension'),
        ('no response', 'No Response'),
        ('not observable', 'Not Observable')
    ]

    _description = "Neurological Observation"
    # TODO Remove when EOBS-982 complete.
    # Also decides the order fields are displayed in the mobile view.
    _required = [
        'eyes', 'verbal', 'motor', 'pupil_right_size', 'pupil_right_reaction',
        'pupil_left_size', 'pupil_left_reaction',
        'limb_movement_left_arm', 'limb_movement_right_arm',
        'limb_movement_left_leg', 'limb_movement_right_leg'
    ]

    pupil_right_size = obs_fields.Selection(
        _pupil_size_selection, 'Pupil Right - Size')
    pupil_right_reaction = obs_fields.Selection(
        _pupil_reaction_selection, 'Pupil Right - Reaction'
    )
    pupil_left_size = obs_fields.Selection(
        _pupil_size_selection, 'Pupil Left - Size')
    pupil_left_reaction = obs_fields.Selection(
        _pupil_reaction_selection, 'Pupil Left - Reaction'
    )
    limb_movement_left_arm = obs_fields.Selection(
        _limb_movement_selection, 'Limb Movement - Left Arm'
    )
    limb_movement_right_arm = obs_fields.Selection(
        _limb_movement_selection, 'Limb Movement - Right Arm'
    )
    limb_movement_left_leg = obs_fields.Selection(
        _limb_movement_selection, 'Limb Movement - Left Leg'
    )
    limb_movement_right_leg = obs_fields.Selection(
        _limb_movement_selection, 'Limb Movement - Right leg'
    )

    @api.model
    def get_form_description(self, patient_id):
        """
        Returns a list of dicts that represent the form description used by
        the mobile

        :param patient_id: ID for the patient
        :return: list of dicts
        """
        res = super(NhClinicalPatientObservationNeurological, self)\
            .get_form_description(patient_id)
        for input in res:
            if input.get('type') == 'meta':
                input['partial_flow'] = 'score'
        return res

    @api.model
    def get_data_visualisation_resource(self):
        """
        Returns URL of JS file to plot data visualisation so can be loaded on
        mobile and desktop

        :return: URL of JS file to plot graph
        :rtype: str
        """
        return '/neurological_observations/static/src/js/chart.js'
