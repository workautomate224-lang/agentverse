"""
Output Auditor Service - LLM Output Temporal Compliance Auditing
Reference: temporal.md §8 Phase 4 item 12

This service audits LLM outputs to detect and flag:
1. Hallucinated facts not grounded in the data manifest
2. References to post-cutoff events or data
3. Non-manifest factual claims
4. Temporal contamination indicators

The auditor returns a compliance score and list of violations that
are recorded in the run audit report.

Usage:
    auditor = OutputAuditor(manifest, cutoff_time)
    result = auditor.audit_output(llm_response)
    if not result.is_compliant:
        for violation in result.violations:
            logger.warning(f"Violation: {violation.description}")
"""

import re
import hashlib
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field

from app.services.data_manifest import DataManifestService, ManifestEntry

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================

class ViolationType(str, Enum):
    """Types of temporal compliance violations."""
    POST_CUTOFF_REFERENCE = "post_cutoff_reference"  # Reference to date/event after cutoff
    UNGROUNDED_FACT = "ungrounded_fact"  # Factual claim not in manifest data
    NUMERIC_HALLUCINATION = "numeric_hallucination"  # Specific number not from manifest
    ENTITY_NOT_IN_CONTEXT = "entity_not_in_context"  # Entity reference not in context
    PREDICTION_FROM_KNOWLEDGE = "prediction_from_knowledge"  # Prediction based on future knowledge
    TEMPORAL_CONFUSION = "temporal_confusion"  # Mixing pre/post cutoff information


class Violation(BaseModel):
    """A single compliance violation detected in LLM output."""
    id: str = Field(default_factory=lambda: hashlib.md5(str(datetime.utcnow()).encode()).hexdigest()[:8])
    violation_type: ViolationType
    description: str
    severity: str = "medium"  # low, medium, high, critical
    evidence: str  # The text snippet that triggered the violation
    line_number: Optional[int] = None
    confidence: float = 0.8  # Confidence in the violation detection


class AuditResult(BaseModel):
    """Result of auditing LLM output."""
    is_compliant: bool
    compliance_score: float  # 0.0 (many violations) to 1.0 (fully compliant)
    violations: List[Violation] = Field(default_factory=list)
    grounded_facts_count: int = 0
    ungrounded_facts_count: int = 0
    temporal_references_checked: int = 0
    audit_timestamp: datetime = Field(default_factory=datetime.utcnow)
    auditor_version: str = "1.0.0"


class FactExtraction(BaseModel):
    """A factual claim extracted from LLM output."""
    text: str
    fact_type: str  # numeric, entity, date, general
    context: str  # Surrounding text
    line_number: int
    is_grounded: Optional[bool] = None
    grounding_source: Optional[str] = None


# =============================================================================
# Output Auditor Service
# =============================================================================

class OutputAuditor:
    """
    Audits LLM outputs for temporal compliance and manifest grounding.

    This service checks that:
    1. All factual claims are grounded in manifest data
    2. No references to post-cutoff events/dates
    3. Numeric values match manifest data
    4. Entity references are present in context

    Reference: temporal.md §8 Phase 4 item 12
    """

    VERSION = "1.0.0"

    # Patterns for detecting temporal references
    DATE_PATTERNS = [
        r'\b(20\d{2})\b',  # Years 2000-2099
        r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+20\d{2}\b',
        r'\b\d{1,2}[/-]\d{1,2}[/-]20\d{2}\b',
        r'\b(Q[1-4])\s+20\d{2}\b',  # Quarters
    ]

    # Keywords that suggest future knowledge
    FUTURE_KNOWLEDGE_INDICATORS = [
        r'\bwill\s+(?:be|have|see|experience)\b',
        r'\bgoing\s+to\b',
        r'\bexpected\s+to\b',
        r'\bpredicted\s+(?:to|that)\b',
        r'\bforecasted?\b',
        r'\bby\s+20\d{2}\b',
        r'\bin\s+the\s+future\b',
        r'\bupcoming\b',
        r'\bnext\s+(?:year|quarter|month)\b',
    ]

    def __init__(
        self,
        manifest_entries: List[ManifestEntry],
        cutoff_time: datetime,
        isolation_level: int = 2,
        strict_mode: bool = True,
    ):
        """
        Initialize the Output Auditor.

        Args:
            manifest_entries: List of manifest entries from the current run
            cutoff_time: The temporal cutoff datetime
            isolation_level: Isolation strictness (1-3)
            strict_mode: If True, flag all suspicious content
        """
        self.manifest_entries = manifest_entries
        self.cutoff_time = cutoff_time
        self.isolation_level = isolation_level
        self.strict_mode = strict_mode
        self._manifest_data_cache: Set[str] = self._build_data_cache()
        self._manifest_numbers: Set[str] = self._extract_manifest_numbers()

    def audit_output(self, output: str) -> AuditResult:
        """
        Audit LLM output for temporal compliance.

        Args:
            output: The LLM response text to audit

        Returns:
            AuditResult with compliance status and violations
        """
        violations: List[Violation] = []
        grounded_count = 0
        ungrounded_count = 0
        temporal_refs_checked = 0

        # 1. Check for post-cutoff temporal references
        date_violations, temporal_refs = self._check_temporal_references(output)
        violations.extend(date_violations)
        temporal_refs_checked = temporal_refs

        # 2. Check for future knowledge indicators
        future_violations = self._check_future_knowledge_indicators(output)
        violations.extend(future_violations)

        # 3. Extract and verify numeric facts (at isolation level 2+)
        if self.isolation_level >= 2:
            numeric_violations, grounded, ungrounded = self._check_numeric_facts(output)
            violations.extend(numeric_violations)
            grounded_count = grounded
            ungrounded_count = ungrounded

        # 4. Check for ungrounded entity references (at isolation level 3)
        if self.isolation_level >= 3:
            entity_violations = self._check_entity_references(output)
            violations.extend(entity_violations)

        # 5. Calculate compliance score
        total_checks = len(violations) + grounded_count + 1  # +1 to avoid division by zero
        compliance_score = max(0.0, 1.0 - (len(violations) * 0.15))  # Each violation reduces by 15%

        # Adjust for severity
        for v in violations:
            if v.severity == "critical":
                compliance_score -= 0.2
            elif v.severity == "high":
                compliance_score -= 0.1

        compliance_score = max(0.0, min(1.0, compliance_score))

        # Determine compliance
        is_compliant = compliance_score >= 0.7 and not any(
            v.severity in ["critical", "high"] for v in violations
        )

        logger.info(
            f"OUTPUT_AUDITOR: Audited output - compliant={is_compliant}, "
            f"score={compliance_score:.2f}, violations={len(violations)}"
        )

        return AuditResult(
            is_compliant=is_compliant,
            compliance_score=compliance_score,
            violations=violations,
            grounded_facts_count=grounded_count,
            ungrounded_facts_count=ungrounded_count,
            temporal_references_checked=temporal_refs_checked,
            auditor_version=self.VERSION,
        )

    def _check_temporal_references(self, output: str) -> tuple[List[Violation], int]:
        """
        Check for references to dates after the cutoff.

        Returns:
            Tuple of (violations list, count of temporal refs checked)
        """
        violations = []
        refs_checked = 0
        cutoff_year = self.cutoff_time.year

        lines = output.split('\n')
        for line_num, line in enumerate(lines, 1):
            for pattern in self.DATE_PATTERNS:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    refs_checked += 1
                    matched_text = match.group(0)

                    # Extract year from match
                    year_match = re.search(r'20\d{2}', matched_text)
                    if year_match:
                        year = int(year_match.group(0))
                        if year > cutoff_year:
                            violations.append(Violation(
                                violation_type=ViolationType.POST_CUTOFF_REFERENCE,
                                description=f"Reference to year {year} which is after cutoff year {cutoff_year}",
                                severity="high",
                                evidence=matched_text,
                                line_number=line_num,
                                confidence=0.95,
                            ))

        return violations, refs_checked

    def _check_future_knowledge_indicators(self, output: str) -> List[Violation]:
        """
        Check for language patterns that suggest future knowledge.
        """
        violations = []
        lines = output.split('\n')

        for line_num, line in enumerate(lines, 1):
            for pattern in self.FUTURE_KNOWLEDGE_INDICATORS:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    violations.append(Violation(
                        violation_type=ViolationType.PREDICTION_FROM_KNOWLEDGE,
                        description=f"Language suggests prediction based on future knowledge",
                        severity="medium",
                        evidence=match.group(0),
                        line_number=line_num,
                        confidence=0.7,
                    ))

        return violations

    def _check_numeric_facts(self, output: str) -> tuple[List[Violation], int, int]:
        """
        Check that numeric values are grounded in manifest data.

        Returns:
            Tuple of (violations, grounded_count, ungrounded_count)
        """
        violations = []
        grounded = 0
        ungrounded = 0

        # Pattern for significant numbers (exclude small integers and percentages)
        number_pattern = r'\b(\d{1,3}(?:,\d{3})+|\d{4,}(?:\.\d+)?)\b'

        lines = output.split('\n')
        for line_num, line in enumerate(lines, 1):
            matches = re.finditer(number_pattern, line)
            for match in matches:
                number_str = match.group(0).replace(',', '')

                # Check if this number is in manifest data
                if self._is_number_in_manifest(number_str):
                    grounded += 1
                else:
                    ungrounded += 1
                    if self.strict_mode:
                        violations.append(Violation(
                            violation_type=ViolationType.NUMERIC_HALLUCINATION,
                            description=f"Numeric value '{match.group(0)}' not found in manifest data",
                            severity="medium",
                            evidence=line[:100],
                            line_number=line_num,
                            confidence=0.6,
                        ))

        return violations, grounded, ungrounded

    def _check_entity_references(self, output: str) -> List[Violation]:
        """
        Check that entity references are present in the context.

        This is a more advanced check for isolation level 3.
        """
        violations = []

        # Extract potential entity references (capitalized words/phrases)
        entity_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'

        # Known safe entities (common words that are capitalized)
        safe_entities = {
            'The', 'This', 'That', 'These', 'Those', 'Here', 'There',
            'What', 'When', 'Where', 'Why', 'How', 'Which', 'Who',
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December',
            'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday',
        }

        lines = output.split('\n')
        for line_num, line in enumerate(lines, 1):
            # Skip if line starts with the entity (likely a header or statement)
            matches = re.finditer(entity_pattern, line)
            for match in matches:
                entity = match.group(0)
                if entity not in safe_entities and not self._is_entity_in_context(entity):
                    violations.append(Violation(
                        violation_type=ViolationType.ENTITY_NOT_IN_CONTEXT,
                        description=f"Entity '{entity}' not found in context data",
                        severity="low",
                        evidence=entity,
                        line_number=line_num,
                        confidence=0.5,
                    ))

        return violations

    def _build_data_cache(self) -> Set[str]:
        """Build a set of strings from manifest data for quick lookup."""
        data_strings = set()
        for entry in self.manifest_entries:
            # Extract string representations from params and data
            data_strings.add(entry.source_name.lower())
            data_strings.add(entry.endpoint.lower())
            for key, value in entry.params.items():
                data_strings.add(str(key).lower())
                data_strings.add(str(value).lower())
        return data_strings

    def _extract_manifest_numbers(self) -> Set[str]:
        """Extract all significant numbers from manifest data."""
        numbers = set()
        # This would extract numbers from actual manifest data
        # For now, we'll return an empty set and rely on strict_mode
        return numbers

    def _is_number_in_manifest(self, number_str: str) -> bool:
        """Check if a number appears in manifest data."""
        # In a real implementation, this would check against actual data values
        # For now, we use a heuristic: numbers in manifest_numbers set
        return number_str in self._manifest_numbers

    def _is_entity_in_context(self, entity: str) -> bool:
        """Check if an entity appears in the manifest context."""
        return entity.lower() in self._data_cache if hasattr(self, '_data_cache') else entity.lower() in self._manifest_data_cache


# =============================================================================
# Factory Functions
# =============================================================================

def create_output_auditor(
    manifest_service: DataManifestService,
    cutoff_time: datetime,
    isolation_level: int = 2,
) -> OutputAuditor:
    """
    Create an OutputAuditor from a DataManifestService.

    Args:
        manifest_service: DataManifestService with collected entries
        cutoff_time: Temporal cutoff datetime
        isolation_level: Isolation strictness (1-3)

    Returns:
        Configured OutputAuditor instance
    """
    entries = manifest_service.get_entries()

    # Convert DataGateway ManifestEntry to local format if needed
    local_entries = []
    for e in entries:
        local_entries.append(ManifestEntry(
            id=e.id,
            source_name=e.source_name,
            endpoint=e.endpoint,
            params=e.params,
            params_hash=e.params_hash,
            time_window=e.time_window,
            record_count=e.record_count,
            filtered_count=e.filtered_count,
            payload_hash=e.payload_hash,
            timestamp=e.timestamp,
        ))

    return OutputAuditor(
        manifest_entries=local_entries,
        cutoff_time=cutoff_time,
        isolation_level=isolation_level,
        strict_mode=(isolation_level >= 2),
    )


async def audit_llm_response(
    response: str,
    manifest_entries: List[Dict[str, Any]],
    cutoff_time: datetime,
    isolation_level: int = 2,
) -> AuditResult:
    """
    Convenience function to audit an LLM response.

    Args:
        response: LLM response text
        manifest_entries: List of manifest entry dicts
        cutoff_time: Temporal cutoff datetime
        isolation_level: Isolation strictness

    Returns:
        AuditResult with compliance status
    """
    # Convert dicts to ManifestEntry objects
    entries = []
    for e in manifest_entries:
        entries.append(ManifestEntry(
            id=e.get('id', ''),
            source_name=e.get('source_name', ''),
            endpoint=e.get('endpoint', ''),
            params=e.get('params', {}),
            params_hash=e.get('params_hash', ''),
            time_window=e.get('time_window'),
            record_count=e.get('record_count', 0),
            filtered_count=e.get('filtered_count', 0),
            payload_hash=e.get('payload_hash', ''),
            timestamp=e.get('timestamp', datetime.utcnow()),
        ))

    auditor = OutputAuditor(
        manifest_entries=entries,
        cutoff_time=cutoff_time,
        isolation_level=isolation_level,
    )

    return auditor.audit_output(response)
