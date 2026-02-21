"""Custom exceptions for Oiduna client"""


class OidunaError(Exception):
    """Base exception for all Oiduna client errors"""
    pass


class OidunaAPIError(OidunaError):
    """API communication error"""
    pass


class ValidationError(OidunaError):
    """Pattern or data validation error"""
    pass


class TimeoutError(OidunaError):
    """Request timeout error"""
    pass
