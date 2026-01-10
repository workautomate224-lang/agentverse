# B3: REP Corruption Test Details

## Test Description
This test verifies that the REP validation system correctly detects when required files are missing or corrupted.

## Procedure
1. Selected an existing REP directory
2. Backed up trace.ndjson
3. Deleted trace.ndjson
4. Ran REP validation
5. Verified validation failed with appropriate error
6. Restored backup

## Result
**Status:** FAILED_AS_EXPECTED
**Error Code:** REP_VALIDATION_ERROR
**Error Message:** Missing trace.ndjson

## Conclusion: **PASS**
