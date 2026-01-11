#!/usr/bin/env python3
"""
Alpha Ops Sampler Script for Step 5 Internal Alpha Prep

This script:
1. Samples 5 random runs per day from the staging environment
2. Downloads and validates REP artifacts
3. Generates weekly failure summary reports
4. Outputs structured JSON for monitoring

Usage:
    python alpha_ops_sampler.py --mode daily
    python alpha_ops_sampler.py --mode weekly --output-dir ./reports

Environment Variables:
    STAGING_API_URL: Staging API URL
    STAGING_OPS_API_KEY: API key for ops endpoints
    DATABASE_URL: PostgreSQL connection string (for direct queries)
"""

import os
import sys
import json
import random
import asyncio
import argparse
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
from uuid import UUID
from dataclasses import dataclass, asdict
import httpx

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SampledRun:
    """A sampled run with validation results."""
    run_id: str
    project_id: str
    user_id: str
    status: str
    created_at: str
    ended_at: Optional[str]
    rep_valid: bool
    rep_files: List[str]
    rep_missing: List[str]
    llm_call_count: int
    token_count: int
    error_message: Optional[str]
    validation_errors: List[str]


@dataclass
class DailySample:
    """Daily sampling result."""
    sample_date: str
    runs_sampled: int
    runs_valid: int
    runs_invalid: int
    total_llm_calls: int
    total_tokens: int
    runs: List[SampledRun]


@dataclass
class WeeklySummary:
    """Weekly failure summary."""
    week_start: str
    week_end: str
    total_runs_sampled: int
    total_runs_valid: int
    total_runs_invalid: int
    failure_rate: float
    common_failures: Dict[str, int]
    daily_samples: List[DailySample]
    recommendations: List[str]


class AlphaOpsSampler:
    """Sampler for alpha ops validation."""

    REQUIRED_REP_FILES = [
        "manifest.json",
        "trace.ndjson",
        "llm_ledger.ndjson",
        "universe_graph.json",
        "report.md"
    ]

    def __init__(
        self,
        api_url: str,
        api_key: str,
        output_dir: Path
    ):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Make API request with auth."""
        async with httpx.AsyncClient(timeout=60) as client:
            headers = kwargs.pop('headers', {})
            headers['X-API-Key'] = self.api_key

            response = await client.request(
                method,
                f"{self.api_url}{endpoint}",
                headers=headers,
                **kwargs
            )
            response.raise_for_status()
            return response.json()

    async def get_runs_for_date(
        self,
        date: datetime
    ) -> List[Dict[str, Any]]:
        """Get all runs for a specific date."""
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

        try:
            result = await self._make_request(
                'GET',
                '/api/v1/ops/runs',
                params={
                    'created_after': start.isoformat(),
                    'created_before': end.isoformat(),
                    'limit': 1000
                }
            )
            return result.get('runs', [])
        except Exception as e:
            logger.warning(f"Could not fetch runs: {e}")
            return []

    async def validate_run_rep(
        self,
        run_id: str
    ) -> Dict[str, Any]:
        """Validate REP files for a run."""
        validation = {
            'valid': False,
            'files_found': [],
            'files_missing': [],
            'llm_call_count': 0,
            'token_count': 0,
            'errors': []
        }

        try:
            # Get REP manifest
            manifest = await self._make_request(
                'GET',
                f'/api/v1/ops/runs/{run_id}/rep/manifest'
            )

            files = manifest.get('files', [])
            validation['files_found'] = files

            for required in self.REQUIRED_REP_FILES:
                if required not in files:
                    validation['files_missing'].append(required)

            # Get LLM ledger stats
            if 'llm_ledger.ndjson' in files:
                try:
                    ledger = await self._make_request(
                        'GET',
                        f'/api/v1/ops/runs/{run_id}/rep/llm_ledger'
                    )
                    validation['llm_call_count'] = ledger.get('call_count', 0)
                    validation['token_count'] = ledger.get('total_tokens', 0)
                except Exception:
                    pass

            if not validation['files_missing']:
                validation['valid'] = True

        except httpx.HTTPStatusError as e:
            validation['errors'].append(f"HTTP {e.response.status_code}")
        except Exception as e:
            validation['errors'].append(str(e))

        return validation

    async def sample_runs(
        self,
        date: datetime,
        sample_size: int = 5
    ) -> DailySample:
        """Sample runs for a given date."""
        logger.info(f"Sampling runs for {date.strftime('%Y-%m-%d')}")

        runs = await self.get_runs_for_date(date)
        logger.info(f"Found {len(runs)} runs for the day")

        # Sample random runs
        if len(runs) > sample_size:
            sampled = random.sample(runs, sample_size)
        else:
            sampled = runs

        sampled_runs = []
        total_llm = 0
        total_tokens = 0
        valid_count = 0

        for run in sampled:
            run_id = run.get('id', run.get('run_id', 'unknown'))
            logger.info(f"Validating run {run_id}")

            rep_validation = await self.validate_run_rep(run_id)

            sampled_run = SampledRun(
                run_id=run_id,
                project_id=run.get('project_id', 'unknown'),
                user_id=run.get('user_id', 'unknown'),
                status=run.get('status', 'unknown'),
                created_at=run.get('created_at', ''),
                ended_at=run.get('ended_at'),
                rep_valid=rep_validation['valid'],
                rep_files=rep_validation['files_found'],
                rep_missing=rep_validation['files_missing'],
                llm_call_count=rep_validation['llm_call_count'],
                token_count=rep_validation['token_count'],
                error_message=run.get('error_message'),
                validation_errors=rep_validation['errors']
            )

            sampled_runs.append(sampled_run)
            total_llm += sampled_run.llm_call_count
            total_tokens += sampled_run.token_count
            if sampled_run.rep_valid:
                valid_count += 1

        return DailySample(
            sample_date=date.strftime('%Y-%m-%d'),
            runs_sampled=len(sampled_runs),
            runs_valid=valid_count,
            runs_invalid=len(sampled_runs) - valid_count,
            total_llm_calls=total_llm,
            total_tokens=total_tokens,
            runs=[asdict(r) for r in sampled_runs]
        )

    async def generate_weekly_summary(
        self,
        week_start: datetime
    ) -> WeeklySummary:
        """Generate weekly failure summary."""
        logger.info(f"Generating weekly summary starting {week_start.strftime('%Y-%m-%d')}")

        daily_samples = []
        failure_reasons = {}

        for day_offset in range(7):
            date = week_start + timedelta(days=day_offset)
            sample = await self.sample_runs(date)
            daily_samples.append(asdict(sample))

            # Track failure reasons
            for run in sample.runs:
                if not run.rep_valid:
                    for missing in run.rep_missing:
                        failure_reasons[f"missing_{missing}"] = (
                            failure_reasons.get(f"missing_{missing}", 0) + 1
                        )
                    for error in run.validation_errors:
                        failure_reasons[error] = failure_reasons.get(error, 0) + 1

        # Calculate totals
        total_sampled = sum(s['runs_sampled'] for s in daily_samples)
        total_valid = sum(s['runs_valid'] for s in daily_samples)
        total_invalid = sum(s['runs_invalid'] for s in daily_samples)
        failure_rate = (total_invalid / total_sampled * 100) if total_sampled > 0 else 0

        # Generate recommendations
        recommendations = []
        if failure_rate > 10:
            recommendations.append(
                f"High failure rate ({failure_rate:.1f}%) - investigate common failures"
            )
        if 'missing_llm_ledger.ndjson' in failure_reasons:
            recommendations.append(
                "LLM ledger missing in some runs - check LLM logging"
            )
        if 'missing_trace.ndjson' in failure_reasons:
            recommendations.append(
                "Trace files missing - check event logging"
            )
        if not recommendations:
            recommendations.append("All metrics within acceptable range")

        week_end = week_start + timedelta(days=6)

        return WeeklySummary(
            week_start=week_start.strftime('%Y-%m-%d'),
            week_end=week_end.strftime('%Y-%m-%d'),
            total_runs_sampled=total_sampled,
            total_runs_valid=total_valid,
            total_runs_invalid=total_invalid,
            failure_rate=round(failure_rate, 2),
            common_failures=failure_reasons,
            daily_samples=daily_samples,
            recommendations=recommendations
        )

    def save_report(
        self,
        data: Dict[str, Any],
        filename: str
    ) -> Path:
        """Save report to output directory."""
        output_path = self.output_dir / filename
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"Report saved to {output_path}")
        return output_path

    async def run_daily(self) -> Path:
        """Run daily sampling."""
        today = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        yesterday = today - timedelta(days=1)

        sample = await self.sample_runs(yesterday)
        filename = f"daily_sample_{yesterday.strftime('%Y%m%d')}.json"

        return self.save_report(asdict(sample), filename)

    async def run_weekly(self) -> Path:
        """Run weekly summary."""
        today = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        # Start from last Monday
        days_since_monday = today.weekday()
        last_monday = today - timedelta(days=days_since_monday + 7)

        summary = await self.generate_weekly_summary(last_monday)
        filename = f"weekly_summary_{last_monday.strftime('%Y%m%d')}.json"

        return self.save_report(asdict(summary), filename)


async def main():
    parser = argparse.ArgumentParser(
        description='Alpha Ops Sampler for AgentVerse'
    )
    parser.add_argument(
        '--mode',
        choices=['daily', 'weekly'],
        required=True,
        help='Sampling mode'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('./alpha_ops_reports'),
        help='Output directory for reports'
    )
    parser.add_argument(
        '--api-url',
        default=os.getenv('STAGING_API_URL', 'https://agentverse-api-staging-production.up.railway.app'),
        help='Staging API URL'
    )
    parser.add_argument(
        '--api-key',
        default=os.getenv('STAGING_OPS_API_KEY', ''),
        help='API key for ops endpoints'
    )

    args = parser.parse_args()

    if not args.api_key:
        logger.error("STAGING_OPS_API_KEY required")
        sys.exit(1)

    sampler = AlphaOpsSampler(
        api_url=args.api_url,
        api_key=args.api_key,
        output_dir=args.output_dir
    )

    if args.mode == 'daily':
        report_path = await sampler.run_daily()
    else:
        report_path = await sampler.run_weekly()

    print(f"Report generated: {report_path}")


if __name__ == '__main__':
    asyncio.run(main())
