"""Customer uniqueness validation functions."""

import pandas as pd
from src.utils.logging import debug_print


def validate_customer_uniqueness(cleaned_df, errors, rows_to_remove, non_unique_row_removals, corrected_cells, flagged_cells):
    """Ensure customer IDs are unique by renaming duplicates."""
    debug_print("=== Starting customer uniqueness validation ===")
    debug_print(f"Customer values: {cleaned_df['customer'].tolist()}")
    cleaned_df["customer"] = cleaned_df["customer"].astype(str)
    cleaned_df["customer_lower"] = cleaned_df["customer"].str.lower().fillna("")
    comparison_columns = ["lat", "lon", "address", "city", "state", "zip", "download", "upload",
                          "voip_lines_quantity", "business_customer", "technology"]
    suffix_counter = 1

    def values_equal(val1, val2):
        """Compare two values handling NA/NaN properly."""
        if pd.isna(val1) and pd.isna(val2):
            return True
        elif pd.isna(val1) or pd.isna(val2):
            return False
        else:
            return val1 == val2

    grouped = cleaned_df.groupby("customer_lower")
    for customer_lower, group in grouped:
        if len(group) > 1:
            debug_print(f"Duplicate customer ID '{customer_lower}' at OrigRowNum={group['OrigRowNum'].tolist()}")
            group = group.reset_index()
            orig_row_to_new_name = {}

            for i in range(len(group)):
                row = group.iloc[i].copy()
                orig_row = row["OrigRowNum"]

                # Keep first occurrence with original name, rename all others
                if i == 0:
                    new_id = row["customer"]
                else:
                    # Check if data is identical to first row
                    first_row = group.iloc[0]
                    identical = all(values_equal(row[col], first_row[col]) for col in comparison_columns)

                    new_id = f"{row['customer']}_{suffix_counter:03d}"
                    suffix_counter += 1
                    orig_row_to_new_name[orig_row] = new_id

                    error_msg = f"Duplicate customer ID, renamed to {new_id}"
                    if identical:
                        error_msg += " (identical data)"

                    corrected_cells[(group.index[i], "customer")] = {
                        "row": int(orig_row),
                        "original": row["customer"],
                        "corrected": new_id,
                        "type": "Duplicate Customer Rename",
                        "status": "Valid"
                    }
                    errors.append({
                        "Row": orig_row,
                        "Column": "customer",
                        "Error": error_msg,
                        "Value": row["customer"]
                    })

            for orig_row, new_id in orig_row_to_new_name.items():
                idx = cleaned_df.index[cleaned_df["OrigRowNum"] == orig_row].tolist()
                if idx:
                    cleaned_df.loc[idx[0], "customer"] = new_id

    cleaned_df.drop(columns=["customer_lower"], inplace=True)

def validate_data_based_duplicates(cleaned_df, errors, rows_to_remove, non_unique_row_removals, corrected_cells, flagged_cells):
    """Detect rows with identical data but different customer IDs and rename them."""
    debug_print("=== Starting data-based duplicate detection ===")

    comparison_columns = ["lat", "lon", "address", "city", "state", "zip", "download", "upload",
                         "voip_lines_quantity", "business_customer", "technology"]

    # Create composite key from all data fields (excluding customer ID)
    cleaned_df["temp_data_key"] = cleaned_df[comparison_columns].astype(str).agg('|'.join, axis=1)

    # Group by data signature
    grouped = cleaned_df.groupby("temp_data_key")
    suffix_counter = 1

    for data_key, group in grouped:
        if len(group) > 1:
            debug_print(f"Found {len(group)} rows with identical data: customers {group['customer'].tolist()}")

            # Keep first occurrence with original customer ID, rename others
            for i in range(1, len(group)):  # Skip first (index 0)
                row = group.iloc[i]
                orig_row = row["OrigRowNum"]
                original_customer_id = row["customer"]
                first_customer_id = group.iloc[0]["customer"]

                # Generate new unique customer ID
                new_customer_id = f"{original_customer_id}_{suffix_counter:03d}"
                suffix_counter += 1

                # Update the customer ID in the dataframe
                idx = cleaned_df.index[cleaned_df["OrigRowNum"] == orig_row].tolist()
                if idx:
                    cleaned_df.loc[idx[0], "customer"] = new_customer_id

                # Mark as corrected
                corrected_cells[(idx[0], "customer")] = {
                    "row": int(orig_row),
                    "original": original_customer_id,
                    "corrected": new_customer_id,
                    "type": "Data-based Duplicate Rename",
                    "status": "Valid"
                }

                # Add error entry
                errors.append({
                    "Row": orig_row,
                    "Column": "customer",
                    "Error": f"Data-based duplicate, renamed to {new_customer_id} (identical data to customer {first_customer_id})",
                    "Value": original_customer_id
                })

                debug_print(f"Renamed customer {original_customer_id} to {new_customer_id} (OrigRowNum {orig_row}) - identical data to customer {first_customer_id}")

    # Clean up temporary column
    cleaned_df.drop(columns=["temp_data_key"], inplace=True)