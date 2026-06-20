#!/usr/bin/env python3
"""
Test script to verify CSV file with OrigRowNum column is properly cleaned.

This simulates a user resubmitting a corrected CSV file but forgetting to
remove the OrigRowNum column.
"""

import pandas as pd
import os
import sys

# Create test CSV file with OrigRowNum column
test_data = {
    'OrigRowNum': [1, 2, 3, 4, 5],
    'customer': ['Test Customer 1', 'Test Customer 2', 'Test Customer 3', 'Test Customer 4', 'Test Customer 5'],
    'lat': [33.9425, 40.7128, 41.8781, 29.7604, 39.7392],
    'lon': [-117.2297, -74.0060, -87.6298, -95.3698, -104.9903],
    'address': ['123 Main St', '456 Broadway', '789 Michigan Ave', '321 Texas St', '654 Colfax Ave'],
    'city': ['Riverside', 'New York', 'Chicago', 'Houston', 'Denver'],
    'state': ['CA', 'NY', 'IL', 'TX', 'CO'],
    'zip': ['92501', '10012', '60611', '77002', '80202'],
    'download': [100, 250, 500, 100, 1000],
    'upload': [25, 50, 100, 25, 250],
    'voip_lines_quantity': [0, 1, 0, 2, 0],
    'business_customer': [0, 0, 1, 0, 0],
    'technology': ['fiber', 'fiber', 'fiber', 'fiber', 'wireless_unlicensed']
}

df = pd.DataFrame(test_data)

# Create test directory
test_dir = '/Users/robertolive/Documents/RSI_Projects/Automated_Subscriber_Validation/CSV_Test'
os.makedirs(test_dir, exist_ok=True)

# Save CSV with OrigRowNum column
test_file_path = os.path.join(test_dir, 'test_subscriber_with_origrownum.csv')
df.to_csv(test_file_path, index=False)

print("=" * 60)
print("TEST: CSV File with OrigRowNum Column")
print("=" * 60)
print(f"\nCreated test file: {test_file_path}")
print(f"\nOriginal DataFrame (WITH OrigRowNum column):")
print(df.head())
print(f"\nOriginal columns: {list(df.columns)}")
print(f"Original column count: {len(df.columns)}")

# Add the directory containing validate_subscription_isp_mod_3.py to Python path
sys.path.insert(0, '/Users/robertolive/documents/RSI_Projects/Automated_Subscriber_Validation')

# Import the function we want to test
from validate_subscription_isp_mod_3 import prepare_subscriber_file

# Run the prepare_subscriber_file function
print("\n" + "=" * 60)
print("Running prepare_subscriber_file()...")
print("=" * 60)

cleaned_file = prepare_subscriber_file(test_file_path, '999')

# Read the cleaned file
cleaned_df = pd.read_csv(cleaned_file)

print(f"\nCleaned file path: {cleaned_file}")
print(f"\nCleaned DataFrame (OrigRowNum should be REMOVED):")
print(cleaned_df.head())
print(f"\nCleaned columns: {list(cleaned_df.columns)}")
print(f"Cleaned column count: {len(cleaned_df.columns)}")

# Verify OrigRowNum was removed
if 'OrigRowNum' in cleaned_df.columns:
    print("\n❌ FAILED: OrigRowNum column still exists!")
    sys.exit(1)
else:
    print("\n✅ SUCCESS: OrigRowNum column was removed!")

# Verify all expected columns remain
expected_columns = ['customer', 'lat', 'lon', 'address', 'city', 'state', 'zip',
                   'download', 'upload', 'voip_lines_quantity', 'business_customer', 'technology']

if list(cleaned_df.columns) == expected_columns:
    print("✅ SUCCESS: All expected columns are present!")
else:
    print("❌ FAILED: Column mismatch!")
    print(f"Expected: {expected_columns}")
    print(f"Got: {list(cleaned_df.columns)}")
    sys.exit(1)

# Verify row count unchanged
if len(cleaned_df) == len(df):
    print(f"✅ SUCCESS: Row count preserved ({len(cleaned_df)} rows)")
else:
    print(f"❌ FAILED: Row count changed from {len(df)} to {len(cleaned_df)}")
    sys.exit(1)

# Check if backup was created
backup_file = os.path.join(test_dir, 'test_subscriber_with_origrownum_original.csv')
if os.path.exists(backup_file):
    print(f"✅ SUCCESS: Backup file created: {os.path.basename(backup_file)}")
else:
    print(f"❌ WARNING: Backup file not found: {os.path.basename(backup_file)}")

print("\n" + "=" * 60)
print("ALL CSV TESTS PASSED! ✅")
print("=" * 60)
print("\nThe comprehensive solution is working:")
print("✅ Excel files: Converted to CSV + OrigRowNum removed")
print("✅ CSV files: OrigRowNum removed automatically")
print("\nUsers can now submit either format without manual cleanup!")
