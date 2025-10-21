import typing as t
from http import HTTPStatus


class DiamondResponseError(Exception):
    code: str
    reason: str
    http_status_code: t.ClassVar[HTTPStatus]

    def __init__(self, reason: str) -> None:
        self.error_args = [reason]
        self.reason = reason

    def __str__(self):
        return self.reason

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            + ",".join(
                [
                    # Both reason and detail for backwards compatibility
                    f"reason='{self.reason}'",
                    f"code={self.code}",
                    f"http_status_code={self.http_status_code}",
                    f"error_args={self.error_args}",
                ]
            )
            + ")"
        )

    def to_dict(self) -> t.Dict[str, t.Any]:
        return {
            "reason": self.reason,
            "code": self.code,
            "http_status_code": self.http_status_code,
            "error_args": self.error_args,
        }


class EndpointNotFound(DiamondResponseError):
    """Endpoint could not be resolved from the database"""

    code = "ENDPOINT_NOT_FOUND"
    http_status_code = HTTPStatus.NOT_FOUND

    def __init__(self, reason: str, identity_id: str, endpoint_uuid: str) -> None:
        self.reason = reason
        self.error_args = [identity_id, endpoint_uuid]
        self.reason = f"Endpoint {endpoint_uuid} could not be resolved"


class RequestMalformed(DiamondResponseError):
    """User request malformed"""

    code = "REQUEST_MALFORMED"
    http_status_code = HTTPStatus.BAD_REQUEST

    def __init__(self, malformed_reason: str) -> None:
        self.error_args = [malformed_reason]
        self.reason = (
            f"Request Malformed. Missing critical information: {malformed_reason}"
        )
