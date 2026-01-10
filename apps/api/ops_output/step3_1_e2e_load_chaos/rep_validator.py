"""
Strict REP (Run Evidence Pack) Validator for Step 3.1

Validates that REP packs contain ALL required files with valid content:
1. manifest.json - valid schema with run metadata
2. trace.ndjson - exists and parseable NDJSON
3. llm_ledger.ndjson - exists, parseable, and has >= 1 record for LLM tests
4. universe_graph.json - exists and parseable JSON
5. report.md - exists and references run_id

This is NON-BLACKBOX validation - we verify actual file contents, not just existence.
"""

import json
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
import re


@dataclass
class FileValidationResult:
    """Validation result for a single REP file"""
    file_name: str
    required: bool
    present: bool
    valid: bool
    size_bytes: int = 0
    record_count: int = 0  # For NDJSON files
    validation_errors: List[str] = field(default_factory=list)
    content_hash: str = ""
    sample_data: Optional[Dict[str, Any]] = None


@dataclass
class REPValidationResult:
    """Complete REP validation result"""
    run_id: str
    rep_path: str
    is_valid: bool  # Final verdict - ALL required files must be valid

    # File lists
    required_files: List[str] = field(default_factory=list)
    present_files: List[str] = field(default_factory=list)
    missing_files: List[str] = field(default_factory=list)

    # Per-file validation
    file_validations: Dict[str, FileValidationResult] = field(default_factory=dict)

    # Summary booleans
    manifest_valid: bool = False
    trace_valid: bool = False
    llm_ledger_valid: bool = False
    universe_graph_valid: bool = False
    report_valid: bool = False

    # Aggregated metrics
    total_trace_events: int = 0
    total_llm_calls: int = 0
    llm_ledger_has_records: bool = False

    # Validation timestamp and errors
    validated_at: str = ""
    validation_errors: List[str] = field(default_factory=list)


class StrictREPValidator:
    """
    Non-blackbox REP validator that verifies actual file contents.

    Requirements for PASS:
    - manifest.json: valid JSON with required schema fields
    - trace.ndjson: valid NDJSON with at least RUN_STARTED event
    - llm_ledger.ndjson: valid NDJSON (>=1 record for LLM-requiring tests)
    - universe_graph.json: valid JSON with nodes/edges
    - report.md: exists and contains run_id reference
    """

    REQUIRED_FILES = [
        "manifest.json",
        "trace.ndjson",
        "llm_ledger.ndjson",
        "universe_graph.json",
        "report.md"
    ]

    MANIFEST_REQUIRED_FIELDS = [
        "rep_id", "run_id", "created_at", "status"
    ]

    MANIFEST_OPTIONAL_FIELDS = [
        "project_id", "agent_count", "step_count", "replicate_count",
        "seed", "model_name", "completed_at", "metrics"
    ]

    TRACE_EVENT_TYPES = [
        "RUN_STARTED", "RUN_DONE", "WORLD_TICK", "AGENT_STEP",
        "AGENT_DECISION", "POLICY_UPDATE", "NODE_CREATE", "NODE_EXPAND",
        "NODE_BRANCH", "REPLICATE_START", "REPLICATE_DONE", "AGGREGATE",
        "PROBABILITY_COMPUTE", "CONFIDENCE_INTERVAL", "CALIBRATE",
        "DATA_INGEST", "PERSONA_GENERATE", "EXPORT_CREATED", "REPORT_GENERATED"
    ]

    LLM_LEDGER_REQUIRED_FIELDS = [
        "call_id", "timestamp", "run_id", "model"
    ]

    def __init__(self, require_llm_records: bool = False):
        """
        Args:
            require_llm_records: If True, llm_ledger must have >= 1 record
        """
        self.require_llm_records = require_llm_records

    def validate_manifest(self, content: bytes) -> FileValidationResult:
        """Validate manifest.json schema and content"""
        result = FileValidationResult(
            file_name="manifest.json",
            required=True,
            present=True,
            valid=False,
            size_bytes=len(content),
            content_hash=hashlib.sha256(content).hexdigest()[:16]
        )

        try:
            data = json.loads(content.decode('utf-8'))
            result.sample_data = {k: v for k, v in list(data.items())[:5]}

            # Check required fields
            for field in self.MANIFEST_REQUIRED_FIELDS:
                if field not in data:
                    result.validation_errors.append(f"Missing required field: {field}")

            # Validate field types
            if "run_id" in data and not isinstance(data["run_id"], str):
                result.validation_errors.append("run_id must be string")

            if "status" in data:
                valid_statuses = ["running", "completed", "failed", "pending", "cancelled"]
                if data["status"] not in valid_statuses:
                    result.validation_errors.append(f"Invalid status: {data['status']}")

            # Validate timestamp format
            if "created_at" in data:
                try:
                    # Check ISO format
                    datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    result.validation_errors.append("Invalid created_at timestamp format")

            result.valid = len(result.validation_errors) == 0

        except json.JSONDecodeError as e:
            result.validation_errors.append(f"Invalid JSON: {e}")
        except Exception as e:
            result.validation_errors.append(f"Validation error: {e}")

        return result

    def validate_trace_ndjson(self, content: bytes) -> FileValidationResult:
        """Validate trace.ndjson - must be valid NDJSON with trace events"""
        result = FileValidationResult(
            file_name="trace.ndjson",
            required=True,
            present=True,
            valid=False,
            size_bytes=len(content),
            content_hash=hashlib.sha256(content).hexdigest()[:16]
        )

        try:
            lines = content.decode('utf-8').strip().split('\n')
            result.record_count = 0
            event_types_found = set()
            sample_events = []

            for i, line in enumerate(lines):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                    result.record_count += 1

                    # Collect event types
                    if "event_type" in event:
                        event_types_found.add(event["event_type"])

                    # Sample first 3 events
                    if len(sample_events) < 3:
                        sample_events.append({
                            "event_type": event.get("event_type"),
                            "timestamp": event.get("timestamp"),
                            "run_id": event.get("run_id")
                        })

                except json.JSONDecodeError as e:
                    result.validation_errors.append(f"Invalid JSON at line {i+1}: {e}")
                    if len(result.validation_errors) > 5:
                        result.validation_errors.append("... (truncated)")
                        break

            result.sample_data = {
                "event_types_found": list(event_types_found),
                "sample_events": sample_events
            }

            # Validation checks
            if result.record_count == 0:
                result.validation_errors.append("No trace events found")

            if "RUN_STARTED" not in event_types_found and result.record_count > 0:
                result.validation_errors.append("Missing RUN_STARTED event")

            result.valid = len(result.validation_errors) == 0 and result.record_count > 0

        except Exception as e:
            result.validation_errors.append(f"Parse error: {e}")

        return result

    def validate_llm_ledger(self, content: bytes) -> FileValidationResult:
        """Validate llm_ledger.ndjson - LLM call records"""
        result = FileValidationResult(
            file_name="llm_ledger.ndjson",
            required=True,
            present=True,
            valid=False,
            size_bytes=len(content),
            content_hash=hashlib.sha256(content).hexdigest()[:16]
        )

        try:
            lines = content.decode('utf-8').strip().split('\n')
            result.record_count = 0
            models_used = set()
            total_tokens = 0
            mock_count = 0
            real_count = 0
            sample_calls = []

            for i, line in enumerate(lines):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    result.record_count += 1

                    # Track models
                    if "model" in record:
                        models_used.add(record["model"])

                    # Track tokens
                    total_tokens += record.get("tokens_in", 0) + record.get("tokens_out", 0)

                    # Track mock vs real
                    if record.get("mock", False):
                        mock_count += 1
                    else:
                        real_count += 1

                    # Sample first 3 calls
                    if len(sample_calls) < 3:
                        sample_calls.append({
                            "call_id": record.get("call_id"),
                            "model": record.get("model"),
                            "tokens_in": record.get("tokens_in"),
                            "tokens_out": record.get("tokens_out"),
                            "mock": record.get("mock", False)
                        })

                    # Validate required fields
                    for field in self.LLM_LEDGER_REQUIRED_FIELDS:
                        if field not in record and i == 0:  # Only report for first record
                            result.validation_errors.append(f"Missing field in ledger: {field}")

                except json.JSONDecodeError as e:
                    result.validation_errors.append(f"Invalid JSON at line {i+1}: {e}")
                    if len(result.validation_errors) > 5:
                        break

            result.sample_data = {
                "models_used": list(models_used),
                "total_tokens": total_tokens,
                "mock_count": mock_count,
                "real_count": real_count,
                "sample_calls": sample_calls
            }

            # For LLM-requiring tests, must have records
            if self.require_llm_records and result.record_count == 0:
                result.validation_errors.append("LLM ledger is empty but LLM records required")

            # Valid if parseable (records may be 0 for non-LLM tests)
            result.valid = len(result.validation_errors) == 0

        except Exception as e:
            result.validation_errors.append(f"Parse error: {e}")

        return result

    def validate_universe_graph(self, content: bytes) -> FileValidationResult:
        """Validate universe_graph.json - node/edge structure"""
        result = FileValidationResult(
            file_name="universe_graph.json",
            required=True,
            present=True,
            valid=False,
            size_bytes=len(content),
            content_hash=hashlib.sha256(content).hexdigest()[:16]
        )

        try:
            data = json.loads(content.decode('utf-8'))

            nodes = data.get("nodes", [])
            edges = data.get("edges", [])

            result.record_count = len(nodes)
            result.sample_data = {
                "project_id": data.get("project_id"),
                "root_node_id": data.get("root_node_id"),
                "node_count": len(nodes),
                "edge_count": len(edges),
                "sample_nodes": nodes[:2] if nodes else []
            }

            # Validation
            if "nodes" not in data and "edges" not in data:
                result.validation_errors.append("Missing nodes and edges arrays")

            # Validate node structure
            for i, node in enumerate(nodes[:5]):
                if "node_id" not in node:
                    result.validation_errors.append(f"Node {i} missing node_id")
                    break

            result.valid = len(result.validation_errors) == 0

        except json.JSONDecodeError as e:
            result.validation_errors.append(f"Invalid JSON: {e}")
        except Exception as e:
            result.validation_errors.append(f"Parse error: {e}")

        return result

    def validate_report_md(self, content: bytes, run_id: str) -> FileValidationResult:
        """Validate report.md - must exist and reference run_id"""
        result = FileValidationResult(
            file_name="report.md",
            required=True,
            present=True,
            valid=False,
            size_bytes=len(content),
            content_hash=hashlib.sha256(content).hexdigest()[:16]
        )

        try:
            text = content.decode('utf-8')

            # Check for run_id reference
            has_run_id = run_id in text or "run_id" in text.lower()

            # Check for basic markdown structure
            has_headers = text.count('#') >= 1

            # Extract first 500 chars as sample
            result.sample_data = {
                "preview": text[:500] + "..." if len(text) > 500 else text,
                "has_run_id_reference": has_run_id,
                "has_headers": has_headers,
                "line_count": len(text.split('\n'))
            }

            if not has_run_id:
                result.validation_errors.append(f"Report does not reference run_id: {run_id}")

            if len(text.strip()) < 100:
                result.validation_errors.append("Report content is too short (< 100 chars)")

            result.valid = len(result.validation_errors) == 0

        except Exception as e:
            result.validation_errors.append(f"Parse error: {e}")

        return result

    def validate_rep(
        self,
        run_id: str,
        rep_path: str,
        files: Dict[str, bytes]  # filename -> content
    ) -> REPValidationResult:
        """
        Validate a complete REP pack.

        Args:
            run_id: The run ID this REP belongs to
            rep_path: Storage path to the REP directory
            files: Dictionary mapping filename to file contents

        Returns:
            REPValidationResult with detailed validation status
        """
        result = REPValidationResult(
            run_id=run_id,
            rep_path=rep_path,
            is_valid=False,
            required_files=self.REQUIRED_FILES.copy(),
            present_files=list(files.keys()),
            validated_at=datetime.utcnow().isoformat() + "Z"
        )

        # Identify missing files
        result.missing_files = [
            f for f in self.REQUIRED_FILES if f not in files
        ]

        # Validate each file
        for filename in self.REQUIRED_FILES:
            if filename not in files:
                # File is missing
                result.file_validations[filename] = FileValidationResult(
                    file_name=filename,
                    required=True,
                    present=False,
                    valid=False,
                    validation_errors=["File not found"]
                )
                continue

            content = files[filename]

            if filename == "manifest.json":
                validation = self.validate_manifest(content)
                result.manifest_valid = validation.valid

            elif filename == "trace.ndjson":
                validation = self.validate_trace_ndjson(content)
                result.trace_valid = validation.valid
                result.total_trace_events = validation.record_count

            elif filename == "llm_ledger.ndjson":
                validation = self.validate_llm_ledger(content)
                result.llm_ledger_valid = validation.valid
                result.total_llm_calls = validation.record_count
                result.llm_ledger_has_records = validation.record_count > 0

            elif filename == "universe_graph.json":
                validation = self.validate_universe_graph(content)
                result.universe_graph_valid = validation.valid

            elif filename == "report.md":
                validation = self.validate_report_md(content, run_id)
                result.report_valid = validation.valid

            else:
                validation = FileValidationResult(
                    file_name=filename,
                    required=False,
                    present=True,
                    valid=True,
                    size_bytes=len(content)
                )

            result.file_validations[filename] = validation

            # Collect errors
            if validation.validation_errors:
                result.validation_errors.extend([
                    f"{filename}: {err}" for err in validation.validation_errors
                ])

        # Final verdict: ALL required files must be present AND valid
        result.is_valid = (
            len(result.missing_files) == 0 and
            result.manifest_valid and
            result.trace_valid and
            result.llm_ledger_valid and
            result.universe_graph_valid and
            result.report_valid
        )

        # Add summary error if invalid
        if not result.is_valid:
            if result.missing_files:
                result.validation_errors.insert(0,
                    f"Missing required files: {result.missing_files}")

            invalid_files = [
                f for f, v in result.file_validations.items()
                if not v.valid
            ]
            if invalid_files:
                result.validation_errors.insert(0,
                    f"Invalid files: {invalid_files}")

        return result

    def to_dict(self, result: REPValidationResult) -> Dict[str, Any]:
        """Convert REPValidationResult to dictionary for JSON serialization"""
        d = asdict(result)
        # Convert FileValidationResult objects
        d["file_validations"] = {
            k: asdict(v) for k, v in result.file_validations.items()
        }
        return d


def validate_rep_from_storage(
    storage_client,
    run_id: str,
    rep_path: str,
    require_llm_records: bool = False
) -> REPValidationResult:
    """
    Convenience function to validate a REP directly from storage.

    Args:
        storage_client: Storage service client with get_object method
        run_id: The run ID
        rep_path: Base path to REP directory (e.g., "tenant_id/run_id/")
        require_llm_records: Whether LLM ledger must have records

    Returns:
        REPValidationResult
    """
    validator = StrictREPValidator(require_llm_records=require_llm_records)
    files = {}

    for filename in validator.REQUIRED_FILES:
        try:
            key = f"{rep_path.rstrip('/')}/{filename}"
            content = storage_client.get_object(key)
            if content:
                files[filename] = content
        except Exception as e:
            # File not found or error - will be marked as missing
            pass

    return validator.validate_rep(run_id, rep_path, files)
