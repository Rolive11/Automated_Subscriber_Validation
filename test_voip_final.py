#!/usr/bin/env python3
"""Final VoIP validation test."""

import sys
import pandas as pd
sys.path.insert(0, '/Users/robertolive/Documents/RSI_Projects/Automated_Subscriber_Validation')

from src.validation.general import validate_general_columns

# Create test dataframe
test_data = {
    'OrigRowNum': [1, 2, 3, 4, 5],
    'customer': ['VOIP001', 'VOIP002', 'FIBER001', 'FIBER002', 'VOIP003'],
    'lat': [39.0, 39.1, 39.2, 39.3, 39.4],
    'lon': [-84.5, -84.6, -84.7, -84.8, -84.9],
    'address': ['123 Main St', '456 Oak Ave', '789 Pine Rd', '321 Elm St', '654 Maple Dr'],
    'city': ['Cincinnati', 'Cincinnati', 'Cincinnati', 'Cincinnati', 'Cincinnati'],
    'state': ['OH', 'OH', 'OH', 'OH', 'OH'],
    'zip': ['45201', '45202', '45203', '45204', '45205'],
    'download': ['', '100', '', '500', '25'],
    'upload': ['', '50', '', '100', '10'],
    'voip_lines_quantity': [2, 1, 0, 0, 3],
    'business_customer': [0, 1, 0, 1, 0],
    'technology': ['voip', 'voip', 'fiber', 'fiber', 'voip']
}

df = pd.DataFrame(test_data)

print("\n" + "="*80)
print("VoIP VALIDATION TEST - FINAL RESULTS")
print("="*80)

# Run validation
errors = []
corrected_cells = {}
flagged_cells = {}

validate_general_columns(df, errors, corrected_cells, flagged_cells)

print("\n✅ TEST RESULTS:\n")

# Test 1: VoIP with blank speeds should pass
voip1_errors = [e for e in errors if e.get('Row') == 1]
status1 = "✅ PASS" if len(voip1_errors) == 0 else "❌ FAIL"
print(f"{status1} | Row 1 (VOIP001): voip + blank speeds → {len(voip1_errors)} errors")

# Test 2: VoIP with filled speeds should delete them
speeds_deleted_2 = pd.isna(df.loc[1, 'download']) and pd.isna(df.loc[1, 'upload'])
status2 = "✅ PASS" if speeds_deleted_2 else "❌ FAIL"
print(f"{status2} | Row 2 (VOIP002): voip + speeds (100/50) → Deleted: {speeds_deleted_2}")

# Test 3: Fiber with blank speeds should error
fiber_errors = [e for e in errors if e.get('Row') == 3]
status3 = "✅ PASS" if len(fiber_errors) == 2 else "❌ FAIL"
print(f"{status3} | Row 3 (FIBER001): fiber + blank speeds → {len(fiber_errors)} errors (expected 2)")

# Test 4: Fiber with filled speeds should pass
fiber2_errors = [e for e in errors if e.get('Row') == 4]
speeds_ok_4 = df.loc[3, 'download'] == 500.0 and df.loc[3, 'upload'] == 100.0
status4 = "✅ PASS" if len(fiber2_errors) == 0 and speeds_ok_4 else "❌ FAIL"
print(f"{status4} | Row 4 (FIBER002): fiber + speeds (500/100) → {len(fiber2_errors)} errors, speeds: {speeds_ok_4}")

# Test 5: VoIP with filled speeds should delete them
speeds_deleted_5 = pd.isna(df.loc[4, 'download']) and pd.isna(df.loc[4, 'upload'])
status5 = "✅ PASS" if speeds_deleted_5 else "❌ FAIL"
print(f"{status5} | Row 5 (VOIP003): voip + speeds (25/10) → Deleted: {speeds_deleted_5}")

# Overall summary
all_pass = (
    len(voip1_errors) == 0 and
    speeds_deleted_2 and
    len(fiber_errors) == 2 and
    len(fiber2_errors) == 0 and speeds_ok_4 and
    speeds_deleted_5
)

print("\n" + "="*80)
if all_pass:
    print("🎉 ALL TESTS PASSED!")
else:
    print("⚠️  SOME TESTS FAILED")

print("="*80)
print(f"Total errors: {len(errors)}")
print(f"Errors for FIBER001 (missing speeds): {len(fiber_errors)}")
if len(fiber_errors) > 0:
    for e in fiber_errors:
        print(f"  - {e.get('Column')}: {e.get('Error')}")
print("="*80 + "\n")
