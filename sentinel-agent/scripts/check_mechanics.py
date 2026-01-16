#!/usr/bin/env python3
"""
SENTINEL Mechanics Integrity Auditor

Validates game data consistency across regions, jobs, vehicles, and favors.
Catches bugs before they surface during deep play runs.

Usage:
    python check_mechanics.py          # Console output
    python check_mechanics.py --json   # JSON output for CI

Exit codes:
    0 - All checks passed
    1 - Warnings only
    2 - Errors found
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

# Ensure UTF-8 output on Windows (needed for piping to Kimi and other tools)
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


# ─────────────────────────────────────────────────────────────────────────────
# Data Structures
# ─────────────────────────────────────────────────────────────────────────────


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Issue:
    """A single validation issue."""

    category: str
    severity: Severity
    message: str
    file_path: str | None = None
    context: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "severity": self.severity.value,
            "message": self.message,
            "file_path": self.file_path,
            "context": self.context,
        }


@dataclass
class ValidationResult:
    """Complete validation results."""

    issues: list[Issue] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)

    @property
    def error_count(self) -> int:
        return len([i for i in self.issues if i.severity == Severity.ERROR])

    @property
    def warning_count(self) -> int:
        return len([i for i in self.issues if i.severity == Severity.WARNING])

    @property
    def info_count(self) -> int:
        return len([i for i in self.issues if i.severity == Severity.INFO])

    @property
    def is_healthy(self) -> bool:
        return self.error_count == 0

    def to_dict(self) -> dict:
        return {
            "status": "pass" if self.is_healthy else "fail",
            "stats": self.stats,
            "summary": {
                "errors": self.error_count,
                "warnings": self.warning_count,
                "info": self.info_count,
            },
            "issues": [i.to_dict() for i in self.issues],
        }


# ─────────────────────────────────────────────────────────────────────────────
# Enum Registry (parses enums from schema.py without importing)
# ─────────────────────────────────────────────────────────────────────────────


class EnumRegistry:
    """Loads enum values from schema.py for cross-validation."""

    def __init__(self, schema_path: Path):
        self.factions: set[str] = set()  # FactionName.value strings (display names)
        self.faction_ids: set[str] = set()  # Normalized IDs for regions
        self.regions: set[str] = set()  # Region.value strings (IDs)
        self.mission_types: set[str] = set()  # MissionType.value strings
        self.favor_types: set[str] = set()  # FavorType.value strings
        self.dispositions: set[str] = set()  # Disposition.value strings
        self._load(schema_path)

    def _load(self, schema_path: Path) -> None:
        """Parse enums from schema.py using regex."""
        if not schema_path.exists():
            return

        content = schema_path.read_text(encoding="utf-8")

        # Extract each enum
        self.factions = self._extract_enum_values(content, "FactionName")
        self.regions = self._extract_enum_values(content, "Region")
        self.mission_types = self._extract_enum_values(content, "MissionType")
        self.favor_types = self._extract_enum_values(content, "FavorType")
        self.dispositions = self._extract_enum_values(content, "Disposition")

        # Generate normalized faction IDs from display names
        self.faction_ids = {self._to_id(f) for f in self.factions}

    def _extract_enum_values(self, source: str, enum_name: str) -> set[str]:
        """Extract enum member values from Python source."""
        # Match: class EnumName(str, Enum): followed by member definitions
        pattern = rf"class {enum_name}\s*\([^)]*Enum[^)]*\):\s*\n((?:[ \t]+.*\n)*)"
        match = re.search(pattern, source)
        if not match:
            return set()

        body = match.group(1)
        values = set()

        # Match: MEMBER = "value" or MEMBER = 'value'
        for line in body.split("\n"):
            value_match = re.search(r'=\s*["\']([^"\']+)["\']', line)
            if value_match:
                values.add(value_match.group(1))

        return values

    @staticmethod
    def _to_id(display_name: str) -> str:
        """Convert display name to ID format."""
        return display_name.lower().replace(" ", "_").replace("-", "_")

    def is_valid_faction(self, name: str) -> bool:
        """Check if faction name is valid (either display or ID format)."""
        return name in self.factions or name in self.faction_ids

    def is_valid_faction_id(self, faction_id: str) -> bool:
        """Check if faction ID is valid."""
        return faction_id in self.faction_ids


# ─────────────────────────────────────────────────────────────────────────────
# Validators
# ─────────────────────────────────────────────────────────────────────────────


class RegionValidator:
    """Validates regions.json against schema enums."""

    def __init__(
        self, enums: EnumRegistry, regions_data: dict, regions_path: str
    ):
        self.enums = enums
        self.regions = regions_data.get("regions", {})
        self.path = regions_path

    def validate(self) -> list[Issue]:
        issues = []
        issues.extend(self._check_enum_coverage())
        issues.extend(self._check_faction_references())
        issues.extend(self._check_adjacency_bidirectional())
        issues.extend(self._check_adjacency_valid_targets())
        return issues

    def _check_enum_coverage(self) -> list[Issue]:
        """Verify all Region enum values have entries in regions.json."""
        issues = []
        region_keys = set(self.regions.keys())

        for region_id in self.enums.regions:
            if region_id not in region_keys:
                issues.append(
                    Issue(
                        category="region",
                        severity=Severity.ERROR,
                        message=f"Region enum value '{region_id}' has no entry in regions.json",
                        file_path=self.path,
                        context={"missing_region": region_id},
                    )
                )

        return issues

    def _check_faction_references(self) -> list[Issue]:
        """Verify faction references are valid."""
        issues = []

        for region_id, region in self.regions.items():
            # Check primary_faction
            primary = region.get("primary_faction")
            if primary and not self.enums.is_valid_faction_id(primary):
                issues.append(
                    Issue(
                        category="region",
                        severity=Severity.ERROR,
                        message=f"Region '{region_id}' has invalid primary_faction '{primary}'",
                        file_path=self.path,
                        context={
                            "region": region_id,
                            "field": "primary_faction",
                            "value": primary,
                            "valid": sorted(self.enums.faction_ids),
                        },
                    )
                )

            # Check contested_by
            for faction_id in region.get("contested_by", []):
                if not self.enums.is_valid_faction_id(faction_id):
                    issues.append(
                        Issue(
                            category="region",
                            severity=Severity.ERROR,
                            message=f"Region '{region_id}' has invalid contested_by faction '{faction_id}'",
                            file_path=self.path,
                            context={
                                "region": region_id,
                                "field": "contested_by",
                                "value": faction_id,
                            },
                        )
                    )

        return issues

    def _check_adjacency_bidirectional(self) -> list[Issue]:
        """Verify adjacency is bidirectional (if A→B then B→A)."""
        issues = []

        for region_id, region in self.regions.items():
            for adjacent_id in region.get("adjacent", []):
                adjacent_region = self.regions.get(adjacent_id)
                if adjacent_region:
                    adjacent_neighbors = adjacent_region.get("adjacent", [])
                    if region_id not in adjacent_neighbors:
                        issues.append(
                            Issue(
                                category="adjacency",
                                severity=Severity.WARNING,
                                message=f"Adjacency not bidirectional: {region_id} → {adjacent_id} but not reverse",
                                file_path=self.path,
                                context={
                                    "from": region_id,
                                    "to": adjacent_id,
                                    "reverse_missing": True,
                                },
                            )
                        )

        return issues

    def _check_adjacency_valid_targets(self) -> list[Issue]:
        """Verify adjacent region IDs exist."""
        issues = []
        region_keys = set(self.regions.keys())

        for region_id, region in self.regions.items():
            for adjacent_id in region.get("adjacent", []):
                if adjacent_id not in region_keys:
                    issues.append(
                        Issue(
                            category="adjacency",
                            severity=Severity.ERROR,
                            message=f"Region '{region_id}' references non-existent adjacent region '{adjacent_id}'",
                            file_path=self.path,
                            context={
                                "region": region_id,
                                "invalid_adjacent": adjacent_id,
                            },
                        )
                    )

        return issues


class JobValidator:
    """Validates job template files against schema and vehicle data."""

    def __init__(
        self,
        enums: EnumRegistry,
        jobs: dict[str, tuple[dict, str]],  # job_id -> (job_data, file_path)
        vehicle_tags: set[str],
        vehicle_types: set[str],
    ):
        self.enums = enums
        self.jobs = jobs
        self.vehicle_tags = vehicle_tags
        self.vehicle_types = vehicle_types

    def validate(self) -> list[Issue]:
        issues = []
        for job_id, (job, file_path) in self.jobs.items():
            issues.extend(self._validate_job(job_id, job, file_path))
        issues.extend(self._check_vehicle_tag_coverage())
        return issues

    def _validate_job(
        self, job_id: str, job: dict, file_path: str
    ) -> list[Issue]:
        issues = []

        # Check faction
        faction = job.get("faction")
        if faction and faction not in self.enums.factions:
            issues.append(
                Issue(
                    category="job",
                    severity=Severity.ERROR,
                    message=f"Job '{job_id}' has invalid faction '{faction}'",
                    file_path=file_path,
                    context={
                        "job_id": job_id,
                        "field": "faction",
                        "value": faction,
                        "valid": sorted(self.enums.factions),
                    },
                )
            )

        # Check mission type
        mission_type = job.get("type")
        if mission_type and mission_type not in self.enums.mission_types:
            issues.append(
                Issue(
                    category="job",
                    severity=Severity.ERROR,
                    message=f"Job '{job_id}' has invalid type '{mission_type}'",
                    file_path=file_path,
                    context={
                        "job_id": job_id,
                        "field": "type",
                        "value": mission_type,
                        "valid": sorted(self.enums.mission_types),
                    },
                )
            )

        # Check region (if present)
        region = job.get("region")
        if region and region not in self.enums.regions:
            issues.append(
                Issue(
                    category="job",
                    severity=Severity.ERROR,
                    message=f"Job '{job_id}' has invalid region '{region}'",
                    file_path=file_path,
                    context={
                        "job_id": job_id,
                        "field": "region",
                        "value": region,
                        "valid": sorted(self.enums.regions),
                    },
                )
            )

        # Check opposing_factions
        for opp_faction in job.get("opposing_factions", []):
            if opp_faction not in self.enums.factions:
                issues.append(
                    Issue(
                        category="job",
                        severity=Severity.ERROR,
                        message=f"Job '{job_id}' has invalid opposing faction '{opp_faction}'",
                        file_path=file_path,
                        context={
                            "job_id": job_id,
                            "field": "opposing_factions",
                            "value": opp_faction,
                        },
                    )
                )

        # Check vehicle type (if present)
        vehicle_type = job.get("requires_vehicle_type")
        if vehicle_type and vehicle_type not in self.vehicle_types:
            issues.append(
                Issue(
                    category="job",
                    severity=Severity.ERROR,
                    message=f"Job '{job_id}' requires non-existent vehicle type '{vehicle_type}'",
                    file_path=file_path,
                    context={
                        "job_id": job_id,
                        "field": "requires_vehicle_type",
                        "value": vehicle_type,
                        "valid": sorted(self.vehicle_types),
                    },
                )
            )

        # Check vehicle tags (if present)
        for tag in job.get("requires_vehicle_tags", []):
            if tag not in self.vehicle_tags:
                issues.append(
                    Issue(
                        category="job",
                        severity=Severity.WARNING,
                        message=f"Job '{job_id}' requires vehicle tag '{tag}' not provided by any vehicle",
                        file_path=file_path,
                        context={
                            "job_id": job_id,
                            "field": "requires_vehicle_tags",
                            "value": tag,
                            "available_tags": sorted(self.vehicle_tags),
                        },
                    )
                )

        return issues

    def _check_vehicle_tag_coverage(self) -> list[Issue]:
        """Check for orphan vehicle tags (not used by any job)."""
        issues = []

        # Collect all tags required by jobs
        required_tags: set[str] = set()
        for job_id, (job, _) in self.jobs.items():
            required_tags.update(job.get("requires_vehicle_tags", []))

        # Find orphan tags
        orphan_tags = self.vehicle_tags - required_tags
        for tag in orphan_tags:
            issues.append(
                Issue(
                    category="vehicle",
                    severity=Severity.INFO,
                    message=f"Vehicle tag '{tag}' is not required by any job",
                    context={"orphan_tag": tag},
                )
            )

        return issues


class FavorValidator:
    """Validates favor system configuration."""

    def __init__(
        self,
        enums: EnumRegistry,
        favor_costs: dict[str, Any],
        disposition_favors: dict[str, Any],
        disposition_modifiers: dict[str, Any],
        favors_path: str,
    ):
        self.enums = enums
        self.favor_costs = favor_costs
        self.disposition_favors = disposition_favors
        self.disposition_modifiers = disposition_modifiers
        self.path = favors_path

    def validate(self) -> list[Issue]:
        issues = []
        issues.extend(self._check_favor_type_coverage())
        issues.extend(self._check_disposition_coverage())
        return issues

    def _check_favor_type_coverage(self) -> list[Issue]:
        """Verify all FavorType values have costs defined."""
        issues = []

        for favor_type in self.enums.favor_types:
            if favor_type not in self.favor_costs:
                issues.append(
                    Issue(
                        category="favor",
                        severity=Severity.ERROR,
                        message=f"FavorType '{favor_type}' has no entry in FAVOR_COSTS",
                        file_path=self.path,
                        context={"missing_favor_type": favor_type},
                    )
                )

        return issues

    def _check_disposition_coverage(self) -> list[Issue]:
        """Verify all Disposition values have favor mappings."""
        issues = []

        for disposition in self.enums.dispositions:
            if disposition not in self.disposition_favors:
                issues.append(
                    Issue(
                        category="favor",
                        severity=Severity.ERROR,
                        message=f"Disposition '{disposition}' has no entry in DISPOSITION_FAVORS",
                        file_path=self.path,
                        context={"missing_disposition": disposition},
                    )
                )

            if disposition not in self.disposition_modifiers:
                issues.append(
                    Issue(
                        category="favor",
                        severity=Severity.ERROR,
                        message=f"Disposition '{disposition}' has no entry in DISPOSITION_COST_MODIFIER",
                        file_path=self.path,
                        context={"missing_disposition": disposition},
                    )
                )

        return issues


# ─────────────────────────────────────────────────────────────────────────────
# Main Auditor
# ─────────────────────────────────────────────────────────────────────────────


class MechanicsAuditor:
    """Main auditor that coordinates all validators."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.sentinel_agent = project_root / "sentinel-agent"

    def run(self) -> ValidationResult:
        result = ValidationResult()

        # Load data sources
        enums = self._load_enums()
        if not enums.factions:
            result.issues.append(
                Issue(
                    category="setup",
                    severity=Severity.ERROR,
                    message="Could not parse enums from schema.py",
                    file_path=str(self.sentinel_agent / "src" / "state" / "schema.py"),
                )
            )
            return result

        regions, regions_path = self._load_regions()
        jobs, job_files = self._load_all_jobs()
        vehicle_tags, vehicle_types = self._load_vehicles()
        favor_config = self._load_favor_config()

        # Collect stats
        result.stats = {
            "factions": len(enums.factions),
            "regions_in_enum": len(enums.regions),
            "regions_in_json": len(regions.get("regions", {})),
            "jobs": len(jobs),
            "job_files": job_files,
            "vehicles": len(vehicle_types),
            "vehicle_tags": len(vehicle_tags),
        }

        # Run validators
        if regions:
            result.issues.extend(
                RegionValidator(enums, regions, regions_path).validate()
            )

        if jobs:
            result.issues.extend(
                JobValidator(enums, jobs, vehicle_tags, vehicle_types).validate()
            )

        if favor_config:
            favor_costs, disp_favors, disp_mods, favors_path = favor_config
            result.issues.extend(
                FavorValidator(
                    enums, favor_costs, disp_favors, disp_mods, favors_path
                ).validate()
            )

        return result

    def _load_enums(self) -> EnumRegistry:
        """Parse schema.py for enum values."""
        schema_path = self.sentinel_agent / "src" / "state" / "schema.py"
        return EnumRegistry(schema_path)

    def _load_regions(self) -> tuple[dict, str]:
        """Load regions.json."""
        regions_path = self.sentinel_agent / "data" / "regions.json"
        if not regions_path.exists():
            return {}, str(regions_path)

        try:
            with open(regions_path, encoding="utf-8") as f:
                return json.load(f), str(regions_path)
        except json.JSONDecodeError as e:
            return {"_error": str(e)}, str(regions_path)

    def _load_all_jobs(self) -> tuple[dict[str, tuple[dict, str]], int]:
        """Load all job template files."""
        jobs_dir = self.sentinel_agent / "data" / "jobs"
        if not jobs_dir.exists():
            return {}, 0

        all_jobs: dict[str, tuple[dict, str]] = {}
        file_count = 0

        for job_file in jobs_dir.glob("*.json"):
            file_count += 1
            try:
                with open(job_file, encoding="utf-8") as f:
                    data = json.load(f)
                    for job in data.get("jobs", []):
                        job_id = job.get("id", f"unknown_{file_count}")
                        all_jobs[job_id] = (job, str(job_file))
            except json.JSONDecodeError:
                pass  # Skip malformed files

        return all_jobs, file_count

    def _load_vehicles(self) -> tuple[set[str], set[str]]:
        """Extract vehicle data from tui_commands.py."""
        tui_path = self.sentinel_agent / "src" / "interface" / "tui_commands.py"
        if not tui_path.exists():
            return set(), set()

        content = tui_path.read_text(encoding="utf-8")

        # Extract VEHICLE_DATA using regex
        # Look for the dict and parse unlock tags and types
        vehicle_tags: set[str] = set()
        vehicle_types: set[str] = set()

        # Match unlocks_tags: ["tag1", "tag2"]
        for match in re.finditer(r'"unlocks_tags":\s*\[([^\]]*)\]', content):
            tags_str = match.group(1)
            for tag_match in re.finditer(r'"([^"]+)"', tags_str):
                vehicle_tags.add(tag_match.group(1))

        # Match "type": "typename"
        for match in re.finditer(r'"type":\s*"([^"]+)"', content):
            vehicle_types.add(match.group(1))

        return vehicle_tags, vehicle_types

    def _load_favor_config(
        self,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str] | None:
        """Extract favor configuration from favors.py."""
        favors_path = self.sentinel_agent / "src" / "systems" / "favors.py"
        if not favors_path.exists():
            return None

        content = favors_path.read_text(encoding="utf-8")

        # Extract favor types from FAVOR_COSTS
        # Note: Enum member names (RIDE) differ from values (ride)
        favor_costs: dict[str, Any] = {}
        for match in re.finditer(r"FavorType\.(\w+):\s*(\d+)", content):
            # Store with lowercase key to match enum values
            favor_costs[match.group(1).lower()] = int(match.group(2))

        # Extract disposition favors (list comprehension or explicit list)
        disposition_favors: dict[str, Any] = {}
        # Match: Disposition.HOSTILE: [],  or  Disposition.WARM: list(FavorType),
        for match in re.finditer(
            r"Disposition\.(\w+):\s*(\[(?:[^\]]*)\]|list\([^)]*\))", content
        ):
            disposition_favors[match.group(1).lower()] = match.group(2)

        # Extract disposition modifiers
        disposition_modifiers: dict[str, Any] = {}
        for match in re.finditer(
            r"Disposition\.(\w+):\s*([\d.]+)", content
        ):
            disposition_modifiers[match.group(1).lower()] = float(
                match.group(2)
            )

        return favor_costs, disposition_favors, disposition_modifiers, str(favors_path)


# ─────────────────────────────────────────────────────────────────────────────
# Output Formatters
# ─────────────────────────────────────────────────────────────────────────────


def format_console(result: ValidationResult) -> str:
    """Format results for console output."""
    lines = [
        "Mechanics Integrity Report",
        "=" * 50,
        "Data loaded:",
    ]

    for key, value in result.stats.items():
        lines.append(f"  - {key}: {value}")

    lines.extend(["", "Validation Results", "=" * 50, ""])

    if not result.issues:
        lines.append("✓ All checks passed!")
    else:
        # Group by severity
        for severity in [Severity.ERROR, Severity.WARNING, Severity.INFO]:
            issues = [i for i in result.issues if i.severity == severity]
            for issue in issues:
                prefix = {
                    Severity.ERROR: "[ERROR]",
                    Severity.WARNING: "[WARNING]",
                    Severity.INFO: "[INFO]",
                }[severity]

                lines.append(f"{prefix} {issue.category}: {issue.message}")
                if issue.file_path:
                    # Use forward slashes for consistency
                    path = issue.file_path.replace("\\", "/")
                    lines.append(f"  File: {path}")
                if issue.context.get("valid"):
                    lines.append(f"  Valid: {', '.join(issue.context['valid'][:5])}...")
                lines.append("")

    lines.extend([
        "-" * 50,
        f"Summary: {result.error_count} error(s), {result.warning_count} warning(s), {result.info_count} info",
        f"Status: {'HEALTHY' if result.is_healthy else 'NEEDS ATTENTION' if result.error_count == 0 else 'BROKEN'}",
    ])

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Validate SENTINEL game data integrity"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Project root directory (auto-detected if not specified)",
    )
    args = parser.parse_args()

    # Auto-detect project root
    if args.project_root:
        project_root = args.project_root
    else:
        # Walk up from script location to find SENTINEL root
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent.parent  # scripts/ -> sentinel-agent/ -> SENTINEL/

        # Verify we found the right directory
        if not (project_root / "sentinel-agent").exists():
            print("Error: Could not locate SENTINEL project root", file=sys.stderr)
            sys.exit(2)

    auditor = MechanicsAuditor(project_root)
    result = auditor.run()

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(format_console(result))

    # Exit code based on results
    if result.error_count > 0:
        sys.exit(2)
    elif result.warning_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
