__author__ = 'lorenzo'

import json
import logging
import openerp.tests
import requests

from datetime import datetime
from random import choice as random_choice
from unittest import skip

from openerp.addons.nh_eobs_api.routing import Route, RouteManager, ResponseJSON
from openerp.addons.nh_eobs_api.controllers.route_api import route_manager
from openerp.tests import DB as DB_NAME
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF


test_logger = logging.getLogger(__name__)


class TestOdooRouteDecoratorIntegration(openerp.tests.common.HttpCase):

    json_response_structure_keys = ['status', 'title', 'description', 'data']

    def _get_user_belonging_to_group(self, group_name):
        """Get the 'id' and the 'login' name of a user belonging to a specific group.

        :param group_name: A string with the name of the group from which retrieve a user (belonging to it)
        :return: A dictionary with 2 key-value couples:
            - 'login': the login name of the retrieved user (belonging to the group passed as argument)
            - 'id': the id of the retrieved user (belonging to the group passed as argument)
        :return: None if there isn't any user belonging to that group
        """
        users_pool = self.registry['res.users']
        users_login_list = users_pool.search_read(self.cr, self.uid,
                                                  domain=[('groups_id.name', '=', group_name)],
                                                  fields=['login', 'id'])
        try:
            user_data = random_choice(users_login_list)
        except IndexError:
            user_data = None
        return user_data

    def _get_authenticated_response(self, user_name):
        """Get a Response object with an authenticated session within its cookies.

        :param user_name: A string with the username of the user to be authenticated as
        :return: A Response object
        """
        auth_response = requests.post(route_manager.BASE_URL + '/web/login',
                                      {'login': user_name,
                                       'password': user_name,
                                       'database': DB_NAME},
                                      cookies=self.session_resp.cookies)
        return auth_response

    def check_response_json(self, resp, status, title, description, data):
        """Test the response JSON for correct status, title, desc and data values.

        :param resp: Raw response from requests
        :param status: The expected status code for the response
        :param title: The title to be shown on the popup on Frontend
        :param description: The description to be used in the popup on Frontend
        :param data: Data the be sent to the Frontend to show in popup
        :return: True cos the tests will cause the thing to fail anyways
        """
        returned_json = json.loads(resp.text)
        for k in self.json_response_structure_keys:
            self.assertIn(k, returned_json)

        self.assertEqual(returned_json['status'], status)
        self.assertEqual(returned_json['title'], title)
        self.assertEqual(returned_json['description'], description)
        returned_data = json.dumps(returned_json['data'])
        json_data = json.dumps(data)
        self.assertEqual(json.loads(returned_data), json.loads(json_data))
        return True

    def _bulk_patch_odoo_model_method(self, odoo_model, methods_patching):
        """Patch a list of methods related to an Odoo's model.

        :param odoo_model: A valid Odoo's model instance (e.g. fetched by 'self.registry()')
        :param methods_patching: A list of two-values tuples, each containing:
            - the method to be patched (string)
            - the function that will substitute the method to be patched (the actual name of the function)
        :return: True (if no errors were raised during the patching)
        """
        for method_to_patch, substituting_function in methods_patching:
            odoo_model._patch_method(method_to_patch, substituting_function)
        return True

    def _revert_bulk_patch_odoo_model_method(self, odoo_model, methods_to_be_reverted):
        """Revert the Odoo's patching of a list of methods.

        :param odoo_model: A valid Odoo's model instance (e.g. fetched by 'self.registry()')
        :param methods_to_be_reverted: A list of model's 'original' methods to be reactivated back (string)
        :return: True (if no errors were raised during the patching)
        """
        for m in methods_to_be_reverted:
            odoo_model._revert_method(m)
        return True

    # Mock Odoo's models' methods
    @staticmethod
    def mock_get_assigned_activities(*args, **kwargs):
        """Return a list of dictionaries (one for each assigned activity)."""
        assigned_activities_list = [
            {
                'id': 2001,
                'user': 'Nurse Nadine',
                'count': 3,
                'patient_ids': [1, 2, 3],
                'message': 'You have been invited to follow 3 patients from Nurse Nadine'
            }
        ]
        return assigned_activities_list

    @staticmethod
    def mock_get_patients(*args, **kwargs):
        patients_list = [
            {
                'clinical_risk': 'None',
                'dob': '1980-12-25 08:00:00',
                'ews_score': '0',
                'ews_trend': 'down',
                'frequency': 720,
                'full_name': 'Campbell, Bruce',
                'gender': 'M',
                'id': 2,
                'location': 'Bed 3',
                'next_ews_time': '04:00 hours',
                'other_identifier': '1234567',
                'parent_location': 'Ward E',
                'patient_identifier': '908 475 1234',
                'sex': 'M'
            },
            {
                'clinical_risk': 'Low',
                'dob': '1980-08-31 18:00:00',
                'ews_score': '2',
                'ews_trend': 'down',
                'frequency': 240,
                'full_name': 'Franklin, Donna',
                'gender': 'F',
                'id': 1,
                'location': 'Bed 2',
                'next_ews_time': 'overdue: 02:00 hours',
                'other_identifier': '4867593',
                'parent_location': 'Ward E',
                'patient_identifier': '494 333 0012',
                'sex': 'F'
            },
            {
                'clinical_risk': 'Medium',
                'dob': '1980-04-25 12:00:00',
                'ews_score': '5',
                'ews_trend': 'up',
                'frequency': 60,
                'full_name': 'Hasselhoff, David',
                'gender': 'M',
                'id': 3,
                'location': 'Bed 1',
                'next_ews_time': '01:00 hours',
                'other_identifier': '3958684',
                'parent_location': 'Ward E',
                'patient_identifier': '112 009 007',
                'sex': 'M'
            }
        ]
        return patients_list

    @staticmethod
    def mock_res_users_read(*args, **kwargs):
        users_list = [
            {
                'id': 33,
                'login': 'john',
                'display_name': 'John Smith'
            },
            {
                'id': 34,
                'login': 'jane',
                'display_name': 'Jane Doe'
            },
            {
                'id': 35,
                'login': 'joe',
                'display_name': 'Joe Average'
            },
        ]
        return users_list

    @staticmethod
    def mock_method_returning_true(*args, **kwargs):
        return True

    @staticmethod
    def mock_method_returning_osv_exception(*args, **kwargs):
        raise osv.except_osv('Expected exception!', 'Expected exception raised during the test.')

    def setUp(self):
        """Get an authenticated response from the server so we can half-inch the session cookie for subsequent calls."""
        super(TestOdooRouteDecoratorIntegration, self).setUp()
        self.session_resp = requests.post(route_manager.BASE_URL + '/web', {'db': DB_NAME})
        if 'session_id' not in self.session_resp.cookies:
            self.fail('Cannot retrieve a valid session to be used for the tests!')

        # Authenticate as a 'nurse' user and check the login was successful
        user_data = self._get_user_belonging_to_group('NH Clinical Nurse Group')
        self.login_name = user_data.get('login')
        self.user_id = user_data.get('id')
        self.assertNotEqual(self.login_name, False,
                            "Cannot find any 'nurse' user for authentication before running the test!")
        self.auth_resp = self._get_authenticated_response(self.login_name)
        self.assertEqual(self.auth_resp.status_code, 200)

    # Test Observation based routes
    def test_01_route_calculate_ews_score(self):
        """Test the EWS score route, send EWS parameters to route and make
        sure it sends back score
        :return:
        """
        # check if the route under test is actually present in the Route Manager
        route_under_test = route_manager.get_route('calculate_obs_score')
        self.assertIsInstance(route_under_test, Route)

        # Create demo data
        demo_data = {
            'respiration_rate': 40,
            'indirect_oxymetry_spo2': 99,
            'oxygen_administration_flag': False,
            'body_temperature': 37.0,
            'blood_pressure_systolic': 120,
            'blood_pressure_diastolic': 80,
            'pulse_rate': 55,
            'avpu_text': 'A',
            'taskId': 666,
            'startTimestamp': 0,
        }

        # Access the route
        test_resp = requests.post(route_manager.BASE_URL + route_manager.URL_PREFIX + '/observation/score/ews/',
                                  data=json.dumps(demo_data),
                                  cookies=self.auth_resp.cookies)
        self.assertEqual(test_resp.status_code, 200)
        self.assertEqual(test_resp.headers['content-type'], 'application/json')

        expected_json = {
            'score': {
                'score': 3,
                'clinical_risk': 'Medium',
                'three_in_one': True
            },
            'modal_vals': {
                'next_action': 'json_task_form_action',
                'title': 'Submit NEWS of 3',
                'content': '<p><strong>Clinical risk: Medium</strong></p><p>Please confirm you want to submit this score</p>'
            }
        }
        self.check_response_json(test_resp, ResponseJSON.STATUS_SUCCESS,
                                 'Submit NEWS of 3',
                                 '<p><strong>Clinical risk: Medium</strong></p><p>Please confirm you want to submit this score</p>',
                                 expected_json)

    def test_02_route_calculate_gcs_score(self):
        """ Test the GCS score route, send GCS parameters to route and make sure
        it sends back score but not clinical risk
        :return:
        """
        # check if the route under test is actually present in the Route Manager
        route_under_test = route_manager.get_route('calculate_obs_score')
        self.assertIsInstance(route_under_test, Route)

        # Create demo data
        demo_data = {
            'eyes': '4',
            'verbal': '5',
            'motor': '6',
            'startTimestamp': '0',
        }

        # Access the route
        test_resp = requests.post(route_manager.BASE_URL + route_manager.URL_PREFIX + '/observation/score/gcs/',
                                  data=json.dumps(demo_data),
                                  cookies=self.auth_resp.cookies)
        self.assertEqual(test_resp.status_code, 200)
        self.assertEqual(test_resp.headers['content-type'], 'application/json')

        expected_json = {
            'score': {
                'score': 15
            },
            'modal_vals': {
                'next_action': 'json_patient_form_action',
                'title': 'Submit GCS of 15',
                'content': '<p>Please confirm you want to submit this score</p>'
            }
        }
        self.check_response_json(test_resp, ResponseJSON.STATUS_SUCCESS,
                                 'Submit GCS of 15',
                                 '<p>Please confirm you want to submit this score</p>',
                                 expected_json)

    def test_03_route_calculate_non_scoring_observation_score(self):
        """ Test the GCS score route, send GCS parameters to route and make sure
        it sends back score but not clinical risk
        :return:
        """
        # check if the route under test is actually present in the Route Manager
        route_under_test = route_manager.get_route('calculate_obs_score')
        self.assertIsInstance(route_under_test, Route)

        # Create demo data
        demo_data = {
            'weight': '4',
            'startTimestamp': '0',
        }

        # Access the route
        test_resp = requests.post(route_manager.BASE_URL + route_manager.URL_PREFIX + '/observation/score/weight/',
                                  data=json.dumps(demo_data),
                                  cookies=self.auth_resp.cookies)
        self.assertEqual(test_resp.status_code, 400)
        self.assertEqual(test_resp.headers['content-type'], 'text/html')

    def test_04_route_json_partial_reasons(self):
        """ Test the partial reasons route attribute of the EWS class
        (set in nh_observations)
        :return:
        """
        # Check if the route under test is actually present into the Route Manager
        route_under_test = route_manager.get_route('json_partial_reasons')
        self.assertIsInstance(route_under_test, Route)

        # Access the route
        test_resp = requests.get(route_manager.BASE_URL + route_manager.URL_PREFIX + route_under_test.url, cookies=self.auth_resp.cookies)
        self.assertEqual(test_resp.status_code, 200)
        self.assertEqual(test_resp.headers['content-type'], 'application/json')

        # Check the returned JSON data against the expected ones
        expected_json = self.registry('nh.clinical.patient.observation.ews')._partial_reasons
        self.check_response_json(test_resp, ResponseJSON.STATUS_SUCCESS,
                                 'Reason for partial observation',
                                 'Please select an option from the list',
                                 expected_json)

    # Test Stand-in routes
    def test_05_route_share_patients(self):
        """Test that the 'json_share_patients' route returns a list of users who you've invited to follow your patients."""
        route_under_test = route_manager.get_route('json_share_patients')
        self.assertIsInstance(route_under_test, Route)

        def mock_nh_eobs_api_follow_invite(*args, **kwargs):
            return 2001

        # Get list of users to share with
        users_login_list = TestOdooRouteDecoratorIntegration.mock_res_users_read()

        # Get a list of patients to share
        patient_list = TestOdooRouteDecoratorIntegration.mock_get_patients()

        # Create demo data
        demo_data = {
            'patient_ids': ','.join([str(p['id']) for p in patient_list]),
            'user_ids': ','.join([str(u['id']) for u in users_login_list])
        }

        # Start Odoo's patchers
        api_pool = self.registry('nh.eobs.api')
        users_pool = self.registry('res.users')

        api_pool._patch_method('follow_invite', mock_nh_eobs_api_follow_invite)
        users_pool._patch_method('read', TestOdooRouteDecoratorIntegration.mock_res_users_read)

        # Access the route
        test_resp = requests.post(route_manager.BASE_URL + route_manager.URL_PREFIX + route_under_test.url,
                                  data=json.dumps(demo_data),
                                  cookies=self.auth_resp.cookies)

        # Stop Odoo's patchers
        api_pool._revert_method('follow_invite')
        users_pool._revert_method('read')

        self.assertEqual(test_resp.status_code, 200)
        self.assertEqual(test_resp.headers['content-type'], 'application/json')

        # Actual test
        expected_json = {
            'reason': 'An invite has been sent to follow the selected patients.',
            'shared_with': ['John Smith', 'Jane Doe', 'Joe Average']
        }
        self.check_response_json(test_resp, ResponseJSON.STATUS_SUCCESS,
                                 'Invitation sent',
                                 'An invite has been sent to follow the selected patients',
                                 expected_json)

    def test_06_route_claim_patients(self):
        """Test the 'json_claim_patients' route.

        Sending a POST request with a list of patients' ids should return a confirmation that you've taken those patients back.
        """
        route_under_test = route_manager.get_route('json_claim_patients')
        self.assertIsInstance(route_under_test, Route)

        # Set up the list of patients to claim back
        patient_list = TestOdooRouteDecoratorIntegration.mock_get_patients()

        # Create demo data
        demo_data = {
            'patient_ids': ','.join([str(p['id']) for p in patient_list])
        }

        # Start Odoo's patchers
        api_pool = self.registry('nh.eobs.api')
        api_pool._patch_method('remove_followers', TestOdooRouteDecoratorIntegration.mock_method_returning_true)

        # Access the route
        test_resp = requests.post(route_manager.BASE_URL + route_manager.URL_PREFIX + route_under_test.url,
                                  data=json.dumps(demo_data),
                                  cookies=self.auth_resp.cookies)

        # Stop Odoo's patchers
        api_pool._revert_method('remove_followers')

        self.assertEqual(test_resp.status_code, 200)
        self.assertEqual(test_resp.headers['content-type'], 'application/json')

        # Actual test
        expected_json = {
            'reason': 'Followers removed successfully.'
        }
        self.check_response_json(test_resp, ResponseJSON.STATUS_SUCCESS,
                                 'Patients claimed',
                                 'Followers removed successfully',
                                 expected_json)

    def test_07_route_colleagues_list(self):
        """Test that the 'json_colleagues_list' route returns a list of colleagues you can invite to follow your patients."""
        route_under_test = route_manager.get_route('json_colleagues_list')
        self.assertIsInstance(route_under_test, Route)

        def mock_get_share_users(*args, **kwargs):
            share_users_list = [
                {
                    'id': 33,
                    'patients': 12,
                    'name': 'John Smith'
                },
                {
                    'id': 34,
                    'patients': 2,
                    'name': 'Jane Doe'
                },
                {
                    'id': 35,
                    'patients': 9,
                    'name': 'Joe Average'
                }
            ]
            return share_users_list

        # Start Odoo's patchers
        api_pool = self.registry('nh.eobs.api')
        api_pool._patch_method('get_share_users', mock_get_share_users)

        # Access the route
        test_resp = requests.get(route_manager.BASE_URL + route_manager.URL_PREFIX + route_under_test.url, cookies=self.auth_resp.cookies)

        # Stop Odoo's patchers
        api_pool._revert_method('get_share_users')

        self.assertEqual(test_resp.status_code, 200)
        self.assertEqual(test_resp.headers['content-type'], 'application/json')

        # Check the returned JSON data against the expected ones
        expected_json = mock_get_share_users()
        self.check_response_json(test_resp, ResponseJSON.STATUS_SUCCESS,
                                 'Colleagues on shift',
                                 'Choose colleagues for stand-in',
                                 expected_json)

    def test_08_route_invite_user(self):
        """Test patients you're invited to follow route, should return a list of patients and their activities."""
        route_under_test = route_manager.get_route('json_invite_patients')
        self.assertIsInstance(route_under_test, Route)
        url_under_test = route_manager.BASE_URL + route_manager.URL_PREFIX + '/staff/invite/2001'

        # Start Odoo's patchers
        eobs_api = self.registry['nh.eobs.api']
        methods_patching_list = [
            ('get_assigned_activities', TestOdooRouteDecoratorIntegration.mock_get_assigned_activities),
            ('get_patients', TestOdooRouteDecoratorIntegration.mock_get_patients),
        ]
        self._bulk_patch_odoo_model_method(eobs_api, methods_patching_list)

        # Access the url under test
        test_resp = requests.get(url_under_test, cookies=self.auth_resp.cookies)

        # Stop Odoo's patchers
        methods_to_revert = [m[0] for m in methods_patching_list]
        self._revert_bulk_patch_odoo_model_method(eobs_api, methods_to_revert)

        self.assertEqual(test_resp.status_code, 200)
        self.assertEqual(test_resp.headers['content-type'], 'application/json')

        # Test that the response is correct
        expected_json = TestOdooRouteDecoratorIntegration.mock_get_patients()
        self.check_response_json(test_resp, ResponseJSON.STATUS_SUCCESS,
                                 'Patients shared with you',
                                 'These patients have been shared for you to follow',
                                 expected_json)

    def test_09_route_accept_user(self):
        """Test the route for accepting invitation to follow patient.

        The method under test should return the id of an activity and a 'true' status.
        """
        route_under_test = route_manager.get_route('json_accept_patients')
        self.assertIsInstance(route_under_test, Route)
        url_under_test = route_manager.BASE_URL + route_manager.URL_PREFIX + '/staff/accept/2001'

        # Start Odoo's patchers
        eobs_api = self.registry['nh.eobs.api']
        methods_patching_list = [
            ('get_assigned_activities', TestOdooRouteDecoratorIntegration.mock_get_assigned_activities),
            ('complete', TestOdooRouteDecoratorIntegration.mock_method_returning_true),
        ]
        self._bulk_patch_odoo_model_method(eobs_api, methods_patching_list)

        # Access the url under test
        test_resp = requests.post(url_under_test, cookies=self.auth_resp.cookies)

        # Stop Odoo's patchers
        methods_to_revert = [m[0] for m in methods_patching_list]
        self._revert_bulk_patch_odoo_model_method(eobs_api, methods_to_revert)

        self.assertEqual(test_resp.status_code, 200)
        self.assertEqual(test_resp.headers['content-type'], 'application/json')

        # Test that the response is correct
        expected_json = {
            'id': 2001,
            'user': 'Nurse Nadine',
            'count': 3,
            'patient_ids': [1, 2, 3],
            'message': 'You have been invited to follow 3 patients from Nurse Nadine',
            'status': True
            }

        self.check_response_json(test_resp, ResponseJSON.STATUS_SUCCESS,
                                 'Successfully accepted stand-in invite',
                                 'You are following these patient(s)',
                                 expected_json)

    def test_09_bis_accept_user_route_manages_exception_while_completing_activity(self):
        """Test if the route for accepting invitation to follow patient manages exceptions."""
        route_under_test = route_manager.get_route('json_accept_patients')
        self.assertIsInstance(route_under_test, Route)
        url_under_test = route_manager.BASE_URL + route_manager.URL_PREFIX + '/staff/accept/2001'

        # Start Odoo's patchers
        eobs_api = self.registry['nh.eobs.api']
        methods_patching_list = [
            ('get_assigned_activities', TestOdooRouteDecoratorIntegration.mock_get_assigned_activities),
            ('complete', TestOdooRouteDecoratorIntegration.mock_method_returning_osv_exception),
        ]
        self._bulk_patch_odoo_model_method(eobs_api, methods_patching_list)

        # Access the url under test
        test_resp = requests.post(url_under_test, cookies=self.auth_resp.cookies)

        # Stop Odoo's patchers
        methods_to_revert = [m[0] for m in methods_patching_list]
        self._revert_bulk_patch_odoo_model_method(eobs_api, methods_to_revert)

        self.assertEqual(test_resp.status_code, 200)
        self.assertEqual(test_resp.headers['content-type'], 'application/json')

        # Test that the response is correct
        expected_json = {'reason': 'Unable to complete the activity.'}

        self.check_response_json(test_resp, ResponseJSON.STATUS_ERROR,
                                 'Unable to accept stand-in invite',
                                 'An error occurred when trying to accept the stand-in invite',
                                 expected_json)

    def test_10_route_reject_user(self):
        """Test the route for rejecting invitation to follow patient.

        The method under test should return the id of an activity and a 'true' status.
        """
        route_under_test = route_manager.get_route('json_reject_patients')
        self.assertIsInstance(route_under_test, Route)
        url_under_test = route_manager.BASE_URL + route_manager.URL_PREFIX + '/staff/reject/2001'

        # Start Odoo's patchers
        eobs_api = self.registry['nh.eobs.api']
        methods_patching_list = [
            ('get_assigned_activities', TestOdooRouteDecoratorIntegration.mock_get_assigned_activities),
            ('cancel', TestOdooRouteDecoratorIntegration.mock_method_returning_true),
        ]
        self._bulk_patch_odoo_model_method(eobs_api, methods_patching_list)

        # Access the url under test
        test_resp = requests.post(url_under_test, cookies=self.auth_resp.cookies)

        # Stop Odoo's patchers
        methods_to_revert = [m[0] for m in methods_patching_list]
        self._revert_bulk_patch_odoo_model_method(eobs_api, methods_to_revert)

        self.assertEqual(test_resp.status_code, 200)
        self.assertEqual(test_resp.headers['content-type'], 'application/json')

        # Test that the response is correct
        expected_json = {
            'id': 2001,
            'user': 'Nurse Nadine',
            'count': 3,
            'patient_ids': [1, 2, 3],
            'message': 'You have been invited to follow 3 patients from Nurse Nadine',
            'status': True
            }

        self.check_response_json(test_resp, ResponseJSON.STATUS_SUCCESS,
                                 'Successfully rejected stand-in invite',
                                 'You are not following these patient(s)',
                                 expected_json)

    def test_10_bis_reject_user_route_manages_exception_while_cancelling_activity(self):
        """Test if the route for rejecting invitation to follow patient manages exceptions."""
        route_under_test = route_manager.get_route('json_reject_patients')
        self.assertIsInstance(route_under_test, Route)
        url_under_test = route_manager.BASE_URL + route_manager.URL_PREFIX + '/staff/reject/2001'

        # Start Odoo's patchers
        eobs_api = self.registry['nh.eobs.api']
        methods_patching_list = [
            ('get_assigned_activities', TestOdooRouteDecoratorIntegration.mock_get_assigned_activities),
            ('cancel', TestOdooRouteDecoratorIntegration.mock_method_returning_osv_exception),
        ]
        self._bulk_patch_odoo_model_method(eobs_api, methods_patching_list)

        # Access the url under test
        test_resp = requests.post(url_under_test, cookies=self.auth_resp.cookies)

        # Stop Odoo's patchers
        methods_to_revert = [m[0] for m in methods_patching_list]
        self._revert_bulk_patch_odoo_model_method(eobs_api, methods_to_revert)

        self.assertEqual(test_resp.status_code, 200)
        self.assertEqual(test_resp.headers['content-type'], 'application/json')

        # Test that the response is correct
        expected_json = {'reason': 'Unable to cancel the activity.'}

        self.check_response_json(test_resp, ResponseJSON.STATUS_ERROR,
                                 'Unable to reject stand-in invite',
                                 'An error occurred when trying to reject the stand-in invite',
                                 expected_json)

    # Test Task routes

    def test_11_take_task_route(self):
        """Test the 'json_take_task' route, supplying it correct data.

        The method under test should return a successful message.
        """
        route_under_test = route_manager.get_route('json_take_task')
        self.assertIsInstance(route_under_test, Route)
        url_under_test = route_manager.BASE_URL + route_manager.URL_PREFIX + '/tasks/take_ajax/1002'
        auth_user_id = self.user_id

        def mock_nh_activity_read(*args, **kwargs):
            task_detail = {
                'id': 1002,
                'user_id': (auth_user_id, 'Test User')
            }
            return task_detail

        # Start Odoo's patchers
        activity_pool = self.registry('nh.activity')
        api_pool = self.registry('nh.eobs.api')
        activity_pool._patch_method('read', mock_nh_activity_read)
        api_pool._patch_method('assign', TestOdooRouteDecoratorIntegration.mock_method_returning_true)

        # Access the route
        test_resp = requests.post(url_under_test, cookies=self.auth_resp.cookies)

        # Stop Odoo's patchers
        activity_pool._revert_method('read')
        api_pool._revert_method('assign')

        self.assertEqual(test_resp.status_code, 200)
        self.assertEqual(test_resp.headers['content-type'], 'application/json')

        expected_json = {
            'reason': 'Task was free to take.'
        }
        # Check the returned JSON data against the expected ones
        self.check_response_json(test_resp, ResponseJSON.STATUS_SUCCESS,
                                 'Task successfully taken',
                                 'You can now perform this task',
                                 expected_json)

    def test_12_take_task_route_with_exception_while_assigning_task(self):
        """Test the 'json_take_task' route, when an exception is raised while assigning the task.

        The method under test should return an error message.
        """
        route_under_test = route_manager.get_route('json_take_task')
        self.assertIsInstance(route_under_test, Route)
        url_under_test = route_manager.BASE_URL + route_manager.URL_PREFIX + '/tasks/take_ajax/1002'
        auth_user_id = self.user_id

        def mock_nh_activity_read(*args, **kwargs):
            task_detail = {
                'id': 1002,
                'user_id': (auth_user_id, 'Test User')
            }
            return task_detail

        # Start Odoo's patchers
        activity_pool = self.registry('nh.activity')
        api_pool = self.registry('nh.eobs.api')
        activity_pool._patch_method('read', mock_nh_activity_read)
        api_pool._patch_method('assign', TestOdooRouteDecoratorIntegration.mock_method_returning_osv_exception)

        # Access the route
        test_resp = requests.post(url_under_test, cookies=self.auth_resp.cookies)

        # Stop Odoo's patchers
        activity_pool._revert_method('read')
        api_pool._revert_method('assign')

        self.assertEqual(test_resp.status_code, 200)
        self.assertEqual(test_resp.headers['content-type'], 'application/json')

        expected_json = {
            'reason': "Unable to assign to user."
        }
        self.check_response_json(test_resp, ResponseJSON.STATUS_ERROR,
                                 'Unable to take task',
                                 'An error occurred when trying to take the task',
                                 expected_json)

    def test_13_take_task_route_with_task_already_assigned_to_different_user(self):
        """Test the 'json_take_task' route, when the task is already assigned to a different user.

        The method under test should return a fail message.
        """
        route_under_test = route_manager.get_route('json_take_task')
        self.assertIsInstance(route_under_test, Route)
        url_under_test = route_manager.BASE_URL + route_manager.URL_PREFIX + '/tasks/take_ajax/1002'
        different_user_id = int(self.user_id) + 1

        def mock_nh_activity_read(*args, **kwargs):
            task_detail = {
                'id': 1002,
                'user_id': (different_user_id, 'Test User')
            }
            return task_detail

        # Start Odoo's patchers
        activity_pool = self.registry('nh.activity')
        activity_pool._patch_method('read', mock_nh_activity_read)

        # Access the route
        test_resp = requests.post(url_under_test, cookies=self.auth_resp.cookies)

        # Stop Odoo's patchers
        activity_pool._revert_method('read')

        self.assertEqual(test_resp.status_code, 200)
        self.assertEqual(test_resp.headers['content-type'], 'application/json')

        expected_json = {
            'reason': "Task assigned to another user."
        }
        self.check_response_json(test_resp, ResponseJSON.STATUS_FAIL,
                                 'Unable to take task',
                                 'This task is already assigned to another user',
                                 expected_json)

    def test_14_cancel_take_task_route(self):
        """Test the 'json_cancel_take_task' route, supplying it correct data.

        The method under test should return a successful message that says the task has been put back into the pool."""
        route_under_test = route_manager.get_route('json_cancel_take_task')
        self.assertIsInstance(route_under_test, Route)
        url_under_test = route_manager.BASE_URL + route_manager.URL_PREFIX + '/tasks/cancel_take_ajax/2001'
        auth_user_id = self.user_id

        def mock_nh_activity_read(*args, **kwargs):
            task_detail = {
                'id': 1002,
                'user_id': (auth_user_id, 'Test User')
            }
            return task_detail

        # Start Odoo's patchers
        activity_pool = self.registry('nh.activity')
        api_pool = self.registry('nh.eobs.api')
        activity_pool._patch_method('read', mock_nh_activity_read)
        api_pool._patch_method('unassign', TestOdooRouteDecoratorIntegration.mock_method_returning_true)

        # Access the route
        test_resp = requests.post(url_under_test, cookies=self.auth_resp.cookies)

        # Stop Odoo's patchers
        activity_pool._revert_method('read')
        api_pool._revert_method('unassign')

        self.assertEqual(test_resp.status_code, 200)
        self.assertEqual(test_resp.headers['content-type'], 'application/json')

        expected_json = {
            'reason': 'Task was successfully unassigned from you.'
        }
        # Check the returned JSON data against the expected one
        self.check_response_json(test_resp, ResponseJSON.STATUS_SUCCESS,
                                 'Successfully released task',
                                 'The task has now been released back into the task pool',
                                 expected_json)

    def test_15_cancel_take_task_route_with_exception_while_unassigning_task(self):
        """Test the 'json_cancel_take_task' route, when an exception is raised while unassigning the task.

        This case occurs, for example, when trying to unassign a task that is already unassigned.
        The method under test should return an error message.
        """
        route_under_test = route_manager.get_route('json_cancel_take_task')
        self.assertIsInstance(route_under_test, Route)
        url_under_test = route_manager.BASE_URL + route_manager.URL_PREFIX + '/tasks/cancel_take_ajax/2001'
        auth_user_id = self.user_id

        def mock_nh_activity_read(*args, **kwargs):
            task_detail = {
                'id': 1002,
                'user_id': (auth_user_id, 'Test User')
            }
            return task_detail

        # Start Odoo's patchers
        activity_pool = self.registry('nh.activity')
        api_pool = self.registry('nh.eobs.api')
        activity_pool._patch_method('read', mock_nh_activity_read)
        api_pool._patch_method('unassign', TestOdooRouteDecoratorIntegration.mock_method_returning_osv_exception)

        # Access the route
        test_resp = requests.post(url_under_test, cookies=self.auth_resp.cookies)

        # Stop Odoo's patchers
        activity_pool._revert_method('read')
        api_pool._revert_method('unassign')

        self.assertEqual(test_resp.status_code, 200)
        self.assertEqual(test_resp.headers['content-type'], 'application/json')

        expected_json = {
            'reason': 'Unable to unassign task.'
        }
        self.check_response_json(test_resp, ResponseJSON.STATUS_ERROR,
                                 'Unable to release task',
                                 'An error occurred when trying to release the task back into the task pool',
                                 expected_json)

    def test_16_cancel_take_route_with_task_assigned_to_different_user(self):
        """Test the 'json_cancel_take_task' route when the task is assigned to a different user.

        The method under test should return a fail message.
        """
        route_under_test = route_manager.get_route('json_cancel_take_task')
        self.assertIsInstance(route_under_test, Route)
        url_under_test = route_manager.BASE_URL + route_manager.URL_PREFIX + '/tasks/cancel_take_ajax/1002'
        different_user_id = int(self.user_id) + 1

        def mock_nh_activity_read(*args, **kwargs):
            task_detail = {
                'id': 1002,
                'user_id': (different_user_id, 'Test User')
            }
            return task_detail

        # Start Odoo's patchers
        activity_pool = self.registry('nh.activity')
        activity_pool._patch_method('read', mock_nh_activity_read)

        # Access the route
        test_resp = requests.post(url_under_test, cookies=self.auth_resp.cookies)

        # Stop Odoo's patchers
        activity_pool._revert_method('read')

        self.assertEqual(test_resp.status_code, 200)
        self.assertEqual(test_resp.headers['content-type'], 'application/json')

        expected_json = {
            'reason': "Can't cancel other user's task."
        }
        self.check_response_json(test_resp, ResponseJSON.STATUS_FAIL,
                                 'Unable to release task',
                                 'The task you are trying to release is being carried out by another user',
                                 expected_json)

    def test_17_route_task_form_action(self):
        """Test the form submission route (task side).

        The method under test should return a successful status and a list of activities to carry out.
        """
        route_under_test = route_manager.get_route('json_task_form_action')
        self.assertIsInstance(route_under_test, Route)
        url_under_test = route_manager.BASE_URL + route_manager.URL_PREFIX + '/tasks/submit_ajax/ews/1605'

        # Test demo for EWS observation.
        # (Supplying specific data which result in an EWS total score less than 4 (according to the default EWS policy).
        # This way, no related tasks are created - does not really matter, due to mocking every Odoo's models calling).
        demo_data = {
            'respiration_rate': 18,
            'indirect_oxymetry_spo2': 100,
            'oxygen_administration_flag': False,
            'body_temperature': 37.5,
            'blood_pressure_systolic': 120,
            'blood_pressure_diastolic': 80,
            'pulse_rate': 80,
            'avpu_text': 'A',
            'taskId': 1605,
            'startTimestamp': 0
        }

        def mock_method_returning_converter_function(*args, **kwargs):
            """The converter function just returns the same data dictionary sent via POST request to the route."""
            def converter(*args, **kwargs):
                return demo_data
            return converter

        def mock_method_returning_list_of_ids(*args, **kwargs):
            return [123, 456, 789]

        def mock_method_returning_list_of_activities(*args, **kwargs):
            activities_list = [
                {
                    'id': 123,
                    'data_model': 'nh.clinical.patient.observation.ews',
                    'state': 'new'
                },
                {
                    'id': 456,
                    'data_model': 'nh.clinical.notification.frequency',
                    'state': 'scheduled'
                },
                {
                    'id': 789,
                    'data_model': 'nh.clinical.notification.assessment',
                    'state': 'completed'
                },
            ]
            return activities_list

        # Start Odoo's patchers
        activity_pool = self.registry('nh.activity')
        api_pool = self.registry('nh.eobs.api')
        ir_fields_converter = self.registry('ir.fields.converter')

        activity_pool._patch_method('search', mock_method_returning_list_of_ids)
        activity_pool._patch_method('read', mock_method_returning_list_of_activities)
        api_pool._patch_method('complete', TestOdooRouteDecoratorIntegration.mock_method_returning_true)
        api_pool._patch_method('check_activity_access', TestOdooRouteDecoratorIntegration.mock_method_returning_true)
        ir_fields_converter._patch_method('for_model', mock_method_returning_converter_function)

        # Access the route
        test_resp = requests.post(url_under_test, data=json.dumps(demo_data), cookies=self.auth_resp.cookies)

        # Stop Odoo's patchers
        activity_pool._revert_method('search')
        activity_pool._revert_method('read')
        api_pool._revert_method('complete')
        api_pool._revert_method('check_activity_access')
        ir_fields_converter._revert_method('for_model')

        self.assertEqual(test_resp.status_code, 200)
        self.assertEqual(test_resp.headers['content-type'], 'application/json')

        expected_json = {
            'related_tasks': [
                {
                    'id': 456,
                    'data_model': 'nh.clinical.notification.frequency',
                    'state': 'scheduled'
                }
            ]
        }

        self.check_response_json(test_resp, ResponseJSON.STATUS_SUCCESS,
                                 'Successfully submitted observation',
                                 'Here are related tasks based on the observation',
                                 expected_json)

    def test_18_route_confirm_notification(self):
        """Test the confirmation submission for notifications.

        The method under test should return a successful status and a list of activities to carry out.
        """
        route_under_test = route_manager.get_route('confirm_clinical_notification')
        self.assertIsInstance(route_under_test, Route)
        url_under_test = route_manager.BASE_URL + route_manager.URL_PREFIX + '/tasks/confirm_clinical/5061'

        # Access the route
        demo_data = {
            'taskId': 5061
        }

        def mock_method_returning_list_of_ids(*args, **kwargs):
            return [123, 456, 789]

        def mock_method_returning_list_of_activities(*args, **kwargs):
            activities_list = [
                {
                    'id': 123,
                    'data_model': 'nh.clinical.patient.observation.ews'
                },
                {
                    'id': 456,
                    'data_model': 'nh.clinical.notification.frequency'
                },
                {
                    'id': 789,
                    'data_model': 'nh.clinical.notification.assessment'
                },
            ]
            return activities_list

        # Start Odoo's patchers
        api_pool = self.registry('nh.eobs.api')
        activity_pool = self.registry('nh.activity')

        activity_pool._patch_method('search', mock_method_returning_list_of_ids)
        activity_pool._patch_method('read', mock_method_returning_list_of_activities)
        api_pool._patch_method('complete', TestOdooRouteDecoratorIntegration.mock_method_returning_true)
        api_pool._patch_method('check_activity_access', TestOdooRouteDecoratorIntegration.mock_method_returning_true)

        test_resp = requests.post(url_under_test, data=json.dumps(demo_data), cookies=self.auth_resp.cookies)

        # Stop Odoo's patchers
        activity_pool._revert_method('search')
        activity_pool._revert_method('read')
        api_pool._revert_method('complete')
        api_pool._revert_method('check_activity_access')

        self.assertEqual(test_resp.status_code, 200)
        self.assertEqual(test_resp.headers['content-type'], 'application/json')

        expected_json = {
            'related_tasks': [
                {
                    'id': 456,
                    'data_model': 'nh.clinical.notification.frequency'
                },
                {
                    'id': 789,
                    'data_model': 'nh.clinical.notification.assessment'
                },
            ]
        }

        self.check_response_json(test_resp, ResponseJSON.STATUS_SUCCESS,
                                 'Submission successful',
                                 'The notification was successfully submitted',
                                 expected_json)

    def test_19_route_cancel_notification(self):
        """Test the cancel submission for notifications.

        The method under test should return a successful status without any other activities to carry out.
        """
        route_under_test = route_manager.get_route('cancel_clinical_notification')
        self.assertIsInstance(route_under_test, Route)
        url_under_test = route_manager.BASE_URL + route_manager.URL_PREFIX + '/tasks/cancel_clinical/5061'

        demo_data = {
            'reason': 1
        }

        # Start Odoo's patchers
        api_pool = self.registry('nh.eobs.api')
        api_pool._patch_method('cancel', TestOdooRouteDecoratorIntegration.mock_method_returning_true)

        test_resp = requests.post(url_under_test, data=json.dumps(demo_data), cookies=self.auth_resp.cookies)

        # Stop Odoo's patchers
        api_pool._revert_method('cancel')

        self.assertEqual(test_resp.status_code, 200)
        self.assertEqual(test_resp.headers['content-type'], 'application/json')

        expected_json = {
            'related_tasks': []
        }

        self.check_response_json(test_resp, ResponseJSON.STATUS_SUCCESS,
                                 'Cancellation successful',
                                 'The notification was successfully cancelled',
                                 expected_json)

    def test_20_route_task_cancellation_options(self):
        """Test the route to get the task cancellation options.

        The method under test should return a list of task cancellation options.
        """
        route_under_test = route_manager.get_route('ajax_task_cancellation_options')
        self.assertIsInstance(route_under_test, Route)
        url_under_test = route_manager.BASE_URL + route_manager.URL_PREFIX + route_under_test.url

        def mock_method_returning_cancel_reasons_list(*args, **kwargs):
            cancel_reasons_list = [
                {
                    'name': 'Cancelled by Ward Manager',
                    'system': True
                },
                {
                    'name': 'Cancelled by System',
                    'system': True
                },
                {
                    'name': 'Already Done',
                    'system': False
                },
                {
                    'name': 'No need to do this task',
                    'system': False
                }
            ]
            return cancel_reasons_list

        # Start Odoo's patchers
        api_pool = self.registry('nh.eobs.api')
        api_pool._patch_method('get_cancel_reasons', mock_method_returning_cancel_reasons_list)

        test_resp = requests.get(url_under_test, cookies=self.auth_resp.cookies)

        # Stop Odoo's patchers
        api_pool._revert_method('get_cancel_reasons')

        self.assertEqual(test_resp.status_code, 200)
        self.assertEqual(test_resp.headers['content-type'], 'application/json')

        expected_json = mock_method_returning_cancel_reasons_list()

        self.check_response_json(test_resp, ResponseJSON.STATUS_SUCCESS,
                                 'Reason for cancelling task?',
                                 'Please select an option from the dropdown',
                                 expected_json)

    # Test Patient routes

    def test_21_route_patient_info(self):
        """ Test the route to get patient information, should return a dict of
        information on the patient
        :return:
        """
        api_pool = self.registry('nh.eobs.api')
        patient = api_pool.get_patients(self.cr, self.user_id, [])[0]

        # Check if the route under test is actually present into the Route Manager
        route_under_test = route_manager.get_route('json_patient_info')
        self.assertIsInstance(route_under_test, Route)

        # Access the route
        test_resp = requests.get(route_manager.BASE_URL + route_manager.URL_PREFIX + '/patient/info/' + str(patient['id']), cookies=self.auth_resp.cookies)
        self.assertEqual(test_resp.status_code, 200)
        self.assertEqual(test_resp.headers['content-type'], 'application/json')

        # Check the returned JSON data against the expected ones
        self.check_response_json(test_resp, ResponseJSON.STATUS_SUCCESS,
                                 '{0}'.format(patient['full_name']),
                                 'Information on {0}'.format(patient['full_name']),
                                 patient)

    def test_22_route_patient_info_invalid_id(self):
        """ Test the route to get patient information with an ID for a patient
        not in the system, should return an error
        :return:
        """
        api_pool = self.registry('nh.eobs.api')
        patient_pool = self.registry('nh.clinical.patient')
        patient = patient_pool.search(self.cr, self.uid, [])[-1]
        patient = patient + 1
        # patient = api_pool.get_patients(self.cr, self.auth_uid, [])[0]

        # Check if the route under test is actually present into the Route Manager
        route_under_test = route_manager.get_route('json_patient_info')
        self.assertIsInstance(route_under_test, Route)

        # Access the route
        test_resp = requests.get(route_manager.BASE_URL + route_manager.URL_PREFIX + '/patient/info/' + str(patient), cookies=self.auth_resp.cookies)
        self.assertEqual(test_resp.status_code, 200)
        self.assertEqual(test_resp.headers['content-type'], 'application/json')

        # Check the returned JSON data against the expected ones
        expected_json = {
            'error': 'Patient not found.'
        }
        self.check_response_json(test_resp, ResponseJSON.STATUS_ERROR,
                                 'Patient not found',
                                 'Unable to get patient with id provided',
                                 expected_json)

    def test_23_route_patient_barcode(self):
        """ Test the route to get patient information when sent a hospital no
        from a barcode, should return a dict of information on the patient
        :return:
        """
        api_pool = self.registry('nh.eobs.api')
        patient = api_pool.get_patients(self.cr, self.user_id, [])[0]

        # Check if the route under test is actually present into the Route Manager
        route_under_test = route_manager.get_route('json_patient_barcode')
        self.assertIsInstance(route_under_test, Route)

        # Access the route
        test_resp = requests.get(route_manager.BASE_URL + route_manager.URL_PREFIX + '/patient/barcode/' + str(patient['other_identifier']), cookies=self.auth_resp.cookies)
        self.assertEqual(test_resp.status_code, 200)
        self.assertEqual(test_resp.headers['content-type'], 'application/json')

        patient_info = api_pool.get_patient_info(self.cr, self.user_id, [patient['other_identifier']])[0]
        # Check the returned JSON data against the expected ones
        self.check_response_json(test_resp, ResponseJSON.STATUS_SUCCESS,
                                 '{0}'.format(patient['full_name']),
                                 'Information on {0}'.format(patient['full_name']),
                                 patient_info)

    def test_24_route_patient_barcode_invalid_id(self):
        """ Test the route to get patient information when sent an invalid
        hospital no from a barcode, should return an error
        :return:
        """
        api_pool = self.registry('nh.eobs.api')
        patient = api_pool.get_patients(self.cr, self.user_id, [])[0]

        # Check if the route under test is actually present into the Route Manager
        route_under_test = route_manager.get_route('json_patient_barcode')
        self.assertIsInstance(route_under_test, Route)

        # Access the route
        test_resp = requests.get(route_manager.BASE_URL + route_manager.URL_PREFIX + '/patient/barcode/this_should_not_work', cookies=self.auth_resp.cookies)
        self.assertEqual(test_resp.status_code, 200)
        self.assertEqual(test_resp.headers['content-type'], 'application/json')

        expected_json = {
            'error': 'Patient not found.'
        }
        # Check the returned JSON data against the expected ones
        self.check_response_json(test_resp, ResponseJSON.STATUS_ERROR,
                                 'Patient not found',
                                 'Unable to get patient with id provided',
                                 expected_json)

    def test_25_route_patient_obs(self):
        """ Test the route to get the observation data for a patient, should
        return an array of dictionaries with the observations
        :return:
        """
        api_pool = self.registry('nh.eobs.api')
        patient = api_pool.get_patients(self.cr, self.user_id, [])[0]

        # Check if the route under test is actually present into the Route Manager
        route_under_test = route_manager.get_route('ajax_get_patient_obs')
        self.assertIsInstance(route_under_test, Route)

        # Access the route
        test_resp = requests.get(route_manager.BASE_URL + route_manager.URL_PREFIX + '/patient/ajax_obs/' + str(patient['id']), cookies=self.auth_resp.cookies)
        self.assertEqual(test_resp.status_code, 200)
        self.assertEqual(test_resp.headers['content-type'], 'application/json')

        ews = api_pool.get_activities_for_patient(self.cr, self.user_id, patient_id=int(patient['id']), activity_type='ews')
        for ew in ews:
            for e in ew:
                if e in ['date_terminated', 'create_date', 'write_date', 'date_started']:
                    ew[e] = fields.datetime.context_timestamp(self.cr, self.user_id, datetime.strptime(ew[e], DTF)).strftime(DTF)

        expected_json = {
            'obs': ews,
            'obsType': 'ews'
        }
        # Check the returned JSON data against the expected ones
        self.check_response_json(test_resp, ResponseJSON.STATUS_SUCCESS,
                                 '{0}'.format(patient['full_name']),
                                 'Observations for {0}'.format(patient['full_name']),
                                 expected_json)

    def test_26_route_patient_form_action(self):
        """ Test the route to submit an observation via the patient form, should
        return a status and the ids of other activities to carry out
        :return:
        """
        api_pool = self.registry('nh.eobs.api')
        patient = api_pool.get_patients(self.cr, self.user_id, [])[0]

        # test demo for ews observation
        # supplying specific data which result in an EWS total score less than 4 (according to the default EWS policy)
        # this way, no related tasks are created
        demo_data = {
            'respiration_rate': 18,
            'indirect_oxymetry_spo2': 100,
            'oxygen_administration_flag': False,
            'body_temperature': 37.5,
            'blood_pressure_systolic': 120,
            'blood_pressure_diastolic': 80,
            'pulse_rate': 80,
            'avpu_text': 'A',
            'startTimestamp': 0
        }

        # Check if the route under test is actually present into the Route Manager
        route_under_test = route_manager.get_route('json_patient_form_action')
        self.assertIsInstance(route_under_test, Route)

        # Access the route
        test_resp = requests.post(route_manager.BASE_URL + route_manager.URL_PREFIX + '/patient/submit_ajax/ews/' + str(patient['id']),
                                  data=json.dumps(demo_data),
                                  cookies=self.auth_resp.cookies)
        self.assertEqual(test_resp.status_code, 200)
        self.assertEqual(test_resp.headers['content-type'], 'application/json')

        expected_json = {
            'related_tasks': []
        }

        self.check_response_json(test_resp, ResponseJSON.STATUS_SUCCESS,
                                 'Observation successfully submitted',
                                 'Here are related tasks based on the observation',
                                 expected_json)