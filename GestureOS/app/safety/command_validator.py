"""Security and privileged command validator safeguarding against shell injection and unauthorized executions."""

from __future__ import annotations
import re
from typing import Tuple

# Blacklisted dangerous shell tokens
DANGEROUS_PATTERNS = [
    r"[|;&`$><]",
    r"\brmdir\b",
    r"\bdel\b",
    r"\bformat\b",
    r"\bpowershell\b.*-enc",
    r"\bcmd\b.*/c",
    r"\bcurl\b",
    r"\bwget\b",
    r"\breg\b.*delete",
    r"\bshutdown\b",
]

ALLOWED_COMMAND_WHITELIST = {
    "calc": "calc.exe",
    "notepad": "notepad.exe",
    "explorer": "explorer.exe",
}


class CommandValidator:
    """Validates user-defined custom commands to prevent arbitrary code execution or shell escapes."""

    @staticmethod
    def is_command_safe(command: str) -> Tuple[bool, str]:
        cmd = command.strip()
        if not cmd:
            return (False, "Command cannot be empty")

        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, cmd, re.IGNORECASE):
                return (False, f"Command contains forbidden security pattern: '{pattern}'")

        # Command must either be in allowed whitelist or simple path/executable name without shell args
        parts = cmd.split()
        exec_name = parts[0].lower()
        if exec_name in ALLOWED_COMMAND_WHITELIST:
            return (True, "Whitelisted safe system utility")

        # Allow basic alphanumeric application launches
        if re.match(r"^[a-zA-Z0-9_\-\.\:\\]+$", exec_name):
            return (True, "Safe executable path")

        return (False, "Command format is not permitted")
