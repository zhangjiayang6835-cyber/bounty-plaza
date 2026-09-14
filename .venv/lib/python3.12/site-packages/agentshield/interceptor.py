"""
AgentShield Tool Interceptor

Wraps agent tools to intercept calls, enforce security policies,
and log activity to AgentShield.
"""

import time
import logging
import functools
from typing import Any, Callable, Optional, Dict

from .client import AgentShieldClient
from .exceptions import SecurityException, ConfigurationError

logger = logging.getLogger(__name__)


class SecureAgent:
    """
    Wraps an AI agent to add security monitoring and policy enforcement.

    SecureAgent intercepts tool/function calls, sends them to AgentShield
    for evaluation, and enforces policy decisions (BLOCK/ALLOW/FLAG).

    Works transparently with any agent framework (LangChain, OpenAI, custom).
    """

    def __init__(
        self,
        agent: Any,
        shield_key: str,
        agent_id: str,
        api_url: Optional[str] = None,
        timeout: int = 30,
        debug: bool = False,
        fail_open: bool = False,
    ):
        """
        Initialize SecureAgent wrapper.

        Args:
            agent: The agent to wrap (LangChain agent, OpenAI assistant, etc.)
            shield_key: Your AgentShield API key (starts with 'agsh_')
            agent_id: Unique identifier for this agent
            api_url: Optional custom API endpoint
            timeout: API request timeout in seconds (default: 30)
            debug: Enable debug logging (default: False)
            fail_open: If True, allow calls when API is unavailable (default: False)

        Raises:
            ConfigurationError: If configuration is invalid
        """
        if not shield_key:
            raise ConfigurationError("shield_key is required")

        if not agent_id:
            raise ConfigurationError("agent_id is required")

        self.agent = agent
        self.shield_key = shield_key
        self.agent_id = agent_id
        self.fail_open = fail_open
        self.debug = debug

        # Initialize API client
        self.client = AgentShieldClient(
            shield_key=shield_key,
            agent_id=agent_id,
            api_url=api_url,
            timeout=timeout,
            debug=debug,
        )

        # Wrap agent tools
        self._wrap_agent_tools()

        logger.info(f"SecureAgent initialized: agent_id={agent_id}")

    def _wrap_agent_tools(self):
        """
        Detect and wrap agent tools based on agent type.

        This method attempts multiple wrapping strategies to ensure
        tool calls are intercepted regardless of agent framework.
        """
        wrapped_count = 0

        # Strategy 1: Try LangChain AgentExecutor (wrap individual tools)
        if hasattr(self.agent, "tools") and self.agent.tools:
            logger.info(f"Detected LangChain agent with {len(self.agent.tools)} tools")
            self._wrap_langchain_tools()
            wrapped_count += len(self.agent.tools) if hasattr(self.agent, "tools") else 0
            logger.info(f"Wrapped {wrapped_count} LangChain tools for security interception")

        # Strategy 2: Try LangChain LCEL Runnable (wrap invoke method)
        # Only wrap invoke if we didn't already wrap individual tools
        elif hasattr(self.agent, "invoke"):
            logger.info("Detected agent with invoke() method")

            # Check if this is an agent with bindable tools
            if hasattr(self.agent, "bind_tools"):
                logger.warning(
                    "Agent has bind_tools() method. Tools may need to be wrapped "
                    "after binding. Consider using wrap_function() manually."
                )

            # Wrap the invoke method as a fallback
            self._wrap_lcel_invoke()
            wrapped_count += 1
            logger.info("Wrapped agent invoke() method for security interception")

        # Strategy 3: OpenAI Assistant
        elif hasattr(self.agent, "create") or hasattr(self.agent, "run"):
            logger.info("Detected OpenAI-style agent")
            logger.warning(
                "OpenAI assistants require manual wrapping. Use wrap_function() "
                "to wrap your tool functions before passing them to the assistant."
            )

        else:
            logger.warning(
                "Could not auto-detect agent type. Manual tool wrapping required.\n"
                "Use secure_agent.wrap_function(your_tool) to wrap tools manually."
            )

        if wrapped_count == 0:
            logger.warning(
                "No tools were automatically wrapped! Security policies may not be enforced.\n"
                "Please use wrap_function() to manually wrap your tools."
            )

    def _wrap_langchain_tools(self):
        """
        Wrap LangChain tools by intercepting their execution methods.

        Wraps both sync (_run) and async (_arun) methods to ensure
        all tool calls are checked against security policies.
        """
        if not hasattr(self.agent, "tools") or not self.agent.tools:
            logger.warning("Agent has no tools to wrap")
            return

        original_tools = self.agent.tools
        wrapped_tools = []
        wrapped_sync_count = 0
        wrapped_async_count = 0

        for tool in original_tools:
            tool_name = getattr(tool, "name", tool.__class__.__name__)
            logger.debug(f"Wrapping tool: {tool_name}")

            # Wrap synchronous _run method
            if hasattr(tool, "_run") and callable(tool._run):
                original_run = tool._run
                tool._run = self._create_wrapped_sync_function(
                    original_run,
                    tool_name=tool_name
                )
                wrapped_sync_count += 1
                logger.debug(f"  ✓ Wrapped _run() for {tool_name}")
            else:
                logger.debug(f"  ⊘ No _run() method for {tool_name}")

            # Wrap asynchronous _arun method
            if hasattr(tool, "_arun") and callable(tool._arun):
                original_arun = tool._arun
                tool._arun = self._create_wrapped_async_function(
                    original_arun,
                    tool_name=tool_name
                )
                wrapped_async_count += 1
                logger.debug(f"  ✓ Wrapped _arun() for {tool_name}")
            else:
                logger.debug(f"  ⊘ No _arun() method for {tool_name}")

            wrapped_tools.append(tool)

        self.agent.tools = wrapped_tools
        logger.info(
            f"Successfully wrapped {len(wrapped_tools)} tools "
            f"({wrapped_sync_count} sync, {wrapped_async_count} async methods)"
        )

    def _wrap_lcel_invoke(self):
        """Wrap LangChain LCEL runnable invoke method."""
        if hasattr(self.agent, "invoke"):
            original_invoke = self.agent.invoke
            self.agent.invoke = self._create_wrapped_sync_function(
                original_invoke,
                tool_name="invoke"
            )
            logger.debug("Wrapped LCEL invoke method")

    def _create_wrapped_sync_function(
        self,
        func: Callable,
        tool_name: str
    ) -> Callable:
        """
        Create a wrapped version of a synchronous function.

        Args:
            func: Original function to wrap
            tool_name: Name of the tool for logging

        Returns:
            Wrapped function that enforces AgentShield policies
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Extract arguments for logging
            tool_args = self._extract_args(args, kwargs)

            # Extract real tool name if this is an invoke() wrapper
            actual_tool_name = tool_name
            actual_tool_args = tool_args

            if tool_name == "invoke" and args and len(args) > 0:
                input_dict = args[0]
                if isinstance(input_dict, dict):
                    # Extract real tool name if present
                    if 'tool' in input_dict:
                        actual_tool_name = input_dict['tool']

                    # Extract tool args if present
                    if 'args' in input_dict:
                        actual_tool_args = self._serialize_value(input_dict['args'])

            # STEP 1: Call AgentShield API BEFORE executing tool
            start_time = time.time()

            try:
                # Call AgentShield for policy evaluation
                response = self.client.log_call(
                    tool_name=actual_tool_name,
                    tool_args=actual_tool_args,
                )

                # STEP 2: Extract status (fail closed if missing)
                status = response.get("status")
                if not status:
                    logger.error(f"No status in API response for {actual_tool_name}")
                    raise SecurityException(
                        message=f"Policy check failed: no status returned for '{actual_tool_name}'",
                        policy_matched=None,
                        call_id=response.get("call_id"),
                        status="ERROR",
                    )

                call_id = response.get("call_id")
                policy_matched = response.get("policy_matched")
                message = response.get("message", "")

                logger.debug(
                    f"Policy check: tool={actual_tool_name}, status={status}, "
                    f"call_id={call_id}"
                )

                # STEP 3: Check status and decide whether to execute

                # BLOCKED - raise exception, DO NOT execute tool
                if status == "BLOCKED":
                    logger.warning(
                        f"BLOCKED: Tool '{actual_tool_name}' blocked by policy | {message}"
                    )
                    raise SecurityException(
                        message=message or f"Tool '{actual_tool_name}' blocked by security policy",
                        policy_matched=policy_matched,
                        call_id=call_id,
                        status=status,
                    )

                # PENDING_APPROVAL - raise exception, DO NOT execute tool
                elif status == "PENDING_APPROVAL":
                    logger.info(
                        f"PENDING: Tool '{actual_tool_name}' requires approval | {message}"
                    )
                    raise SecurityException(
                        message=message or f"Tool '{actual_tool_name}' requires manual approval",
                        policy_matched=policy_matched,
                        call_id=call_id,
                        status=status,
                    )

                # FLAGGED - log warning, but ALLOW execution
                elif status == "FLAGGED":
                    logger.warning(
                        f"FLAGGED: Tool '{actual_tool_name}' flagged for review | {message}"
                    )
                    # Continue to execution

                # ALLOWED - proceed with execution
                elif status == "ALLOWED":
                    logger.debug(f"ALLOWED: Tool '{actual_tool_name}' approved for execution")
                    # Continue to execution

                # Unknown status - fail closed
                else:
                    logger.error(f"Unknown status '{status}' for {actual_tool_name}")
                    raise SecurityException(
                        message=f"Unknown policy status '{status}' for tool '{actual_tool_name}'",
                        policy_matched=policy_matched,
                        call_id=call_id,
                        status=status,
                    )

                # STEP 4: Execute the tool (only if ALLOWED or FLAGGED)
                logger.debug(f"Executing tool: {actual_tool_name}")
                result = func(*args, **kwargs)

                # Log execution time
                execution_time_ms = int((time.time() - start_time) * 1000)
                logger.debug(
                    f"Tool executed successfully: {actual_tool_name} | {execution_time_ms}ms"
                )

                return result

            except SecurityException:
                # Re-raise security exceptions immediately - do NOT execute tool
                logger.debug(f"Tool NOT executed due to security policy: {actual_tool_name}")
                raise

            except Exception as e:
                # Handle network/API errors based on fail_open setting
                logger.error(f"AgentShield API error for {actual_tool_name}: {str(e)}")

                if self.fail_open:
                    logger.warning(
                        f"Fail-open mode: executing {actual_tool_name} despite API error"
                    )
                    return func(*args, **kwargs)
                else:
                    # Fail closed - block execution
                    logger.error(f"Fail-closed mode: blocking {actual_tool_name} due to API error")
                    raise SecurityException(
                        message=f"Cannot verify security policy due to API error: {str(e)}",
                        policy_matched=None,
                        call_id=None,
                        status="ERROR",
                    )

        return wrapper

    def _create_wrapped_async_function(
        self,
        func: Callable,
        tool_name: str
    ) -> Callable:
        """
        Create a wrapped version of an async function.

        Args:
            func: Original async function to wrap
            tool_name: Name of the tool for logging

        Returns:
            Wrapped async function that enforces AgentShield policies
        """
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract arguments for logging
            tool_args = self._extract_args(args, kwargs)

            # Extract real tool name if this is an invoke() wrapper
            actual_tool_name = tool_name
            actual_tool_args = tool_args

            if tool_name == "invoke" and args and len(args) > 0:
                input_dict = args[0]
                if isinstance(input_dict, dict):
                    # Extract real tool name if present
                    if 'tool' in input_dict:
                        actual_tool_name = input_dict['tool']

                    # Extract tool args if present
                    if 'args' in input_dict:
                        actual_tool_args = self._serialize_value(input_dict['args'])

            # STEP 1: Call AgentShield API BEFORE executing tool
            start_time = time.time()

            try:
                # Call AgentShield for policy evaluation (sync call in async context)
                response = self.client.log_call(
                    tool_name=actual_tool_name,
                    tool_args=actual_tool_args,
                )

                # STEP 2: Extract status (fail closed if missing)
                status = response.get("status")
                if not status:
                    logger.error(f"No status in API response for {actual_tool_name}")
                    raise SecurityException(
                        message=f"Policy check failed: no status returned for '{actual_tool_name}'",
                        policy_matched=None,
                        call_id=response.get("call_id"),
                        status="ERROR",
                    )

                call_id = response.get("call_id")
                policy_matched = response.get("policy_matched")
                message = response.get("message", "")

                logger.debug(
                    f"Policy check (async): tool={actual_tool_name}, status={status}, "
                    f"call_id={call_id}"
                )

                # STEP 3: Check status and decide whether to execute

                # BLOCKED - raise exception, DO NOT execute tool
                if status == "BLOCKED":
                    logger.warning(
                        f"BLOCKED: Tool '{actual_tool_name}' blocked by policy | {message}"
                    )
                    raise SecurityException(
                        message=message or f"Tool '{actual_tool_name}' blocked by security policy",
                        policy_matched=policy_matched,
                        call_id=call_id,
                        status=status,
                    )

                # PENDING_APPROVAL - raise exception, DO NOT execute tool
                elif status == "PENDING_APPROVAL":
                    logger.info(
                        f"PENDING: Tool '{actual_tool_name}' requires approval | {message}"
                    )
                    raise SecurityException(
                        message=message or f"Tool '{actual_tool_name}' requires manual approval",
                        policy_matched=policy_matched,
                        call_id=call_id,
                        status=status,
                    )

                # FLAGGED - log warning, but ALLOW execution
                elif status == "FLAGGED":
                    logger.warning(
                        f"FLAGGED: Tool '{actual_tool_name}' flagged for review | {message}"
                    )
                    # Continue to execution

                # ALLOWED - proceed with execution
                elif status == "ALLOWED":
                    logger.debug(f"ALLOWED: Tool '{actual_tool_name}' approved for execution")
                    # Continue to execution

                # Unknown status - fail closed
                else:
                    logger.error(f"Unknown status '{status}' for {actual_tool_name}")
                    raise SecurityException(
                        message=f"Unknown policy status '{status}' for tool '{actual_tool_name}'",
                        policy_matched=policy_matched,
                        call_id=call_id,
                        status=status,
                    )

                # STEP 4: Execute the tool (only if ALLOWED or FLAGGED)
                logger.debug(f"Executing tool (async): {actual_tool_name}")
                result = await func(*args, **kwargs)

                # Log execution time
                execution_time_ms = int((time.time() - start_time) * 1000)
                logger.debug(
                    f"Tool executed successfully (async): {actual_tool_name} | {execution_time_ms}ms"
                )

                return result

            except SecurityException:
                # Re-raise security exceptions immediately - do NOT execute tool
                logger.debug(f"Tool NOT executed due to security policy: {actual_tool_name}")
                raise

            except Exception as e:
                # Handle network/API errors based on fail_open setting
                logger.error(f"AgentShield API error for {actual_tool_name}: {str(e)}")

                if self.fail_open:
                    logger.warning(
                        f"Fail-open mode: executing {actual_tool_name} despite API error"
                    )
                    return await func(*args, **kwargs)
                else:
                    # Fail closed - block execution
                    logger.error(f"Fail-closed mode: blocking {actual_tool_name} due to API error")
                    raise SecurityException(
                        message=f"Cannot verify security policy due to API error: {str(e)}",
                        policy_matched=None,
                        call_id=None,
                        status="ERROR",
                    )

        return wrapper

    def _extract_args(self, args: tuple, kwargs: dict) -> Dict[str, Any]:
        """
        Extract and serialize arguments for logging.

        Args:
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            Dictionary of serialized arguments
        """
        tool_args = {}

        # Add positional args
        if args:
            for i, arg in enumerate(args):
                tool_args[f"arg_{i}"] = self._serialize_value(arg)

        # Add keyword args
        if kwargs:
            for key, value in kwargs.items():
                tool_args[key] = self._serialize_value(value)

        return tool_args

    def _serialize_value(self, value: Any) -> Any:
        """
        Serialize a value for JSON transmission.

        Args:
            value: Value to serialize

        Returns:
            JSON-serializable value
        """
        # Handle common types
        if isinstance(value, (str, int, float, bool, type(None))):
            return value

        if isinstance(value, (list, tuple)):
            return [self._serialize_value(item) for item in value]

        if isinstance(value, dict):
            return {
                str(k): self._serialize_value(v)
                for k, v in value.items()
            }

        # Convert other types to string
        return str(value)

    def wrap_function(self, func: Callable, tool_name: Optional[str] = None) -> Callable:
        """
        Manually wrap a function with AgentShield security.

        Use this method to wrap custom functions or tools that weren't
        automatically detected.

        Args:
            func: Function to wrap
            tool_name: Optional name for the tool (defaults to function name)

        Returns:
            Wrapped function

        Example:
            >>> secure_agent = SecureAgent(agent, shield_key, agent_id)
            >>> secure_search = secure_agent.wrap_function(google_search, "web_search")
            >>> result = secure_search("AI security")
        """
        name = tool_name or func.__name__
        logger.debug(f"Manually wrapping function: {name}")
        return self._create_wrapped_sync_function(func, name)

    def __getattr__(self, name: str) -> Any:
        """
        Proxy attribute access to wrapped agent.

        Allows SecureAgent to be used as a drop-in replacement for the
        original agent.
        """
        return getattr(self.agent, name)

    def __del__(self):
        """Cleanup on deletion."""
        if hasattr(self, "client"):
            self.client.close()
