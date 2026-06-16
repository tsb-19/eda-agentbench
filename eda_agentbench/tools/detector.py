"""Best-effort EDA tool environment detector."""

from __future__ import annotations

import os
from pathlib import Path

from eda_agentbench.types import DetectedTool


def _tool_root(probe_root: str) -> str:
    """Resolve a probe's filesystem root, honoring the EDA_TOOL_ROOT override.

    Probes are written against the conventional ``/EDA`` mount. If a site installs
    the tools under a different prefix, set ``EDA_TOOL_ROOT`` to that prefix and it
    replaces the leading ``/EDA`` (e.g. EDA_TOOL_ROOT=/opt/eda -> /opt/eda/soft2/...).
    """
    override = os.environ.get("EDA_TOOL_ROOT")
    if override and probe_root.startswith("/EDA"):
        return override.rstrip("/") + probe_root[len("/EDA"):]
    return probe_root

# Probe definitions with explicit tool_home paths.
# tool_home = the directory that should be set as *_HOME env var.
_PROBES: list[dict] = [
    {"name": "vcs",       "vendor": "synopsys", "root": "/EDA/soft2/synopsys/vcs",       "binary_glob": "*/amd64/bin/vcs",      "env_var": "VCS_HOME",       "version_pattern": r"[A-Z]-\d{4}\.\d{2}(-SP\d+)?"},
    {"name": "xcelium",   "vendor": "cadence",  "root": "/EDA/soft2/cadence/XCELIUM209", "binary_glob": "*/bin/xrun",           "env_var": "VRST_HOME",      "version_pattern": r"XCELIUM\d+"},
    {"name": "hspice",    "vendor": "synopsys", "root": "/EDA/soft2/synopsys/hspice",     "binary_glob": "*/hspice/bin/hspice",  "env_var": "HSPICE_HOME",    "version_pattern": r"[A-Z]-\d{4}\.\d{2}(-SP\d+)?"},
    {"name": "spectre",   "vendor": "cadence",  "root": "/EDA/soft2/cadence/SPECTRE21.10.582", "binary_glob": "*/bin/spectre", "env_var": "SPECTRE_HOME",   "version_pattern": r"SPECTRE[\d.]+"},
    {"name": "dc",        "vendor": "synopsys", "root": "/EDA/soft2/synopsys/syn",        "binary_glob": "*/bin/dc_shell",       "env_var": "SYN_HOME",       "version_pattern": r"[A-Z]-\d{4}\.\d{2}(-SP\d+)?"},
    {"name": "pt",        "vendor": "synopsys", "root": "/EDA/soft2/synopsys/prime",      "binary_glob": "*/bin/pt_shell",       "env_var": "PT_HOME",        "version_pattern": r"[A-Z]-\d{4}\.\d{2}(-SP\d+)?"},
    {"name": "spyglass",  "vendor": "synopsys", "root": "/EDA/soft2/synopsys/spyglass",   "binary_glob": "*/SPYGLASS_HOME/bin/spyglass", "env_var": "SG_HOME", "version_pattern": r"[A-Z]-\d{4}\.\d{2}(-SP\d+)?"},
    {"name": "icc2",      "vendor": "synopsys", "root": "/EDA/soft2/synopsys/icc2",       "binary_glob": "*/bin/icc2_shell",     "env_var": "ICC2_HOME",      "version_pattern": r"[A-Z]-\d{4}\.\d{2}(-SP\d+)?"},
    {"name": "innovus",   "vendor": "cadence",  "root": "/EDA/soft2/cadence/INNOVUS211",  "binary_glob": "*/bin/innovus",        "env_var": "CDS_HOME",       "version_pattern": r"INNOVUS\d+"},
    {"name": "starrc",    "vendor": "synopsys", "root": "/EDA/soft2/synopsys/starrc",     "binary_glob": "*/bin/StarXtract",     "env_var": "STARRC_HOME",    "version_pattern": r"[A-Z]-\d{4}\.\d{2}(-SP\d+)?"},
    {"name": "sentaurus", "vendor": "synopsys", "root": "/EDA/soft2/synopsys/sentaurus2/sentaurus", "binary_glob": "*/bin/sprocess", "env_var": "SENTAURUS_HOME", "version_pattern": r"O_\d{4}\.\d{2}(-SP\d+)?"},
    {"name": "verdi",     "vendor": "synopsys", "root": "/EDA/soft2/synopsys/verdi",      "binary_glob": "*/bin/verdi",          "env_var": "VERDI_HOME",     "version_pattern": r"[A-Z]-\d{4}\.\d{2}(-SP\d+)?"},
]

# tool_home relative to the glob match's version directory.
# For tools where the binary is at <root>/<version>/bin/<binary>, tool_home = <root>/<version>.
# For VCS: binary at <root>/<version>/amd64/bin/vcs, tool_home = <root>/<version>.
# For HSPICE: binary at <root>/<version>/hspice/bin/hspice, tool_home = <root>/<version>.
# For SpyGlass: binary at <root>/<version>/SPYGLASS_HOME/bin/spyglass, tool_home = <root>/<version>/SPYGLASS_HOME.
# Strategy: find the version directory by looking for the version pattern in the path.
_TOOL_HOME_OVERRIDES = {
    "spyglass": "SPYGLASS_HOME",  # SpyGlass uses SPYGLASS_HOME as the home
}


class ToolEnvironmentDetector:
    """Discovers installed EDA tools by probing the filesystem (best-effort)."""

    def detect_all(self) -> list[DetectedTool]:
        results = []
        for probe in _PROBES:
            tool = self._probe_one(probe)
            if tool:
                results.append(tool)
        return results

    def detect_one(self, tool_name: str) -> DetectedTool | None:
        for probe in _PROBES:
            if probe["name"] == tool_name:
                return self._probe_one(probe)
        return None

    def get_available_tools(self) -> dict[str, DetectedTool]:
        return {t.name: t for t in self.detect_all() if t.available}

    def _probe_one(self, probe: dict) -> DetectedTool | None:
        import glob
        import re

        root = Path(_tool_root(probe["root"]))
        if not root.is_dir():
            return DetectedTool(
                name=probe["name"], vendor=probe["vendor"], version="unknown",
                binary_path=Path("/nonexistent"), tool_home=Path("/nonexistent"),
                env_var=probe["env_var"], available=False,
            )

        pattern = str(root / probe["binary_glob"])
        matches = glob.glob(pattern)

        if not matches:
            return DetectedTool(
                name=probe["name"], vendor=probe["vendor"], version="unknown",
                binary_path=Path("/nonexistent"), tool_home=Path("/nonexistent"),
                env_var=probe["env_var"], available=False,
            )

        binary_path = Path(matches[0])
        available = os.access(binary_path, os.X_OK)

        # Extract version from path
        version = "unknown"
        m = re.search(probe["version_pattern"], str(binary_path))
        if m:
            version = m.group()

        # Compute tool_home: walk up from binary to find the version directory
        tool_home = self._find_tool_home(binary_path, probe, version)

        return DetectedTool(
            name=probe["name"],
            vendor=probe["vendor"],
            version=version,
            binary_path=binary_path,
            tool_home=tool_home,
            env_var=probe["env_var"],
            available=available,
        )

    def _find_tool_home(self, binary_path: Path, probe: dict, version: str) -> Path:
        """Find the tool home directory by walking up from the binary path."""
        # Special case: SpyGlass home is inside SPYGLASS_HOME
        if probe["name"] in _TOOL_HOME_OVERRIDES:
            override = _TOOL_HOME_OVERRIDES[probe["name"]]
            for ancestor in binary_path.parents:
                if ancestor.name == override:
                    return ancestor

        # General case: find the version directory
        # Walk up from binary until we find a directory whose name matches the version pattern
        import re
        version_re = re.compile(probe["version_pattern"])
        for ancestor in binary_path.parents:
            if version_re.fullmatch(ancestor.name):
                return ancestor
            # Also check if this is the root (for tools like XCELIUM209 where root IS the version)
            if ancestor == Path(_tool_root(probe["root"])):
                return ancestor

        # Fallback: root directory
        return Path(_tool_root(probe["root"]))
