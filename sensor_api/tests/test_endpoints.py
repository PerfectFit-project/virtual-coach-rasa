import pytest

from perfectfit.run import create_app


@pytest.fixture(scope='class')
def client(request):
    '''Build http client'''
    app = create_app(host='0.0.0.0', port=8080)
    with app.test_client() as client:
        yield client


class TestEndpoints:

    def test_accelerometer_api(self, client):
        """Testing Accelerometer API"""
        data = '{"sensorData": 0, "userID": "user@example.com"}'
        rv = client.post(
            '/sensor/accelerometer',
            data=data,
            content_type='application/json')
        assert rv.status_code == 200
        assert 'message' in rv.json
        assert rv.json['message'] == 'Ok'
