from openerp.osv import orm, osv, fields
from datetime import datetime as dt, timedelta as td
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF
from openerp.tools.translate import _
from openerp import SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)


class nh_eobs_api(orm.AbstractModel):
    _name = 'nh.eobs.api'
    _active_observations = [
        {
            'type': 'ews',
            'name': 'National Early Warning Score (NEWS)'
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
            'name': 'Bristol Stool Scale'
        },
        {
            'type': 'gcs',
            'name': 'Glasglow Coma Scale (GCS)'
        },
        {
            'type': 'pbp',
            'name': 'Postural Blood Pressure'
        }
    ]

    def _check_activity_id(self, cr, uid, activity_id, context=None):
        activity_pool = self.pool['nh.activity']
        domain = [('id', '=', activity_id)]
        activity_ids = activity_pool.search(cr, uid, domain, context=context)
        if not activity_ids:
            raise osv.except_osv(_('Error!'), 'Activity ID not found: %s' % activity_id)
        return True

    def check_activity_access(self, cr, uid, activity_id, context=None):
        activity_pool = self.pool['nh.activity']
        domain = [('id', '=', activity_id), '|', ('user_ids', 'in', [uid]), ('user_id', '=', uid)]
        activity_ids = activity_pool.search(cr, uid, domain, context=context)
        if not activity_ids:
            return False
        user_id = activity_pool.read(cr, uid, activity_id, ['user_id'], context=context)['user_id']
        if user_id and user_id[0] != uid:
            return False
        return True

    def _create_activity(self, cr, uid, data_model, vals_activity=None, vals_data=None, context=None):
        model_pool = self.pool[data_model]
        activity_id = model_pool.create_activity(cr, uid, vals_activity, vals_data, context=context)
        _logger.debug("Activity created id=%s, data_model=%s\n vals_activity: %s\n vals_data: %s"
                     % (activity_id, data_model, vals_activity, vals_data))
        return activity_id

    def _cancel_activity(self, cr, uid, patient_id, activity_type, context=None):
        # Y: what if more than one activities of the type for the patient exist?
        patient_pool = self.pool['nh.clinical.patient']
        if not patient_pool._check_hospital_number(cr, uid, patient_id, context=context):
            raise osv.except_osv(_('Error!'), 'Patient ID not found: %s' % patient_id)
        activity_pool = self.pool['nh.activity']
        domain = [('data_model', '=', activity_type), ('state', '=', 'completed')]
        admit_activity = activity_pool.search(cr, uid, domain, order='date_terminated desc', context=context)
        return activity_pool.cancel(cr, uid, admit_activity[0], context=context)

    def _frequency(self, cr, uid, patient_id, activity_type, operation, data=None, context=None):
        if not activity_type:
            raise osv.except_osv(_('Error!'), 'Activity type not valid')
        field_name = activity_type+'_frequency'
        spell_pool = self.pool['nh.clinical.spell']
        domain = [('patient_id', '=', patient_id), ('state', 'not in', ['completed', 'cancelled'])]
        spell_ids = spell_pool.search(cr, SUPERUSER_ID, domain, context=context)
        if not spell_ids:
            raise osv.except_osv(_('Error!'), 'Spell not found')
        if operation == 'get':
            return spell_pool.read(cr, SUPERUSER_ID, spell_ids, [field_name], context=context)
        else:
            return spell_pool.write(cr, SUPERUSER_ID, spell_ids, {field_name: data['frequency']}, context=context)

    # ALTERNATIVE TO GET ACTIVITIES FOR PATIENT IF WE ONLY HAVE SPELL ID
    def get_activities_for_spell(self, cr, uid, spell_id, activity_type, start_date=None, end_date=None, context=None):
        spell_pool = self.pool['nh.clinical.spell']
        spell = spell_pool.browse(cr, uid, spell_id, context=None)
        return self.get_activities_for_patient(cr, uid, spell.patient_id.id, activity_type, start_date, end_date, context=context)

    def get_share_users(self, cr, uid, context=None):
        result = []
        user_pool = self.pool['res.users']
        activity_pool = self.pool['nh.activity']
        user = user_pool.browse(cr, SUPERUSER_ID, uid, context=context)
        groups = [g.name for g in user.groups_id]
        share_groups = ['NH Clinical Ward Manager Group', 'NH Clinical Nurse Group', 'NH Clinical HCA Group']
        while share_groups[0] not in groups and len(share_groups) > 0:
            share_groups.remove(share_groups[0])
        domain = [['id', '!=', uid], ['groups_id.name', 'in', share_groups]]
        user_ids = user_pool.search(cr, uid, domain, context=context)
        for user_id in user_ids:
            user_data = user_pool.read(cr, SUPERUSER_ID, user_id, ['name'])
            patients_number = len(activity_pool.search(cr, uid, [
                ['user_ids', 'in', user_id],
                ['data_model', '=', 'nh.clinical.spell'],
                ['state', 'not in', ['cancelled', 'completed']]], context=context))
            result.append({
                'name': user_data['name'],
                'id': user_id,
                'patients': patients_number
            })
        return result

    # # # # # # # #
    #  ACTIVITIES #
    # # # # # # # #

    def get_activities(self, cr, uid, ids, context=None):
        """
        Return a list of activities
        :param ids: ids of the activities we want. If empty returns all activities.
        """

        domain = [('id', 'in', ids)] if ids else [
            ('state', 'not in', ['completed', 'cancelled']),
            '|', ('date_scheduled', '<=', (dt.now()+td(days=1)).strftime(DTF)),
            ('date_deadline', '<=', (dt.now()+td(days=1)).strftime(DTF)),
            ('user_ids', 'in', [uid])
        ]
        activity_pool = self.pool['nh.activity']
        activity_ids = activity_pool.search(cr, uid, domain, context=context)
        activity_ids_sql = ','.join(map(str, activity_ids))
        sql = """
        with
            completed_ews as(
                select
                    ews.id,
                    spell.patient_id,
                    ews.score,
                    ews.clinical_risk,
                    rank() over (partition by spell.patient_id order by activity.date_terminated desc, activity.id desc)
                from nh_clinical_spell spell
                left join nh_clinical_patient_observation_ews ews on ews.patient_id = spell.patient_id
                inner join nh_activity activity on ews.activity_id = activity.id
                where activity.state = 'completed' and ews.none_values = '[]'
            )
        select activity.id,
            activity.summary,
            patient.id as patient_id,
            ews1.clinical_risk,
            case
                when activity.date_scheduled is not null then activity.date_scheduled::text
                when activity.date_deadline is not null then activity.date_deadline::text
                else ''
            end as deadline,
            case
                when activity.date_scheduled is not null and greatest(now() at time zone 'UTC',activity.date_scheduled) != activity.date_scheduled then 'overdue: ' || to_char(justify_hours(greatest(now() at time zone 'UTC',activity.date_scheduled) - least(now() at time zone 'UTC',activity.date_scheduled)), 'HH24:MI') || ' hours'
                when activity.date_scheduled is not null and greatest(now() at time zone 'UTC',activity.date_scheduled) = activity.date_scheduled then to_char(justify_hours(greatest(now() at time zone 'UTC',activity.date_scheduled) - least(now() at time zone 'UTC',activity.date_scheduled)), 'HH24:MI') || ' hours'
                when activity.date_deadline is not null and greatest(now() at time zone 'UTC',activity.date_deadline) != activity.date_deadline then 'overdue: ' || to_char(justify_hours(greatest(now() at time zone 'UTC',activity.date_deadline) - least(now() at time zone 'UTC',activity.date_deadline)), 'HH24:MI') || ' hours'
                when activity.date_deadline is not null and greatest(now() at time zone 'UTC',activity.date_deadline) = activity.date_deadline then to_char(justify_hours(greatest(now() at time zone 'UTC',activity.date_deadline) - least(now() at time zone 'UTC',activity.date_deadline)), 'HH24:MI') || ' hours'
                else to_char((interval '0s'), 'HH24:MI') || ' hours'
            end as deadline_time,
            coalesce(patient.family_name, '') || ', ' || coalesce(patient.given_name, '') || ' ' || coalesce(patient.middle_names,'') as full_name,
            location.name as location,
            location_parent.name as parent_location,
            case
                when ews1.score is not null then ews1.score::text
                else ''
            end as ews_score,
            case
                when ews1.id is not null and ews2.id is not null and (ews1.score - ews2.score) = 0 then 'same'
                when ews1.id is not null and ews2.id is not null and (ews1.score - ews2.score) > 0 then 'down'
                when ews1.id is not null and ews2.id is not null and (ews1.score - ews2.score) < 0 then 'up'
                when ews1.id is null and ews2.id is null then 'none'
                when ews1.id is not null and ews2.id is null then 'first'
                when ews1.id is null and ews2.id is not null then 'no latest' -- shouldn't happen.
            end as ews_trend,
            case
                when position('notification' in activity.data_model)::bool then true
                else false
            end as notification
        from nh_activity activity
        inner join nh_activity spell on spell.id = activity.parent_id
        inner join nh_clinical_patient patient on patient.id = activity.patient_id
        inner join nh_clinical_location location on location.id = spell.location_id
        inner join nh_clinical_location location_parent on location_parent.id = location.parent_id
        left join completed_ews ews1 on ews1.patient_id = activity.patient_id and ews1.rank = 1
        left join completed_ews ews2 on ews2.patient_id = activity.patient_id and ews2.rank = 2
        where activity.id in (%s)
        order by deadline asc, activity.id desc
        """ % activity_ids_sql
        activity_values = []
        if activity_ids:
            cr.execute(sql)
            activity_values = cr.dictfetchall()
        return activity_values

    def get_assigned_activities(self, cr, uid, activity_type=None, context=None):
        """
        Get open assigned activities of the specified type (any by default).
        """
        activity_pool = self.pool['nh.activity']
        domain = [['state', 'not in', ['cancelled', 'completed']],
                  ['user_id', '=', uid]]
        if activity_type:
            domain.append(['data_model', '=', activity_type])
        activity_ids = activity_pool.search(cr, uid, domain, context=context)
        return activity_ids

    def cancel(self, cr, uid, activity_id, data, context=None):
        """
        Cancel an activity
        """
        if not data:
            data = {}
        activity_pool = self.pool['nh.activity']
        self._check_activity_id(cr, uid, activity_id, context=context)
        activity_pool.submit(cr, uid, activity_id, data, context=context)
        return activity_pool.cancel(cr, uid, activity_id, context=context)

    def submit(self, cr, uid, activity_id, data, context=None):
        """
        Submit an activity update
        """
        activity_pool = self.pool['nh.activity']
        self._check_activity_id(cr, uid, activity_id, context=context)
        if not self.check_activity_access(cr, uid, activity_id, context=context):
            raise osv.except_osv(_('Error!'), 'User ID %s not allowed to update this activity: %s' % (uid, activity_id))
        return activity_pool.submit(cr, uid, activity_id, data, context=context)

    def unassign(self, cr, uid, activity_id, context=None):
        """
        Unassign the activity from the user.
        """
        activity_pool = self.pool['nh.activity']
        self._check_activity_id(cr, uid, activity_id, context=context)
        if not self.check_activity_access(cr, uid, activity_id, context=context):
            raise osv.except_osv(_('Error!'), 'User ID %s not allowed to unassign this activity: %s' % (uid, activity_id))
        return activity_pool.unassign(cr, uid, activity_id, context=context)

    def unassign_my_activities(self, cr, uid, context=None):
        """calls unassign for every activity the user is assigned to.
        It doesn't include activities that are always tied to a specific user."""
        activity_pool = self.pool['nh.activity']
        domain = [['user_id', '=', uid],
                  ['data_model', 'not in', ['nh.clinical.notification.hca', 'nh.clinical.patient.follow']],
                  ['state', 'not in', ['completed', 'cancelled']]]
        activity_ids = activity_pool.search(cr, uid, domain, context=context)
        [self.unassign(cr, uid, aid, context=context) for aid in activity_ids]
        return True

    def assign(self, cr, uid, activity_id, data, context=None):
        """
        Assign an activity to a user.
        """
        if not data:
            data = {}
        activity_pool = self.pool['nh.activity']
        user_pool = self.pool['res.users']
        user_id = uid
        self._check_activity_id(cr, uid, activity_id, context=context)
        if data.get('user_id'):
            user_id = data['user_id']
            domain = [('id', '=', user_id)]
            user_ids = user_pool.search(cr, uid, domain, context=context)
            if not user_ids:
                raise osv.except_osv(_('Error!'), 'User ID not found: %s' % user_id)
            if not self.check_activity_access(cr, user_id, activity_id, context=context):
                raise osv.except_osv(_('Error!'), 'User ID %s not allowed to assign this activity: %s' % (user_id, activity_id))
        return activity_pool.assign(cr, uid, activity_id, user_id, context=context)

    def complete(self, cr, uid, activity_id, data, context=None):
        """
        Complete an activity.
        """
        activity_pool = self.pool['nh.activity']
        self._check_activity_id(cr, uid, activity_id, context=context)
        if not self.check_activity_access(cr, uid, activity_id, context=context):
            raise osv.except_osv(_('Error!'), 'User ID %s not allowed to complete this activity: %s' % (uid, activity_id))
        activity_pool.submit(cr, uid, activity_id, data, context=context)
        return activity_pool.complete(cr, uid, activity_id, context=context)

    def get_cancel_reasons(self, cr, uid, context=None):
        cancel_pool = self.pool['nh.cancel.reason']
        reason_ids = cancel_pool.search(cr, uid, [], context=context)
        reasons = []
        for reason in cancel_pool.browse(cr, uid, reason_ids, context=context):
            if not reason.system:
                reasons.append({'id':reason.id, 'name': reason.name})
        return reasons

    def get_form_description(self, cr, uid, patient_id, data_model, context=None):
        """
        :return: The form description dictionary
        """
        model_pool = self.pool[data_model]
        return model_pool.get_form_description(cr, uid, patient_id, context=context)

    def is_cancellable(self, cr, uid, data_model, context=None):
        model_pool = self.pool[data_model]
        return model_pool.is_cancellable(cr, uid, context=context) if 'notification' in data_model else False

    def get_activity_score(self, cr, uid, data_model, data, context=None):
        model_pool = self.pool[data_model]
        return model_pool.calculate_score(data) if 'observation' in data_model else False

    def get_active_observations(self, cr, uid, context=None):
        user = self.pool['res.users'].browse(cr, 1, uid, context=context)
        groups = [g.name for g in user.groups_id]
        if 'NH Clinical Nurse Group' in groups or 'NH Clinical HCA Group' in groups:
            return self._active_observations
        return []

    # # # # # # #
    #  PATIENTS #
    # # # # # # #

    def get_patient_info(self, cr, uid, hospital_number, context=None):
        """
        Get patient information for a single patient and the list of activities.
        :param hospital_number: expects a Hospital Number. (String)
        :return: dictionary containing the patient fields.
        """
        patient_pool = self.pool['nh.clinical.patient']
        activity_pool = self.pool['nh.activity']
        patient_ids = patient_pool.search(cr, uid, [['other_identifier', '=', hospital_number]], context=context)
        domain = [
            ('patient_id', '=', patient_ids[0]),
            ('state', 'not in', ['cancelled', 'completed']),
            ('data_model', 'not in', ['nh.clinical.spell'])
        ]
        activity_ids = activity_pool.search(cr, uid, domain, context=context)
        activities = activity_pool.read(cr, uid, activity_ids, [], context=context)
        for a in activities:
            if a.get('date_scheduled'):
                scheduled = dt.strptime(a['date_scheduled'], DTF)
                time = scheduled - dt.now() if dt.now() <= scheduled else dt.now() - scheduled
                hours = time.seconds/3600
                minutes = time.seconds/60 - time.seconds/3600*60
                time_string = '{overdue}{days}{hours}:{minutes}'.format(
                    overdue='overdue: ' if dt.now() > scheduled else '',
                    days=str(time.days) + 'Days ' if time.days else '',
                    hours=hours if hours > 9 else '0' + str(hours),
                    minutes=str(minutes if minutes > 9 else '0' + str(minutes)) + ' hours')
                a['time'] = time_string
            else:
                a['time'] = ''
        patient = self.get_patients(cr, uid, patient_ids, context=context)
        patient[0]['activities'] = activities
        return patient

    def get_patients(self, cr, uid, ids, context=None):
        """
        Return a list of patients in dictionary format (containing every field from the table)
        :param ids: ids of the patients we want. If empty returns all patients.
        """
        domain = [
            ('state', '=', 'started'),
            ('patient_id', 'in', ids),
            ('data_model', '=', 'nh.clinical.spell')
        ] if ids else [
            ('state', '=', 'started'),
            ('data_model', '=', 'nh.clinical.spell'),
            ('user_ids', 'in', [uid])
        ]
        activity_pool = self.pool['nh.activity']
        spell_ids = activity_pool.search(cr, uid, domain, context=context)
        spell_ids_sql = ','.join(map(str, spell_ids))
        sql = """
        with
            completed_ews as(
                select
                    ews.id,
                    spell.patient_id,
                    ews.score,
                    ews.three_in_one,
                    ews.clinical_risk,
                    rank() over (partition by spell.patient_id order by activity.date_terminated desc, activity.id desc)
                from nh_clinical_spell spell
                left join nh_clinical_patient_observation_ews ews on ews.patient_id = spell.patient_id
                inner join nh_activity activity on ews.activity_id = activity.id
                where activity.state = 'completed' and ews.none_values = '[]'
            ),
            scheduled_ews as(
                select
                    spell.patient_id,
                    activity.date_scheduled,
                    ews.frequency,
                    rank() over (partition by spell.patient_id order by activity.date_terminated desc, activity.id desc)
                from nh_clinical_spell spell
                left join nh_clinical_patient_observation_ews ews on ews.patient_id = spell.patient_id
                inner join nh_activity activity on ews.activity_id = activity.id
                where activity.state = 'scheduled'
            )
        select patient.id,
            patient.dob,
            patient.gender,
            patient.sex,
            patient.other_identifier,
            case char_length(patient.patient_identifier) = 10
                when true then substring(patient.patient_identifier from 1 for 3) || ' ' || substring(patient.patient_identifier from 4 for 3) || ' ' || substring(patient.patient_identifier from 7 for 4)
                else patient.patient_identifier
            end as patient_identifier,
            coalesce(patient.family_name, '') || ', ' || coalesce(patient.given_name, '') || ' ' || coalesce(patient.middle_names,'') as full_name,
            case
                when ews0.date_scheduled is not null and greatest(now() at time zone 'UTC',ews0.date_scheduled) != ews0.date_scheduled then 'overdue: ' || to_char(justify_hours(greatest(now() at time zone 'UTC',ews0.date_scheduled) - least(now() at time zone 'UTC',ews0.date_scheduled)), 'HH24:MI') || ' hours'
                when ews0.date_scheduled is not null and greatest(now() at time zone 'UTC',ews0.date_scheduled) = ews0.date_scheduled then to_char(justify_hours(greatest(now() at time zone 'UTC',ews0.date_scheduled) - least(now() at time zone 'UTC',ews0.date_scheduled)), 'HH24:MI') || ' hours'
                else to_char((interval '0s'), 'HH24:MI') || ' hours'
            end as next_ews_time,
            location.name as location,
            location_parent.name as parent_location,
            case
                when ews1.score is not null then ews1.score::text
                else ''
            end as ews_score,
            case
                when ews1.score is not null then ews1.three_in_one
                else False
            end as ews_3in1,
            ews1.clinical_risk,
            case
                when ews1.id is not null and ews2.id is not null and (ews1.score - ews2.score) = 0 then 'same'
                when ews1.id is not null and ews2.id is not null and (ews1.score - ews2.score) > 0 then 'up'
                when ews1.id is not null and ews2.id is not null and (ews1.score - ews2.score) < 0 then 'down'
                when ews1.id is null and ews2.id is null then 'none'
                when ews1.id is not null and ews2.id is null then 'first'
                when ews1.id is null and ews2.id is not null then 'no latest' -- shouldn't happen.
            end as ews_trend,
            case
                when ews0.frequency is not null then ews0.frequency
                else 0
            end as frequency
        from nh_activity activity
        inner join nh_clinical_patient patient on patient.id = activity.patient_id
        inner join nh_clinical_location location on location.id = activity.location_id
        inner join nh_clinical_location location_parent on location_parent.id = location.parent_id
        left join completed_ews ews1 on ews1.patient_id = activity.patient_id and ews1.rank = 1
        left join completed_ews ews2 on ews2.patient_id = activity.patient_id and ews2.rank = 2
        left join scheduled_ews ews0 on ews0.patient_id = activity.patient_id and ews0.rank = 1
        where activity.state = 'started' and activity.data_model = 'nh.clinical.spell' and activity.id in (%s)
        """ % spell_ids_sql
        patient_values = []
        if spell_ids:
            cr.execute(sql)
            patient_values = cr.dictfetchall()
        return patient_values

    def get_followed_patients(self, cr, uid, context=None):
        """
        Return a list of the patients followed by the user in dictionary format (containing every field from the table)
        """
        patient_pool = self.pool['nh.clinical.patient']
        patient_ids = patient_pool.search(cr, uid, [['follower_ids', 'in', [uid]]], context=context)
        patient_ids_sql = ','.join(map(str, patient_ids))
        sql = """
        with
            completed_ews as(
                select
                    ews.id,
                    spell.patient_id,
                    ews.score,
                    ews.three_in_one,
                    ews.clinical_risk,
                    rank() over (partition by spell.patient_id order by activity.date_terminated desc, activity.id desc)
                from nh_clinical_spell spell
                left join nh_clinical_patient_observation_ews ews on ews.patient_id = spell.patient_id
                inner join nh_activity activity on ews.activity_id = activity.id
                where activity.state = 'completed' and ews.none_values = '[]'
            ),
            scheduled_ews as(
                select
                    spell.patient_id,
                    activity.date_scheduled,
                    ews.frequency,
                    rank() over (partition by spell.patient_id order by activity.date_terminated desc, activity.id desc)
                from nh_clinical_spell spell
                left join nh_clinical_patient_observation_ews ews on ews.patient_id = spell.patient_id
                inner join nh_activity activity on ews.activity_id = activity.id
                where activity.state = 'scheduled'
            )
        select patient.id,
            patient.dob,
            patient.gender,
            patient.sex,
            patient.other_identifier,
            case char_length(patient.patient_identifier) = 10
                when true then substring(patient.patient_identifier from 1 for 3) || ' ' || substring(patient.patient_identifier from 4 for 3) || ' ' || substring(patient.patient_identifier from 7 for 4)
                else patient.patient_identifier
            end as patient_identifier,
            coalesce(patient.family_name, '') || ', ' || coalesce(patient.given_name, '') || ' ' || coalesce(patient.middle_names,'') as full_name,
            case
                when ews0.date_scheduled is not null and greatest(now() at time zone 'UTC',ews0.date_scheduled) != ews0.date_scheduled then 'overdue: ' || to_char(justify_hours(greatest(now() at time zone 'UTC',ews0.date_scheduled) - least(now() at time zone 'UTC',ews0.date_scheduled)), 'HH24:MI') || ' hours'
                when ews0.date_scheduled is not null and greatest(now() at time zone 'UTC',ews0.date_scheduled) = ews0.date_scheduled then to_char(justify_hours(greatest(now() at time zone 'UTC',ews0.date_scheduled) - least(now() at time zone 'UTC',ews0.date_scheduled)), 'HH24:MI') || ' hours'
                else to_char((interval '0s'), 'HH24:MI') || ' hours'
            end as next_ews_time,
            location.name as location,
            location_parent.name as parent_location,
            case
                when ews1.score is not null then ews1.score::text
                else ''
            end as ews_score,
            case
                when ews1.score is not null then ews1.three_in_one
                else False
            end as ews_3in1,
            ews1.clinical_risk,
            case
                when ews1.id is not null and ews2.id is not null and (ews1.score - ews2.score) = 0 then 'same'
                when ews1.id is not null and ews2.id is not null and (ews1.score - ews2.score) > 0 then 'up'
                when ews1.id is not null and ews2.id is not null and (ews1.score - ews2.score) < 0 then 'down'
                when ews1.id is null and ews2.id is null then 'none'
                when ews1.id is not null and ews2.id is null then 'first'
                when ews1.id is null and ews2.id is not null then 'no latest' -- shouldn't happen.
            end as ews_trend,
            case
                when ews0.frequency is not null then ews0.frequency
                else 0
            end as frequency
        from nh_activity activity
        inner join nh_clinical_patient patient on patient.id = activity.patient_id
        inner join nh_clinical_location location on location.id = activity.location_id
        inner join nh_clinical_location location_parent on location_parent.id = location.parent_id
        left join completed_ews ews1 on ews1.patient_id = activity.patient_id and ews1.rank = 1
        left join completed_ews ews2 on ews2.patient_id = activity.patient_id and ews2.rank = 2
        left join scheduled_ews ews0 on ews0.patient_id = activity.patient_id and ews0.rank = 1
        where activity.state = 'started' and activity.data_model = 'nh.clinical.spell' and patient.id in (%s)
        """ % patient_ids_sql
        patient_values = []
        if patient_ids:
            cr.execute(sql)
            patient_values = cr.dictfetchall()
        return patient_values

    def get_invited_users(self, cr, uid, patients, context=None):
        """
        Expects the return value from get_patients or get_followed_patients and adds the users that have an open follow invitation for each patient.
        """
        follow_pool = self.pool['nh.clinical.patient.follow']
        for p in patients:
            follow_ids = follow_pool.search(cr, uid, [
                ['activity_id.state', 'not in', ['completed', 'cancelled']],
                ['patient_ids', 'in', [p['id']]]], context=context)
            p['invited_users'] = [{'id': f.activity_id.user_id.id, 'name': f.activity_id.user_id.name}
                                      for f in follow_pool.browse(cr, uid, follow_ids, context=context)]
        return True

    def get_patient_followers(self, cr, uid, patients, context=None):
        """
        Expects the return value from get_patients or get_followed_patients and adds the followers for each patient.
        """
        patient_pool = self.pool['nh.clinical.patient']
        for p in patients:
            patient = patient_pool.browse(cr, uid, p['id'], context=context)
            p['followers'] = [{'id': f.id, 'name': f.name} for f in patient.follower_ids]
        return True

    def update(self, cr, uid, patient_id, data, context=None):
        """
        Update patient information
        """
        activity_pool = self.pool['nh.activity']
        patient_pool = self.pool['nh.clinical.patient']
        if not patient_pool._check_hospital_number(cr, uid, patient_id, context=context):
            nhs_data = data.copy()
            nhs_data['other_identifier'] = patient_id
            if not patient_pool._check_nhs_number(cr, uid, data.get('patient_identifier'), nhs_data, context=context):
                _logger.warn("Patient registered from an update call - data available:%s" % data)
                self.register(cr, uid, patient_id, data, context=context)
        data.update({'other_identifier': patient_id})
        update_activity = self._create_activity(cr, uid, 'nh.clinical.adt.patient.update', {}, {}, context=context)
        res = activity_pool.submit(cr, uid, update_activity, data, context=context)
        activity_pool.complete(cr, uid, update_activity, context=context)
        _logger.debug("Patient updated\n data: %s" % data)
        return res

    def register(self, cr, uid, patient_id, data, context=None):
        """
        Registers a new patient into the system
        :param patient_id: Hospital Number of the patient
        :param data: dictionary parameter that may contain the following keys:
            patient_identifier: NHS number
            family_name: Surname
            given_name: Name
            middle_names: Middle names
            dob: Date of birth
            gender: Gender (M/F)
            sex: Sex (M/F)
        """
        activity_pool = self.pool['nh.activity']
        register_activity = self._create_activity(cr, uid, 'nh.clinical.adt.patient.register', {}, {}, context=context)
        data.update({'other_identifier': patient_id})
        activity_pool.submit(cr, uid, register_activity, data, context=context)
        activity_pool.complete(cr, uid, register_activity, context=context)
        _logger.debug("Patient registered\n data: %s" % data)
        return True

    def admit(self, cr, uid, patient_id, data, context=None):
        """
        Admits a patient into the specified location.
        :param patient_id: Hospital number of the patient
        :param data: dictionary parameter that may contain the following keys:
            location: location code where the patient will be admitted. REQUIRED
            start_date: admission start date.
            doctors: consulting and referring doctors list of dictionaries. expected format:
               [...
               {
               'type': 'c' or 'r',
               'code': code string,
               'title':, 'given_name':, 'family_name':, }
               ...]
                if doctor doesn't exist, we create partner, but don't create user for that doctor.
        """
        activity_pool = self.pool['nh.activity']
        spell_timespan_pool = self.pool['nh.clinical.spell.timespan']
        patient_pool = self.pool['nh.clinical.patient']
        if not patient_pool._check_hospital_number(cr, uid, patient_id, context=context):
            nhs_data = data.copy()
            nhs_data['other_identifier'] = patient_id
            patient_pool._check_nhs_number(cr, uid, data.get('patient_identifier'), nhs_data, context=context)
        data.update({'other_identifier': patient_id})
        admit_activity = self._create_activity(cr, uid, 'nh.clinical.adt.patient.admit', {}, {}, context=context)
        activity_pool.submit(cr, uid, admit_activity, data, context=context)
        activity_pool.complete(cr, uid, admit_activity, context=context)
        spell_timespan_pool.start_patient_timespan(cr, uid, patient_id, context=context)
        _logger.debug("Patient admitted\n data: %s" % data)
        return True
    
    def admit_update(self, cr, uid, patient_id, data, context=None):
        """
        Updates the spell information of the patient. Accepts the same parameters as admit.
        """
        activity_pool = self.pool['nh.activity']
        patient_pool = self.pool['nh.clinical.patient']
        if not patient_pool._check_hospital_number(cr, uid, patient_id, context=context):
            nhs_data = data.copy()
            nhs_data['other_identifier'] = patient_id
            patient_pool._check_nhs_number(cr, uid, data.get('patient_identifier'), nhs_data, context=context)
        data.update({'other_identifier': patient_id})
        update_activity = self._create_activity(cr, uid, 'nh.clinical.adt.spell.update', {}, {}, context=context)
        activity_pool.submit(cr, uid, update_activity, data, context=context)
        activity_pool.complete(cr, uid, update_activity, context=context)
        _logger.debug("Admission updated\n data: %s" % data)
        return True
        
    def cancel_admit(self, cr, uid, patient_id, context=None):
        """
        Cancels the open admission of the patient.
        """
        activity_pool = self.pool['nh.activity']
        spell_timespan_pool = self.pool['nh.clinical.spell.timespan']
        patient_pool = self.pool['nh.clinical.patient']
        if not patient_pool._check_hospital_number(cr, uid, patient_id, context=context):
            raise osv.except_osv(_('Error!'), 'Patient ID not found: %s' % patient_id)
        data = {'other_identifier': patient_id}
        cancel_activity = self._create_activity(cr, uid, 'nh.clinical.adt.patient.cancel_admit', {}, {}, context=context)
        activity_pool.submit(cr, uid, cancel_activity, data, context=context)
        spell_timespan_pool.delete_patient_timespans(cr, uid, patient_id, context=context)
        activity_pool.complete(cr, uid, cancel_activity, context=context)
        _logger.debug("Admission cancelled\n data: %s" % data)
        return True

    def discharge(self, cr, uid, patient_id, data, context=None):
        """
        Discharges the patient.
        :param patient_id: Hospital number of the patient
        :param data: dictionary parameter that may contain the following keys:
            discharge_date: patient discharge date.
        """
        spell_timespan_pool = self.pool['nh.clinical.spell.timespan']
        activity_pool = self.pool['nh.activity']
        patient_pool = self.pool['nh.clinical.patient']
        if not patient_pool._check_hospital_number(cr, uid, patient_id, context=context):
            nhs_data = data.copy()
            nhs_data['other_identifier'] = patient_id
            patient_pool._check_nhs_number(cr, uid, data.get('patient_identifier'), nhs_data, context=context)
        patientdb_id = patient_pool.search(cr, uid, [('other_identifier', '=', patient_id)], context=context)
        discharge_activity = self._create_activity(cr, uid, 'nh.clinical.adt.patient.discharge', {'patient_id': patientdb_id[0]}, {'other_identifier': patient_id, 'discharge_date': data.get('discharge_date')}, context=context)
        spell_timespan_pool.end_patient_timespan(cr, uid, patient_id, context=context)
        activity_pool.complete(cr, uid, discharge_activity, context=context)
        _logger.debug("Patient discharged: %s" % patient_id)
        return True

    def cancel_discharge(self, cr, uid, patient_id, context=None):
        """
        Cancels the last discharge of the patient.
        """
        patient_pool = self.pool['nh.clinical.patient']
        if not patient_pool._check_hospital_number(cr, uid, patient_id, context=context):
            raise osv.except_osv(_('Error!'), 'Patient ID not found: %s' % patient_id)
        activity_pool = self.pool['nh.activity']
        patient_pool = self.pool['nh.clinical.patient']
        spell_timespan_pool = self.pool['nh.clinical.spell.timespan']
        patientdb_id = patient_pool.search(cr, uid, [('other_identifier', '=', patient_id)], context=context)
        cancel_discharge_activity = self._create_activity(cr, uid, 'nh.clinical.adt.patient.cancel_discharge', {'patient_id': patientdb_id[0]}, {}, context=context)
        activity_pool.submit(cr, uid, cancel_discharge_activity, {'other_identifier': patient_id}, context=context)
        activity_pool.complete(cr, uid, cancel_discharge_activity, context=context)
        spell_timespan_pool.cancel_changes_patient_timespan(cr, uid, patient_id, context=context)
        _logger.debug("Discharge cancelled for patient: %s" % patient_id)
        return True

    def merge(self, cr, uid, patient_id, data, context=None):
        """
        Merges a specified patient into the patient.
        :param patient_id: Hospital number of the patient we want to merge INTO
        :param data: dictionary parameter that may contain the following keys:
            from_identifier: Hospital number of the patient we want to merge FROM
        """
        patient_pool = self.pool['nh.clinical.patient']
        if not patient_pool._check_hospital_number(cr, uid, patient_id, context=context):
            raise osv.except_osv(_('Error!'), 'Patient ID not found: %s' % patient_id)
        activity_pool = self.pool['nh.activity']
        data.update({'into_identifier': patient_id})
        merge_activity = self._create_activity(cr, uid, 'nh.clinical.adt.patient.merge', {}, {}, context=context)
        activity_pool.submit(cr, uid, merge_activity, data, context=context)
        activity_pool.complete(cr, uid, merge_activity, context=context)
        _logger.debug("Patient merged\n data: %s" % data)
        return True

    def transfer(self, cr, uid, patient_id, data, context=None):
        """
        Transfers the patient to the specified location.
        :param patient_id: Hospital number of the patient
        :param data: dictionary parameter that may contain the following keys:
            location: location code where the patient will be transferred. REQUIRED
        """
        spell_timespan_pool = self.pool['nh.clinical.spell.timespan']
        activity_pool = self.pool['nh.activity']
        patient_pool = self.pool['nh.clinical.patient']
        if not patient_pool._check_hospital_number(cr, uid, patient_id, context=context):
            nhs_data = data.copy()
            nhs_data['other_identifier'] = patient_id
            patient_pool._check_nhs_number(cr, uid, data.get('patient_identifier'), nhs_data, context=context)
        patientdb_id = patient_pool.search(cr, uid, [('other_identifier', '=', patient_id)], context=context)
        data.update({'other_identifier': patient_id})
        transfer_activity = self._create_activity(cr, uid, 'nh.clinical.adt.patient.transfer', {'patient_id': patientdb_id[0]}, {}, context=context)
        activity_pool.submit(cr, uid, transfer_activity, data, context=context)
        activity_pool.complete(cr, uid, transfer_activity, context=context)
        spell_timespan_pool.end_patient_timespan(cr, uid, patient_id, context=context)
        spell_timespan_pool.start_patient_timespan(cr, uid, patient_id, start=dt.now().strftime(DTF), context=context)
        _logger.debug("Patient transferred\n data: %s" % data)
        return True

    def cancel_transfer(self, cr, uid, patient_id, context=None):
        """
        Cancels the last transfer of the patient.
        """
        patient_pool = self.pool['nh.clinical.patient']
        if not patient_pool._check_hospital_number(cr, uid, patient_id, context=context):
            raise osv.except_osv(_('Error!'), 'Patient ID not found: %s' % patient_id)
        activity_pool = self.pool['nh.activity']
        spell_timespan_pool = self.pool['nh.clinical.spell.timespan']
        patientdb_id = patient_pool.search(cr, uid, [('other_identifier', '=', patient_id)], context=context)
        cancel_transfer_activity = self._create_activity(cr, uid, 'nh.clinical.adt.patient.cancel_transfer', {'patient_id': patientdb_id[0]}, {}, context=context)
        activity_pool.submit(cr, uid, cancel_transfer_activity, {'other_identifier': patient_id}, context=context)
        activity_pool.complete(cr, uid, cancel_transfer_activity, context=context)
        spell_timespan_pool.cancel_changes_patient_timespan(cr, uid, patient_id, context=context)
        _logger.debug("Transfer cancelled for patient: %s" % patient_id)
        return True

    def check_patient_responsibility(self, cr, uid, patient_id, context=None):
        api = self.pool['nh.clinical.api']
        spell_activity_id = api.get_patient_spell_activity_id(cr, uid, patient_id, context=context)
        return self.check_activity_access(cr, uid, spell_activity_id, context=context)

    def follow_invite(self, cr, uid, patient_ids, to_user_id, context=None):
        """
        Creates a follow activity for the user to follow the patients in 'patient_ids'
        :param patient_ids: List of integers. Ids of the patients to follow.
        :param to_user_id: Integer. Id of the user to send the invite.
        :return: ID of the follow activity
        """
        if not all([self.check_patient_responsibility(cr, uid, patient_id, context=context) for patient_id in patient_ids]):
            raise osv.except_osv('Error!', 'You are not responsible for this patient.')
        follow_pool = self.pool['nh.clinical.patient.follow']
        follow_activity_id = follow_pool.create_activity(cr, uid, {'user_id': to_user_id}, {
            'patient_ids': [[6, 0, patient_ids]]}, context=context)
        return follow_activity_id

    def remove_followers(self, cr, uid, patient_ids, context=None):
        """
        Remove the followers from the patients provided
        :param patient_ids: List of integers. Ids of the patients to unfollow.
        :return: True if successful
        """
        if not all([self.check_patient_responsibility(cr, uid, patient_id, context=context)for patient_id in patient_ids]):
            raise osv.except_osv('Error!', 'You are not responsible for this patient.')
        activity_pool = self.pool['nh.activity']
        unfollow_pool = self.pool['nh.clinical.patient.unfollow']
        unfollow_activity_id = unfollow_pool.create_activity(cr, uid, {}, {
            'patient_ids': [[6, 0, patient_ids]]}, context=context)
        activity_pool.complete(cr, uid, unfollow_activity_id, context=context)
        return True

    def get_activities_for_patient(self, cr, uid, patient_id, activity_type, start_date=None,
                                end_date=None, context=None):
        """
        Returns a list of activities in dictionary format (containing every field from the table)
        :param patient_id: Postgres ID of the patient to get the activities from.
        :param activity_type: Type of activity we want.
        :param start_date: start date to filter. A month from now by default.
        :param end_date: end date to filter. Now by default.
        """
        start_date = dt.now()-td(days=30) if not start_date else start_date
        end_date = dt.now() if not end_date else end_date
        model_pool = self.pool['nh.clinical.patient.observation.'+activity_type] if activity_type else self.pool['nh.activity']
        domain = [
            ('patient_id', '=', patient_id),
            #('parent_id.state', '=', 'started'),
            ('state', '=', 'completed'),
            ('date_terminated', '>=', start_date.strftime(DTF)),
            ('date_terminated', '<=', end_date.strftime(DTF))] if activity_type \
            else [('patient_id', '=', patient_id), ('state', 'not in', ['completed', 'cancelled'])]
        ids = model_pool.search(cr, SUPERUSER_ID, domain, context=context)
        return model_pool.read(cr, SUPERUSER_ID, ids, [], context=context)

    def create_activity_for_patient(self, cr, uid, patient_id, activity_type, context=None):
        if not activity_type:
            raise osv.except_osv(_('Error!'), 'Activity type not valid')
        model_name = 'nh.clinical.patient.observation.'+activity_type
        user_pool = self.pool['res.users']
        access_pool = self.pool['ir.model.access']
        activity_pool = self.pool['nh.activity']
        user = user_pool.browse(cr, SUPERUSER_ID, uid, context=context)
        groups = [g.id for g in user.groups_id]
        rules_ids = access_pool.search(cr, SUPERUSER_ID, [('model_id', '=', model_name), ('group_id', 'in', groups)], context=context)
        if not rules_ids:
            raise osv.except_osv(_('Error!'), 'Access denied, there are no access rules for these activity type - user groups')
        rules_values = access_pool.read(cr, SUPERUSER_ID, rules_ids, ['perm_responsibility'], context=context)
        if not any([r['perm_responsibility'] for r in rules_values]):
            raise osv.except_osv(_('Error!'), 'Access denied, the user is not responsible for this activity type')
        activity_ids = activity_pool.search(cr, SUPERUSER_ID,
                                            [('patient_id', '=', patient_id),
                                             ('state', 'not in', ['completed', 'cancelled']),
                                             ('data_model', '=', model_name)], context=context)
        if activity_ids:
            return activity_ids[0]
        return self._create_activity(cr, SUPERUSER_ID, model_name, {}, {'patient_id': patient_id}, context=context)

    def get_frequency(self, cr, uid, patient_id, activity_type, context=None):
        return self._frequency(cr, uid, patient_id, activity_type, 'get', context=context)

    def set_frequency(self, cr, uid, patient_id, activity_type, data, context=None):
        return self._frequency(cr, uid, patient_id, activity_type, 'set', data=data, context=context)



