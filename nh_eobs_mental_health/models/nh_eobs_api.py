from openerp.osv import orm


class NHeObsAPI(orm.AbstractModel):
    """
        Defines attributes and methods used by `Open eObs` in the making of
        patient observations.

        ``_active_observations`` are the observation types supported by
        eObs.
        """

    _name = 'nh.eobs.api'
    _inherit = 'nh.eobs.api'
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
            'type': 'food_fluid',
            'name': 'Daily Food and Fluid'
        },
        {
            'type': 'blood_sugar',
            'name': 'Blood Glucose'
        },
        {
            'type': 'stools',
            'name': 'Bristol Stool Scale'
        },
        {
            'type': 'gcs',
            'name': 'Glasgow Coma Scale (GCS)'
        },
        {
            'type': 'pbp',
            'name': 'Postural Blood Pressure'
        }
    ]

    def get_active_observations(self, cr, uid, patient_id, context=None):
        """
        Returns all active observation types supported by eObs, if the
        :class:`patient<base.nh_clinical_patient>` has an active
        :class:`spell<spell.nh_clinical_spell>`.

        :param cr: Odoo Cursor
        :param uid: User doing operation
        :param patient_id: id of patient
        :type patient_id: int
        :param context: Odoo context
        :returns: list of all observation types
        :rtype: list
        """
        spell_model = self.pool['nh.clinical.spell']
        spell_id = spell_model.search(cr, uid, [
            ['patient_id', '=', patient_id],
            ['state', 'not in', ['completed', 'cancelled']]
        ], context=context)
        if spell_id:
            spell_id = spell_id[0]
            obs_stopped = spell_model.read(
                cr, uid, spell_id, ['obs_stop'], context=context)\
                .get('obs_stop')
            if obs_stopped:
                return []
        return super(NHeObsAPI, self)\
            .get_active_observations(cr, uid, patient_id, context=context)

    def transfer(self, cr, uid, hospital_number, data, context=None):
        """
        Extends
        :meth:`transfer()<api.nh_clinical_api.transfer>`, transferring
        a :class:`patient<base.nh_clinical_patient>` to a
        :class:`location<base.nh_clinical_location>`.

        - Set transferred patients to not have obs_stop flag set
        :param cr: Odoo cursor
        :param uid: User doing the operation
        :param hospital_number: `hospital number` of the patient
        :type hospital_number: str
        :param data: dictionary parameter that may contain the key
            ``location``
        :param context: Odoo Context
        :returns: ``True``
        :rtype: bool
        """
        spell_model = self.pool['nh.clinical.spell']
        patient_model = self.pool['nh.clinical.patient']
        wardboard_model = self.pool['nh.clinical.wardboard']
        patient_id = patient_model.search(cr, uid, [
            ['other_identifier', '=', hospital_number]
        ])
        spell_id = spell_model.search(cr, uid, [
            ['patient_id', 'in', patient_id],
            ['state', 'not in', ['completed', 'cancelled']]
        ], context=context)
        if spell_id:
            spell_id = spell_id[0]
            spell = spell_model.read(
                cr, uid, spell_id, [
                    'obs_stop',
                    'activity_id'
                ], context=context)
            obs_stopped = spell.get('obs_stop')
            if obs_stopped:
                spell_model.write(
                    cr, uid, spell_id, {'obs_stop': False}, context=context)
                wardboard_model.browse(
                    cr, uid, spell.get('id'), context=context)\
                    .end_patient_monitoring_exception(cancellation=True)
        res = self.pool['nh.clinical.api'].transfer(
            cr, uid, hospital_number, data, context=context)
        return res
