# Part of Open eObs. See LICENSE file for full copyright and licensing details.
from openerp import api, models
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as dtf
from openerp.osv import fields
import json
import copy
from . import helpers


class ObservationReport(models.AbstractModel):
    _name = 'report.nh.clinical.observation_report'

    pretty_date_format = '%H:%M %d/%m/%y'
    wkhtmltopdf_format = "%a %b %d %Y %H:%M:%S GMT"
    patient_id = None

    monitoring_dict = {
        'targeto2': 'nh.clinical.patient.o2target',
        'mrsa_history': 'nh.clinical.patient.mrsa',
        'diabetes_history': 'nh.clinical.patient.diabetes',
        'palliative_care_history': 'nh.clinical.patient.palliative_care',
        'post_surgery_history': 'nh.clinical.patient.post_surgery',
        'critical_care_history': 'nh.clinical.patient.critical_care',
        'patient_monitoring_exception_history':
            'nh.clinical.patient_monitoring_exception'
    }

    @api.multi
    def get_activity_data(self, spell_id, model, start_time, end_time):
        cr, uid = self._cr, self._uid
        activity_model = self.pool['nh.activity']

        states = self._get_allowed_activity_states_for_model(model)
        domain = helpers.build_activity_search_domain(
            spell_id, model, start_time, end_time, states=states
        )
        activity_ids = activity_model.search(cr, uid, domain)
        return activity_model.read(cr, uid, activity_ids)

    def _get_allowed_activity_states_for_model(self, cr, uid, model):
        """
        Returns the states that an activity can be in if it is to be included
        on the observation report.
        :param model:
        :return: string or list of strings.
        :rtype: str or list
        """
        activity_model = self.pool['nh.activity']
        monitoring_models = self.monitoring_dict.values()

        if model in monitoring_models:
            # Add activities of any state to the report for these models.
            return activity_model.get_possible_states()
        else:
            return 'completed'

    def get_model_data(self, spell_id, model, start, end):
        """
        Get activities associated with the passed model and return them as
        a dictionary.
        :param spell_id:
        :param model:
        :param start:
        :param end:
        :return:
        :rtype: dict
        """
        activity_data = self.get_activity_data(spell_id, model, start, end)
        if activity_data:
            self.convert_dates_to_context_dates(activity_data)
        return self.get_model_values(model, activity_data)

    def get_model_values(self, model, activity_data):
        """
        Get values of records associated with the passed activity data
        as a dictionary and return it.
        :param model:
        :param activity_data:
        :return:
        :rtype: dict
        """
        cr, uid = self._cr, self._uid
        model_pool = self.pool[model]
        for activity in activity_data:
            model_data = model_pool.read(
                cr, uid, self._get_data_ref_id(activity), []
            )
            if model_data:
                stat = 'No'
                date_terminated = 'date_terminated'
                if 'status' in model_data and model_data['status']:
                    stat = 'Yes'
                    model_data['status'] = stat
                if 'date_started' in model_data and model_data['date_started']:
                    model_data['date_started'] = \
                        helpers.convert_db_date_to_context_date(
                            cr, uid,
                            datetime.strptime(
                                model_data['date_started'],
                                dtf
                            ),
                            self.pretty_date_format
                        )
                if date_terminated in model_data \
                        and model_data[date_terminated]:
                    model_data['date_terminated'] = \
                        helpers.convert_db_date_to_context_date(
                            cr, uid,
                            datetime.strptime(
                                model_data['date_terminated'],
                                dtf
                            ),
                            self.pretty_date_format
                        )
            activity['values'] = model_data
        return activity_data

    @classmethod
    def _get_data_ref_id(cls, dictionary):
        return int(dictionary['data_ref'].split(',')[1])

    def get_multi_model_data(self, spell_id,
                             model_one, model_two,  start, end):
        act_data = self.get_activity_data(spell_id, model_one, start, end)
        return self.get_model_values(model_two, act_data)

    def get_model_data_as_json(self, model_data):
        for data in model_data:
            if 'write_date' in data and data['write_date']:
                data['write_date'] = datetime.strftime(
                    datetime.strptime(data['write_date'], dtf),
                    self.wkhtmltopdf_format
                )
            if 'create_date' in data and data['create_date']:
                data['create_date'] = datetime.strftime(
                    datetime.strptime(data['create_date'], dtf),
                    self.wkhtmltopdf_format
                )
            if 'date_started' in data and data['date_started']:
                data['date_started'] = datetime.strftime(
                    datetime.strptime(
                        data['date_started'],
                        self.pretty_date_format
                    ),
                    self.wkhtmltopdf_format
                )
            if 'date_terminated' in data and data['date_terminated']:
                data['date_terminated'] = datetime.strftime(
                    datetime.strptime(
                        data['date_terminated'],
                        self.pretty_date_format
                    ),
                    self.wkhtmltopdf_format
                )
        return json.dumps(model_data)

    def create_report_data(self, data):
        cr, uid = self._cr, self._uid
        pretty_date_format = self.pretty_date_format

        # set up pools
        company_pool = self.pool['res.company']
        partner_pool = self.pool['res.partner']
        user_pool = self.pool['res.users']

        # get user data
        user = user_pool.read(cr, uid, uid, ['name'])['name']

        # get company data
        company_name = company_pool.read(cr, uid, 1, ['name'])['name']
        company_logo = partner_pool.read(cr, uid, 1, ['image'])['image']

        # generate report timestamp
        time_generated = fields.datetime.context_timestamp(
            cr, uid,
            datetime.now(),
            context=None
        ).strftime(pretty_date_format)
        return helpers.BaseReport(
            user,
            company_name,
            company_logo,
            time_generated
        )

    def get_triggered_actions(self, cr, uid, activity_id, activity_list=None):
        """
        Recursively get the triggered actions of the activity passed to it
        and then it's children and so on
        :param activity_id: The current activity under inspection
        :param activity_list: the list to use
        :return: list of activity ids
        """
        if not activity_list:
            activity_list = []
        activity_pool = self.pool['nh.activity']
        created_ids = activity_pool.search(
            cr, uid, [
                ['creator_id', '=', activity_id],
                ['data_model', '!=', 'nh.clinical.patient.observation.ews']
            ])
        if created_ids:
            activity_list += created_ids
            for created_id in created_ids:
                self.get_triggered_actions(cr, uid, created_id,
                                           activity_list=activity_list)
        return activity_list

    @api.multi
    def get_ews_observations(self, data, spell_activity_id):
        cr, uid = self._cr, self._uid
        ews_model = 'nh.clinical.patient.observation.ews'
        ews = self.get_model_data(spell_activity_id,
                                  ews_model,
                                  data.start_time, data.end_time)
        for observation in ews:
            o2target_dt = datetime.strptime(
                observation['values']['date_terminated'],
                self.pretty_date_format
            ).strftime(dtf)
            o2_level_id = self.pool['nh.clinical.patient.o2target'].get_last(
                cr, uid, self.patient_id,
                datetime=o2target_dt)
            o2_level = False
            if o2_level_id:
                o2_level = self.pool['nh.clinical.o2level'].browse(
                    cr, uid, o2_level_id)
            observation['values']['o2_target'] = False
            if o2_level:
                observation['values']['o2_target'] = o2_level.name
            triggered_actions = self.pool['nh.activity'].read(
                cr, uid, self.get_triggered_actions(observation['id'])
            )
            for t in triggered_actions:
                ds = t.get('date_started', False)
                dt = t.get('date_terminated', False)
                if ds:
                    t['date_started'] = \
                        helpers.convert_db_date_to_context_date(
                            cr, uid,
                            datetime.strptime(t['date_started'], dtf),
                            self.pretty_date_format
                        )
                if dt:
                    t['date_terminated'] = \
                        helpers.convert_db_date_to_context_date(
                            cr, uid,
                            datetime.strptime(t['date_terminated'], dtf),
                            self.pretty_date_format
                        )
            observation['triggered_actions'] = triggered_actions
        return ews

    @staticmethod
    def convert_bristol_stools_booleans(model_data):
        for ob in model_data:
            vals = ob['values']
            vals['bowel_open'] = helpers.boolean_to_text(vals['bowel_open'])
            vals['vomiting'] = helpers.boolean_to_text(vals['vomiting'])
            vals['nausea'] = helpers.boolean_to_text(vals['nausea'])
            vals['strain'] = helpers.boolean_to_text(vals['strain'])
            vals['offensive'] = helpers.boolean_to_text(vals['offensive'])
            vals['laxatives'] = helpers.boolean_to_text(vals['laxatives'])
            vals['rectal_exam'] = helpers.boolean_to_text(vals['rectal_exam'])
        return model_data

    @staticmethod
    def convert_pbp_booleans(model_data):
        for ob in model_data:
            vals = ob['values']
            vals['result'] = helpers.boolean_to_text(vals['result'])
        return model_data

    def process_transfer_history(self, model_data):
        for observation in model_data:
                patient_location = self.pool['nh.clinical.location'].read(
                    self._cr,
                    self._uid,
                    observation['values']['location_id'][0], [])
                if patient_location:
                    observation['bed'] = patient_location.get('name', False)
                    ward = patient_location.get('parent_id', False)
                if ward:
                    observation['ward'] = ward[1]
        return model_data

    def process_report_dates(self, data, spell, base_report):
        start_time = False
        end_time = False
        if data.start_time:
            if isinstance(data.start_time, str):
                start_time = datetime.strptime(data.start_time, dtf)
                data.start_time = start_time
        if data.end_time:
            if isinstance(data.end_time, str):
                end_time = datetime.strptime(data.end_time, dtf)
                data.end_time = end_time

        # - get the start and end date of spell
        spell_start = helpers.convert_db_date_to_context_date(
            self._cr, self._uid, datetime.strptime(spell['date_started'], dtf),
            self.pretty_date_format, context=None)
        spell_end = spell['date_terminated']
        report_start = spell_start
        report_end = base_report.time_generated
        if start_time:
            report_start = start_time.strftime(self.pretty_date_format)
        if end_time:
            report_end = end_time.strftime(self.pretty_date_format)
        else:
            if spell_end:
                report_end = helpers.convert_db_date_to_context_date(
                    self._cr, self._uid, datetime.strptime(spell_end, dtf),
                    self.pretty_date_format,
                    context=None)
        return helpers.ReportDates(
            report_start,
            report_end,
            spell_start,
            spell_end
        )

    def get_activity_data_from_dict(self, dict, spell_id, data):
        for k, v in dict.iteritems():
            dict[k] = self.get_model_data(
                spell_id, v, data.start_time, data.end_time)
        return dict

    @staticmethod
    def process_patient_height_weight(patient, height_weight):
        heights = height_weight['height']
        height = False
        if len(heights) > 0:
            height = heights[-1]['values']['height']
        patient['height'] = height

        # get weight observations
        weights = height_weight['weight']
        weight = False
        if len(weights) > 0:
            weight = weights[-1]['values']['weight']
        patient['weight'] = weight
        return patient

    def get_report_data(self, data, ews_only=False):
        """
        Returns a dictionary that will be used to populate the report.
        Most of the values are themselves dictionaries returned by
        `activity.read()`. However they also have an additional key named
        'values' that contains the model record as dictionaries returned by
        `model.read()`.
        :param data:
        :param ews_only:
        :return:
        """
        cr, uid = self._cr, self._uid
        # set up pools
        report = self.env['report']._get_report_from_name(
            'nh.clinical.observation_report')
        spell_pool = self.pool['nh.clinical.spell']
        patient_pool = self.pool['nh.clinical.patient']
        partner_pool = self.pool['res.partner']
        base_report = self.create_report_data(data)
        spell_id = int(data.spell_id)
        spell = spell_pool.read(cr, uid, [spell_id])[0]
        dates = self.process_report_dates(data, spell, base_report)
        spell_activity_id = spell['activity_id'][0]

        spell_docs = spell['con_doctor_ids']
        spell['consultants'] = False
        if len(spell_docs) > 0:
            spell['consultants'] = partner_pool.read(cr, uid, spell_docs)
        #
        # # - get patient id
        self.patient_id = spell['patient_id'][0]
        patient_id = self.patient_id
        #
        # get patient information
        patient = patient_pool.read(cr, uid, [patient_id])[0]
        patient_location = patient.get('current_location_id')
        patient['dob'] = helpers.convert_db_date_to_context_date(
            cr, uid, datetime.strptime(patient['dob'], dtf),
            '%d/%m/%Y', context=None)if patient.get('dob', False) else ''
        ews = self.get_ews_observations(data, spell_activity_id)
        json_data = []
        table_ews = []
        for activity in ews:
            json_data.append(copy.deepcopy(activity['values']))
            table_ews.append(copy.deepcopy(activity['values']))
        json_ews = self.get_model_data_as_json(json_data)

        # Get the script files to load
        observation_report = '/nh_eobs/static/src/js/observation_report.js'

        height_weight_dict = {
            'height': 'nh.clinical.patient.observation.height',
            'weight': 'nh.clinical.patient.observation.weight'
        }
        height_weight = self.get_activity_data_from_dict(
            height_weight_dict,
            spell_activity_id,
            data
        )
        patient = self.process_patient_height_weight(patient, height_weight)

        monitoring = self.create_patient_monitoring_exception_dictionary(
            data, spell_activity_id
        )

        transfer_history = self.process_transfer_history(
            self.get_model_data(
                spell_activity_id,
                'nh.clinical.patient.move',
                data.start_time, data.end_time)
        )
        if patient_location:
            location_pool = self.pool['nh.clinical.location']
            current_loc = location_pool.read(cr, uid, patient_location[0])
            loc = current_loc.get('full_name')
            patient['location'] = loc if loc else ''

        device_session_history = self.get_multi_model_data(
            spell_activity_id,
            'nh.clinical.patient.o2target',
            'nh.clinical.device.session',
            data.start_time, data.end_time
        )

        ews_dict = {
            'doc_ids': self._ids,
            'doc_model': report.model,
            'docs': self,
            'spell': spell,
            'patient': patient,
            'ews': ews,
            'table_ews': table_ews,
            'report_start': dates.report_start,
            'report_end': dates.report_end,
            'spell_start': dates.spell_start,
            'ews_data': json_ews,
            'draw_graph_js': observation_report,
            'device_session_history': device_session_history,
            'transfer_history': transfer_history,
        }

        ews_report = helpers.merge_dicts(ews_dict,
                                         base_report.footer_values,
                                         monitoring)
        if ews_only:
            return ews_report

        basic_obs_dict = {
            'gcs': 'nh.clinical.patient.observation.gcs',
            'bs': 'nh.clinical.patient.observation.blood_sugar',
            'pains': 'nh.clinical.patient.observation.pain',
            'blood_products': 'nh.clinical.patient.observation.blood_product'
        }

        basic_obs = self.get_activity_data_from_dict(
            basic_obs_dict,
            spell_activity_id,
            data
        )

        pbps = self.convert_pbp_booleans(
            self.get_model_data(
                spell_activity_id,
                'nh.clinical.patient.observation.pbp',
                data.start_time, data.end_time)
        )

        bristol_stools = self.convert_bristol_stools_booleans(
            self.get_model_data(
                spell_activity_id,
                'nh.clinical.patient.observation.stools',
                data.start_time, data.end_time))

        weights = height_weight['weight']

        non_basic_obs = {
            'bristol_stools': bristol_stools,
            'weights': weights,
            'pbps': pbps
        }

        rep_data = helpers.merge_dicts(
            basic_obs,
            non_basic_obs,
            ews_report
        )
        return rep_data

    def create_patient_monitoring_exception_dictionary(self, data,
                                                       spell_activity_id):
        cr, uid = self._cr, self._uid
        activity_model = self.env['nh.activity']
        this_model = self.env['report.nh.clinical.observation_report']

        old_style_patient_monitoring_exceptions = \
            copy.deepcopy(self.monitoring_dict)
        old_style_patient_monitoring_exceptions = \
            self.get_activity_data_from_dict(
                old_style_patient_monitoring_exceptions,
                spell_activity_id, data
            )

        # Tried using a browse here but it broke all the unit tests due to
        # mocked read methods.
        spell_activity = activity_model.read(cr, uid, spell_activity_id)[0]
        spell_id = self._get_data_ref_id(spell_activity)

        new_style_patient_monitoring_exceptions = \
            this_model.get_patient_monitoring_exception_report_data(
                    spell_activity_id, None
                )

        patient_monitoring_exception_dictionary = helpers.merge_dicts(
            old_style_patient_monitoring_exceptions,
            new_style_patient_monitoring_exceptions
        )

        return patient_monitoring_exception_dictionary

    def convert_dates_to_context_dates(self, activity_data):
        cr, uid = self._cr, self._uid
        for activity in activity_data:
            date_started = False
            date_terminated = False
            if 'date_started' in activity and activity['date_started']:
                date_started = activity['date_started']
            if 'date_terminated' in activity \
                    and activity['date_terminated']:
                date_terminated = activity['date_terminated']
            if date_started:
                date_started = helpers.convert_db_date_to_context_date(
                    cr, uid, datetime.strptime(date_started, dtf),
                    self.pretty_date_format
                )
                activity['date_started'] = date_started
            if date_terminated:
                date_terminated = helpers.convert_db_date_to_context_date(
                    cr, uid, datetime.strptime(date_terminated, dtf),
                    self.pretty_date_format
                )
                activity['date_terminated'] = date_terminated

    def get_patient_monitoring_exception_report_data(self, cr, uid,
                                                     spell_activity_id,
                                                     start_date,
                                                     end_date=None):
        activity_model = self.pool['nh.activity']
        model = 'nh.clinical.patient_monitoring_exception'

        states = self._get_allowed_activity_states_for_model(cr, uid, model)
        domain = helpers.build_activity_search_domain(
            spell_activity_id, model,
            start_date, end_date,
            states=states, date_field='date_started'
        )
        activity_id = activity_model.search(cr, uid, domain)
        if isinstance(activity_id, list):
            activity_id = activity_id[0]

        report_data = self.get_monitoring_exception_report_data_from_activity(
            cr, uid, activity_id
        )

        dictionary = {
            'patient_monitoring_exceptions': [
                report_data
            ]
        }
        return dictionary

    def get_monitoring_exception_report_data_from_activities(self, activities):
        pass

    def get_monitoring_exception_report_data_from_activity(self, cr, uid, activity_id):
        activity_model = self.pool['nh.activity']
        pme_model = \
            self.pool['nh.clinical.patient_monitoring_exception']
        reason_model = \
            self.pool['nh.clinical.patient_monitoring_exception.reason']

        activity = activity_model.read(cr, uid, activity_id)
        if isinstance(activity, list):
            activity = activity[0]

        pme_id = self._get_data_ref_id(activity)
        pme = pme_model.read(cr, uid, pme_id)
        reason_display_name = pme['reason'][1] # tuple: (id, display_name)

        return {
            'date': activity['date_started'],
            'user': activity['terminate_uid'] if activity['terminate_uid'] else activity['create_uid'],
            'status': 'Stop Observations',
            'reason': reason_display_name
        }


    @api.multi
    def render_html(self, data=None):

        if isinstance(data, dict):
            data = helpers.data_dict_to_obj(data)

        if data and data.spell_id:
            report_obj = self.env['report']
            if hasattr(data, 'ews_only') and data.ews_only:
                ews_report = self.get_report_data(data, ews_only=True)
                return report_obj.render('nh_eobs.observation_report',
                                         ews_report)
            rep_data = self.get_report_data(data)
            return report_obj.render(
                'nh_eobs.observation_report',
                rep_data)
        else:
            return None