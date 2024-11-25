from rest_framework.exceptions import APIException
from rest_framework import status as http_status


class ResourceNotFound(APIException):
    status_code = http_status.HTTP_404_NOT_FOUND
    default_detail = 'Resource not found'
    default_code = 'resource_not_found'

    data = {}

    def __init__(self, message='Resource not found'):
        if message:
            self.detail = {'status': 'FAILED', 'message': message}
        else:
            self.detail = {'status': 'FAILED', 'message': self.default_detail}
        super().__init__(self.detail)
