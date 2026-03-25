class AppError(Exception):
    def __init__(self, message: str, *, status_code: int = 400, success: bool | None = False, field: str = "message"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.success = success
        self.field = field
