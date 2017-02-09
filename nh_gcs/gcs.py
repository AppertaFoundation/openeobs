# -*- coding: utf-8 -*-
# Part of Open eObs. See LICENSE file for full copyright and licensing details.
"""
`gcs.py` defines the Glasgow Coma Scale observation class and its
standard behaviour and policy triggers based on this worldwide standard.
"""
import bisect
import logging

from openerp import SUPERUSER_ID
from openerp.osv import orm, fields, osv

_logger = logging.getLogger(__name__)


class nh_clinical_patient_observation_gcs(orm.Model):
    """
    Represents an Glasgow Coma Scale
    :class:`observation<observations.nh_clinical_patient_observation>`
    which stores three parameters that are used as a way to communicate
    about the level of consciousness of
    :class:`patients<base.nh_clinical_patient>` with acute brain injury.

    The basis of the scale system are the following parameters:
    Eye response: spontaneous, to sound, to pressure, none.
    Verbal response: orientated, confused, words, sounds, none.
    Motor response: obey commands, localising, normal flexion, abnormal
    flexion, extension, none.
    """
    _name = 'nh.clinical.patient.observation.gcs'
    _inherit = ['nh.clinical.patient.observation']
    _required = ['eyes', 'verbal', 'motor']
    _description = "GCS Observation"
    _eyes_selection = [
        ('4', 'Spontaneous'),
        ('3', 'To Sound'),
        ('2', 'To Pressure'),
        ('1', 'None'),
        ('0', 'Not Testable')
    ]
    _verbal_selection = [
        ('5', 'Orientated'),
        ('4', 'Confused'),
        ('3', 'Words'),
        ('2', 'Sounds'),
        ('1', 'None'),
        ('0', 'Not Testable')
    ]
    _motor_selection = [
        ('6', 'Obey Commands'),
        ('5', 'Localising'),
        ('4', 'Normal Flexion'),
        ('3', 'Abnormal Flexion'),
        ('2', 'Extension'),
        ('1', 'None'),
        ('0', 'Not Testable')
    ]

    """
    Default GCS policy has 5 different scenarios:
        case 0: 30 min frequency
        case 1: 1 hour frequency
        case 2: 2 hour frequency
        case 3: 4 hour frequency
        case 4: 12 hour frequency (no clinical risk)
    """
    _POLICY = {'ranges': [5, 9, 13, 14],
               'case': '01234',
               'frequencies': [30, 60, 120, 240, 720],
               'notifications': [[], [], [], [], []]}

    def calculate_score(self, gcs_data):
        """
        Computes the score based on the GCS parameters provided.

        :param gcs_data: The GCS parameters: ``eyes``, ``verbal`` and
                         ``motor``.
        :type gcs_data: dict
        :returns: ``score``
        :rtype: dict
        """
        eyes = 1 if gcs_data['eyes'] == 'C' else int(gcs_data['eyes'])
        verbal = 1 if gcs_data['verbal'] == 'T' else int(gcs_data['verbal'])
        motor = int(gcs_data['motor'])

        return {'score': eyes+verbal+motor}

    def _get_score(self, cr, uid, ids, field_names, arg, context=None):
        res = {}
        for gcs in self.browse(cr, uid, ids, context):
            res[gcs.id] = self.calculate_score(
                {'eyes': gcs.eyes, 'verbal': gcs.verbal, 'motor': gcs.motor})
            _logger.debug(
                "Observation GCS activity_id=%s gcs_id=%s score: %s"
                % (gcs.activity_id.id, gcs.id, res[gcs.id]))
        return res

    _columns = {
        'score': fields.function(
            _get_score, type='integer', multi='score', string='Score', store={
                'nh.clinical.patient.observation.gcs':
                    (lambda self, cr, uid, ids, ctx: ids, [], 10)}),
        'eyes': fields.selection(_eyes_selection, 'Eyes Open'),
        'verbal': fields.selection(_verbal_selection, 'Best Verbal Response'),
        'motor': fields.selection(_motor_selection, 'Best Motor Response')
    }

    _defaults = {
        'frequency': 60
    }

    _form_description = [
        {
            'name': 'meta',
            'type': 'meta',
            'score': True,
        },
        {
            'name': 'eyes',
            'type': 'selection',
            'label': 'Eyes Open',
            'selection': _eyes_selection,
            'initially_hidden': False,
            'mandatory': True
        },
        {
            'name': 'verbal',
            'type': 'selection',
            'label': 'Best Verbal Response',
            'selection': _verbal_selection,
            'initially_hidden': False,
            'mandatory': True
        },
        {
            'name': 'motor',
            'type': 'selection',
            'label': 'Best Motor Response',
            'selection': _motor_selection,
            'initially_hidden': False,
            'mandatory': True
        }
    ]

    def complete(self, cr, uid, activity_id, context=None):
        """
        It determines which acuity case the current observation is in
        with the stored data and responds to the different policy
        triggers accordingly defined on the ``_POLICY`` dictionary.

        :returns: ``True``
        :rtype: bool
        """
        activity_pool = self.pool['nh.activity']
        api_pool = self.pool['nh.clinical.api']
        groups_pool = self.pool['res.groups']
        activity = activity_pool.browse(cr, uid, activity_id, context=context)
        case = int(self._POLICY['case'][bisect.bisect_left(
            self._POLICY['ranges'], activity.data_ref.score)])
        hcagroup_ids = groups_pool.search(
            cr, uid, [('users', 'in', [uid]),
                      ('name', '=', 'NH Clinical HCA Group')])
        nursegroup_ids = groups_pool.search(
            cr, uid, [('users', 'in', [uid]),
                      ('name', '=', 'NH Clinical Nurse Group')])
        group = nursegroup_ids and 'nurse' or hcagroup_ids and 'hca' or False

        # TRIGGER NOTIFICATIONS
        api_pool.trigger_notifications(cr, uid, {
            'notifications': self._POLICY['notifications'][case],
            'parent_id': activity.parent_id.id,
            'creator_id': activity_id,
            'patient_id': activity.data_ref.patient_id.id,
            'model': self._name,
            'group': group
        }, context=context)

        return super(nh_clinical_patient_observation_gcs, self).complete(
            cr, SUPERUSER_ID, activity_id, context)

    def create_activity(self, cr, uid, vals_activity=None, vals_data=None,
                        context=None):
        """
        When creating a new activity of this type, an exception will be
        raised if the :class:`spell<base.nh_clinical_spell>` already has
        an open GCS.

        :returns: :class:`activity<activity.nh_activity>` id.
        :rtype: int
        """
        if not vals_activity:
            vals_activity = {}
        if not vals_data:
            vals_data = {}
        assert vals_data.get('patient_id'), "patient_id is a required field!"
        activity_pool = self.pool['nh.activity']
        domain = [['patient_id', '=', vals_data['patient_id']],
                  ['data_model', '=', self._name],
                  ['state', 'in', ['new', 'started', 'scheduled']]]
        ids = activity_pool.search(cr, SUPERUSER_ID, domain)
        if len(ids):
            raise osv.except_osv("GCS Create Error!",
                                 "Having more than one activity of type '%s' "
                                 "is restricted. Terminate activities with "
                                 "ids=%s first" % (self._name, str(ids)))
        return super(
            nh_clinical_patient_observation_gcs, self).create_activity(
            cr, uid, vals_activity, vals_data, context)
