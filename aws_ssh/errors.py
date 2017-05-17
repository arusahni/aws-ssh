"""Common errors"""

class ProjectConfigNotFoundError(Exception):
    """Raised when a project config file cannot be found in the FS hierarchy"""
    pass

class TooManyInstancesError(Exception):
    """Too many instances were returned when attempting to get just one"""
    pass

class NoInstanceFoundError(Exception):
    """No instance matching the given parameters was found"""
    pass

class UsernameNotFoundError(Exception):
    """aws_ssh was unable to guess the username"""
    pass

class SSHError(Exception):
    """Issues connecting to an instance via SSH"""
    pass

class NoConfigError(Exception):
    """No configuration is present"""
    pass
