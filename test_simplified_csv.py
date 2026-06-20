#!/usr/bin/env python3
"""
Test script to verify simplified OrigRowNum detection works correctly.
Now only checks for exact "OrigRowNum" column name.
"""

import pandas as pd
import os
import shutil

# Simplified function - only checks for OrigRowNum name
def _detect_and_remove_index_column(df, file_type, org_id):
    """
    Helper function to detect and remove OrigRowNum column.
    """
    if len(df.columns) == 0:
        return df, False, None

    first_col_name = df.columns[0]

    # Check for OrigRowNum column name (exact match)
    if str(first_col_name).strip() == 'OrigRowNum':
        # Remove OrigRowNum column
        modified_df = df.iloc[:, 1:]  # Drop first column
        print(f'[{file_type} CLEANING] Org {org_id}: Detected and removed OrigRowNum column')
        return modified_df, True, first_col_name

    return df, False, None


def prepare_subscriber_file(file_path, org_id):
    """
    Prepare subscriber file for validation.
    """
    file_ext = os.path.splitext(file_path)[1].lower()

    # Handle CSV files
    if file_ext == '.csv':
        print(f'[CSV CHECK] Org {org_id}: Detected CSV file: {os.path.basename(file_path)}')
        print(f'[CSV CHECK] Checking for OrigRowNum column...')

        try:
            # Read CSV file
            df = pd.read_csv(file_path)
            original_columns = len(df.columns)

            # Detect and remove OrigRowNum column
            df, was_removed, removed_col = _detect_and_remove_index_column(df, 'CSV', org_id)

            # If we removed a column, save the cleaned CSV
            if was_removed:
                print(f'[CSV CLEANING] OrigRowNum column found - cleaning file...')

                # Backup original CSV file
                backup_path = os.path.splitext(file_path)[0] + '_original.csv'
                shutil.copy2(file_path, backup_path)
                print(f'[CSV CLEANING] Original CSV backed up as: {os.path.basename(backup_path)}')

                # Overwrite original CSV with cleaned version
                df.to_csv(file_path, index=False)

                print(f'[CSV CLEANING] Successfully cleaned CSV file')
                print(f'[CSV CLEANING] Original columns: {original_columns}, Final columns: {len(df.columns)}')
                print(f'[CSV CLEANING] Removed column: "{removed_col}"')
                print(f'[CSV CLEANING] Rows: {len(df)}')
            else:
                print(f'[CSV CHECK] No OrigRowNum column found - file is clean')
                print(f'[CSV CHECK] Columns: {len(df.columns)}, Rows: {len(df)}')

            return file_path

        except Exception as e:
            print(f'[CSV CLEANING ERROR] Failed to process CSV file: {str(e)}')
            return file_path

    return file_path


print("=" * 70)
print("SIMPLIFIED ORIGROWNUM DETECTION TEST")
print("=" * 70)

# Test 1: CSV with OrigRowNum column (should be removed)
print("\n" + "=" * 70)
print("TEST 1: CSV file WITH OrigRowNum column")
print("=" * 70)

test_data_1 = {
    'OrigRowNum': [1, 2, 3, 4, 5],
    'customer': ['Customer 1', 'Customer 2', 'Customer 3', 'Customer 4', 'Customer 5'],
    'lat': [33.9425, 40.7128, 41.8781, 29.7604, 39.7392],
    'lon': [-117.2297, -74.0060, -87.6298, -95.3698, -104.9903],
    'state': ['CA', 'NY', 'IL', 'TX', 'CO'],
    'download': [100, 250, 500, 100, 1000],
    'upload': [25, 50, 100, 25, 250]
}

df1 = pd.DataFrame(test_data_1)
test_dir = '/Users/robertolive/Documents/RSI_Projects/Automated_Subscriber_Validation/CSV_Test_Simplified'
os.makedirs(test_dir, exist_ok=True)

test_file_1 = os.path.join(test_dir, 'test_with_origrownum.csv')
df1.to_csv(test_file_1, index=False)

print(f"\nBefore: {list(df1.columns)}")
print(f"Column count: {len(df1.columns)}")

cleaned_file_1 = prepare_subscriber_file(test_file_1, '001')
df1_cleaned = pd.read_csv(cleaned_file_1)

print(f"\nAfter: {list(df1_cleaned.columns)}")
print(f"Column count: {len(df1_cleaned.columns)}")

if 'OrigRowNum' not in df1_cleaned.columns:
    print("✅ TEST 1 PASSED: OrigRowNum was removed")
else:
    print("❌ TEST 1 FAILED: OrigRowNum still exists")
    exit(1)

# Test 2: CSV without OrigRowNum column (should pass through unchanged)
print("\n" + "=" * 70)
print("TEST 2: CSV file WITHOUT OrigRowNum column")
print("=" * 70)

test_data_2 = {
    'customer': ['Customer 1', 'Customer 2', 'Customer 3'],
    'lat': [33.9425, 40.7128, 41.8781],
    'lon': [-117.2297, -74.0060, -87.6298],
    'state': ['CA', 'NY', 'IL'],
    'download': [100, 250, 500],
    'upload': [25, 50, 100]
}

df2 = pd.DataFrame(test_data_2)
test_file_2 = os.path.join(test_dir, 'test_without_origrownum.csv')
df2.to_csv(test_file_2, index=False)

print(f"\nBefore: {list(df2.columns)}")
print(f"Column count: {len(df2.columns)}")

cleaned_file_2 = prepare_subscriber_file(test_file_2, '002')
df2_cleaned = pd.read_csv(cleaned_file_2)

print(f"\nAfter: {list(df2_cleaned.columns)}")
print(f"Column count: {len(df2_cleaned.columns)}")

if list(df2.columns) == list(df2_cleaned.columns):
    print("✅ TEST 2 PASSED: Clean file passed through unchanged")
else:
    print("❌ TEST 2 FAILED: Columns were modified")
    exit(1)

# Test 3: CSV with column named "customer_id" starting with integers (should NOT be removed)
print("\n" + "=" * 70)
print("TEST 3: CSV with legitimate integer column (NOT OrigRowNum)")
print("=" * 70)

test_data_3 = {
    'customer_id': [1, 2, 3, 4, 5],  # Sequential integers but legitimate column
    'customer': ['Customer 1', 'Customer 2', 'Customer 3', 'Customer 4', 'Customer 5'],
    'state': ['CA', 'NY', 'IL', 'TX', 'CO'],
    'download': [100, 250, 500, 100, 1000]
}

df3 = pd.DataFrame(test_data_3)
test_file_3 = os.path.join(test_dir, 'test_with_customer_id.csv')
df3.to_csv(test_file_3, index=False)

print(f"\nBefore: {list(df3.columns)}")
print(f"Column count: {len(df3.columns)}")

cleaned_file_3 = prepare_subscriber_file(test_file_3, '003')
df3_cleaned = pd.read_csv(cleaned_file_3)

print(f"\nAfter: {list(df3_cleaned.columns)}")
print(f"Column count: {len(df3_cleaned.columns)}")

if 'customer_id' in df3_cleaned.columns and list(df3.columns) == list(df3_cleaned.columns):
    print("✅ TEST 3 PASSED: Legitimate customer_id column preserved")
else:
    print("❌ TEST 3 FAILED: Legitimate data column was removed")
    exit(1)

print("\n" + "=" * 70)
print("ALL TESTS PASSED! ✅")
print("=" * 70)
print("\n✅ Simplified logic is working correctly:")
print("   • Only checks for exact 'OrigRowNum' column name")
print("   • Faster execution (no data scanning)")
print("   • Preserves all legitimate columns")
print("   • Solves the actual problem users encounter")
print("\n🚀 Performance improved - unnecessary checks removed!")
