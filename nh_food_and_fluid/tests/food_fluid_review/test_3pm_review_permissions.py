from openerp.tests.common import TransactionCase


class Test3PMReviewPermissions(TransactionCase):
    """
    Test that only HCA, Nurses and Doctors can see the triggered F&F Review
    tasks
    """

    def test_hca_sees_3pm_task(self):
        """
        Test that once a 3pm review is triggered that the HCA associated with
        patient can see it
        """
        self.assertTrue(False)

    def test_nurse_sees_3pm_task(self):
        """
        Test that once 3pm review is triggered that the Nurse associated with
        patient can see it
        """
        self.assertTrue(False)

    def test_doctor_sees_3pm_task(self):
        """
        Test that once 3pm review is triggered that that Doctor associated with
        patient can see it
        """
        self.assertTrue(False)

    def test_shift_coordinator_cant_see_3pm_task(self):
        """
        Test that once 3pm review is triggered that the shift coordinator
        for ward patient is on cannot see it
        """
        self.assertTrue(False)

    def test_senior_manager_cant_see_3pm_task(self):
        """
        Test that once 3pm review is triggered that the senior manager
        for ward patient is on cannot see it
        """
        self.assertTrue(False)

    def test_system_admin_cant_see_3pm_task(self):
        """
        Test that once 3pm review is triggered that the system admin
        for system cannot see it
        """
        self.assertTrue(False)

    def test_super_user_cant_see_3pm_task(self):
        """
        Test that once 3pm review is triggered that the super user for system
        cannot see it
        """
        self.assertTrue(False)
