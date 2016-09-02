from openerp.osv import orm, osv, fields


class NHClinicalWardboard(orm.Model):

    _name = 'nh.clinical.wardboard'
    _inherit = 'nh.clinical.wardboard'

    def _get_obs_stop_from_spell(self, cr, uid, ids, field_name, arg,
                                 context=None):
        """
        Function field to return obs_stop flag from spell
        :param cr: Odoo cursor
        :param uid: User ID of user doing operatoin
        :param ids: Ids to read
        :param field_name: name of field
        :param arg: arguments
        :param context: Odoo context
        :return: obs_stop flag from spell
        """
        spell_model = self.pool['nh.clinical.spell']
        flags = spell_model.read(cr, uid, ids, ['obs_stop'], context=context)
        return dict([(rec.get('id'), rec.get('obs_stop')) for rec in flags])

    _columns = {
        'obs_stop': fields.function(_get_obs_stop_from_spell, type='boolean')
    }

    def toggle_obs_stop(self, cr, uid, ids, context=None):
        """
        Handle button press on 'Stop Observations'/'Restore Observation' button
        :param cr: Odoo cursor
        :param uid: User doing the action
        :param ids: IDs of wardboard
        :param context: Odoo context
        :return: True
        """
        spell_model = self.pool['nh.clinical.spell']
        if isinstance(ids, list):
            ids = ids[0]
        wardboard_obj = self.read(cr, uid, ids, context=context)
        spell_activity_id = wardboard_obj.get('spell_activity_id')[0]
        patient = wardboard_obj.get('patient_id')
        spell_id = spell_model.search(
            cr, uid, [['patient_id', '=', patient[0]]])
        if not spell_id:
            raise ValueError('No spell found for patient')
        self.toggle_obs_stop_flag(cr, uid, spell_id[0], context=context)
        if self.spell_has_open_escalation_tasks(cr, uid, spell_activity_id,
                                                context=context):
            # action_model = self.pool['ir.ui.view']
            # view_id = action_model.search(cr, uid, [
            #     ['name', '=', 'Wardboard Open Escalation Tasks View']
            # ])
            # if view_id and isinstance(view_id, list):
            #     view_id = view_id[0]
            # return {
            #     'name': 'Warning!',
            #     'view_type': 'form',
            #     'view_mode': 'form',
            #     'views': [(view_id, 'form')],
            #     'res_model': 'nh.clinical.wardboard.exception',
            #     'view_id': view_id,
            #     'type': 'ir.actions.act_windo.view',
            #     'res_id': ids,
            #     'target': 'new',
            #     'context': {},
            # }
            return True
        else:
            return True

    def toggle_obs_stop_flag(self, cr, uid, spell_id, context=None):
        """
        Toggle the obs_stop flag on the spell object
        :param cr: Odoo cursor
        :param uid: User doing the action
        :param spell_id: spell to toggle
        :param context: context
        :return: True
        """
        spell_model = self.pool['nh.clinical.spell']
        spell = spell_model.read(cr, uid, spell_id, ['obs_stop'])
        obs_stop = spell.get('obs_stop')
        return spell_model.write(cr, uid, spell_id, {'obs_stop': not obs_stop})

    def spell_has_open_escalation_tasks(self, cr, uid, spell_activity_id,
                                        context=None):
        """
        Check to see if spell has any open escalation tasks
        :param cr: Odoo cursor
        :param uid: User carrying out operation
        :param spell_activity_id: IDs of the spell
        :param context: Odoo context
        :return: True if open tasks, False if not
        """
        activity_model = self.pool['nh.activity']
        escalation_task_domain = [
            ['data_model', 'like', 'nh.clinical.notification.%'],
            ['state', 'not in', ['completed', 'cancelled']],
            ['spell_activity_id', '=', spell_activity_id]
        ]
        return any(activity_model.search(
            cr, uid, escalation_task_domain, context=context))


class PatientMonitoringException(orm.TransientModel):

    _name = 'nh.clinical.wardboard.exception'

    def fields_view_get(self, cr, uid, view_id=None, view_type='form',
                        context=None, toolbar=False, submenu=False):
        result = super(PatientMonitoringException, self)\
            .fields_view_get(
            cr, uid, view_id, view_type, context, toolbar, submenu)
        active_id = context.get('active_id')
        if active_id:
            patient_model = self.pool['nh.clinical.patient']
            patient_name = patient_model.read(
                cr, uid, active_id, ['display_name']).get('display_name')
        else:
            patient_name = ''
        result['arch'] = result['arch'].replace('_patient_name_',
                                                    patient_name)
        return result