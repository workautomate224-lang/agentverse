"""
STEP 3: Persona Validation Service

Generates validation reports for persona sets, analyzing:
- Coverage gaps (missing demographic segments)
- Duplication analysis (overlapping personas)
- Bias risk (over/under-representation)
- Uncertainty warnings (data quality issues)
- Recommendations for improvement

This service ensures that persona sets used in simulations are:
- Representative of target populations
- Free from systematic biases
- Sufficient for reliable outcome predictions
"""

import hashlib
import json
import uuid
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.persona import (
    CENSUS_AGE_BRACKETS,
    CENSUS_INCOME_BRACKETS,
    CENSUS_EDUCATION_LEVELS,
)


# Expected segment distributions for bias detection
EXPECTED_AGE_DISTRIBUTION = {
    "18-24": 0.12,
    "25-34": 0.18,
    "35-44": 0.17,
    "45-54": 0.17,
    "55-64": 0.16,
    "65+": 0.20,
}

EXPECTED_INCOME_DISTRIBUTION = {
    "Under $25,000": 0.20,
    "$25,000 - $50,000": 0.22,
    "$50,000 - $75,000": 0.17,
    "$75,000 - $100,000": 0.12,
    "$100,000 - $150,000": 0.14,
    "Over $150,000": 0.15,
}

EXPECTED_GENDER_DISTRIBUTION = {
    "Male": 0.49,
    "Female": 0.50,
    "Non-binary": 0.01,
}


class PersonaValidationService:
    """
    STEP 3: Validates persona sets and generates quality reports.

    The validation report is stored in the database and referenced
    by PersonaSnapshot for confidence calculations.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def validate_persona_set(
        self,
        tenant_id: str,
        project_id: str,
        template_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Validate all active personas in a project and generate a report.

        Returns:
            Complete validation report with all analysis results
        """
        # Load active personas
        persona_query = text("""
            SELECT id, label, demographics, preferences, perception_weights,
                   bias_parameters, action_priors, uncertainty_score
            FROM personas
            WHERE project_id = :project_id AND is_active = true
        """)
        result = await self.db.execute(persona_query, {"project_id": project_id})
        persona_rows = result.fetchall()

        if not persona_rows:
            return self._empty_report(tenant_id, template_id)

        # Convert to list of dicts
        personas = []
        for row in persona_rows:
            personas.append({
                "id": str(row.id),
                "label": row.label,
                "demographics": row.demographics or {},
                "preferences": row.preferences or {},
                "perception_weights": row.perception_weights or {},
                "bias_parameters": row.bias_parameters or {},
                "action_priors": row.action_priors or {},
                "uncertainty_score": row.uncertainty_score or 0.5,
            })

        # Run validation analyses
        coverage_gaps = self._analyze_coverage_gaps(personas)
        duplication_analysis = self._analyze_duplication(personas)
        bias_risk = self._analyze_bias_risk(personas)
        uncertainty_warnings = self._analyze_uncertainty(personas)
        statistics = self._compute_statistics(personas)
        recommendations = self._generate_recommendations(
            coverage_gaps, duplication_analysis, bias_risk, uncertainty_warnings
        )

        # Compute overall score (0-100)
        overall_score = self._compute_overall_score(
            coverage_gaps, duplication_analysis, bias_risk, uncertainty_warnings
        )

        # Compute confidence impact (-1.0 to +1.0)
        confidence_impact = self._compute_confidence_impact(overall_score)

        # Create validation report
        report_id = uuid.uuid4()
        report = {
            "id": str(report_id),
            "tenant_id": tenant_id,
            "template_id": template_id,
            "status": "completed",
            "overall_score": overall_score,
            "coverage_gaps": coverage_gaps,
            "duplication_analysis": duplication_analysis,
            "bias_risk": bias_risk,
            "uncertainty_warnings": uncertainty_warnings,
            "statistics": statistics,
            "recommendations": recommendations,
            "confidence_impact": confidence_impact,
            "created_at": datetime.utcnow().isoformat(),
        }

        # Store in database
        await self._store_report(report)

        return report

    def _analyze_coverage_gaps(self, personas: List[Dict]) -> Dict[str, Any]:
        """
        Identify missing demographic segments.

        STEP 3: Coverage gaps reduce confidence in simulation predictions
        because important population segments may be unrepresented.
        """
        total = len(personas)
        if total == 0:
            return {"status": "error", "message": "No personas to analyze"}

        # Analyze age coverage
        age_counts = Counter()
        for p in personas:
            age = p.get("demographics", {}).get("age_bracket") or p.get("demographics", {}).get("age")
            if isinstance(age, int):
                age = self._age_to_bracket(age)
            age_counts[age] += 1

        missing_ages = [b for b in CENSUS_AGE_BRACKETS if age_counts.get(b, 0) == 0]
        underrepresented_ages = [
            b for b in CENSUS_AGE_BRACKETS
            if 0 < age_counts.get(b, 0) < total * 0.05  # Less than 5% representation
        ]

        # Analyze income coverage
        income_counts = Counter()
        for p in personas:
            income = p.get("demographics", {}).get("income_bracket") or p.get("demographics", {}).get("income")
            income_counts[income] += 1

        missing_incomes = [b for b in CENSUS_INCOME_BRACKETS if income_counts.get(b, 0) == 0]

        # Analyze education coverage
        education_counts = Counter()
        for p in personas:
            edu = p.get("demographics", {}).get("education_level") or p.get("demographics", {}).get("education")
            education_counts[edu] += 1

        missing_education = [b for b in CENSUS_EDUCATION_LEVELS if education_counts.get(b, 0) == 0]

        # Calculate coverage score
        total_expected = len(CENSUS_AGE_BRACKETS) + len(CENSUS_INCOME_BRACKETS) + len(CENSUS_EDUCATION_LEVELS)
        total_missing = len(missing_ages) + len(missing_incomes) + len(missing_education)
        coverage_score = max(0, 100 - (total_missing / total_expected * 100))

        return {
            "coverage_score": round(coverage_score, 1),
            "missing_segments": {
                "age_brackets": missing_ages,
                "income_brackets": missing_incomes,
                "education_levels": missing_education,
            },
            "underrepresented_segments": {
                "age_brackets": underrepresented_ages,
            },
            "total_missing": total_missing,
            "total_expected": total_expected,
        }

    def _analyze_duplication(self, personas: List[Dict]) -> Dict[str, Any]:
        """
        Detect duplicate or highly similar personas.

        STEP 3: High duplication reduces diversity and can bias outcomes
        toward certain persona types.
        """
        total = len(personas)
        if total < 2:
            return {"duplication_rate": 0.0, "duplicate_groups": [], "status": "ok"}

        # Hash each persona's demographic profile
        profile_hashes = {}
        duplicate_groups = []

        for p in personas:
            demo = p.get("demographics", {})
            # Create a normalized profile string
            profile_key = f"{demo.get('age_bracket', demo.get('age', ''))}|{demo.get('gender', '')}|{demo.get('income_bracket', demo.get('income', ''))}|{demo.get('education_level', demo.get('education', ''))}"

            if profile_key in profile_hashes:
                profile_hashes[profile_key].append(p["id"])
            else:
                profile_hashes[profile_key] = [p["id"]]

        # Find groups with more than one persona
        for profile_key, ids in profile_hashes.items():
            if len(ids) > 1:
                duplicate_groups.append({
                    "profile": profile_key,
                    "count": len(ids),
                    "persona_ids": ids[:5],  # Limit to first 5 for display
                })

        # Calculate duplication rate
        duplicated_personas = sum(len(g["persona_ids"]) - 1 for g in duplicate_groups)
        duplication_rate = duplicated_personas / total * 100 if total > 0 else 0

        return {
            "duplication_rate": round(duplication_rate, 1),
            "duplicate_groups": duplicate_groups[:10],  # Limit to top 10 groups
            "unique_profiles": len(profile_hashes),
            "total_personas": total,
            "status": "warning" if duplication_rate > 20 else "ok",
        }

    def _analyze_bias_risk(self, personas: List[Dict]) -> Dict[str, Any]:
        """
        Detect over/under-representation compared to expected distributions.

        STEP 3: Bias risk indicates that simulation outcomes may not
        generalize to real-world populations.
        """
        total = len(personas)
        if total == 0:
            return {"bias_score": 100, "biases": [], "status": "error"}

        biases = []

        # Check age distribution bias
        age_counts = Counter()
        for p in personas:
            age = p.get("demographics", {}).get("age_bracket") or p.get("demographics", {}).get("age")
            if isinstance(age, int):
                age = self._age_to_bracket(age)
            age_counts[age] += 1

        for bracket, expected in EXPECTED_AGE_DISTRIBUTION.items():
            actual = age_counts.get(bracket, 0) / total
            deviation = abs(actual - expected) / expected * 100 if expected > 0 else 0
            if deviation > 50:  # More than 50% deviation
                biases.append({
                    "dimension": "age",
                    "segment": bracket,
                    "expected": round(expected * 100, 1),
                    "actual": round(actual * 100, 1),
                    "deviation": round(deviation, 1),
                    "direction": "over" if actual > expected else "under",
                })

        # Check gender distribution bias
        gender_counts = Counter()
        for p in personas:
            gender = p.get("demographics", {}).get("gender", "Unknown")
            gender_counts[gender] += 1

        for gender, expected in EXPECTED_GENDER_DISTRIBUTION.items():
            actual = gender_counts.get(gender, 0) / total
            deviation = abs(actual - expected) / expected * 100 if expected > 0 else 0
            if deviation > 30:  # More than 30% deviation
                biases.append({
                    "dimension": "gender",
                    "segment": gender,
                    "expected": round(expected * 100, 1),
                    "actual": round(actual * 100, 1),
                    "deviation": round(deviation, 1),
                    "direction": "over" if actual > expected else "under",
                })

        # Calculate overall bias score (lower is better, so invert for user display)
        avg_deviation = sum(b["deviation"] for b in biases) / len(biases) if biases else 0
        bias_score = max(0, 100 - avg_deviation)

        return {
            "bias_score": round(bias_score, 1),
            "biases": biases[:10],  # Limit to top 10 biases
            "total_biases_detected": len(biases),
            "status": "critical" if bias_score < 50 else "warning" if bias_score < 70 else "ok",
        }

    def _analyze_uncertainty(self, personas: List[Dict]) -> Dict[str, Any]:
        """
        Identify data quality issues that increase prediction uncertainty.

        STEP 3: High uncertainty scores indicate personas with incomplete
        or low-quality data.
        """
        total = len(personas)
        if total == 0:
            return {"uncertainty_level": "unknown", "warnings": [], "status": "error"}

        warnings = []
        high_uncertainty_count = 0
        missing_data_count = 0

        for p in personas:
            uncertainty = p.get("uncertainty_score", 0.5)
            if uncertainty > 0.7:
                high_uncertainty_count += 1

            # Check for missing key fields
            demo = p.get("demographics", {})
            required_fields = ["age", "age_bracket", "gender", "income", "income_bracket"]
            missing = [f for f in required_fields if not demo.get(f)]
            if len(missing) >= 3:
                missing_data_count += 1

        # Generate warnings
        if high_uncertainty_count > total * 0.2:
            warnings.append({
                "type": "high_uncertainty",
                "message": f"{high_uncertainty_count} personas ({round(high_uncertainty_count/total*100, 1)}%) have high uncertainty scores",
                "severity": "medium",
            })

        if missing_data_count > total * 0.1:
            warnings.append({
                "type": "missing_data",
                "message": f"{missing_data_count} personas ({round(missing_data_count/total*100, 1)}%) are missing key demographic data",
                "severity": "high",
            })

        if total < 30:
            warnings.append({
                "type": "small_sample",
                "message": f"Only {total} personas. Recommend at least 30 for reliable predictions",
                "severity": "medium",
            })

        # Calculate uncertainty level
        uncertainty_pct = (high_uncertainty_count + missing_data_count) / (total * 2) * 100
        uncertainty_level = (
            "high" if uncertainty_pct > 30 else
            "medium" if uncertainty_pct > 15 else
            "low"
        )

        return {
            "uncertainty_level": uncertainty_level,
            "high_uncertainty_personas": high_uncertainty_count,
            "missing_data_personas": missing_data_count,
            "warnings": warnings,
            "status": "critical" if uncertainty_level == "high" else "warning" if uncertainty_level == "medium" else "ok",
        }

    def _compute_statistics(self, personas: List[Dict]) -> Dict[str, Any]:
        """Compute summary statistics for the persona set."""
        total = len(personas)

        # Age statistics
        ages = []
        for p in personas:
            age = p.get("demographics", {}).get("age")
            if isinstance(age, int):
                ages.append(age)

        avg_age = sum(ages) / len(ages) if ages else None
        min_age = min(ages) if ages else None
        max_age = max(ages) if ages else None

        # Segment counts
        segments = Counter()
        for p in personas:
            demo = p.get("demographics", {})
            segment = demo.get("segment", demo.get("income_bracket", "Unknown"))
            segments[segment] += 1

        return {
            "total_personas": total,
            "age_statistics": {
                "mean": round(avg_age, 1) if avg_age else None,
                "min": min_age,
                "max": max_age,
            },
            "segment_distribution": dict(segments),
            "unique_segments": len(segments),
        }

    def _generate_recommendations(
        self,
        coverage_gaps: Dict,
        duplication: Dict,
        bias_risk: Dict,
        uncertainty: Dict,
    ) -> List[Dict[str, str]]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []

        # Coverage recommendations
        missing = coverage_gaps.get("missing_segments", {})
        if missing.get("age_brackets"):
            recommendations.append({
                "priority": "high",
                "category": "coverage",
                "action": f"Add personas for missing age brackets: {', '.join(missing['age_brackets'])}",
            })

        if missing.get("income_brackets"):
            recommendations.append({
                "priority": "medium",
                "category": "coverage",
                "action": f"Add personas for missing income brackets: {', '.join(missing['income_brackets'][:3])}",
            })

        # Duplication recommendations
        if duplication.get("duplication_rate", 0) > 20:
            recommendations.append({
                "priority": "medium",
                "category": "diversity",
                "action": f"Reduce duplicate profiles. Current duplication rate: {duplication['duplication_rate']}%",
            })

        # Bias recommendations
        if bias_risk.get("total_biases_detected", 0) > 3:
            recommendations.append({
                "priority": "high",
                "category": "representation",
                "action": "Rebalance persona set to better match expected population distribution",
            })

        # Uncertainty recommendations
        if uncertainty.get("uncertainty_level") == "high":
            recommendations.append({
                "priority": "high",
                "category": "data_quality",
                "action": "Improve data quality for high-uncertainty personas or replace with better data",
            })

        if uncertainty.get("warnings"):
            for warning in uncertainty["warnings"][:2]:
                if warning.get("severity") == "high":
                    recommendations.append({
                        "priority": "high",
                        "category": "data_quality",
                        "action": warning["message"],
                    })

        return recommendations[:5]  # Limit to top 5 recommendations

    def _compute_overall_score(
        self,
        coverage_gaps: Dict,
        duplication: Dict,
        bias_risk: Dict,
        uncertainty: Dict,
    ) -> float:
        """Compute overall validation score (0-100)."""
        coverage_score = coverage_gaps.get("coverage_score", 50)
        duplication_score = max(0, 100 - duplication.get("duplication_rate", 0) * 2)
        bias_score = bias_risk.get("bias_score", 50)

        uncertainty_level = uncertainty.get("uncertainty_level", "medium")
        uncertainty_score = {"low": 100, "medium": 70, "high": 40}.get(uncertainty_level, 50)

        # Weighted average
        overall = (
            coverage_score * 0.30 +
            duplication_score * 0.20 +
            bias_score * 0.30 +
            uncertainty_score * 0.20
        )

        return round(overall, 1)

    def _compute_confidence_impact(self, overall_score: float) -> float:
        """Compute confidence impact for outcome calculations."""
        # Map score to impact: 0-50 -> -0.3 to 0, 50-100 -> 0 to +0.2
        if overall_score < 50:
            return round((overall_score - 50) / 50 * 0.3, 3)
        else:
            return round((overall_score - 50) / 50 * 0.2, 3)

    def _age_to_bracket(self, age: int) -> str:
        """Convert numeric age to bracket string."""
        if age < 25:
            return "18-24"
        elif age < 35:
            return "25-34"
        elif age < 45:
            return "35-44"
        elif age < 55:
            return "45-54"
        elif age < 65:
            return "55-64"
        else:
            return "65+"

    def _empty_report(self, tenant_id: str, template_id: Optional[str]) -> Dict[str, Any]:
        """Generate report for empty persona set."""
        return {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "template_id": template_id,
            "status": "completed",
            "overall_score": 0.0,
            "coverage_gaps": {"status": "error", "message": "No personas to analyze"},
            "duplication_analysis": {"status": "error", "message": "No personas to analyze"},
            "bias_risk": {"status": "error", "message": "No personas to analyze"},
            "uncertainty_warnings": {"status": "error", "message": "No personas to analyze"},
            "statistics": {"total_personas": 0},
            "recommendations": [{
                "priority": "critical",
                "category": "setup",
                "action": "Generate or import personas before running validation",
            }],
            "confidence_impact": -0.5,
            "created_at": datetime.utcnow().isoformat(),
        }

    async def _store_report(self, report: Dict[str, Any]) -> None:
        """Store validation report in database."""
        insert_sql = text("""
            INSERT INTO persona_validation_reports (
                id, tenant_id, template_id, status, overall_score,
                coverage_gaps, duplication_analysis, bias_risk,
                uncertainty_warnings, statistics, recommendations,
                confidence_impact, created_at, updated_at
            ) VALUES (
                :id, :tenant_id, :template_id, :status, :overall_score,
                :coverage_gaps, :duplication_analysis, :bias_risk,
                :uncertainty_warnings, :statistics, :recommendations,
                :confidence_impact, :created_at, :updated_at
            )
        """)

        now = datetime.utcnow()
        await self.db.execute(insert_sql, {
            "id": uuid.UUID(report["id"]),
            "tenant_id": uuid.UUID(report["tenant_id"]),
            "template_id": uuid.UUID(report["template_id"]) if report.get("template_id") else None,
            "status": report["status"],
            "overall_score": report["overall_score"],
            "coverage_gaps": json.dumps(report["coverage_gaps"]),
            "duplication_analysis": json.dumps(report["duplication_analysis"]),
            "bias_risk": json.dumps(report["bias_risk"]),
            "uncertainty_warnings": json.dumps(report["uncertainty_warnings"]),
            "statistics": json.dumps(report.get("statistics", {})),
            "recommendations": json.dumps(report["recommendations"]),
            "confidence_impact": report["confidence_impact"],
            "created_at": now,
            "updated_at": now,
        })


async def get_persona_validation_service(db: AsyncSession) -> PersonaValidationService:
    """Factory function for PersonaValidationService."""
    return PersonaValidationService(db)
