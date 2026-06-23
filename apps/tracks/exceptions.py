from rest_framework.views import exception_handler


NOT_FOUND_DETAIL = 'N\u00e3o encontrado.'


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if (
        response is not None
        and response.status_code == 404
        and isinstance(response.data, dict)
        and 'detail' in response.data
        and 'code' not in response.data
    ):
        detail = response.data['detail']
        code = getattr(detail, 'code', None)
        if code:
            response.data = {
                'detail': NOT_FOUND_DETAIL if code == 'not_found' else str(detail),
                'code': code,
            }

    return response
