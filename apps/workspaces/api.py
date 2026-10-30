"""Shared envelope, session authentication, throttles and bounded pagination."""
import logging
import uuid

from django.http import Http404
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework.views import APIView


class Conflict(APIException):
    status_code = 409
    default_detail = 'The request conflicts with the current resource.'
    default_code = 'conflict'


class WorkspaceAnonThrottle(AnonRateThrottle):
    rate = '60/min'
    scope = 'workspace_anon'


class WorkspaceUserThrottle(UserRateThrottle):
    rate = '180/min'
    scope = 'workspace_user'


class LoginThrottle(AnonRateThrottle):
    rate = '10/min'
    scope = 'workspace_login'

    def get_cache_key(self, request, view):
        # Count attempts even if an existing session is authenticated.
        return self.cache_format % {'scope': self.scope, 'ident': self.get_ident(request)}


def ok(data=None, status=200, meta=None):
    return Response({'success': True, 'data': data, 'error': None, 'meta': meta or {}}, status=status)


def page(queryset, request, serialize):
    try:
        limit = min(50, int(request.query_params.get('limit', 20)))
        offset = int(request.query_params.get('offset', 0))
        if limit < 1 or offset < 0 or offset > 100000:
            raise ValueError()
    except (ValueError, TypeError):
        raise ValidationError('Invalid pagination: limit > 0, offset between 0 and 100000.')
    count = queryset.count()
    return ok([serialize(item) for item in queryset[offset:offset + limit]],
              meta={'count': count, 'limit': limit, 'offset': offset})


logger = logging.getLogger(__name__)


class WorkspaceAPIView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, FormParser]
    renderer_classes = [JSONRenderer]
    throttle_classes = [WorkspaceAnonThrottle, WorkspaceUserThrottle]

    def initialize_request(self, request, *args, **kwargs):
        self.request_id = str(uuid.uuid4())
        return super().initialize_request(request, *args, **kwargs)

    def handle_exception(self, exc):
        try:
            response = super().handle_exception(exc)
        except Exception:
            logger.exception('Workspace request failed (request_id=%s)', self.request_id)
            response = Response({'detail': 'An internal error occurred.'}, status=500)
        code = getattr(exc, 'default_code', 'not_found' if isinstance(exc, Http404) else 'internal_error')
        details = response.data
        message = details.get('detail') if isinstance(details, dict) else None
        response.data = {'success': False, 'data': None,
                         'error': {'code': code, 'message': str(message or 'Request validation failed.'),
                                   'field_errors': details if not message else {}}, 'meta': {}}
        return response

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        if isinstance(response.data, dict):
            response.data = {**response.data, 'meta': {**response.data.get('meta', {}),
                                                     'request_id': self.request_id}}
        response['Cache-Control'] = 'no-store'
        response['X-Request-ID'] = self.request_id
        return response
