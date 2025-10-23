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

def remove_full_row_duplicates(cleaned_df, errors, rows_to_remove, duplicate_removals, corrected_cells, flagged_cells):
    """Remove exact duplicate rows and intelligently handle customer duplicates based on speed/technology.

    This function:
    1. Removes rows that are 100% identical across all fields (keeps first occurrence)
    2. For duplicate customer IDs, keeps the best row based on:
       - Highest download speed
       - Highest upload speed
       - Best technology (fiber > wireless_pal > wireless_gaa > wireless_unlicensed)
       - First occurrence (tiebreaker)

    OrigRowNum is preserved throughout so users can trace back to original file.

    Args:
        cleaned_df: DataFrame with subscriber data
        errors: List to append error records
        rows_to_remove: List to append removed row numbers
        duplicate_removals: List to track which rows were removed and why
        corrected_cells: Dict tracking cell corrections
        flagged_cells: Dict tracking flagged cells
    """
    debug_print("=== Starting full-row duplicate removal ===")
    initial_row_count = len(cleaned_df)

    # Step 1: Remove exact duplicates (100% identical rows)
    # Keep track of which rows are duplicates before removing
    all_columns = [col for col in cleaned_df.columns if col != 'OrigRowNum']
    cleaned_df['_temp_dup_check'] = cleaned_df.duplicated(subset=all_columns, keep='first')

    exact_duplicates = cleaned_df[cleaned_df['_temp_dup_check'] == True].copy()

    for idx, row in exact_duplicates.iterrows():
        orig_row_num = int(row['OrigRowNum'])

        # Find which row this is a duplicate of
        matching_rows = cleaned_df[
            (cleaned_df[all_columns] == row[all_columns]).all(axis=1) &
            (cleaned_df.index < idx)
        ]

        if len(matching_rows) > 0:
            first_occurrence_row = int(matching_rows.iloc[0]['OrigRowNum'])

            duplicate_removals.append({
                "OrigRowNum": orig_row_num,
                "Reason": "Exact duplicate - 100% identical to another row",
                "Duplicate_Of_Row": first_occurrence_row,
                "Customer_ID": row['customer'],
                "Address": row.get('address', ''),
                "Download_Speed": row.get('download', ''),
                "Upload_Speed": row.get('upload', ''),
                "Technology": row.get('technology', '')
            })

            debug_print(f"Removing exact duplicate: OrigRowNum {orig_row_num} (duplicate of row {first_occurrence_row})")

    # Remove exact duplicates
    cleaned_df = cleaned_df[cleaned_df['_temp_dup_check'] == False].copy()
    cleaned_df.drop(columns=['_temp_dup_check'], inplace=True)

    exact_dup_count = initial_row_count - len(cleaned_df)
    debug_print(f"Removed {exact_dup_count} exact duplicate rows")

    # Step 2: Handle duplicate customer IDs with speed/technology ranking
    # Define technology priority (lower = better)
    tech_priority = {
        'fiber': 1,
        'wireless_pal': 2,
        'wireless_gaa': 3,
        'wireless_unlicensed': 4
    }

    # Add temporary ranking column
    cleaned_df['_tech_rank'] = cleaned_df['technology'].map(tech_priority).fillna(999)

    # Convert speed columns to numeric for sorting
    cleaned_df['_download_numeric'] = pd.to_numeric(cleaned_df['download'], errors='coerce').fillna(0)
    cleaned_df['_upload_numeric'] = pd.to_numeric(cleaned_df['upload'], errors='coerce').fillna(0)

    # Group by customer ID to find duplicates
    customer_groups = cleaned_df.groupby('customer')

    rows_to_keep_indices = []

    for customer_id, group in customer_groups:
        if len(group) == 1:
            # No duplicates, keep the row
            rows_to_keep_indices.extend(group.index.tolist())
        else:
            # Multiple rows for same customer - apply ranking logic
            debug_print(f"Found {len(group)} rows for customer '{customer_id}' - applying speed/technology ranking")

            # Sort by: download (desc), upload (desc), tech_rank (asc), original index (asc)
            sorted_group = group.sort_values(
                by=['_download_numeric', '_upload_numeric', '_tech_rank'],
                ascending=[False, False, True]
            )

            # Keep the best (first) row
            best_row = sorted_group.iloc[0]
            best_row_orig_num = int(best_row['OrigRowNum'])
            rows_to_keep_indices.append(sorted_group.index[0])

            # Log all other rows as removed with detailed reason
            for i in range(1, len(sorted_group)):
                removed_row = sorted_group.iloc[i]
                removed_orig_num = int(removed_row['OrigRowNum'])

                # Build detailed reason
                reason_parts = [f"Duplicate customer ID '{customer_id}'"]

                # Compare speeds
                if removed_row['_download_numeric'] < best_row['_download_numeric']:
                    reason_parts.append(f"lower download speed ({removed_row['download']} < {best_row['download']} Mbps)")
                elif removed_row['_upload_numeric'] < best_row['_upload_numeric']:
                    reason_parts.append(f"lower upload speed ({removed_row['upload']} < {best_row['upload']} Mbps)")
                elif removed_row['_tech_rank'] > best_row['_tech_rank']:
                    reason_parts.append(f"lower-priority technology ({removed_row['technology']} < {best_row['technology']})")
                else:
                    reason_parts.append("not the first occurrence")

                reason = " - ".join(reason_parts)

                duplicate_removals.append({
                    "OrigRowNum": removed_orig_num,
                    "Reason": reason,
                    "Duplicate_Of_Row": best_row_orig_num,
                    "Customer_ID": customer_id,
                    "Address": removed_row.get('address', ''),
                    "Download_Speed": removed_row.get('download', ''),
                    "Upload_Speed": removed_row.get('upload', ''),
                    "Technology": removed_row.get('technology', '')
                })

                debug_print(f"Removing duplicate customer row: OrigRowNum {removed_orig_num} - {reason}")

    # Filter to keep only the selected rows
    cleaned_df = cleaned_df.loc[rows_to_keep_indices].copy()

    # Clean up temporary columns
    cleaned_df.drop(columns=['_tech_rank', '_download_numeric', '_upload_numeric'], inplace=True)

    # Reset index to avoid KeyError issues in subsequent processing
    # This ensures index is sequential 0, 1, 2, ... matching the row count
    cleaned_df.reset_index(drop=True, inplace=True)

    customer_dup_count = len(duplicate_removals) - exact_dup_count
    debug_print(f"Removed {customer_dup_count} duplicate customer rows based on speed/technology ranking")

    final_row_count = len(cleaned_df)
    total_removed = initial_row_count - final_row_count

    debug_print(f"=== Duplicate removal complete ===")
    debug_print(f"Initial rows: {initial_row_count}")
    debug_print(f"Exact duplicates removed: {exact_dup_count}")
    debug_print(f"Customer duplicates removed: {customer_dup_count}")
    debug_print(f"Final rows: {final_row_count}")
    debug_print(f"Total removed: {total_removed}")

    return cleaned_df