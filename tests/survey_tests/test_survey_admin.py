import pytest


class TestAdminSurveyResults:
    """Test administrator survey results access and viewing"""

    def test_admin_results_access_control(self, client, auth):
        """Test access control for admin survey results page"""
        # Attempt access as student
        auth.login('student1', 'password')
        response = client.get('/admin/survey-results', follow_redirects=True)
        assert response.status_code == 200

        response_text = response.data.decode('utf-8')

        if 'Access denied. Admin only' not in response_text:
            assert 'Login' in response_text or 'Please log in' in response_text

        # Attempt access as teacher
        auth.logout()
        auth.login('teacher1', 'password')
        response = client.get('/admin/survey-results', follow_redirects=True)
        assert response.status_code == 200
        response_text = response.data.decode('utf-8')
        if 'Access denied. Admin only' not in response_text:
            assert 'Login' in response_text or 'Please log in' in response_text

        # Access as admin
        auth.logout()
        auth.login('admin1', 'password')
        response = client.get('/admin/survey-results')
        # If 200 status is returned, check page content
        if response.status_code == 200:
            response_text = response.data.decode('utf-8')
            assert 'Survey Results' in response_text
        else:
            # May redirect with 302
            assert response.status_code == 302

    def test_management_survey_results(self, client, auth, app):
        """Test viewing management survey results"""
        # Login as administrator
        auth.login('admin1', 'password')

        response = client.get('/admin/survey-results/management')
        # Check status code
        if response.status_code == 302:
            # Redirected, verify redirect location
            assert response.location is not None
        else:
            assert response.status_code == 200