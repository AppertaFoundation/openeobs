from openerp.tests.common import TransactionCase


class TestToggleObsStopFlag(TransactionCase):
    """
    Test the toggle Stop Observation button
    """

    def setUp(self):
        super(TestToggleObsStopFlag, self).setUp()
        self.spell_model = self.registry('nh.clinical.spell')
        self.patient_model = self.registry('nh.clinical.patient')
        self.wardboard_model = self.registry('nh.clinical.wardboard')
        cr, uid = self.cr, self.uid
        self.patient_id = self.patient_model.create(cr, uid, {
            'given_name': 'Test',
            'family_name': 'Icicles',
            'patient_identifier': '666',
            'other_identifier': '1337'
        })

        self.spell = self.spell_model.create(cr, uid, {
            'patient_id': self.patient_id,
            'pos_id': 1
        })

    def test_sets_flag_to_passed_value(self):
        """
        Test setting of obs stop value.
        """
        cr, uid = self.cr, self.uid
        self.spell_model.write(cr, uid, self.spell, {'obs_stop': False})
        self.wardboard_model.set_obs_stop_flag(
            cr, uid, self.spell, True, context={'test': 'has_activities'})
        flag = self.spell_model.read(cr, uid, self.spell, ['obs_stop'])
        self.assertTrue(flag.get('obs_stop'))
