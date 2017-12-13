# -*- coding: utf-8 -*-
"""
Module containing the TestSetParams class.
"""
from openerp.exceptions import ValidationError, AccessError
from openerp.tests.common import TransactionCase
from psycopg2 import IntegrityError


class TestSetParams(TransactionCase):
    """
    Test the `set_params` method of the `nh.clinical.frequencies.ews_settings`
    model.
    """
    def setUp(self):
        """
        Setup the test environment.
        """
        super(TestSetParams, self).setUp()
        self.settings_model = self.env['nh.clinical.frequencies.ews_settings']
        self.config_parameters_model = self.env['ir.config_parameter']

        self.field_names = [
            'no_risk_minimum',
            'low_risk_minimum',
            'medium_risk_minimum',
            'high_risk_minimum',
            'no_risk_maximum',
            'low_risk_maximum',
            'medium_risk_maximum',
            'high_risk_maximum',
            'no_risk',
            'low_risk',
            'medium_risk',
            'high_risk',
            'placement',
            'obs_restart'
        ]

    def call_test(self, values=6, minimum=5, maximum=10):
        """
        Call the method under test.
        :param values:
        :param minimum:
        :param maximum:
        """
        self._set_field_dict(values, minimum, maximum)
        settings = self.settings_model.create(self.fields_dict)
        settings.set_params()
        return settings

    def _set_field_dict(self, values, minimum, maximum):
        """
        Set a dictionary of values to create the settings record that will
        set the params.
        :param values:
        :param minimum:
        :param maximum:
        """
        self.fields_dict = {
            field_name: values for field_name in self.field_names
        }
        for field_name in self.fields_dict:
            if 'minimum' in field_name:
                self.fields_dict[field_name] = minimum
            elif 'maximum' in field_name:
                self.fields_dict[field_name] = maximum


class TestUpdatesExistingParameters(TestSetParams):
    """
    Even if the config parameters have already been created, calling
    `set_params` will overwrite those values with the new ones.
    """
    def test_updates_existing_parameters(self):
        settings = self.call_test(values=8)
        expected_param_values = [str(field_value) for field_value
                                 in self.fields_dict.itervalues()]
        actual_param_values = \
            settings.get_default_params(self.field_names).values()
        self.assertEqual(expected_param_values, actual_param_values)

        self.call_test(values=9)
        expected_param_values = [str(field_value) for field_value
                                 in self.fields_dict.itervalues()]
        actual_param_values = \
            settings.get_default_params(self.field_names).values()
        self.assertEqual(expected_param_values, actual_param_values)


class TestRaisesValidationErrorIfAFieldIsBelowMinimum(TestSetParams):
    """
    A ValidationError is raised if the config value is below the minimum
    specified by its corresponding 'minimum' field.
    """
    def test_positive_values(self):
        with self.assertRaises(ValidationError):
            self.call_test(values=4, minimum=5, maximum=10)

    def test_other_positive_values(self):
        with self.assertRaises(ValidationError):
            self.call_test(values=8, minimum=9, maximum=10)

    def test_equal_minimum_and_maximum(self):
        with self.assertRaises(ValidationError):
            self.call_test(values=9, minimum=10, maximum=10)

    def test_some_negative_values(self):
        with self.assertRaises(ValidationError):
            self.call_test(values=-2, minimum=-1, maximum=10)

    def test_all_negative_values(self):
        with self.assertRaises(ValidationError):
            self.call_test(values=-11, minimum=-10, maximum=-9)


class TestRaisesValidationErrorIfAFieldIsAboveMaximum(TestSetParams):
    """
    A ValidationError is raised if the config value is below the maximum
    specified by its corresponding 'maximum' field.
    """
    def test_positive_values(self):
        with self.assertRaises(ValidationError):
            self.call_test(values=11, minimum=5, maximum=10)

    def test_other_positive_values(self):
        with self.assertRaises(ValidationError):
            self.call_test(values=10, minimum=5, maximum=9)

    def test_equal_minimum_and_maximum(self):
        with self.assertRaises(ValidationError):
            self.call_test(values=6, minimum=5, maximum=5)

    def test_some_negative_values(self):
        with self.assertRaises(ValidationError):
            self.call_test(values=-1, minimum=-5, maximum=-5)

    def test_all_negative_values(self):
        with self.assertRaises(ValidationError):
            self.call_test(values=-4, minimum=-5, maximum=-5)


class TestDoesNotRaiseIfFieldValueIsMinimum(TestSetParams):
    """
    No exception is raised if the config value is equal to the minimum
    specified by its corresponding 'minimum' field.
    """
    def test_positive_values(self):
        self.call_test(values=5, minimum=5, maximum=10)

    def test_other_positive_values(self):
        self.call_test(values=9, minimum=9, maximum=10)

    def test_some_negative_values(self):
        self.call_test(values=-5, minimum=-5, maximum=1)

    def test_all_negative_values(self):
        self.call_test(values=-5, minimum=-5, maximum=-1)


class TestDoesNotRaiseIfFieldValueIsMaximum(TestSetParams):
    """
    No exception is raised if the config value is equal to the maximum
    specified by its corresponding 'maximum' field.
    """
    def test_positive_values(self):
        self.call_test(values=10, minimum=5, maximum=10)

    def test_other_positive_values(self):
        self.call_test(values=6, minimum=5, maximum=6)

    def test_some_negative_values(self):
        self.call_test(values=1, minimum=-10, maximum=1)

    def test_all_negative_values(self):
        self.call_test(values=-5, minimum=-10, maximum=-5)


class TestDoesNotRaiseIfAllParametersEqual(TestSetParams):
    """
    No exception is raised if all arguments are equal.
    """
    def test_does_not_raise_if_all_parameters_equal(self):
        self.call_test(values=10, minimum=10, maximum=10)
        self.call_test(values=1, minimum=1, maximum=1)
        self.call_test(values=-1, minimum=-1, maximum=-1)


class TestDoesNotRaiseIfCalledByAdmin(TestSetParams):
    """
    No exception is raised if method is called by admin.
    """
    def test_does_not_raise_if_called_by_admin(self):
        self.call_test(values=6, minimum=5, maximum=10)
        self.call_test(values=2, minimum=1, maximum=3)
        self.call_test(values=-1, minimum=-10, maximum=10)
        self.call_test(values=-9, minimum=-10, maximum=-8)


class TestRaisesIfFieldIsZero(TestSetParams):
    """
    Raises if value is zero because that is not a valid value for an integer
    in Odoo. It results in a null being inserted / updated in the database
    which violates a not-null constraint.
    """
    def test_raises_if_field_is_zero(self):
        with self.assertRaises(IntegrityError):
            self.call_test(values=1, minimum=0, maximum=2)


class TestRaisesIfCalledBySystemAdmin(TestSetParams):
    def test_raises_if_called_by_system_admin(self):
        """
        Check that a system admin cannot set the params.
        """
        self._set_field_dict(8, 5, 10)
        test_utils = self.env['nh.clinical.test_utils']
        test_utils.create_locations()
        test_utils.create_system_admin()
        settings = self.settings_model.sudo(test_utils.system_admin).create(
            self.fields_dict)
        with self.assertRaises(AccessError):
            settings.sudo(test_utils.system_admin).set_params()
