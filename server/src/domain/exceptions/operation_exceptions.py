class OperationError(BaseException):
    """Class utilized for errors during system operation."""

    pass


class ConfigurationError(OperationError):
    """Error class for configuration errors."""

    pass


class SetupError(OperationError):
    """Error class for errors during setup."""

    pass


class LoadError(OperationError):
    """Error class for errors during data loading."""

    pass
