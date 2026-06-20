#!/usr/bin/env python3
"""Test DSL to ADSL2 auto-conversion."""

import sys
import pandas as pd
sys.path.insert(0, '/Users/robertolive/Documents/RSI_Projects/Automated_Subscriber_Validation')

from src.validation.general import validate_general_columns

# Create test dataframe with various DSL formats
test_data = {
    'OrigRowNum': [1, 2, 3, 4, 5, 6, 7],
    'customer': ['DSL001', 'DSL002', 'DSL003', 'DSL004', 'ADSL001', 'FIBER001', 'WIRELESS001'],
    'lat': [39.0, 39.1, 39.2, 39.3, 39.4, 39.5, 39.6],
    'lon': [-84.5, -84.6, -84.7, -84.8, -84.9, -85.0, -85.1],
    'address': ['123 Main St', '456 Oak Ave', '789 Pine Rd', '321 Elm St', '654 Maple Dr', '987 Birch Ln', '147 Cedar Ct'],
    'city': ['Cincinnati', 'Cincinnati', 'Cincinnati', 'Cincinnati', 'Cincinnati', 'Cincinnati', 'Cincinnati'],
    'state': ['OH', 'OH', 'OH', 'OH', 'OH', 'OH', 'OH'],
    'zip': ['45201', '45202', '45203', '45204', '45205', '45206', '45207'],
    'download': [25, 50, 100, 75, 50, 1000, 100],
    'upload': [5, 10, 20, 15, 10, 500, 50],
    'voip_lines_quantity': [0, 0, 0, 0, 0, 0, 0],
    'business_customer': [0, 1, 0, 1, 0, 1, 0],
    'technology': ['dsl', 'DSL', 'Dsl', '  dsl  ', 'adsl2', 'fiber', 'wireless_unlicensed']
}

df = pd.DataFrame(test_data)

print("\n" + "="*80)
print("DSL TO ADSL2 CONVERSION TEST")
print("="*80)
print("\nOriginal Technology Values:")
for idx, row in enumerate(test_data['technology']):
    print(f"  Row {idx + 1}: '{row}' (OrigRowNum={test_data['OrigRowNum'][idx]})")

# Run validation
errors = []
corrected_cells = {}
flagged_cells = {}

validate_general_columns(df, errors, corrected_cells, flagged_cells)

print("\n✅ TEST RESULTS:\n")

# Test 1: Lowercase 'dsl' should convert to 'adsl2'
test1_converted = df.loc[0, 'technology'] == 'adsl2'
test1_corrected = (0, 'technology') in corrected_cells
status1 = "✅ PASS" if test1_converted and test1_corrected else "❌ FAIL"
print(f"{status1} | Row 1 (dsl): Converted to '{df.loc[0, 'technology']}', Logged: {test1_corrected}")

# Test 2: Uppercase 'DSL' should convert to 'adsl2'
test2_converted = df.loc[1, 'technology'] == 'adsl2'
test2_corrected = (1, 'technology') in corrected_cells
status2 = "✅ PASS" if test2_converted and test2_corrected else "❌ FAIL"
print(f"{status2} | Row 2 (DSL): Converted to '{df.loc[1, 'technology']}', Logged: {test2_corrected}")

# Test 3: Mixed case 'Dsl' should convert to 'adsl2'
test3_converted = df.loc[2, 'technology'] == 'adsl2'
test3_corrected = (2, 'technology') in corrected_cells
status3 = "✅ PASS" if test3_converted and test3_corrected else "❌ FAIL"
print(f"{status3} | Row 3 (Dsl): Converted to '{df.loc[2, 'technology']}', Logged: {test3_corrected}")

# Test 4: 'dsl' with whitespace should convert to 'adsl2'
test4_converted = df.loc[3, 'technology'] == 'adsl2'
test4_corrected = (3, 'technology') in corrected_cells
status4 = "✅ PASS" if test4_converted and test4_corrected else "❌ FAIL"
print(f"{status4} | Row 4 ('  dsl  '): Converted to '{df.loc[3, 'technology']}', Logged: {test4_corrected}")

# Test 5: 'adsl2' should remain unchanged (no conversion needed)
test5_unchanged = df.loc[4, 'technology'] == 'adsl2'
test5_not_corrected = (4, 'technology') not in corrected_cells
status5 = "✅ PASS" if test5_unchanged and test5_not_corrected else "❌ FAIL"
print(f"{status5} | Row 5 (adsl2): Unchanged '{df.loc[4, 'technology']}', Not logged: {test5_not_corrected}")

# Test 6: 'fiber' should remain unchanged
test6_unchanged = df.loc[5, 'technology'] == 'fiber'
test6_not_corrected = (5, 'technology') not in corrected_cells
status6 = "✅ PASS" if test6_unchanged and test6_not_corrected else "❌ FAIL"
print(f"{status6} | Row 6 (fiber): Unchanged '{df.loc[5, 'technology']}', Not logged: {test6_not_corrected}")

# Test 7: 'wireless_unlicensed' should remain unchanged
test7_unchanged = df.loc[6, 'technology'] == 'wireless_unlicensed'
test7_not_corrected = (6, 'technology') not in corrected_cells
status7 = "✅ PASS" if test7_unchanged and test7_not_corrected else "❌ FAIL"
print(f"{status7} | Row 7 (wireless_unlicensed): Unchanged '{df.loc[6, 'technology']}', Not logged: {test7_not_corrected}")

# Test 8: No validation errors should occur for converted DSL entries
dsl_rows = [1, 2, 3, 4]
dsl_errors = [e for e in errors if e.get('Row') in dsl_rows and e.get('Column') == 'technology']
status8 = "✅ PASS" if len(dsl_errors) == 0 else "❌ FAIL"
print(f"{status8} | No technology errors for DSL rows: {len(dsl_errors)} errors found")

# Test 9: Verify correction metadata
print("\n📋 CORRECTION DETAILS:")
for idx in range(4):  # Rows 1-4 should have corrections
    if (idx, 'technology') in corrected_cells:
        correction = corrected_cells[(idx, 'technology')]
        print(f"  Row {idx + 1}:")
        print(f"    Original: '{correction['original']}'")
        print(f"    Corrected: '{correction['corrected']}'")
        print(f"    Type: {correction['type']}")
        print(f"    Status: {correction['status']}")

# Overall summary
all_pass = (
    test1_converted and test1_corrected and
    test2_converted and test2_corrected and
    test3_converted and test3_corrected and
    test4_converted and test4_corrected and
    test5_unchanged and test5_not_corrected and
    test6_unchanged and test6_not_corrected and
    test7_unchanged and test7_not_corrected and
    len(dsl_errors) == 0
)

print("\n" + "="*80)
if all_pass:
    print("🎉 ALL TESTS PASSED!")
    print("✅ DSL to ADSL2 conversion is working correctly")
else:
    print("⚠️  SOME TESTS FAILED")
    print("❌ Review the test results above")

print("="*80)
print(f"Total errors: {len(errors)}")
print(f"Total corrections logged: {len(corrected_cells)}")
print(f"DSL-related corrections: {sum(1 for k, v in corrected_cells.items() if k[1] == 'technology' and v.get('type') == 'Technology Auto-Correction')}")
print("="*80 + "\n")

# Display final dataframe state
print("\n📊 FINAL TECHNOLOGY VALUES:")
print(df[['OrigRowNum', 'customer', 'technology']].to_string(index=False))
print()
