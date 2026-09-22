class AppError(Exception):
    """User-friendly error. `message` frontend ko dikhta hai, technical detail sirf log mein jaati hai."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
