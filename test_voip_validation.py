#!/usr/bin/env python3
"""Quick test script for VoIP validation logic."""

import sys
import pandas as pd
sys.path.insert(0, '/Users/robertolive/Documents/RSI_Projects/Automated_Subscriber_Validation')

from src.validation.general import validate_general_columns
from src.config.settings import DEBUG_MODE

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

print("="*80)
print("TEST DATA:")
print("="*80)
print(df.to_string())
print("\n")

# Run validation
errors = []
corrected_cells = {}
flagged_cells = {}

print("="*80)
print("RUNNING VALIDATION...")
print("="*80)

validate_general_columns(df, errors, corrected_cells, flagged_cells)

print("\n")
print("="*80)
print("RESULTS AFTER VALIDATION:")
print("="*80)
print(df.to_string())

print("\n")
print("="*80)
print(f"ERRORS: {len(errors)}")
print("="*80)
for error in errors:
    print(f"  Row {error.get('row', '?')}, Column {error.get('column', '?')}: {error.get('error', '?')}")

print("\n")
print("="*80)
print("EXPECTED RESULTS:")
print("="*80)
print("Row 1 (VOIP001): voip with blank speeds → Should PASS (no error)")
print("Row 2 (VOIP002): voip with speeds (100/50) → Speeds should be DELETED")
print("Row 3 (FIBER001): fiber with blank speeds → Should ERROR (required)")
print("Row 4 (FIBER002): fiber with speeds (500/100) → Should PASS (valid)")
print("Row 5 (VOIP003): voip with speeds (25/10) → Speeds should be DELETED")

print("\n")
print("="*80)
print("VERIFICATION:")
print("="*80)
print(f"Row 1 download: '{df.loc[0, 'download']}' (should be blank/NA)")
print(f"Row 1 upload: '{df.loc[0, 'upload']}' (should be blank/NA)")
print(f"Row 2 download: '{df.loc[1, 'download']}' (should be NA - was 100)")
print(f"Row 2 upload: '{df.loc[1, 'upload']}' (should be NA - was 50)")
print(f"Row 3 download: '{df.loc[2, 'download']}' (should be blank/NA)")
print(f"Row 3 upload: '{df.loc[2, 'upload']}' (should be blank/NA)")
print(f"Row 4 download: '{df.loc[3, 'download']}' (should be 500.0)")
print(f"Row 4 upload: '{df.loc[3, 'upload']}' (should be 100.0)")
print(f"Row 5 download: '{df.loc[4, 'download']}' (should be NA - was 25)")
print(f"Row 5 upload: '{df.loc[4, 'upload']}' (should be NA - was 10)")

# Check for fiber errors
fiber_errors = [e for e in errors if e.get('row') == 3]
if fiber_errors:
    print(f"\n✅ PASS: Row 3 (FIBER001) correctly has {len(fiber_errors)} error(s) for missing speeds")
else:
    print(f"\n❌ FAIL: Row 3 (FIBER001) should have errors for missing speeds")

# Check VoIP speeds were deleted
voip_speeds_deleted = (
    pd.isna(df.loc[1, 'download']) and pd.isna(df.loc[1, 'upload']) and
    pd.isna(df.loc[4, 'download']) and pd.isna(df.loc[4, 'upload'])
)
if voip_speeds_deleted:
    print("✅ PASS: VoIP speeds correctly deleted for rows 2 and 5")
else:
    print("❌ FAIL: VoIP speeds not deleted properly")
