"""Excepciones controladas de la Capa de Negocio de E.V.A."""


class DomainError(Exception):
    """Error de validación o regla de negocio con código HTTP semántico."""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        code: str = "DOMAIN_ERROR",
        payload: dict = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.payload = payload or {}

    def to_dict(self) -> dict:
        data = {
            "ok": False,
            "error": self.message,
            "code": self.code,
        }
        if self.payload:
            data["details"] = self.payload
        return data
