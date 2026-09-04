"""Safe Deep Merge & Prototype Pollution Defense.
Resolves Issue #305: Server-Side Prototype Pollution to RCE ($200).
"""

import json
from typing import Any, Dict, List, Set, Union


FORBIDDEN_KEYS: Set[str] = {"__proto__", "constructor", "prototype"}


class PrototypePollutionError(ValueError):
    """Raised when an illegal prototype pollution key is encountered."""
    pass


def sanitize_keys(obj: Any) -> Any:
    """Recursively sanitize an object, rejecting any banned prototype keys.

    Args:
        obj: The parsed data structure (dict, list, or primitive).

    Returns:
        The validated and sanitized data structure.

    Raises:
        PrototypePollutionError: If '__proto__', 'constructor', or 'prototype' is found.
    """
    if isinstance(obj, dict):
        clean_dict: Dict[str, Any] = {}
        for k, v in obj.items():
            if not isinstance(k, str):
                str_k = str(k)
            else:
                str_k = k

            if str_k in FORBIDDEN_KEYS or str_k.strip() in FORBIDDEN_KEYS:
                raise PrototypePollutionError(
                    f"Illegal key '{str_k}' detected: prototype pollution vector prohibited."
                )

            clean_dict[k] = sanitize_keys(v)
        return clean_dict

    elif isinstance(obj, list):
        return [sanitize_keys(item) for item in obj]

    return obj


def safe_json_loads(raw_json: Union[str, bytes]) -> Any:
    """Parse JSON string and validate against prototype pollution payloads.

    Args:
        raw_json: Raw JSON string or bytes.

    Returns:
        The sanitized parsed Python structure.
    """
    data = json.loads(raw_json)
    return sanitize_keys(data)


def safe_merge(target: Dict[str, Any], source: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively deep-merge source dictionary into target dictionary safely.
    Guarantees that target cannot be mutated via __proto__, constructor, or prototype.

    Args:
        target: Target dictionary.
        source: Source dictionary to merge into target.

    Returns:
        The mutated target dictionary.

    Raises:
        PrototypePollutionError: If any forbidden key is detected in source.
    """
    if not isinstance(target, dict) or not isinstance(source, dict):
        raise TypeError("Both target and source must be dictionaries")

    for key, value in source.items():
        if key in FORBIDDEN_KEYS or str(key).strip() in FORBIDDEN_KEYS:
            raise PrototypePollutionError(
                f"Prototype pollution attempt blocked for key: {key}"
            )

        if isinstance(value, dict):
            # If target does not have this key or it's not a dict, initialize a clean dict
            target_node = target.get(key)
            if not isinstance(target_node, dict):
                target[key] = {}
            safe_merge(target[key], value)
        elif isinstance(value, list):
            # Sanitize items in list before assigning or merging
            target[key] = [sanitize_keys(item) for item in value]
        else:
            target[key] = value

    return target
