"""Parser for normalized PrimeTime/OpenSTA-style timing reports.

Extracts structured data from text-format timing reports for P3 QA tasks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class TimingPath:
    """A single timing path entry."""
    path_index: int
    startpoint: str
    endpoint: str
    path_group: str
    clock: str
    slack: float
    arrival_time: float
    required_time: float
    data_type: str = "setup"  # setup or hold


@dataclass
class TimingReport:
    """Parsed timing report data."""
    paths: list[TimingPath] = field(default_factory=list)
    wns: float | None = None
    tns: float | None = None
    violating_count: int = 0

    def get_wns(self) -> float | None:
        """Get Worst Negative Slack."""
        if self.wns is not None:
            return self.wns
        if not self.paths:
            return None
        return min(p.slack for p in self.paths)

    def get_tns(self) -> float | None:
        """Get Total Negative Slack."""
        if self.tns is not None:
            return self.tns
        if not self.paths:
            return None
        return sum(p.slack for p in self.paths if p.slack < 0)

    def get_violating_count(self) -> int:
        """Get number of violating paths (slack < 0)."""
        if self.violating_count > 0:
            return self.violating_count
        return sum(1 for p in self.paths if p.slack < 0)

    def get_worst_path(self) -> TimingPath | None:
        """Get path with worst (minimum) slack."""
        if not self.paths:
            return None
        return min(self.paths, key=lambda p: p.slack)

    def get_path_by_endpoint(self, endpoint: str) -> TimingPath | None:
        """Get path by endpoint name (case-insensitive)."""
        endpoint_lower = endpoint.lower()
        for p in self.paths:
            if p.endpoint.lower() == endpoint_lower:
                return p
        return None

    def get_path_by_index(self, index: int) -> TimingPath | None:
        """Get path by 1-based index."""
        for p in self.paths:
            if p.path_index == index:
                return p
        return None


def parse_timing_report(text: str) -> TimingReport:
    """Parse a normalized timing report text.

    Supports report formats like:
        **** Report : timing
            -path_type full
            -delay_type max
            -max_paths 100

        Startpoint: reg_a (rising edge-triggered flip-flop clocked by clk)
        Endpoint: reg_b (rising edge-triggered flip-flop clocked by clk)
        Path Group: clk
        -----------------------------------
        Startpoint: reg_a
        Endpoint: reg_b
        Path Group: clk
        -----------------------------------
        Slack:                    -0.15
        Arrival Time:              2.35
        Required Time:             2.20

    Also supports summary lines:
        wns: -0.15
        tns: -0.45
        violating_path_count: 3
    """
    report = TimingReport()
    lines = text.splitlines()

    # Parse summary values (WNS, TNS, violating count)
    for line in lines:
        stripped = line.strip().lower()
        m = re.match(r"(?:\*\*\s*)?wns\s*[:=]\s*([-\d.eE+]+)", stripped)
        if m:
            report.wns = _parse_float(m.group(1))
            continue
        m = re.match(r"(?:\*\*\s*)?tns\s*[:=]\s*([-\d.eE+]+)", stripped)
        if m:
            report.tns = _parse_float(m.group(1))
            continue
        m = re.match(r"(?:\*\*\s*)?violating_path_count\s*[:=]\s*(\d+)", stripped)
        if m:
            report.violating_count = int(m.group(1))
            continue

    # Parse individual paths using a state machine
    i = 0
    path_index = 0
    while i < len(lines):
        line = lines[i].strip()

        # Look for path headers: "Startpoint: xxx"
        sp_match = re.match(r"Startpoint:\s*(\S+)", line, re.IGNORECASE)
        if sp_match:
            startpoint = sp_match.group(1)

            # Collect path data until next separator or Startpoint
            endpoint = ""
            path_group = ""
            clock = ""
            slack = None
            arrival = None
            required = None
            data_type = "setup"

            j = i + 1
            while j < len(lines):
                pline = lines[j].strip()

                # Endpoint
                ep_match = re.match(r"Endpoint:\s*(\S+)", pline, re.IGNORECASE)
                if ep_match:
                    endpoint = ep_match.group(1)

                # Path Group
                pg_match = re.match(r"Path Group:\s*(.+)", pline, re.IGNORECASE)
                if pg_match:
                    path_group = pg_match.group(1).strip()

                # Clock (from startpoint/endpoint lines or explicit clock line)
                clk_match = re.match(r"Clock:\s*(\S+)", pline, re.IGNORECASE)
                if clk_match:
                    clock = clk_match.group(1)

                # Also extract clock from Startpoint/Endpoint lines
                sp_clk = re.search(r"clocked by (\S+)", pline, re.IGNORECASE)
                if sp_clk and not clock:
                    clock = sp_clk.group(1)

                # Slack
                sl_match = re.match(r"Slack:\s*([-\d.eE+]+)", pline, re.IGNORECASE)
                if sl_match:
                    slack = _parse_float(sl_match.group(1))

                # Arrival Time
                at_match = re.match(r"Arrival Time:\s*([-\d.eE+]+)", pline, re.IGNORECASE)
                if at_match:
                    arrival = _parse_float(at_match.group(1))

                # Required Time
                rt_match = re.match(r"Required Time:\s*([-\d.eE+]+)", pline, re.IGNORECASE)
                if rt_match:
                    required = _parse_float(rt_match.group(1))

                # Data Type (setup/hold)
                dt_match = re.match(r"Data Type:\s*(setup|hold)", pline, re.IGNORECASE)
                if dt_match:
                    data_type = dt_match.group(1).lower()

                # Break at separator or next Startpoint
                if j > i + 1 and re.match(r"Startpoint:", pline, re.IGNORECASE):
                    break
                if pline.startswith("---") and slack is not None:
                    # End of path block after we've collected data
                    break

                j += 1

            # Only create path if we have minimum required fields
            if endpoint and slack is not None:
                path_index += 1
                path = TimingPath(
                    path_index=path_index,
                    startpoint=startpoint,
                    endpoint=endpoint,
                    path_group=path_group,
                    clock=clock,
                    slack=slack,
                    arrival_time=arrival if arrival is not None else 0.0,
                    required_time=required if required is not None else 0.0,
                    data_type=data_type,
                )
                report.paths.append(path)

            i = j
            continue

        i += 1

    return report


def _parse_float(s: str) -> float:
    """Parse a string to float, handling edge cases."""
    s = s.strip()
    try:
        return float(s)
    except ValueError:
        # Try removing trailing units like 'ns', 'ps'
        s = re.sub(r"\s*(ns|ps|us|ms)\s*$", "", s, flags=re.IGNORECASE)
        try:
            return float(s)
        except ValueError:
            return 0.0


def normalize_answer(answer: str) -> str:
    """Normalize an answer string for comparison.

    Strips whitespace, lowercases, removes units, normalizes numeric format.
    """
    answer = answer.strip()
    # If it looks like a number, normalize it
    try:
        val = float(answer)
        # Format to consistent precision
        if val == int(val):
            return str(int(val))
        return f"{val:.6f}".rstrip("0").rstrip(".")
    except ValueError:
        pass
    # String normalization: lowercase, strip, collapse whitespace
    answer = answer.lower().strip()
    answer = re.sub(r"\s+", " ", answer)
    return answer
