"""
AgentShield API Client

HTTP client for communicating with AgentShield Cloud Functions.
Handles API requests, retries, and error handling.
"""

import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .exceptions import (
    APIKeyError,
    NetworkError,
    PolicyEvaluationError,
    ConfigurationError,
)

logger = logging.getLogger(__name__)


class AgentShieldClient:
    """
    HTTP client for AgentShield API.

    Handles communication with the logAgentCall Cloud Function,
    including retries, timeouts, and error handling.
    """

    DEFAULT_API_URL = "https://us-central1-studio-1851270853-1a64c.cloudfunctions.net/logAgentCall"
    DEFAULT_TIMEOUT = 30  # seconds
    MAX_RETRIES = 3

    def __init__(
        self,
        shield_key: str,
        agent_id: str,
        api_url: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
        debug: bool = False,
    ):
        """
        Initialize AgentShield API client.

        Args:
            shield_key: Your AgentShield API key (starts with 'agsh_')
            agent_id: Unique identifier for your agent
            api_url: Optional custom API endpoint URL
            timeout: Request timeout in seconds (default: 30)
            debug: Enable debug logging (default: False)

        Raises:
            ConfigurationError: If shield_key or agent_id is invalid
        """
        if not shield_key or not isinstance(shield_key, str):
            raise ConfigurationError("shield_key must be a non-empty string")

        if not agent_id or not isinstance(agent_id, str):
            raise ConfigurationError("agent_id must be a non-empty string")

        self.shield_key = shield_key
        self.agent_id = agent_id
        self.api_url = api_url or self.DEFAULT_API_URL
        self.timeout = timeout
        self.debug = debug

        # Configure logging
        if debug:
            logging.basicConfig(level=logging.DEBUG)
            logger.setLevel(logging.DEBUG)

        # Create session with retry logic
        self.session = self._create_session()

        logger.debug(
            f"AgentShieldClient initialized: agent_id={agent_id}, api_url={self.api_url}"
        )

    def _create_session(self) -> requests.Session:
        """
        Create requests session with retry configuration.

        Returns:
            Configured requests.Session object
        """
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=self.MAX_RETRIES,
            backoff_factor=1,  # Exponential backoff: 1s, 2s, 4s
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        return session

    def log_agent_call(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        execution_time_ms: Optional[int] = None,
        timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Log an agent call to AgentShield for policy evaluation.

        Args:
            tool_name: Name of the tool/function being called
            tool_args: Arguments passed to the tool (must be JSON-serializable)
            execution_time_ms: Optional execution time in milliseconds
            timestamp: Optional ISO timestamp (defaults to current time)

        Returns:
            dict: Response from API with keys:
                - success (bool): Whether the call succeeded
                - status (str): Policy decision (ALLOWED/BLOCKED/FLAGGED/PENDING_APPROVAL)
                - message (str): Human-readable message
                - call_id (str): Unique call identifier
                - policy_matched (str): Name of matched policy (if any)
                - anomaly_score (float): Anomaly score (0-100)

        Raises:
            APIKeyError: If shield_key is invalid or revoked
            NetworkError: If network request fails
            PolicyEvaluationError: If server-side policy evaluation fails
        """
        # Build request payload for Cloud Functions v2 format
        # Wrap the data in a 'data' field
        payload_data = {
            "shield_key": self.shield_key,
            "agent_id": self.agent_id,
            "tool_name": tool_name,
            "tool_args": tool_args,
        }

        if execution_time_ms is not None:
            payload_data["execution_time_ms"] = execution_time_ms

        if timestamp:
            payload_data["timestamp"] = timestamp
        else:
            payload_data["timestamp"] = datetime.utcnow().isoformat() + "Z"

        # Wrap in 'data' field for Cloud Functions v2
        payload = {"data": payload_data}

        logger.debug(f"Logging agent call: tool={tool_name}, agent={self.agent_id}")

        try:
            # Make API request
            response = self.session.post(
                self.api_url,
                json=payload,
                timeout=self.timeout,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": f"agentshield-python-sdk/0.1.0",
                },
            )

            # Handle HTTP errors
            if response.status_code == 403:
                response_data = response.json() if response.text else {}
                # Check if error is wrapped in 'error' field (Cloud Functions v2)
                error_data = response_data.get("error", response_data)
                error_message = error_data.get("message", "Invalid or revoked shield_key")
                logger.error(f"API key error: {error_message}")
                raise APIKeyError(error_message)

            if response.status_code >= 400:
                response_data = response.json() if response.text else {}
                # Check if error is wrapped in 'error' field (Cloud Functions v2)
                error_data = response_data.get("error", response_data)
                error_message = error_data.get("message", f"HTTP {response.status_code}")
                logger.error(f"API error: {error_message}")
                raise PolicyEvaluationError(
                    f"Policy evaluation failed: {error_message}",
                    details=str(error_data)
                )

            # Parse response - Cloud Functions v2 wraps response in 'result' field
            response_data = response.json()
            result = response_data.get("result", response_data)

            logger.debug(
                f"Agent call logged: status={result.get('status')}, "
                f"call_id={result.get('call_id')}"
            )

            return result

        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout after {self.timeout}s")
            raise NetworkError(
                f"Request to AgentShield API timed out after {self.timeout}s",
                original_error=e
            )

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {str(e)}")
            raise NetworkError(
                "Failed to connect to AgentShield API. Check your network connection.",
                original_error=e
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            raise NetworkError(
                f"Network error while calling AgentShield API: {str(e)}",
                original_error=e
            )

        except ValueError as e:
            # JSON decode error
            logger.error(f"Invalid JSON response: {str(e)}")
            raise PolicyEvaluationError(
                "Received invalid response from AgentShield API",
                details=str(e)
            )

    def log_call(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        execution_time_ms: Optional[int] = None,
        timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Alias for log_agent_call().

        This method provides a cleaner API name for logging agent calls.
        All parameters and behavior are identical to log_agent_call().
        """
        return self.log_agent_call(
            tool_name=tool_name,
            tool_args=tool_args,
            execution_time_ms=execution_time_ms,
            timestamp=timestamp,
        )

    def close(self):
        """Close the HTTP session."""
        if self.session:
            self.session.close()
            logger.debug("AgentShieldClient session closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
