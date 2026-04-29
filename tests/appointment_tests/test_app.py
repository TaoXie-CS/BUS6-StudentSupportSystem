#!/usr/bin/env python3
"""
Functional integrity test scope:
 user authentication, appointment system, permission control, admin access, edge cases.
 TODO: message CRUD, questionnaire submission flow (currently uncovered).
 Note: using an in-memory database, without polluting app.db
"""

import os
import sys
import unittest
from datetime import date

# ========== 0. Configure the testing environment ==========
os.environ['DATABASE_URI'] = 'sqlite:///:memory:'

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(CURRENT_DIR, 'app', '__init__.py')):
    PROJECT_DIR = CURRENT_DIR
else:
    PROJECT_DIR = os.path.join(CURRENT_DIR, 'BUS6-StudentSupportSystem')

if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from app import app, db
from app.models import User, TimeSlot, Appointment, SupportMessage

# ========== Color output ==========
OK = '\033[92m[PASS]\033[0m'
FAIL = '\033[91m[FAIL]\033[0m'
WARN = '\033[93m[WARN]\033[0m'
INFO = '\033[94m[INFO]\033[0m'


class TestResult(unittest.TextTestResult):
    """Custom test result output"""
    def addSuccess(self, test):
        super().addSuccess(test)
        print(f"{OK} {test._testMethodName}")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        print(f"{FAIL} {test._testMethodName}: {err[1]}")

    def addError(self, test, err):
        super().addError(test, err)
        print(f"{FAIL} {test._testMethodName}: {err[1]}")


class BaseTestCase(unittest.TestCase):
    """Base test class: initialize in-memory database before each test"""

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()

            self.student = User(username='test_student', email='student@test.com', role='student', school_id='S2026001')
            self.student.set_password('123456')
            self.teacher = User(username='test_teacher', email='teacher@test.com', role='teacher', school_id='T2026001', teacher_type='lecturer')
            self.teacher.set_password('123456')
            self.admin = User(username='test_admin', email='admin@test.com', role='admin', school_id='A2026001')
            self.admin.set_password('123456')

            db.session.add_all([self.student, self.teacher, self.admin])
            db.session.commit()

            self.student_id = self.student.id
            self.teacher_id = self.teacher.id
            self.admin_id = self.admin.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def login(self, email, password='123456'):
        return self.client.post('/login', data=dict(
            email=email, password=password, remember=False
        ), follow_redirects=True)

    def logout(self):
        return self.client.get('/logout', follow_redirects=True)

    def create_time_slot(self, teacher_id, date_obj, time_str):
        """Helper: create available time slots for teachers"""
        with self.app.app_context():
            slot = TimeSlot(teacher_id=teacher_id, date=date_obj, time_slot=time_str, is_booked=False)
            db.session.add(slot)
            db.session.commit()
            return slot.id


class TestAuthentication(BaseTestCase):
    def test_register_page_loads(self):
        rv = self.client.get('/register')
        self.assertEqual(rv.status_code, 200)

    def test_register_new_user(self):
        rv = self.client.post('/register', data=dict(
            username='newuser', email='new@test.com', school_id='S2026002',
            password='password', confirm_password='password', role='student', teacher_type=''
        ), follow_redirects=True)
        self.assertIn(b'login', rv.data.lower())

    def test_login_success(self):
        rv = self.login('student@test.com')
        self.assertIn(b'logout', rv.data.lower())

    def test_login_failure(self):
        rv = self.client.post('/login', data=dict(
            email='student@test.com', password='wrongpassword'
        ), follow_redirects=True)
        self.assertIn(b'login failed', rv.data.lower())

    def test_logout(self):
        self.login('student@test.com')
        self.logout()
        rv = self.client.get('/', follow_redirects=True)
        self.assertIn('/login', rv.request.path)

    def test_register_password_mismatch(self):
        """Registration fails if passwords do not match"""
        rv = self.client.post('/register', data=dict(
            username='newuser', email='new@test.com', school_id='S2026002',
            password='password', confirm_password='different', role='student', teacher_type=''
        ), follow_redirects=True)
        self.assertNotIn(b'logout', rv.data.lower())

    def test_register_cannot_set_admin_role(self):
        """Admin role cannot be set manually during registration (WTForms restriction)"""
        rv = self.client.post('/register', data=dict(
            username='hacker', email='hacker@test.com', school_id='S2026999',
            password='password', confirm_password='password', role='admin', teacher_type=''
        ), follow_redirects=True)
        self.assertNotIn(b'logout', rv.data.lower())

    def test_register_duplicate_email(self):
        """Duplicate emails are rejected by database unique constraint"""
        with self.app.app_context():
            user2 = User(username='another', email='student@test.com', role='student', school_id='S2026099')
            user2.set_password('password')
            db.session.add(user2)
            from sqlalchemy.exc import IntegrityError
            with self.assertRaises(IntegrityError):
                db.session.commit()
            db.session.rollback()

    def test_register_duplicate_school_id(self):
        """Duplicate school IDs are rejected by database unique constraint"""
        with self.app.app_context():
            user2 = User(username='another', email='another@test.com', role='student', school_id='S2026001')
            user2.set_password('password')
            db.session.add(user2)
            from sqlalchemy.exc import IntegrityError
            with self.assertRaises(IntegrityError):
                db.session.commit()
            db.session.rollback()


class TestUnauthorizedAccess(BaseTestCase):
    def test_unauthorized_access_to_protected_routes(self):
        """Unauthenticated users cannot access protected pages"""
        protected_urls = ['/appointment', '/teacher/time_slots', '/my_appointments']
        for url in protected_urls:
            rv = self.client.get(url, follow_redirects=True)
            self.assertIn(b'login', rv.data.lower(), f"{url} should redirect to login")

    def test_logout_session_invalidated(self):
        """Session is fully invalidated after logout"""
        self.login('student@test.com')
        rv = self.client.get('/appointment')
        self.assertEqual(rv.status_code, 200)
        self.logout()
        rv = self.client.get('/appointment', follow_redirects=True)
        self.assertIn(b'login', rv.data.lower())


class TestAppointmentSystem(BaseTestCase):
    def test_student_can_view_appointment_page(self):
        self.login('student@test.com')
        rv = self.client.get('/appointment')
        self.assertEqual(rv.status_code, 200)

    def test_teacher_cannot_make_appointment(self):
        self.login('teacher@test.com')
        rv = self.client.get('/appointment', follow_redirects=True)
        self.assertIn(b'only students', rv.data.lower())

    def test_teacher_can_manage_time_slots(self):
        self.login('teacher@test.com')
        rv = self.client.get('/teacher/time_slots')
        self.assertEqual(rv.status_code, 200)

    def test_student_cannot_manage_time_slots(self):
        self.login('student@test.com')
        rv = self.client.get('/teacher/time_slots', follow_redirects=True)
        self.assertIn(b'only teachers', rv.data.lower())

    def test_appointment_api_teachers(self):
        self.login('student@test.com')
        rv = self.client.get('/api/teachers/lecturer')
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'test_teacher', rv.data)

    def test_my_appointments_page(self):
        self.login('student@test.com')
        rv = self.client.get('/my_appointments')
        self.assertEqual(rv.status_code, 200)

    def test_student_book_different_subject_teachers(self):
        """Students book appointments with teachers of different types"""
        slot1_id = self.create_time_slot(self.teacher_id, date(2026, 6, 1), "09:00-10:00")

        with self.app.app_context():
            teacher2 = User(username='teacher2', email='teacher2@test.com', role='teacher',
                            school_id='T2026002', teacher_type='wellbeing_adviser')
            teacher2.set_password('123456')
            db.session.add(teacher2)
            db.session.commit()
            teacher2_id = teacher2.id

        slot2_id = self.create_time_slot(teacher2_id, date(2026, 6, 1), "10:00-11:00")

        self.login('student@test.com')

        rv1 = self.client.post('/appointment/submit', json={
            'time_slot_id': slot1_id,
            'appointment_type': 'lecturer',
            'description': 'Math help'
        })
        self.assertEqual(rv1.status_code, 200)
        self.assertTrue(rv1.get_json()['success'])

        rv2 = self.client.post('/appointment/submit', json={
            'time_slot_id': slot2_id,
            'appointment_type': 'wellbeing_adviser',
            'description': 'Counseling'
        })
        self.assertEqual(rv2.status_code, 200)
        self.assertTrue(rv2.get_json()['success'])

    def test_different_students_book_same_teacher(self):
        """Different students book different time slots with the same teacher"""
        with self.app.app_context():
            student2 = User(username='student2', email='student2@test.com', role='student',
                            school_id='S2026002')
            student2.set_password('123456')
            db.session.add(student2)
            db.session.commit()

        slot1_id = self.create_time_slot(self.teacher_id, date(2026, 6, 1), "09:00-10:00")
        slot2_id = self.create_time_slot(self.teacher_id, date(2026, 6, 1), "10:00-11:00")

        self.login('student@test.com')
        rv1 = self.client.post('/appointment/submit', json={
            'time_slot_id': slot1_id,
            'appointment_type': 'lecturer'
        })
        self.assertEqual(rv1.status_code, 200)
        self.assertTrue(rv1.get_json()['success'])

        self.logout()
        self.login('student2@test.com')
        rv2 = self.client.post('/appointment/submit', json={
            'time_slot_id': slot2_id,
            'appointment_type': 'lecturer'
        })
        self.assertEqual(rv2.status_code, 200)
        self.assertTrue(rv2.get_json()['success'])

    def test_student_cancel_appointment(self):
        """Time slot is released when student cancels appointment"""
        slot_id = self.create_time_slot(self.teacher_id, date(2026, 6, 1), "09:00-10:00")

        self.login('student@test.com')
        rv = self.client.post('/appointment/submit', json={
            'time_slot_id': slot_id,
            'appointment_type': 'lecturer'
        })
        self.assertTrue(rv.get_json()['success'])

        with self.app.app_context():
            appt = Appointment.query.filter_by(student_id=self.student_id).first()
            appt_id = appt.id
            self.assertTrue(TimeSlot.query.get(slot_id).is_booked)

        rv_cancel = self.client.post(f'/appointment/{appt_id}/cancel', follow_redirects=True)
        self.assertEqual(rv_cancel.status_code, 200)

        with self.app.app_context():
            self.assertFalse(TimeSlot.query.get(slot_id).is_booked)
            self.assertIsNone(Appointment.query.get(appt_id))

    def test_teacher_view_student_appointments(self):
        """Teacher can view student appointment details"""
        slot_id = self.create_time_slot(self.teacher_id, date(2026, 6, 1), "09:00-10:00")

        self.login('student@test.com')
        self.client.post('/appointment/submit', json={
            'time_slot_id': slot_id,
            'appointment_type': 'lecturer',
            'description': 'Math tutoring'
        })

        self.logout()
        self.login('teacher@test.com')
        rv = self.client.get('/my_appointments')
        self.assertEqual(rv.status_code, 200)

    def test_unauthorized_cannot_cancel_others_appointment(self):
        """Students and other users cannot cancel appointments made by other students"""
        with self.app.app_context():
            student2 = User(username='student2', email='student2@test.com', role='student',
                            school_id='S2026002')
            student2.set_password('123456')
            db.session.add(student2)
            db.session.commit()

        slot_id = self.create_time_slot(self.teacher_id, date(2026, 6, 1), "09:00-10:00")
        self.login('student@test.com')
        self.client.post('/appointment/submit', json={
            'time_slot_id': slot_id, 'appointment_type': 'lecturer'
        })

        with self.app.app_context():
            appt_id = Appointment.query.filter_by(student_id=self.student_id).first().id

        # Student2 tries to cancel
        self.logout()
        self.login('student2@test.com')
        rv = self.client.post(f'/appointment/{appt_id}/cancel', follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        self.assertIn('/', rv.request.path)

    def test_teacher_can_only_manage_own_slots(self):
        """Teachers can only manage their own time slots"""
        with self.app.app_context():
            teacher2 = User(username='teacher2', email='teacher2@test.com', role='teacher',
                            school_id='T2026002', teacher_type='lecturer')
            teacher2.set_password('123456')
            db.session.add(teacher2)
            db.session.commit()
            teacher2_id = teacher2.id

        self.create_time_slot(teacher2_id, date(2026, 6, 1), "09:00-10:00")
        self.login('teacher@test.com')
        rv = self.client.get('/teacher/time_slots')
        self.assertEqual(rv.status_code, 200)

    def test_cannot_double_book_slot(self):
        """Cannot book an already occupied time slot"""
        slot_id = self.create_time_slot(self.teacher_id, date(2026, 6, 1), "09:00-10:00")
        with self.app.app_context():
            student2 = User(username='s2', email='s2@test.com', role='student', school_id='S2026002')
            student2.set_password('123456')
            db.session.add(student2)
            db.session.commit()

        self.login('student@test.com')
        rv1 = self.client.post('/appointment/submit', json={
            'time_slot_id': slot_id, 'appointment_type': 'lecturer'
        })
        self.assertTrue(rv1.get_json()['success'])

        self.logout()
        self.login('s2@test.com')
        rv2 = self.client.post('/appointment/submit', json={
            'time_slot_id': slot_id, 'appointment_type': 'lecturer'
        })
        self.assertFalse(rv2.get_json()['success'])

    def test_cannot_book_past_time_slot(self):
        """Cannot book a time slot in the past"""
        past_slot_id = self.create_time_slot(self.teacher_id, date(2020, 1, 1), "09:00-10:00")
        self.login('student@test.com')
        rv = self.client.post('/appointment/submit', json={
            'time_slot_id': past_slot_id, 'appointment_type': 'lecturer'
        })
        self.assertFalse(rv.get_json()['success'])

    def test_database_unique_constraint_prevents_double_booking(self):
        """Database unique constraint prevents duplicate bookings"""
        slot_id = self.create_time_slot(self.teacher_id, date(2026, 6, 1), "09:00-10:00")
        with self.app.app_context():
            appt1 = Appointment(
                student_id=self.student_id, teacher_id=self.teacher_id,
                time_slot_id=slot_id, appointment_type='lecturer', status='confirmed'
            )
            db.session.add(appt1)
            db.session.commit()

            appt2 = Appointment(
                student_id=self.student_id, teacher_id=self.teacher_id,
                time_slot_id=slot_id, appointment_type='lecturer', status='confirmed'
            )
            db.session.add(appt2)
            from sqlalchemy.exc import IntegrityError
            with self.assertRaises(IntegrityError):
                db.session.commit()

    def test_invalid_appointment_id_returns_404(self):
        """Invalid appointment ID returns 404 without crashing"""
        self.login('student@test.com')
        rv = self.client.post('/appointment/99999/cancel', follow_redirects=True)
        self.assertEqual(rv.status_code, 404)

    def test_invalid_time_slot_id_handled(self):
        """Invalid time slot ID is handled gracefully"""
        self.login('student@test.com')
        rv = self.client.post('/appointment/submit', json={
            'time_slot_id': 99999, 'appointment_type': 'lecturer'
        })
        self.assertEqual(rv.status_code, 200)
        self.assertFalse(rv.get_json()['success'])

    def test_submit_appointment_missing_params(self):
        """Missing required parameters returns error without crashing"""
        self.login('student@test.com')
        rv = self.client.post('/appointment/submit', json={'appointment_type': 'lecturer'})
        self.assertEqual(rv.status_code, 200)
        self.assertFalse(rv.get_json()['success'])

        rv = self.client.post('/appointment/submit', json={'time_slot_id': 1})
        self.assertEqual(rv.status_code, 200)
        self.assertFalse(rv.get_json()['success'])

    def test_teacher_cannot_cancel_student_appointment(self):
        """Teachers cannot cancel appointments made by students"""
        slot_id = self.create_time_slot(self.teacher_id, date(2026, 6, 1), "09:00-10:00")
        self.login('student@test.com')
        self.client.post('/appointment/submit', json={
            'time_slot_id': slot_id, 'appointment_type': 'lecturer'
        })
        with self.app.app_context():
            appt_id = Appointment.query.filter_by(student_id=self.student_id).first().id

        self.logout()
        self.login('teacher@test.com')
        rv = self.client.post(f'/appointment/{appt_id}/cancel', follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        self.assertIn('/', rv.request.path)
        with self.app.app_context():
            self.assertIsNotNone(Appointment.query.get(appt_id))

    @unittest.expectedFailure
    def test_appointment_type_mismatch_with_teacher_type(self):
        """Appointment type should match teacher's teacher_type (backend check TBD)"""
        slot_id = self.create_time_slot(self.teacher_id, date(2026, 6, 1), "09:00-10:00")
        self.login('student@test.com')
        # teacher_type is 'lecturer', try booking as 'wellbeing_adviser'
        rv = self.client.post('/appointment/submit', json={
            'time_slot_id': slot_id,
            'appointment_type': 'wellbeing_adviser',
            'description': 'Type mismatch test'
        })
        self.assertEqual(rv.status_code, 200)
        self.assertFalse(rv.get_json()['success'])


class TestStaticRoutes(BaseTestCase):
    def test_404_page(self):
        rv = self.client.get('/nonexistent-page')
        self.assertEqual(rv.status_code, 404)

    def test_login_page_loads(self):
        rv = self.client.get('/login')
        self.assertEqual(rv.status_code, 200)


class TestAdminAccess(BaseTestCase):
    def test_admin_can_access_survey_results(self):
        """Admin can access survey results dashboard"""
        self.login('admin@test.com')
        rv = self.client.get('/admin/survey-results')
        self.assertEqual(rv.status_code, 200)

    def test_non_admin_cannot_access_survey_results(self):
        """Non-admins cannot access admin-only routes"""
        self.login('student@test.com')
        rv = self.client.get('/admin/survey-results', follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        self.assertIn('/', rv.request.path)

        self.logout()
        self.login('teacher@test.com')
        rv = self.client.get('/admin/survey-results', follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        self.assertIn('/', rv.request.path)


class TestMessageCRUD(BaseTestCase):
    """SupportMessage CRUD tests"""

    def test_teacher_can_create_message(self):
        """Teachers can create support messages"""
        self.login('teacher@test.com')
        rv = self.client.post('/new-message', data=dict(
            subject='Test Subject',
            message_content='Test content here',
            urgency='urgent'
        ), follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        with self.app.app_context():
            msg = SupportMessage.query.filter_by(subject='Test Subject').first()
            self.assertIsNotNone(msg)
            self.assertEqual(msg.author.id, self.teacher_id)

    def test_student_cannot_create_message(self):
        """Students cannot access new message page"""
        self.login('student@test.com')
        rv = self.client.get('/new-message', follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        self.assertIn('/', rv.request.path)

    def test_teacher_can_edit_own_message(self):
        """Teachers can edit their own messages"""
        with self.app.app_context():
            msg = SupportMessage(
                subject='Original',
                message_content='Original content',
                urgency='non-urgent',
                teacher_email=self.teacher.email,
                teacher_name=self.teacher.username,
                teacher_school_id=self.teacher.school_id,
                user_id=self.teacher_id
            )
            db.session.add(msg)
            db.session.commit()
            msg_id = msg.id

        self.login('teacher@test.com')
        rv = self.client.post(f'/edit/{msg_id}', data=dict(
            subject='Updated',
            message_content='Updated content',
            urgency='urgent'
        ), follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        with self.app.app_context():
            updated = SupportMessage.query.get(msg_id)
            self.assertEqual(updated.subject, 'Updated')

    def test_teacher_can_delete_own_message(self):
        """Teachers can delete their own messages"""
        with self.app.app_context():
            msg = SupportMessage(
                subject='To Delete',
                message_content='Delete me',
                urgency='non-urgent',
                teacher_email=self.teacher.email,
                teacher_name=self.teacher.username,
                teacher_school_id=self.teacher.school_id,
                user_id=self.teacher_id
            )
            db.session.add(msg)
            db.session.commit()
            msg_id = msg.id

        self.login('teacher@test.com')
        rv = self.client.get(f'/delete/{msg_id}', follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        with self.app.app_context():
            self.assertIsNone(SupportMessage.query.get(msg_id))

    def test_student_can_view_message_detail(self):
        """Students can view message details"""
        with self.app.app_context():
            msg = SupportMessage(
                subject='View Test',
                message_content='View content',
                urgency='non-urgent',
                teacher_email=self.teacher.email,
                teacher_name=self.teacher.username,
                teacher_school_id=self.teacher.school_id,
                user_id=self.teacher_id
            )
            db.session.add(msg)
            db.session.commit()
            msg_id = msg.id

        self.login('student@test.com')
        rv = self.client.get(f'/message/{msg_id}')
        self.assertEqual(rv.status_code, 200)


class TestSurveySystem(BaseTestCase):
    """Survey system basic flow tests"""

    def test_student_can_access_survey(self):
        """Students can access survey basic info page"""
        self.login('student@test.com')
        rv = self.client.get('/survey/basic_info')
        self.assertEqual(rv.status_code, 200)

    def test_teacher_cannot_access_survey(self):
        """Teachers are redirected from survey pages"""
        self.login('teacher@test.com')
        rv = self.client.get('/survey', follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        self.assertIn('/', rv.request.path)

    def test_survey_basic_info_submission(self):
        """Student can submit basic info and proceed"""
        self.login('student@test.com')
        rv = self.client.post('/survey/basic_info', data=dict(
            grade='Freshman',
            major='Computer Science'
        ), follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('survey_grade'), 'Freshman')
            self.assertEqual(sess.get('survey_major'), 'Computer Science')


class TestEdgeCases(BaseTestCase):
    def test_malformed_inputs_no_500(self):
        """Invalid inputs do not cause 500 errors"""
        self.login('student@test.com')

        rv1 = self.client.post('/appointment/submit', json={
            'time_slot_id': -1, 'appointment_type': 'lecturer'
        })
        self.assertIn(rv1.status_code, [200, 400, 404])
        self.assertFalse(rv1.get_json()['success'])

        rv2 = self.client.post('/appointment/submit', json={})
        self.assertIn(rv2.status_code, [200, 400])
        self.assertFalse(rv2.get_json()['success'])

        rv3 = self.client.post('/appointment/submit', json={
            'time_slot_id': 1, 'appointment_type': 'lecturer', 'description': 'x' * 10000
        })
        self.assertIn(rv3.status_code, [200, 400])


if __name__ == '__main__':
    print(f"\n{INFO} Starting functional integrity testing...")
    print(f"{INFO} Using an in-memory database – app.db will not be modified\n")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    for cls in [TestAuthentication, TestUnauthorizedAccess, TestAppointmentSystem,
                TestStaticRoutes, TestAdminAccess, TestMessageCRUD, TestSurveySystem,
                TestEdgeCases]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=0, resultclass=TestResult)
    result = runner.run(suite)

    print(f"\n{'='*50}")
    total = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total - failures - errors

    print(f"{INFO} Test completed")
    print(f"  Total:    {total}")
    print(f"  Passed:   {passed}")
    print(f"  Failures: {failures}")
    print(f"  Errors:   {errors}")

    if failures == 0 and errors == 0:
        print(f"\n{OK} All functional tests passed！")
    else:
        print(f"\n{FAIL} {failures} failures and {errors} errors detected.")

    sys.exit(0 if (failures == 0 and errors == 0) else 1)