#!/usr/bin/env python3
"""Quick test script for VoIP validation logic - with better error display."""

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

print("\n" + "="*80)
print("VoIP VALIDATION TEST")
print("="*80)

# Run validation
errors = []
corrected_cells = {}
flagged_cells = {}

validate_general_columns(df, errors, corrected_cells, flagged_cells)

print("\n✅ TEST RESULTS:\n")

# Test 1: VoIP with blank speeds should pass
print("1. VOIP001 (voip + blank speeds):")
voip1_errors = [e for e in errors if e.get('row') == 1]
if len(voip1_errors) == 0:
    print("   ✅ PASS: No errors (blank speeds allowed for VoIP)")
else:
    print(f"   ❌ FAIL: Found {len(voip1_errors)} errors (should be 0)")
    for e in voip1_errors:
        print(f"      - {e}")

# Test 2: VoIP with filled speeds should delete them
print("\n2. VOIP002 (voip + speeds 100/50):")
if pd.isna(df.loc[1, 'download']) and pd.isna(df.loc[1, 'upload']):
    print("   ✅ PASS: Speeds deleted (was 100/50, now NA/NA)")
else:
    print(f"   ❌ FAIL: Speeds not deleted (download={df.loc[1, 'download']}, upload={df.loc[1, 'upload']})")

# Test 3: Fiber with blank speeds should error
print("\n3. FIBER001 (fiber + blank speeds):")
fiber_errors = [e for e in errors if e.get('row') == 3]
print(f"   Total errors in errors list: {len(errors)}")
print(f"   Errors for row 3: {len(fiber_errors)}")
if len(fiber_errors) >= 2:
    print(f"   ✅ PASS: {len(fiber_errors)} errors (download + upload required)")
else:
    print(f"   ❌ FAIL: Only {len(fiber_errors)} errors (should be 2)")
    print(f"   All errors: {errors}")

# Test 4: Fiber with filled speeds should pass
print("\n4. FIBER002 (fiber + speeds 500/100):")
fiber2_errors = [e for e in errors if e.get('row') == 4]
if len(fiber2_errors) == 0 and df.loc[3, 'download'] == 500.0 and df.loc[3, 'upload'] == 100.0:
    print("   ✅ PASS: No errors, speeds validated (500.0/100.0)")
else:
    print(f"   ❌ FAIL: Found {len(fiber2_errors)} errors or speeds incorrect")

# Test 5: VoIP with filled speeds should delete them
print("\n5. VOIP003 (voip + speeds 25/10):")
if pd.isna(df.loc[4, 'download']) and pd.isna(df.loc[4, 'upload']):
    print("   ✅ PASS: Speeds deleted (was 25/10, now NA/NA)")
else:
    print(f"   ❌ FAIL: Speeds not deleted (download={df.loc[4, 'download']}, upload={df.loc[4, 'upload']})")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Total errors recorded: {len(errors)}")
print(f"VoIP rows with speeds deleted: {pd.isna(df.loc[1, 'download']) and pd.isna(df.loc[4, 'download'])}")
print(f"Fiber row with missing speeds flagged: {len([e for e in errors if e.get('row') == 3])} >= 2")
print("="*80 + "\n")
