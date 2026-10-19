from http import HTTPStatus

from diamond_backend.app.errors import DiamondResponseError


class BadRequestError(Exception):
    status_code = 400
    message = "Bad Request"

    def __init__(self, message=None, status_code=None, payload=None):
        if message is not None:
            self.message = message
        if status_code is not None:
            self.status_code = status_code

        self.payload = payload

    def to_dict(self):
        ret = dict(self.payload or ())
        ret["message"] = self.message

        return ret


class InternalServerError(Exception):
    status_code = 500
    message = "Internal Server Error"

    def __init__(self, message=None, status_code=None, payload=None):
        if message is not None:
            self.message = message
        if status_code is not None:
            self.status_code = status_code

        self.payload = payload

    def to_dict(self):
        ret = dict(self.payload or ())
        ret["message"] = self.message

        return ret


class UnauthorizedError(Exception):
    status_code = 401
    message = "Not Authorized"

    def __init__(self, message=None, status_code=None, payload=None):
        Exception.__init__(self)
        if message is not None:
            self.message = message
        if status_code is not None:
            self.status_code = status_code

        self.payload = payload

    def to_dict(self):
        ret = dict(self.payload or ())
        ret["message"] = self.message

        return ret


class ForbiddenError(Exception):
    status_code = 403
    message = "Permission Denied"

    def __init__(self, message=None, status_code=None, payload=None):
        Exception.__init__(self)
        if message is not None:
            self.message = message
        if status_code is not None:
            self.status_code = status_code

        self.payload = payload

    def to_dict(self):
        ret = dict(self.payload or ())
        ret["message"] = self.message

        return ret


class TaskNotFoundError(Exception):
    status_code: int = 404
    message: str = "Task not found"

    def __init__(self, task_id: int, status_code: int = 404, payload=None):
        Exception.__init__(self)
        self.message = f"Task with ID {task_id} not found"
        self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        ret = dict(self.payload or ())
        ret["message"] = self.message

        return ret


class ComputeTaskTimeout(DiamondResponseError):
    """Globus Compute task did not finish within the request's deadline"""

    code = "COMPUTE_TASK_TIMEOUT"
    http_status_code = HTTPStatus.GATEWAY_TIMEOUT

    def __init__(self, task_id: str, endpoint_id: str, timeout_s: float) -> None:
        self.error_args = [task_id, endpoint_id]
        self.reason = (
            f"Endpoint did not return a result within {timeout_s:.0f} seconds. "
            "It may be starting up; try again shortly."
        )


class ComputeTaskFailed(DiamondResponseError):
    """Globus Compute task failed remotely or its result could not be fetched"""

    code = "COMPUTE_TASK_FAILED"
    http_status_code = HTTPStatus.BAD_GATEWAY

    def __init__(self, task_id: str, endpoint_id: str, exc: Exception) -> None:
        self.error_args = [task_id, endpoint_id, type(exc).__name__]
        self.reason = (
            "Endpoint task failed or its result could not be retrieved "
            f"({type(exc).__name__})."
        )
