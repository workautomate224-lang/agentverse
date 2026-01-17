-- Slice 1A Database Verification Queries
-- Run these against the staging database to verify LLM provenance

-- ============================================
-- A. PIL Jobs Table - Check job status and provenance
-- ============================================
SELECT
  id,
  job_type,
  status,
  progress_percent,
  result->'llm_proof'->'goal_analysis'->>'provider' as provider,
  result->'llm_proof'->'goal_analysis'->>'model' as model,
  result->'llm_proof'->'goal_analysis'->>'cache_hit' as cache_hit,
  result->'llm_proof'->'goal_analysis'->>'fallback_used' as fallback_used,
  result->'llm_proof'->'goal_analysis'->>'fallback_attempts' as fallback_attempts,
  result->'llm_proof'->'goal_analysis'->>'cost_usd' as cost_usd,
  error_message,
  created_at
FROM pil_jobs
WHERE job_type = 'goal_analysis'
ORDER BY created_at DESC
LIMIT 10;

-- ============================================
-- B. LLM Calls Table - Verify actual LLM calls
-- ============================================
SELECT
  id,
  profile_key,
  model_used,
  status,
  cache_hit,
  input_tokens,
  output_tokens,
  cost_usd,
  latency_ms,
  created_at
FROM llm_calls
WHERE profile_key LIKE 'PIL_%'
ORDER BY created_at DESC
LIMIT 20;

-- ============================================
-- C. Specific Job Verification (replace UUID)
-- ============================================
-- Job ID from evidence: 40af691c-1c26-4ab6-b0bb-f6b912accde8

SELECT
  id,
  job_type,
  status,
  jsonb_pretty(result->'llm_proof') as llm_proof_formatted
FROM pil_jobs
WHERE id = '40af691c-1c26-4ab6-b0bb-f6b912accde8';

-- ============================================
-- D. Verify No Failed Jobs Without Error Messages
-- ============================================
SELECT
  id,
  job_type,
  status,
  error_message,
  result->'llm_proof' IS NOT NULL as has_llm_proof
FROM pil_jobs
WHERE status = 'failed'
  AND error_message IS NULL
ORDER BY created_at DESC
LIMIT 5;

-- Expected: 0 rows (failed jobs should always have error_message)

-- ============================================
-- E. Verify All Successful Jobs Have LLM Proof
-- ============================================
SELECT
  id,
  job_type,
  status,
  result->'llm_proof' IS NOT NULL as has_llm_proof,
  result->'llm_proof'->'goal_analysis'->>'provider' as provider
FROM pil_jobs
WHERE job_type = 'goal_analysis'
  AND status = 'succeeded'
  AND (result->'llm_proof' IS NULL OR result->'llm_proof'->'goal_analysis' IS NULL)
ORDER BY created_at DESC
LIMIT 5;

-- Expected: 0 rows (all succeeded jobs should have llm_proof)

-- ============================================
-- F. Model Verification - Check for Non-GPT-5.2 Models
-- ============================================
SELECT
  id,
  profile_key,
  model_used,
  status,
  created_at
FROM llm_calls
WHERE profile_key LIKE 'PIL_%'
  AND model_used != 'openai/gpt-5.2'
ORDER BY created_at DESC
LIMIT 10;

-- Expected: 0 rows (all PIL calls should use gpt-5.2)
