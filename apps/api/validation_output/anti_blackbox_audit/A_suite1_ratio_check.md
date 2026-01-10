# Suite 1: Ratio Sanity Check

## Run Configurations

### LOW (Run A - Small Scale)
- **agent_count:** 10
- **step_count:** 10
- **replicate_count:** 3
- **run_id:** 92f6d388-5163-47eb-a4af-71f7cf9bfe1c

### HIGH (Run B - Large Scale)
- **agent_count:** 200
- **step_count:** 30
- **replicate_count:** 10
- **run_id:** 0940e2e3-9824-41c9-8c8e-137f81c22185

---

## Ratio Calculations

### LLM Call Ratio

**Formula:** `LLM_calls = agent_count * step_count * replicate_count`

| Run | Calculation | Result |
|-----|-------------|--------|
| LOW | 10 * 10 * 3 | **300** |
| HIGH | 200 * 30 * 10 | **60,000** |

**Expected LLM Ratio:** 60,000 / 300 = **200.0x**

**Observed LLM Ratio:** **200.0x**

**LLM Ratio Match:** EXACT MATCH

---

### Trace Event Ratio

**Formula:** `Trace_events = R * (2 + S + A*S) + 3`

Where:
- R = replicate_count
- S = step_count
- A = agent_count

Breakdown:
- 1 RUN_STARTED event
- Per replicate: 1 REPLICATE_START + S WORLD_TICK + (A*S) AGENT_STEP + 1 REPLICATE_DONE
- 1 AGGREGATE event
- 1 RUN_DONE event

| Run | Calculation | Result |
|-----|-------------|--------|
| LOW | 3 * (2 + 10 + 10*10) + 3 = 3 * 112 + 3 | **339** |
| HIGH | 10 * (2 + 30 + 200*30) + 3 = 10 * 6032 + 3 | **60,323** |

**Expected Trace Ratio:** 60,323 / 339 = **177.945x**

**Observed Trace Ratio:** **177.9x**

**Trace Ratio Match:** EXACT MATCH (within rounding)

---

## Ratio Mismatch Explanation

### Why is LLM ratio (200x) different from trace ratio (177.9x)?

The ratios differ because:

1. **LLM calls scale linearly with A*S*R:**
   - Formula: `agent_count * step_count * replicate_count`
   - HIGH/LOW = (200*30*10) / (10*10*3) = 60000/300 = **200x**

2. **Trace events include overhead events that don't scale with agents:**
   - Per-replicate overhead: 2 events (REPLICATE_START + REPLICATE_DONE)
   - Per-step overhead: 1 event (WORLD_TICK)
   - Global overhead: 3 events (RUN_STARTED + AGGREGATE + RUN_DONE)

3. **Mathematical breakdown:**
   - Pure agent-scaling component: (200*30*10)/(10*10*3) = 200x
   - Overhead dilutes the ratio because LOW has proportionally more overhead relative to its agent events

### Definition of Ratio Used
- **Trace ratio:** total_trace_events_HIGH / total_trace_events_LOW
- **LLM ratio:** total_llm_calls_HIGH / total_llm_calls_LOW

### Step/Replicate Changes Between Runs
| Parameter | LOW | HIGH | Scale Factor |
|-----------|-----|------|--------------|
| agent_count | 10 | 200 | 20x |
| step_count | 10 | 30 | 3x |
| replicate_count | 3 | 10 | 3.33x |

**Combined scale factor:** 20 * 3 * 3.33 = **200x** (matches LLM ratio)

### Cache Stats
- No caching detected in LLM ledger
- All entries have `cache_hit: false` or `mock: true`
- Cache does not affect ratio calculations

---

## Final Conclusion

| Check | Expected | Observed | Status |
|-------|----------|----------|--------|
| LLM Ratio | 200.0x | 200.0x | PASS |
| Trace Ratio | 177.9x | 177.9x | PASS |
| Ratio Difference Explained | Yes | Yes | PASS |

**final_conclusion: PASS**

The observed ratios are 100% consistent with the manifests:
1. LLM ratio of 200.0x exactly matches the scaling factor of configurations
2. Trace ratio of 177.9x is mathematically correct given the overhead events
3. The difference between trace ratio and LLM ratio is fully explained by the non-scaling overhead events in the trace formula
