"""Default sanitization rules for EDA tool logs."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class SanitizeRule:
    name: str
    pattern: re.Pattern[str]
    replacement: str


DEFAULT_RULES: list[SanitizeRule] = [
    SanitizeRule(
        name="user_home",
        pattern=re.compile(r"/home/[a-zA-Z0-9_\-]+"),
        replacement="<USER_HOME>",
    ),
    SanitizeRule(
        name="synopsys_license",
        pattern=re.compile(r"\d+@[a-zA-Z0-9_\-\.]+"),
        replacement="<LICENSE_SERVER>",
    ),
    SanitizeRule(
        name="eda_root",
        pattern=re.compile(r"/EDA/soft2/(synopsys|cadence)/[^\s:]+"),
        replacement="<EDA_ROOT>",
    ),
    SanitizeRule(
        name="ip_address",
        pattern=re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
        replacement="<IP_ADDR>",
    ),
]
