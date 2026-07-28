import shlex
import subprocess

def safe_execute_command(base_cmd: str, user_arg: str):
    """Executes system commands safely without shell injection vulnerability (Issue #291)."""
    # Reject dangerous shell metacharacters
    dangerous_chars = [';', '&&', '||', '|', '`', '$', '>', '<']
    if any(char in user_arg for char in dangerous_chars):
        raise ValueError("Invalid characters detected in command argument.")

    safe_args = [base_cmd] + shlex.split(user_arg)
    result = subprocess.run(safe_args, capture_output=True, text=True, check=True)
    return result.stdout
