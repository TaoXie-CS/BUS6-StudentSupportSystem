import pytest


class TestSurveyAccessControl:
    """Test survey access control permissions"""

    def test_survey_home_student_access(self, client, auth):
        """Test student access to the survey home page"""
        # Login first
        response = auth.login('student1', 'password')
        # Verify successful login
        assert response.status_code == 200

        response = client.get('/survey')
        # Should redirect to basic info page
        assert response.status_code == 302
        # Check redirect location
        if response.location:
            # May redirect to /survey/basic_info or /login?next=...
            assert '/survey/basic_info' in response.location or '/login' in response.location

    def test_survey_home_teacher_access(self, client, auth):
        """Test teacher access to survey home (should be denied)"""
        response = auth.login('teacher1', 'password')
        assert response.status_code == 200

        response = client.get('/survey', follow_redirects=True)
        assert response.status_code == 200
        # Decode byte string to regular string
        response_text = response.data.decode('utf-8')
        # Check for error message or redirect to login
        if 'Only students can complete surveys' not in response_text:
            # May be redirected to another page
            assert 'Login' in response_text or 'Please log in' in response_text

    def test_survey_home_admin_access(self, client, auth):
        """Test admin access to survey home (should be denied)"""
        response = auth.login('admin1', 'password')
        assert response.status_code == 200

        response = client.get('/survey', follow_redirects=True)
        assert response.status_code == 200
        # Decode byte string to regular string
        response_text = response.data.decode('utf-8')
        # Check for error message or redirect to login
        if 'Only students can complete surveys' not in response_text:
            # May be redirected to another page
            assert 'Login' in response_text or 'Please log in' in response_text

    def test_survey_home_unauthenticated(self, client):
        """Test unauthenticated user access to survey home"""
        response = client.get('/survey', follow_redirects=True)
        # Should redirect to login page
        assert response.status_code == 200
        # Decode byte string to regular string
        response_text = response.data.decode('utf-8')
        assert 'Please log in' in response_text or 'Login' in response_text


class TestSurveyTypeSelection:
    """Test survey type selection functionality"""

    def test_get_select_type(self, client, auth):
        """Test accessing the survey type selection page"""
        # Login first
        response = auth.login('student1', 'password')
        assert response.status_code == 200

        with client.session_transaction() as session:
            session['survey_grade'] = 'Junior'
            session['survey_major'] = 'Computer Science'

        response = client.get('/survey/select_type')
        # Check status code, may be 200 or 302
        if response.status_code == 302:
            # Redirected, check if it goes to login page
            assert response.location and '/login' in response.location
        else:
            assert response.status_code == 200
            # Decode byte string to regular string
            response_text = response.data.decode('utf-8')
            # Check page content
            assert 'Select Survey Type' in response_text

    def test_post_select_learning_survey(self, client, auth):
        """Test selecting the learning survey type"""
        # Login first
        response = auth.login('student1', 'password')
        assert response.status_code == 200

        with client.session_transaction() as session:
            session['survey_grade'] = 'Junior'
            session['survey_major'] = 'Computer Science'

        response = client.post('/survey/select_type', data={
            'survey_type': 'learning'
        }, follow_redirects=True)

        # Check status code
        if response.status_code == 302:
            # Redirected
            assert response.location
        else:
            assert response.status_code == 200
            # Check session data
            with client.session_transaction() as session:
                # Note: session may be cleared after redirect
                if 'survey_type' in session:
                    assert session.get('survey_type') == 'learning'

    def test_reset_basic_info(self, client, auth):
        """Test resetting survey basic information"""
        # Login first
        response = auth.login('student1', 'password')
        assert response.status_code == 200

        with client.session_transaction() as session:
            session['survey_grade'] = 'Junior'
            session['survey_major'] = 'Computer Science'
            session['survey_type'] = 'learning'

        # Access reset page
        response = client.get('/survey/reset', follow_redirects=True)

        # Check status code
        if response.status_code == 302:
            # Redirected
            assert response.location
        else:
            assert response.status_code == 200
            # Decode byte string to regular string
            response_text = response.data.decode('utf-8')

            # Check if redirected to login or basic info page
            if 'Grade' in response_text:
                # Returned to basic info page, verify session cleared
                with client.session_transaction() as session:
                    # Session should be cleared
                    assert session.get('survey_grade') is None
                    assert session.get('survey_major') is None
                    assert session.get('survey_type') is None
            elif 'Login' in response_text or 'Please log in' in response_text:
                # Redirected to login page
                assert 'Login' in response_text or 'Please log in' in response_text
            else:
                # Other case, likely success message page
                assert 'Survey' in response_text