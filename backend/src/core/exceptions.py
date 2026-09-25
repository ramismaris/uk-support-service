class AppException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundException(AppException):
    def __init__(self, message: str = "Not found"):
        super().__init__(message, status_code=404)


class ForbiddenException(AppException):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, status_code=403)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=401)


class ConflictException(AppException):
    def __init__(self, message: str = "Conflict"):
        super().__init__(message, status_code=409)


class MessengerException(AppException):
    def __init__(self, message: str = "Не удалось связаться с Max"):
        super().__init__(message, status_code=502)
