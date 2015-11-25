# -*- coding: utf-8 -*-s
import openerp
import re
import urls
import jinja2
import os
import logging
from openerp import http
from openerp.modules.module import get_module_path
from datetime import datetime
from openerp.http import request
from werkzeug import utils, exceptions
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF
from openerp.osv import fields, orm
from openerp.addons.nh_eobs_api.controllers.route_api import route_manager
from openerp.addons.nh_eobs_api.routing import Route as EobsRoute

_logger = logging.getLogger(__name__)

URL_PREFIX = '/mobile/'
URLS = urls.URLS


db_list = http.db_list

db_monodb = http.db_monodb

loader = jinja2.FileSystemLoader(get_module_path('nh_eobs_mobile') + '/views/')
env = jinja2.Environment(loader=loader)
single_patient = EobsRoute('single_patient', '/patient/<patient_id>', methods=['GET'], url_prefix='/mobile')
patient_list = EobsRoute('patient_list', '/patients/', methods=['GET'], url_prefix='/mobile')
task_list = EobsRoute('task_list', '/tasks/', methods=['GET'], url_prefix='/mobile')
single_task = EobsRoute('single_task', '/task/<task_id>', methods=['GET'], url_prefix='/mobile')
route_manager.add_route(single_patient)
route_manager.add_route(patient_list)
route_manager.add_route(single_task)
route_manager.add_route(task_list)


def abort_and_redirect(url):
    r = request.httprequest
    response = utils.redirect(url, 302)
    response = r.app.get_response(r, response, explicit_session=False)
    exceptions.abort(response)

def ensure_db(redirect=URLS['login']):
    # This helper should be used in web client auth="none" routes
    # if those routes needs a db to work with.
    # If the heuristics does not find any database, then the users will be
    # redirected to db selector or any url specified by `redirect` argument.
    # If the db is taken out of a query parameter, it will be checked against
    # `http.db_filter()` in order to ensure it's legit and thus avoid db
    # forgering that could lead to xss attacks.
    db = request.params.get('db')

    # Ensure db is legit
    if db and db not in http.db_filter([db]):
        db = None

    if db and not request.session.db:
        # User asked a specific database on a new session.
        # That mean the nodb router has been used to find the route
        # Depending on installed module in the database, the rendering of the page
        # may depend on data injected by the database route dispatcher.
        # Thus, we redirect the user to the same page but with the session cookie set.
        # This will force using the database route dispatcher...
        r = request.httprequest
        url_redirect = r.base_url
        if r.query_string:
            # Can't use werkzeug.wrappers.BaseRequest.url with encoded hashes:
            # https://github.com/amigrave/werkzeug/commit/b4a62433f2f7678c234cdcac6247a869f90a7eb7
            url_redirect += '?' + r.query_string
        response = utils.redirect(url_redirect, 302)
        request.session.db = db
        abort_and_redirect(url_redirect)

    # if db not provided, use the session one
    if not db:
        db = request.session.db

    # if no database provided and no database in session, use monodb
    if not db:
        db = db_monodb(request.httprequest)

    # if no db can be found til here, send to the database selector
    # the database selector will redirect to database manager if needed
    if not db:
        exceptions.abort(utils.redirect(redirect, 303))

    # always switch the session to the computed db
    if db != request.session.db:
        request.session.logout()
        abort_and_redirect(request.httprequest.url)

    request.session.db = db


class MobileFrontend(openerp.addons.web.controllers.main.Home):

    @http.route(URLS['stylesheet'], type='http', auth='none')
    def get_stylesheet(self, *args, **kw):
        with open(get_module_path('nh_eobs_mobile') + '/static/src/css/nhc.css', 'r') as stylesheet:
            return request.make_response(stylesheet.read(), headers={'Content-Type': 'text/css; charset=utf-8'})

    @http.route(URLS['manifest'], type='http', auth='none')
    def get_manifest(self, *args, **kw):
        with open(get_module_path('nh_eobs_mobile') + '/static/src/manifest.json', 'r') as manifest:
            return request.make_response(manifest.read(), headers={'Content-Type': 'application/json'})

    @http.route(URLS['small_icon'], type='http', auth='none')
    def get_small_icon(self, *args, **kw):
        with open(get_module_path('nh_eobs_mobile') + '/static/src/icon/hd_small.png', 'r') as icon:
            return request.make_response(icon.read(), headers={'Content-Type': 'image/png'})

    @http.route(URLS['big_icon'], type='http', auth='none')
    def get_big_icon(self, *args, **kw):
        with open(get_module_path('nh_eobs_mobile') + '/static/src/icon/hd_hi.png', 'r') as icon:
            return request.make_response(icon.read(), headers={'Content-Type': 'image/png'})

    @http.route('/mobile/src/fonts/<xmlid>', auth='none', type='http')
    def get_font(self, xmlid, *args, **kw):
        font_file_request = get_module_path('nh_eobs_mobile') + '/static/src/fonts/' + xmlid
        # Consider only the file's name (without additional unwanted parts) when checking for file's existence
        font_file_path = get_module_path('nh_eobs_mobile') + '/static/src/fonts/' + xmlid.split('?')[0]
        if isinstance(xmlid, basestring) and os.path.exists(font_file_path):
            with open(font_file_request, 'r') as font:
                return request.make_response(font.read(), headers={'Content-Type': 'application/font-woff'})
        else:
            exceptions.abort(404)

    @http.route(URLS['logo'], type='http', auth='none')
    def get_logo(self, *args, **kw):
        with open(get_module_path('nh_eobs_mobile') + '/static/src/img/open_eobs_logo.png', 'r') as logo:
            return request.make_response(logo.read(), headers={'Content-Type': 'image/png'})

    @http.route(URLS['bristol_stools_chart'], type='http', auth='none')
    def get_bristol_stools_chart(self, *args, **kw):
        with open(get_module_path('nh_eobs_mobile') + '/static/src/img/bristol_stools.png', 'r') as bsc:
            return request.make_response(bsc.read(), headers={'Content-Type': 'image/png'})

    @http.route(URLS['jquery'], type='http', auth='none')
    def get_jquery(self, *args, **kw):
        with open(get_module_path('nh_eobs_mobile') + '/static/src/js/jquery.js', 'r') as jquery:
            return request.make_response(jquery.read(), headers={'Content-Type': 'text/javascript'})

    @http.route(URLS['observation_form_js'], type='http', auth='none')
    def get_observation_js(self, *args, **kw):
        with open(get_module_path('nh_eobs_mobile') + '/static/src/js/observation.js', 'r') as js:
            return request.make_response(js.read(), headers={'Content-Type': 'text/javascript'})

    @http.route(URLS['observation_form_validation'], type='http', auth='none')
    def get_observation_validation(self, *args, **kw):
        with open(get_module_path('nh_eobs_mobile') + '/static/src/js/validation.js', 'r') as js:
            return request.make_response(js.read(), headers={'Content-Type': 'text/javascript'})


    @http.route(URLS['graph_lib'], type='http', auth='none')
    def graph_lib(self, *args, **kw):
        with open(get_module_path('nh_graphs') + '/static/src/js/nh_graphlib.js', 'r') as pg:
            return request.make_response(pg.read(), headers={'Content-Type': 'text/javascript'})

    @http.route(URLS['patient_graph'], type='http', auth='none')
    def patient_graph_js(self, *args, **kw):
        with open(get_module_path('nh_eobs_mobile') + '/static/src/js/draw_ews_graph.js', 'r') as js:
            return request.make_response(js.read(), headers={'Content-Type': 'text/javascript'})

    @http.route(URLS['data_driven_documents'], type='http', auth='none')
    def d_three(self, *args, **kw):
        with open(get_module_path('nh_graphs') + '/static/lib/js/d3.js', 'r') as js:
            return request.make_response(js.read(), headers={'Content-Type': 'text/javascript'})

    @http.route(URL_PREFIX, type='http', auth='none')
    def index(self, *args, **kw):
        ensure_db()
        if request.session.uid:
            return utils.redirect(URLS['task_list'], 303)
        else:
            return utils.redirect(URLS['login'], 303)

    @http.route(URLS['login'], type="http", auth="none")
    def mobile_login(self, *args, **kw):

        if not request.uid:
            request.uid = openerp.SUPERUSER_ID

        values = request.params.copy()
        try:
            values['databases'] = http.db_list()
        except openerp.exceptions.AccessDenied:
            values['databases'] = None

        values['databases'] = [values['database']] if 'database' in values and values['database'] in values['databases'] else values['databases']

        login_template = env.get_template('login.html')

        if request.httprequest.method == 'GET':
            response = request.make_response(login_template.render(stylesheet=URLS['stylesheet'], logo=URLS['logo'], form_action=URLS['login'], errors='', databases=values['databases']))  # , headers={'X-Openerp-Session-Id': request.session_id})
            response.set_cookie('session_id', value=request.session_id, max_age=3600)
            return response
        if request.httprequest.method == 'POST':
            # TODO: Refactor to better manage the 'card pin' use case
            card_pin = request.params.get('card_pin', None)
            if card_pin:
                nfc_api = request.registry['res.users']
                user_id = nfc_api.get_user_id_from_card_pin(request.cr, request.uid, card_pin)
                user_login = nfc_api.get_user_login_from_user_id(request.cr, request.uid, user_id)
                if user_id is not False:
                    request.session.db = 'nhclinical'  # instead should use the variable 'database'
                    request.session.uid = user_id
                    request.session.login = user_login
                    request.session.password = user_login  # instead should use the variable 'card_pin'
                    return utils.redirect(URLS['task_list'], 303)
            database = values['database'] if 'database' in values else False
            if database:
                uid = request.session.authenticate(database, request.params['username'], request.params['password'])
                if uid is not False:
                    request.uid = uid
                    return utils.redirect(URLS['task_list'], 303)
            response = request.make_response(login_template.render(stylesheet=URLS['stylesheet'], logo=URLS['logo'], form_action=URLS['login'], errors='<div class="alert alert-error">Invalid username/password</div>', databases=values['databases']))  # , headers={'X-Openerp-Session-Id': request.session_id})
            response.set_cookie('session_id', value=request.session_id, max_age=3600)
            return response

    @http.route(URLS['logout'], type='http', auth="user")
    def mobile_logout(self, *args, **kw):
        api = request.registry['nh.eobs.api']
        api.unassign_my_activities(request.cr, request.session.uid)
        request.session.logout(keep_db=True)
        return utils.redirect(URLS['login'], 303)


    def calculate_ews_class(self, score):
        if score == 'None':
            return 'level-none'
        elif score == 'Low':
            return 'level-one'
        elif score == 'Medium':
            return 'level-two'
        elif score == 'High':
            return 'level-three'
        else:
            return 'level-none'

    @http.route(URLS['patient_list'], type='http', auth="user")
    def get_patients(self, *args, **kw):
        cr, uid, context = request.cr, request.session.uid, request.context
        patient_api = request.registry['nh.eobs.api']
        patient_api.unassign_my_activities(cr, uid)
        follow_activities = patient_api.get_assigned_activities(cr, uid,
                                                                activity_type='nh.clinical.patient.follow',
                                                                context=context)
        patients = patient_api.get_patients(cr, uid, [], context=context)
        patient_api.get_patient_followers(cr, uid, patients, context=context)
        following_patients = patient_api.get_followed_patients(cr, uid, [])
        for patient in patients:
            patient['url'] = '{0}{1}'.format(URLS['single_patient'], patient['id'])
            patient['color'] = self.calculate_ews_class(patient['clinical_risk'])
            patient['deadline_time'] = patient['next_ews_time']
            patient['summary'] = patient['summary'] if patient.get('summary') else False
        for fpatient in following_patients:
            fpatient['url'] = '{0}{1}'. format(URLS['single_patient'], fpatient['id'])
            fpatient['color'] = self.calculate_ews_class(fpatient['clinical_risk'])
            fpatient['trend_icon'] = 'icon-{0}-arrow'.format(fpatient['ews_trend'])
            fpatient['deadline_time'] = fpatient['next_ews_time']
            fpatient['summary'] = fpatient['summary'] if fpatient.get('summary') else False
        return request.render('nh_eobs_mobile.patient_task_list', qcontext={'notifications': follow_activities,
                                                                            'items': patients,
                                                                            'notification_count': len(follow_activities),
                                                                            'followed_items': following_patients,
                                                                            'section': 'patient',
                                                                            'username': request.session['login'],
                                                                            'urls': URLS})

    @http.route(URLS['share_patient_list'], type='http', auth='user')
    def get_share_patients(self, *args, **kw):
        cr, uid, context = request.cr, request.session.uid, request.context
        api = request.registry['nh.eobs.api']
        api.unassign_my_activities(cr, uid)
        patients = api.get_patients(cr, uid, [], context=context)
        api.get_patient_followers(cr, uid, patients, context=context)
        api.get_invited_users(cr, uid, patients, context=context)
        follow_activities = api.get_assigned_activities(cr, uid,
                                                        activity_type='nh.clinical.patient.follow',
                                                        context=context)
        for patient in patients:
            patient['url'] = '{0}{1}'.format(URLS['single_patient'], patient['id'])
            patient['color'] = self.calculate_ews_class(patient['clinical_risk'])
            patient['trend_icon'] = 'icon-{0}-arrow'.format(patient['ews_trend'])
            patient['deadline_time'] = patient['next_ews_time']
            patient['summary'] = patient['summary'] if patient.get('summary') else False
            if patient.get('followers'):
                followers = patient['followers']
                patient['followers'] = ', '.join([f['name'] for f in followers])
                patient['follower_ids'] = [f['id'] for f in followers]
            if patient.get('invited_users'):
                users = patient['invited_users']
                patient['invited_users'] = ', '.join([u['name'] for u in users])
        sorted_pts = sorted(patients, key=lambda k: cmp(k['followers'], k['invited_users']))
        return request.render('nh_eobs_mobile.share_patients_list', qcontext={'items': sorted_pts,
                                                                              'section': 'patient',
                                                                              'username': request.session['login'],
                                                                              'share_list': True,
                                                                              'notification_count': len(follow_activities),
                                                                              'urls': URLS,
                                                                              'user_id': uid})

    @http.route(URLS['task_list'], type='http', auth='user')
    def get_tasks(self, *args, **kw):
        cr, uid, context = request.cr, request.uid, request.context
        task_api = request.registry['nh.eobs.api']
        task_api.unassign_my_activities(cr, uid)
        follow_activities = task_api.get_assigned_activities(cr, uid,
                                                        activity_type='nh.clinical.patient.follow',
                                                        context=context)
        # grab the patient object and get id?
        tasks = task_api.get_activities(cr, uid, [], context=context)
        for task in tasks:
            task['url'] = '{0}{1}'.format(URLS['single_task'], task['id'])
            task['color'] = self.calculate_ews_class(task['clinical_risk'])
        return request.render('nh_eobs_mobile.patient_task_list', qcontext={'items': tasks,
                                                                             'section': 'task',
                                                                             'username': request.session['login'],
                                                                             'notification_count': len(follow_activities),
                                                                             'urls': URLS})

    @http.route(URLS['single_task']+'<task_id>', type='http', auth='user')
    def get_task(self, task_id, *args, **kw):
        cr, uid, context = request.cr, request.uid, request.context
        activity_reg = request.registry['nh.activity']
        api_reg = request.registry['nh.eobs.api']
        task_id = int(task_id)
        follow_activities = api_reg.get_assigned_activities(cr, uid,
                                                        activity_type='nh.clinical.patient.follow',
                                                        context=context)
        task = activity_reg.read(cr, uid, task_id, ['user_id', 'data_model', 'summary', 'patient_id'], context=context)
        patient = dict()
        if task and task.get('patient_id'):
            patient_info = api_reg.get_patients(cr, uid, [task['patient_id'][0]], context=context)
            if not patient_info:
                exceptions.abort(404)
            elif len(patient_info) > 0:
                patient_info = patient_info[0]
            patient['url'] = URLS['single_patient'] + '{0}'.format(patient_info['id'])
            patient['name'] = patient_info['full_name']
            patient['id'] = patient_info['id']
        else:
            exceptions.abort(404)
        form = dict()
        form['action'] = URLS['task_form_action']+'{0}'.format(task_id)  # TODO: check if this is still actually used!
        form['type'] = task['data_model']
        form['task-id'] = int(task_id)
        form['patient-id'] = int(patient['id']) if patient and 'id' in patient and patient['id'] else False
        form['source'] = "task"
        form['start'] = datetime.now().strftime('%s')
        api_reg.unassign_my_activities(cr, uid)
        try:
            api_reg.assign(cr, uid, task_id, {'user_id': uid}, context=context)
        except orm.except_orm as e:
            exception_message = 'Opening the task (id: {task_id}) ' \
                                'and trying to assign it to the current user (id: {user_id}) ' \
                                'raises this exception: {exception}'.format(task_id=task_id, user_id=uid, exception=e)
            _logger.debug(exception_message)
            return utils.redirect(URLS['task_list'], 303)

        if 'notification' in task['data_model'] or 'placement' in task['data_model']:
            # load notification foo
            obs_reg = request.registry['nh.eobs.api']
            form_desc = obs_reg.get_form_description(cr, uid, task['patient_id'][0], task['data_model'], context=context)
            cancellable = obs_reg.is_cancellable(cr, uid, task['data_model'], context=context)
            form['confirm_url'] = "{0}{1}".format(URLS['confirm_clinical_notification'], task_id)
            form['action'] = "{0}{1}".format(URLS['confirm_clinical_notification'], task_id)
            for form_input in form_desc:
                if form_input['type'] in ['float', 'integer']:
                    form_input['step'] = 0.1 if form_input['type'] is 'float' else 1
                    form_input['type'] = 'number'
                    form_input['number'] = True
                    # form_input['info'] = ''
                    # form_input['errors'] = ''
                    form_input['min'] = str(form_input['min'])
                    #if form_input['target']:
                    #    form_input['target'] = False
                elif form_input['type'] == 'selection':
                    form_input['selection_options'] = []
                    # form_input['info'] = ''
                    # form_input['errors'] = ''
                    for option in form_input['selection']:
                        opt = dict()
                        opt['value'] = '{0}'.format(option[0])
                        opt['label'] = option[1]
                        form_input['selection_options'].append(opt)
                # elif form_input['type'] == 'text':
                #    form_input['info'] = ''
                #    form_input['errors'] = ''
            if cancellable:
                form['cancel_url'] = "{0}{1}".format(URLS['cancel_clinical_notification'], task_id)
            if 'notification' in task['data_model']:
                form['type'] = re.match(r'nh\.clinical\.notification\.(.*)', task['data_model']).group(1)
            else:
                form['type'] = 'placement'
            return request.render('nh_eobs_mobile.notification_confirm_cancel',
                                  qcontext={'name': task['summary'],
                                            'inputs': form_desc,
                                            'cancellable': cancellable,
                                            'patient': patient,
                                            'form': form,
                                            'section': 'task',
                                            'username': request.session['login'],
                                            'notification_count': len(follow_activities),
                                            'urls': URLS})
        elif 'observation' in task['data_model']:
            # load obs foo
            obs_reg = request.registry['nh.eobs.api']
            form_desc = obs_reg.get_form_description(cr, uid, task['patient_id'][0], task['data_model'], context=context)
            form['type'] = re.match(r'nh\.clinical\.patient\.observation\.(.*)', task['data_model']).group(1)
            form['obs_needs_score'] = False
            for form_input in form_desc:
                if form_input['type'] in ['float', 'integer']:
                    form_input['step'] = 0.1 if form_input['type'] is 'float' else 1
                    form_input['type'] = 'number'
                    form_input['number'] = True
                    form_input['info'] = ''
                    form_input['errors'] = ''
                    form_input['min'] = str(form_input['min'])
                    #if form_input['target']:
                    #    form_input['target'] = False
                elif form_input['type'] == 'selection':
                    form_input['selection_options'] = []
                    form_input['info'] = ''
                    form_input['errors'] = ''
                    for option in form_input['selection']:
                        opt = dict()
                        opt['value'] = '{0}'.format(option[0])
                        opt['label'] = option[1]
                        form_input['selection_options'].append(opt)
                elif form_input['type'] == 'text':
                    form_input['info'] = ''
                    form_input['errors'] = ''
                elif form_input['type'] == 'meta':
                    form['obs_needs_score'] = form_input['score'] if 'score' in form_input else False

            return request.render('nh_eobs_mobile.observation_entry', qcontext={'inputs': [i for i in form_desc if i['type'] is not 'meta'],
                                                                                'name': task['summary'],
                                                                                'patient': patient,
                                                                                'form': form,
                                                                                'section': 'task',
                                                                                'username': request.session['login'],
                                                                                'notification_count': len(follow_activities),
                                                                                'urls': URLS})
        else:
            return request.render('nh_eobs_mobile.error', qcontext={'error_string': 'Task is neither a notification nor an observation',
                                                                     'section': 'task',
                                                                     'username': request.session['login'],
                                                                     'urls': URLS})

    # TODO: eventually remove this method, it's no more used: it has been replaced by method 'process_ajax_form()'
    # This method is still a valid fallback in case Javascript is disabled on the client side, but
    # due to our current dependency from Javascript, that is a very improbable scenario.
    @http.route(URLS['task_form_action']+'<task_id>', type="http", auth="user")
    def process_form(self, task_id, *args, **kw):
        cr, uid, context = request.cr, request.uid, request.context
        activity_api = request.registry('nh.activity')
        kw_copy = kw.copy()
        del kw_copy['taskId']
        kw_copy['date_started'] = datetime.fromtimestamp(int(kw_copy['startTimestamp'])).strftime(DTF)
        del kw_copy['startTimestamp']
        activity_api.submit(cr, uid, int(task_id), kw_copy, context)
        activity_api.complete(cr, uid, int(task_id), context)
        return utils.redirect(URLS['task_list'])

    @http.route(URLS['single_patient']+'<patient_id>', type='http', auth='user')
    def get_patient(self, patient_id, *args, **kw):
        cr, uid, context = request.cr, request.uid, request.context
        api_pool = request.registry('nh.eobs.api')
        patient = api_pool.get_patients(cr, uid, [int(patient_id)], context=context)[0]
        obs = api_pool.get_active_observations(cr, uid, int(patient_id), context=context)
        for index, ob in enumerate(obs):
            if ob['type'] == 'ews':
                obs.insert(0, obs.pop(index))
            if ob['type'] == 'gcs':
                obs.insert(1, obs.pop(index))
            if ob['type'] == 'pain':
                obs.insert(2, obs.pop(index))

        follow_activities = api_pool.get_assigned_activities(cr, uid,
                                                        activity_type='nh.clinical.patient.follow',
                                                        context=context)
        return request.render('nh_eobs_mobile.patient', qcontext={'patient': patient,
                                                                   'urls': URLS,
                                                                   'section': 'patient',
                                                                   'obs_list': obs,
                                                                   'notification_count': len(follow_activities),
                                                                   'username': request.session['login']})

    @http.route(URLS['patient_ob']+'<observation>/<patient_id>', type='http', auth='user')
    def take_patient_observation(self, observation, patient_id, *args, **kw):
        cr, uid, context = request.cr, request.uid, request.context
        api_pool = request.registry('nh.eobs.api')
        follow_activities = api_pool.get_assigned_activities(cr, uid,
                                                        activity_type='nh.clinical.patient.follow',
                                                        context=context)

        patient = dict()
        patient_info = api_pool.get_patients(cr, uid, [int(patient_id)], context=context)
        if not patient_info:
                exceptions.abort(404)
        elif len(patient_info) > 0:
            patient_info = patient_info[0]
        patient['url'] = URLS['single_patient'] + '{0}'.format(patient_info['id'])
        patient['name'] = patient_info['full_name']
        patient['id'] = patient_info['id']

        form = dict()
        form['action'] = URLS['patient_form_action']+'{0}/{1}'.format(observation, patient_id)
        form['type'] = observation
        form['task-id'] = False
        form['patient-id'] = int(patient_id)
        form['source'] = "patient"
        form['start'] = datetime.now().strftime('%s')
        form['obs_needs_score'] = False

        form_desc = api_pool.get_form_description(cr, uid, int(patient_id), 'nh.clinical.patient.observation.{0}'.format(observation), context=context)

        for form_input in form_desc:
            if form_input['type'] in ['float', 'integer']:
                form_input['step'] = 0.1 if form_input['type'] is 'float' else 1
                form_input['type'] = 'number'
                form_input['number'] = True
                form_input['info'] = ''
                form_input['errors'] = ''
                form_input['min'] = str(form_input['min'])
                #if form_input['target']:
                #    form_input['target'] = False
            elif form_input['type'] == 'selection':
                form_input['selection_options'] = []
                form_input['info'] = ''
                form_input['errors'] = ''
                for option in form_input['selection']:
                    opt = dict()
                    opt['value'] = '{0}'.format(option[0])
                    opt['label'] = option[1]
                    form_input['selection_options'].append(opt)
            elif form_input['type'] == 'meta':
                form['obs_needs_score'] = form_input['score'] if 'score' in form_input else False

        observation_name_list = [v['name'] for v in api_pool._active_observations if v['type'] == observation]
        if len(observation_name_list) == 0:
            exceptions.abort(404)
        return request.render('nh_eobs_mobile.observation_entry', qcontext={'inputs': form_desc,
                                                                             'name': observation_name_list[0],
                                                                             'patient': patient,
                                                                             'form': form,
                                                                             'section': 'patient',
                                                                             'notification_count': len(follow_activities),
                                                                             'username': request.session['login'],
                                                                             'urls': URLS})
