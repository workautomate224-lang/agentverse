# C: Reproducibility Audit - Outcome Comparison

## Configuration
- **Seed:** 42
- **Agent Count:** 5
- **Step Count:** 5
- **Replicate Count:** 2

## Run IDs
- **Run 1:** 6ab8769f-308c-460c-9f06-51fd5b0494bb
- **Run 2:** c777358d-f505-4483-93de-0258b42b4391

## Outcome Distribution

### Run 1
| Decision | Count |
|----------|-------|
| approve | 14 |
| reject | 16 |
| defer | 20 |

### Run 2
| Decision | Count |
|----------|-------|
| approve | 14 |
| reject | 16 |
| defer | 20 |

## Event Counts

| Metric | Run 1 | Run 2 | Match |
|--------|-------|-------|-------|
| Trace Events | 67 | 67 | YES |
| LLM Ledger Calls | 50 | 50 | YES |

## Reproducibility Check

| Check | Status |
|-------|--------|
| Outcome distributions match | YES |
| Trace event counts match | YES |
| Ledger call counts match | YES |

## Tolerance Definition
Outputs are **IDENTICAL** - no tolerance needed.

## Final Conclusion: **PASS**

Reproducibility test PASSED - same seed produces identical outputs.
