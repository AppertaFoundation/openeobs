# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from openerp.addons.nh_observations import frequencies
from openerp.addons.nh_odoo_fixes.tests.utils.datetime_test_utils \
    import DatetimeTestUtils
from openerp.tests.common import TransactionCase
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF


class TestPatientRefusalAfterPatientMonitoringException(TransactionCase):

    def setUp(self):
        super(TestPatientRefusalAfterPatientMonitoringException, self).setUp()
        self.patient_model = self.env['nh.clinical.patient']
        self.spell_model = self.env['nh.clinical.spell']
        self.activity_model = self.env['nh.activity']
        self.activity_pool = self.registry('nh.activity')
        self.reason_model = \
            self.env['nh.clinical.patient_monitoring_exception.reason']
        self.wardboard_model = self.env['nh.clinical.wardboard']
        self.wizard_model = \
            self.env['nh.clinical.patient_monitoring_exception.select_reason']
        self.ews_model = self.env['nh.clinical.patient.observation.ews']

        self.patient = self.patient_model.create({
            'given_name': 'Jon',
            'family_name': 'Snow',
            'patient_identifier': 'a_patient_identifier'
        })

        self.spell_activity_id = self.spell_model.create_activity(
            {},
            {'patient_id': self.patient.id, 'pos_id': 1}
        )

        self.spell_activity = self.activity_model.browse(
            self.spell_activity_id
        )

        # Fails in spell.get_patient_by_id() if not started.
        self.activity_pool.start(self.env.cr, self.env.uid,
                                 self.spell_activity_id)

        self.wardboard = self.wardboard_model.new({
            'spell_activity_id': self.spell_activity_id,
            'patient_id': self.patient
        })

        self.observation_test_utils = self.env['observation_test_utils']
        self.datetime_test_utils = DatetimeTestUtils()

    def test_obs_after_refusal_due_in_one_hour(self):
        reason_one = self.reason_model.create({'display_text': 'reason one'})
        self.wardboard.start_patient_monitoring_exception(
            reason_one,
            self.spell_activity.data_ref.id,
            self.spell_activity_id
        )
        self.wardboard.end_patient_monitoring_exception()

        refused_obs = \
            self.ews_model.get_open_obs_activity(self.spell_activity_id)
        obs_activity_after_refused = \
            self.observation_test_utils.refuse_open_obs(
                self.patient.id, self.spell_activity_id
            )

        after_refused_frequency = \
            frequencies.PATIENT_REFUSAL_ADJUSTMENTS['Obs Restart'][0]

        expected = \
            datetime.strptime(refused_obs.date_terminated, DTF) \
            + timedelta(minutes=after_refused_frequency)
        actual = datetime.strptime(
            obs_activity_after_refused.date_scheduled, DTF
        )

        self.datetime_test_utils \
            .assert_datetimes_equal_disregarding_seconds(expected, actual)
