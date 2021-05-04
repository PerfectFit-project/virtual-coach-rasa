from flask import make_response, request

def http_response(sensor_type):
    """HTTP responce to a POST request.

    Args:
        sensor_type(str): "Accelerometer".

    Returns:
        HTTP responce: Responce to POST request.
    """
    req_data = request.data
    req_data = req_data.decode('utf-8')
    # TODO: valid userID
    # valid, message = validator.validate(req_data, sensor_type)
    valid = True
    message = ''

    if valid:
        # TODO: store data to DB
        return make_response({'message': 'Ok'}, 200)
    else:
        return make_response({'message': message}, 405)


class Sensor():
    def __init__(self, sensor_type):
        self.sensor_type = sensor_type

    def post(self):
        '''
        POST sensor data
        '''
        return http_response(self.sensor_type)


Accelerometer = Sensor('Accelerometer')