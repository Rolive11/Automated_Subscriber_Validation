"""Customer uniqueness validation functions."""

import pandas as pd
from src.utils.logging import debug_print


def validate_customer_uniqueness(cleaned_df, errors, rows_to_remove, non_unique_row_removals, corrected_cells, flagged_cells):
    """Ensure customer IDs are unique, renaming or deleting duplicates."""
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
            rows_to_keep = []
            orig_row_to_new_name = {}

            for i in range(len(group)):
                row = group.iloc[i].copy()
                orig_row = row["OrigRowNum"]
                is_duplicate = False
                for kept_row in rows_to_keep:
                    identical = all(values_equal(row[col], kept_row[col]) for col in comparison_columns)
                    if identical:
                        rows_to_remove.append(orig_row)
                        non_unique_row_removals.append({
                            "OrigRowNum": orig_row,
                            "customer": row["customer"],
                            "lat": row["lat"],
                            "lon": row["lon"],
                            "address": row["address"],
                            "city": row["city"],
                            "state": row["state"],
                            "zip": row["zip"],
                            "download": row["download"],
                            "upload": row["upload"],
                            "voip_lines_quantity": row["voip_lines_quantity"],
                            "business_customer": row["business_customer"],
                            "technology": row["technology"],
                            "Error": "Duplicate customer ID, identical row deleted"
                        })
                        errors.append({
                            "Row": orig_row,
                            "Column": "customer",
                            "Error": "Duplicate customer ID, identical row deleted",
                            "Value": row["customer"]
                        })
                        is_duplicate = True
                        break
                if not is_duplicate:
                    if i == 0:
                        new_id = row["customer"]
                    else:
                        new_id = f"{row['customer']}_{suffix_counter:03d}"
                        suffix_counter += 1
                        orig_row_to_new_name[orig_row] = new_id
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
                            "Error": f"Duplicate customer ID, renamed to {new_id}",
                            "Value": row["customer"]
                        })
                    rows_to_keep.append(row)

            for orig_row, new_id in orig_row_to_new_name.items():
                idx = cleaned_df.index[cleaned_df["OrigRowNum"] == orig_row].tolist()
                if idx:
                    cleaned_df.loc[idx[0], "customer"] = new_id

    cleaned_df.drop(columns=["customer_lower"], inplace=True)

def validate_data_based_duplicates(cleaned_df, errors, rows_to_remove, non_unique_row_removals, corrected_cells, flagged_cells):
    """Detect rows with identical data but different customer IDs."""
    debug_print("=== Starting data-based duplicate detection ===")
    
    comparison_columns = ["lat", "lon", "address", "city", "state", "zip", "download", "upload",
                         "voip_lines_quantity", "business_customer", "technology"]
    
    # Create composite key from all data fields (excluding customer ID)
    cleaned_df["temp_data_key"] = cleaned_df[comparison_columns].astype(str).agg('|'.join, axis=1)
    
    # Group by data signature
    grouped = cleaned_df.groupby("temp_data_key")
    
    for data_key, group in grouped:
        if len(group) > 1:
            debug_print(f"Found {len(group)} rows with identical data: customers {group['customer'].tolist()}")
            
            # Keep first occurrence, mark others for removal
            for i in range(1, len(group)):  # Skip first (index 0)
                row = group.iloc[i]
                orig_row = row["OrigRowNum"]
                
                # Mark for removal
                rows_to_remove.append(orig_row)
                
                # Log the removal
                non_unique_row_removals.append({
                    "OrigRowNum": orig_row,
                    "customer": row["customer"],
                    "lat": row["lat"],
                    "lon": row["lon"], 
                    "address": row["address"],
                    "city": row["city"],
                    "state": row["state"],
                    "zip": row["zip"],
                    "download": row["download"],
                    "upload": row["upload"],
                    "voip_lines_quantity": row["voip_lines_quantity"],
                    "business_customer": row["business_customer"],
                    "technology": row["technology"],
                    "Error": f"Data-based duplicate (same as customer {group.iloc[0]['customer']})"
                })
                
                # Add error entry
                errors.append({
                    "Row": orig_row,
                    "Column": "customer",
                    "Error": f"Data-based duplicate, removed (identical to customer {group.iloc[0]['customer']})",
                    "Value": row["customer"]
                })
                
                debug_print(f"Marked customer {row['customer']} (OrigRowNum {orig_row}) for removal - identical to customer {group.iloc[0]['customer']}")
    
    # Clean up temporary column
    cleaned_df.drop(columns=["temp_data_key"], inplace=True)