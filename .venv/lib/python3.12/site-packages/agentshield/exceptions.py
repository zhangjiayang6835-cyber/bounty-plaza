"""
AgentShield Exception Classes

Custom exceptions for security events, API errors, and policy violations.
"""


class AgentShieldException(Exception):
    """Base exception for all AgentShield errors."""
    pass


class SecurityException(AgentShieldException):
    """
    Raised when a tool call is blocked by a security policy.

    Attributes:
        message (str): Human-readable error message
        policy_matched (str): Name of the policy that blocked the call
        call_id (str): Unique ID of the blocked agent call
        status (str): Status from policy evaluation (BLOCKED)
    """

    def __init__(
        self,
        message: str,
        policy_matched: str = None,
        call_id: str = None,
        status: str = "BLOCKED"
    ):
        super().__init__(message)
        self.message = message
        self.policy_matched = policy_matched
        self.call_id = call_id
        self.status = status

    def __str__(self) -> str:
        parts = [self.message]
        if self.policy_matched:
            parts.append(f"Policy: {self.policy_matched}")
        if self.call_id:
            parts.append(f"Call ID: {self.call_id}")
        return " | ".join(parts)


class APIKeyError(AgentShieldException):
    """
    Raised when the API key is invalid, missing, or revoked.
    """

    def __init__(self, message: str = "Invalid or revoked shield_key"):
        super().__init__(message)
        self.message = message


class NetworkError(AgentShieldException):
    """
    Raised when network communication with AgentShield API fails.
    """

    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message)
        self.message = message
        self.original_error = original_error


class PolicyEvaluationError(AgentShieldException):
    """
    Raised when policy evaluation fails on the server side.
    """

    def __init__(self, message: str, details: str = None):
        super().__init__(message)
        self.message = message
        self.details = details


class ConfigurationError(AgentShieldException):
    """
    Raised when SDK is misconfigured.
    """

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message
