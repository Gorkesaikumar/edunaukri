from rest_framework import status
from rest_framework.response import Response


def success_response(data, *, status_code=status.HTTP_200_OK) -> Response:
    return Response({"success": True, "data": data}, status=status_code)


def error_response(
    code: str, message: str, *, status_code=status.HTTP_400_BAD_REQUEST, details=None
) -> Response:
    payload = {
        "success": False,
        "code": code,
        "message": message,
        "error": {"code": code, "message": message},
    }
    if details is not None:
        payload["error"]["details"] = details
    return Response(payload, status=status_code)


def validation_error_response(
    details, *, message: str = "Validation failed."
) -> Response:
    return error_response(
        "VALIDATION_ERROR",
        message,
        status_code=status.HTTP_400_BAD_REQUEST,
        details=details,
    )


def paginated_response(
    *, count, results, next_link=None, previous_link=None, page=None, page_size=None
) -> Response:
    data = {
        "count": count,
        "next": next_link,
        "previous": previous_link,
        "results": results,
    }
    if page is not None:
        data["page"] = page
    if page_size is not None:
        data["page_size"] = page_size
    return success_response(data)
