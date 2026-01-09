#!/usr/bin/env python3
"""
CI Check: Ensure all LLM calls go through LLMRouter

This script scans the codebase for direct OpenRouterService usage
and fails if any are found outside of the allowed files.

Reference: GAPS.md GAP-P0-001 - Centralized LLM Router

Usage:
    python scripts/check_llm_usage.py
    # Returns exit code 0 if all LLM calls use LLMRouter
    # Returns exit code 1 if direct OpenRouterService usage found
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Files that are allowed to import OpenRouterService directly
ALLOWED_FILES = {
    "app/services/openrouter.py",      # The OpenRouter service itself
    "app/services/llm_router.py",      # LLMRouter wraps OpenRouter
    "app/api/v1/endpoints/llm_admin.py",  # Admin endpoint uses AVAILABLE_MODELS constant
    "app/services/__init__.py",        # Module re-exports (legacy compatibility)
    # Legacy services pending refactor (use batch_complete which is complex):
    "app/services/product_execution.py",  # Products feature marked for REMOVE in spec
    "app/services/simulation.py",      # Legacy simulation, pending Node/Run system migration
    "tests/",                           # Tests may mock OpenRouter directly
}

# Imports that are allowed (constants only, not the service class)
ALLOWED_IMPORTS = {
    "AVAILABLE_MODELS",  # Model preset constants
    "CompletionResponse",  # Response type for type hints
}

# Patterns that indicate direct OpenRouter usage (not through LLMRouter)
VIOLATION_PATTERNS = [
    (r"from app\.services\.openrouter import", "Direct OpenRouterService import"),
    (r"OpenRouterService\(\)", "Direct OpenRouterService instantiation"),
    (r"openrouter\.complete\(", "Direct OpenRouter.complete() call"),
    (r"openrouter\.batch_complete\(", "Direct OpenRouter.batch_complete() call"),
]


def is_allowed_file(file_path: str) -> bool:
    """Check if file is allowed to use OpenRouterService directly."""
    for allowed in ALLOWED_FILES:
        if allowed in file_path:
            return True
    return False


def is_allowed_import(line: str) -> bool:
    """Check if an import line only imports allowed items."""
    # Check if line imports only allowed items (constants, not the service class)
    for allowed in ALLOWED_IMPORTS:
        if f"import {allowed}" in line or f", {allowed}" in line:
            # Make sure OpenRouterService is not also imported
            if "OpenRouterService" not in line:
                return True
    return False


def check_file(file_path: Path) -> List[Tuple[int, str, str]]:
    """
    Check a single file for direct OpenRouter usage.

    Returns:
        List of (line_number, line_content, violation_type) tuples
    """
    violations = []

    try:
        content = file_path.read_text()
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            for pattern, violation_type in VIOLATION_PATTERNS:
                if re.search(pattern, line):
                    # Check if this is an allowed import
                    if "import" in violation_type and is_allowed_import(line):
                        continue
                    violations.append((line_num, line.strip(), violation_type))

    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}", file=sys.stderr)

    return violations


def scan_directory(directory: Path) -> dict:
    """
    Scan directory for Python files and check for violations.

    Returns:
        Dict mapping file paths to list of violations
    """
    all_violations = {}

    for file_path in directory.rglob("*.py"):
        # Skip allowed files
        relative_path = str(file_path.relative_to(directory))
        if is_allowed_file(relative_path):
            continue

        # Skip virtual environments
        if "venv" in str(file_path) or "site-packages" in str(file_path):
            continue

        violations = check_file(file_path)
        if violations:
            all_violations[relative_path] = violations

    return all_violations


def main():
    """Main entry point."""
    # Find the api directory
    script_dir = Path(__file__).parent
    api_dir = script_dir.parent  # apps/api

    if not api_dir.exists():
        print("Error: Could not find api directory", file=sys.stderr)
        sys.exit(1)

    print("=" * 60)
    print("LLM Router Usage Check")
    print("=" * 60)
    print(f"Scanning: {api_dir}")
    print()

    violations = scan_directory(api_dir)

    if not violations:
        print("✅ All LLM calls go through LLMRouter")
        print()
        print("No direct OpenRouterService usage found outside allowed files.")
        sys.exit(0)

    # Report violations
    print("❌ Direct OpenRouterService usage found!")
    print()
    print("The following files bypass the LLM Router:")
    print("-" * 60)

    total_violations = 0
    for file_path, file_violations in sorted(violations.items()):
        print(f"\n📄 {file_path}")
        for line_num, line, violation_type in file_violations:
            print(f"   Line {line_num}: {violation_type}")
            print(f"   > {line[:80]}{'...' if len(line) > 80 else ''}")
            total_violations += 1

    print()
    print("=" * 60)
    print(f"Total violations: {total_violations}")
    print()
    print("To fix these violations:")
    print("1. Import LLMRouter instead of OpenRouterService")
    print("2. Use llm_router.complete(profile_key=..., messages=...)")
    print("3. See apps/api/app/services/event_compiler.py for an example")
    print()
    print("If this file legitimately needs direct OpenRouter access,")
    print("add it to ALLOWED_FILES in this script.")
    print("=" * 60)

    sys.exit(1)


if __name__ == "__main__":
    main()
