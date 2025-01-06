from rest_framework.response import Response
from rest_framework import status


def get_successful_response(data=None, message=None, **kwargs):
    data = {'data': data, 'status': 'SUCCESS', 'message': message}
    return Response(status=status.HTTP_200_OK, data=data | kwargs)


def get_successful_creation_response(data=None, message=None):
    return Response(
        status=status.HTTP_201_CREATED,
        data={'data': data, 'status': 'SUCCESS', 'message': message},
    )


def get_bad_request_response(data=None, message=None):
    return Response(
        status=status.HTTP_400_BAD_REQUEST,
        data={'data': data, 'status': 'FAILED', 'message': message},
    )


def get_not_found_response(data=None, message=None):
    return Response(
        status=status.HTTP_404_NOT_FOUND,
        data={'data': data, 'status': 'FAILED', 'message': message},
    )


def get_already_exists_response(data=None, message=None):
    return Response(
        status=status.HTTP_409_CONFLICT,
        data={'data': data, 'status': 'FAILED', 'message': message},
    )


def get_unauthorized_response(data=None, message=None):
    return Response(
        status=status.HTTP_401_UNAUTHORIZED,
        data={'data': data, 'status': 'FAILED', 'message': message},
    )
