"""Validation report generation functions."""

import pandas as pd
import numpy as np
import json
import time
import traceback
import os
from datetime import datetime
from src.utils.logging import debug_print
from src.utils.file_handling import save_csv
from src.config.settings import get_validation_threshold, is_address_column, ADDRESS_COLUMNS


def convert_numpy_types(obj):
    """Convert NumPy types to Python native types."""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif pd.isna(obj):
        return None
    return obj


def load_error_dictionary():
    """Load error dictionary from CSV file if it exists."""
    try:
        # Try multiple possible paths for the CSV file
        possible_paths = [
            "config/Code_Response_Dictionary.csv",  # Original path
            "src/config/Code_Response_Dictionary.csv",  # Path relative to project root
            os.path.join(os.path.dirname(__file__), "..", "..", "config", "Code_Response_Dictionary.csv"),  # Relative to this file
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "Code_Response_Dictionary.csv")  # Relative to src directory
        ]
        
        for csv_path in possible_paths:
            if os.path.exists(csv_path):
                debug_print(f"Loading error dictionary from {csv_path}")
                error_dict = pd.read_csv(csv_path)
                debug_print(f"Loaded {len(error_dict)} error descriptions")
                return error_dict
        
        debug_print(f"Error dictionary not found in any of these paths: {possible_paths}")
        return None
    except Exception as e:
        debug_print(f"Failed to load error dictionary: {str(e)}")
        return None


def assess_file_validation_status(cleaned_df, cell_fills, rows_excluded_from_excel):
    """
    Assess the final validation status of the Corrected_Subscribers.xlsx file.
    
    Determines if the file is ready for FCC BDC submission based on:
    1. RED/PINK errors in non-address fields = immediate "Invalid"
    2. RED/PINK errors in address fields = threshold-based decision
    
    Args:
        cleaned_df (pd.DataFrame): The final cleaned subscriber DataFrame
        cell_fills (dict): Dictionary of Excel cell fills {(row, col): (priority, fill_color)}
        rows_excluded_from_excel (set): Row numbers excluded from final Excel output
        
    Returns:
        dict: {
            'file_status': str,  # 'Valid' or 'Invalid'
            'validation_reason': str,  # Explanation of the decision
            'total_subscribers': int,
            'address_error_count': int,
            'non_address_error_count': int,
            'address_error_percentage': float,
            'threshold_used': dict,
            'problematic_address_rows': list,  # CHANGED: Convert set to list for JSON serialization
            'requires_manual_review': bool
        }
    """
    
    # Get column mapping from DataFrame
    df_columns = list(cleaned_df.columns)
    col_name_to_excel_col = {col: idx + 1 for idx, col in enumerate(df_columns)}
    
    # Create mapping from OrigRowNum to Excel row number
    orig_row_to_excel_row = {}
    for idx, row in cleaned_df.iterrows():
        excel_row = idx + 2  # Excel rows start at 2 (after header)
        orig_row = row["OrigRowNum"]
        orig_row_to_excel_row[orig_row] = excel_row
    
    # Count total subscribers in final file
    total_subscribers = len(cleaned_df)
    
    # Track problematic rows
    address_error_rows = set()
    non_address_error_rows = set()
    
    # Analyze cell fills for RED and PINK priorities
    for (excel_row, excel_col_letter), (priority_level, fill_color) in cell_fills.items():
        # Only consider RED (priority 1) and PINK (priority 2) fills
        if priority_level not in [1, 2]:
            continue
            
        # Convert Excel column letter to column index
        import openpyxl.utils
        excel_col_idx = openpyxl.utils.column_index_from_string(excel_col_letter)
        
        # Find the DataFrame column name
        if excel_col_idx <= len(df_columns):
            col_name = df_columns[excel_col_idx - 1]
            
            # Find the original row number for this Excel row
            orig_row = None
            for orig, ex_row in orig_row_to_excel_row.items():
                if ex_row == excel_row:
                    orig_row = orig
                    break
            
            if orig_row is not None:
                # Categorize the error
                # IMPORTANT: We count ALL errors, even in excluded rows
                # Non-address errors should fail validation regardless of whether row was excluded
                if is_address_column(col_name):
                    address_error_rows.add(orig_row)
                else:
                    non_address_error_rows.add(orig_row)
    
    # Calculate metrics
    address_error_count = len(address_error_rows)
    non_address_error_count = len(non_address_error_rows)
    address_error_percentage = (address_error_count / total_subscribers * 100) if total_subscribers > 0 else 0.0
    
    # Get threshold configuration
    threshold_config = get_validation_threshold(total_subscribers)
    
    # Determine file status
    if non_address_error_count > 0:
        # Any non-address errors = immediate invalid
        file_status = "Invalid"
        validation_reason = f"File contains {non_address_error_count} rows with critical errors in required fields (customer, speeds, technology, etc.) that must be manually corrected."
        requires_manual_review = True
        
    elif address_error_percentage <= threshold_config["max_error_percentage"]:
        # Address errors within threshold = valid (remove problematic rows)
        file_status = "Valid"
        if address_error_count == 0:
            validation_reason = "File passed all validations and is ready for FCC BDC submission."
        else:
            validation_reason = f"File is valid after removing {address_error_count} rows ({address_error_percentage:.2f}%) with address issues. Remaining data is ready for FCC BDC submission."
        requires_manual_review = False
        
    else:
        # Address errors exceed threshold = invalid
        file_status = "Invalid"
        validation_reason = f"File contains {address_error_count} rows ({address_error_percentage:.2f}%) with address issues, exceeding the {threshold_config['max_error_percentage']}% threshold for {total_subscribers} subscribers. Manual address review required."
        requires_manual_review = True
    
    return {
        'file_status': file_status,
        'validation_reason': validation_reason,
        'total_subscribers': total_subscribers,
        'address_error_count': address_error_count,
        'non_address_error_count': non_address_error_count,
        'address_error_percentage': round(address_error_percentage, 2),
        'threshold_used': threshold_config,
        'problematic_address_rows': list(address_error_rows),  # FIXED: Convert set to list
        'requires_manual_review': requires_manual_review
    }


def generate_validation_report(cleaned_df, company_id, base_filename, errors, start_time, corrected_cells, flagged_cells, pobox_errors, non_unique_row_removals, smarty_results=None, duplicate_removals=None):
    """Generate validation report in Excel and JSON formats."""
    vr_excel_path = f"{company_id}/{base_filename}_VR.xlsx"
    vr_json_path = f"{company_id}/{base_filename}_VR.json"

    try:
        # Create a copy of the DataFrame and convert all columns to native Python types
        cleaned_df = cleaned_df.copy()
        for col in cleaned_df.columns:
            if cleaned_df[col].dtype == "int64":
                cleaned_df[col] = cleaned_df[col].astype(int)
            elif cleaned_df[col].dtype == "float64":
                cleaned_df[col] = cleaned_df[col].astype(float)
            cleaned_df[col] = cleaned_df[col].apply(convert_numpy_types)

        # Convert other data structures
        pobox_errors_converted = [convert_numpy_types(error) for error in pobox_errors]
        duplicate_removals_converted = [convert_numpy_types(removal) for removal in (duplicate_removals or [])]

        # Deduplicate errors to prevent repetition
        debug_print(f"Raw errors before deduplication: {len(errors)}")
        unique_errors = {f"{e['Row']}_{e['Column']}_{e['Error']}_{e['Value']}": e for e in errors}
        debug_print(f"Deduplicated {len(errors) - len(unique_errors)} errors. Unique errors: {len(unique_errors)}")
        errors_converted = [convert_numpy_types(error) for error in unique_errors.values()]
        street_ending_errors = [error for error in errors_converted if error["Error"] == "Lacks standard street ending"]
        filtered_errors_converted = [error for error in errors_converted if error["Error"] != "Lacks standard street ending"]
        non_unique_row_removals_converted = [convert_numpy_types(removal) for removal in non_unique_row_removals]
        
        # Create a mapping from original row index to new index based on OrigRowNum
        orig_row_to_new_idx = {row["OrigRowNum"]: i for i, row in cleaned_df.iterrows()}
        corrected_cells_converted_raw = {}
        for k, v in corrected_cells.items():
            orig_row = v.get("row", None)  # Get OrigRowNum from correction info
            if orig_row is not None and orig_row in orig_row_to_new_idx:
                new_idx = orig_row_to_new_idx[orig_row]
                corrected_cells_converted_raw[k] = {
                    **convert_numpy_types(v),
                    "row": int(cleaned_df["OrigRowNum"].iloc[new_idx])
                }
            else:
                debug_print(f"Skipping correction for row {orig_row}: not found in cleaned_df")
                corrected_cells_converted_raw[k] = {**convert_numpy_types(v), "row": None}

        # Filter out corrections with row: None
        corrected_cells_converted = {
            k: v for k, v in corrected_cells_converted_raw.items()
            if v.get("row") is not None
        }
        
        flagged_cells_converted = {k: convert_numpy_types(v) for k, v in flagged_cells.items()}

        # Build invalid address removals
        invalid_address_removals = [
            {
                "OrigRowNum": int(error["Row"]),
                "address": error["Value"],
                "Error": error["Error"]
            }
            for error in errors_converted
            if error["Row"] != "N/A" and error["Error"] in [
                "Address too short",
                "Unsupported character detected",
                "Non-address content detected",
                "Address lacks leading number followed by street name"
            ]
        ]
        unique_invalid_addresses = {f"{r['OrigRowNum']}_{r['address']}_{r['Error']}": r for r in invalid_address_removals}
        invalid_address_removals_converted = list(unique_invalid_addresses.values())

        # Process Smarty results
        smarty_corrections_data = []
        smarty_summary = {}
        
        if smarty_results:
            debug_print(f"Processing Smarty results for reporting: {smarty_results}")
            
            # Convert Smarty corrections to processing log format
            smarty_corrections_data = [
                {
                    "OrigRowNum": correction.get("orig_row", "N/A"),
                    "Original Address": correction.get("original_address", ""),
                    "Corrected Address": correction.get("corrected_address", "") if correction.get("success") else "Invalid",
                    "Status": "Valid" if correction.get("success") else "Invalid",
                    "Error Message": correction.get("error", "") if not correction.get("success") else "",
                    "Smarty Key": correction.get("smarty_key", ""),
                    "Timestamp": correction.get("timestamp", "")
                }
                for correction in smarty_results.get("smarty_corrections", [])
            ]
            
            # Smarty summary statistics
            smarty_summary = {
                "Addresses Sent to Smarty": smarty_results.get("addresses_sent", 0),
                "Successful Corrections": smarty_results.get("successful_corrections", 0),
                "Failed Corrections": smarty_results.get("failed_corrections", 0),
                "Loss Rate (%)": round(smarty_results.get("loss_rate", 0.0), 2),
                "Action Taken": smarty_results.get("action_taken", "NONE"),
                "Processing Time (seconds)": round(smarty_results.get("processing_time", 0.0), 2)
            }
        else:
            smarty_summary = {
                "Addresses Sent to Smarty": 0,
                "Successful Corrections": 0,
                "Failed Corrections": 0,
                "Loss Rate (%)": 0.0,
                "Action Taken": "SMARTY_NOT_PROCESSED",
                "Processing Time (seconds)": 0.0
            }

        # Generate Excel file to get cell_fills data for validation assessment
        debug_print("Generating Excel file to assess validation status...")
        
        # Collect all rows to exclude (same logic as in file_handling.py)
        all_rows_to_exclude = set().union(
            int(error["Row"]) for error in pobox_errors_converted if error["Row"] != "N/A"
        ).union(
            int(removal["OrigRowNum"]) for removal in non_unique_row_removals_converted if removal["OrigRowNum"] != "N/A"
        )
        
        # Add Smarty removal rows if applicable
        if smarty_results and smarty_results.get('action_taken') == 'REMOVE_INVALID_ROWS':
            smarty_removal_rows = [
                correction.get('orig_row') for correction in smarty_results.get('smarty_corrections', [])
                if not correction.get('success') and correction.get('orig_row')
            ]
            all_rows_to_exclude.update(smarty_removal_rows)
        
        # Check for critical non-address errors BEFORE any row exclusions
        # This ensures we catch misaligned columns and other critical errors
        debug_print("Checking for critical non-address errors in all flagged cells...")
        critical_non_address_errors = set()

        from src.utils.file_handling import get_error_priority_and_fill
        from src.config.settings import is_address_column

        for (row_idx, col_name), cell_data in flagged_cells_converted.items():
            if isinstance(cell_data, tuple):
                error_msg, orig_row_stored = cell_data
            else:
                error_msg = cell_data
                orig_row_stored = None
                if row_idx < len(cleaned_df):
                    orig_row_stored = cleaned_df["OrigRowNum"].iloc[row_idx]

            if orig_row_stored:
                priority_level, fill_color = get_error_priority_and_fill(error_msg, col_name)

                # Check for RED (priority 1) or PINK (priority 2) cells in non-address columns
                if priority_level in [1, 2] and not is_address_column(col_name):
                    critical_non_address_errors.add(orig_row_stored)
                    debug_print(f"Critical non-address error found: OrigRowNum={orig_row_stored}, col={col_name}, error={error_msg}")

        # If there are critical non-address errors, fail immediately
        if critical_non_address_errors:
            debug_print(f"File validation FAILED: {len(critical_non_address_errors)} rows with critical non-address errors")
            file_validation = {
                'file_status': 'Invalid',
                'validation_reason': f"File contains {len(critical_non_address_errors)} rows with critical errors in required fields (customer, state, speeds, technology, etc.) that must be manually corrected. This includes column misalignment and invalid data.",
                'total_subscribers': len(cleaned_df),
                'address_error_count': 0,
                'non_address_error_count': len(critical_non_address_errors),
                'address_error_percentage': 0.0,
                'threshold_used': {},
                'problematic_address_rows': [],
                'requires_manual_review': True
            }
        else:
            # Simulate cell fills logic for address-only validation (based on save_excel function)
            temp_cell_fills = {}

            for (row_idx, col_name), cell_data in flagged_cells_converted.items():
                if isinstance(cell_data, tuple):
                    error_msg, orig_row_stored = cell_data
                else:
                    error_msg = cell_data
                    orig_row_stored = None
                    if row_idx < len(cleaned_df):
                        orig_row_stored = cleaned_df["OrigRowNum"].iloc[row_idx]

                if orig_row_stored and orig_row_stored not in all_rows_to_exclude:
                    # Find Excel row position
                    orig_row_to_excel_row = {row["OrigRowNum"]: i + 2 for i, row in cleaned_df.iterrows() if row["OrigRowNum"] not in all_rows_to_exclude}

                    if orig_row_stored in orig_row_to_excel_row:
                        excel_row = orig_row_to_excel_row[orig_row_stored]
                        col_map = {col: idx + 1 for idx, col in enumerate(cleaned_df.columns)}

                        if col_name in col_map:
                            import openpyxl.utils
                            excel_col = openpyxl.utils.get_column_letter(col_map[col_name])

                            # Determine priority using existing logic
                            priority_level, fill_color = get_error_priority_and_fill(error_msg, col_name)

                            cell_key = (excel_row, excel_col)
                            if cell_key not in temp_cell_fills or priority_level < temp_cell_fills[cell_key][0]:
                                temp_cell_fills[cell_key] = (priority_level, fill_color)

            # Assess file validation status
            debug_print("Assessing file validation status...")
            file_validation = assess_file_validation_status(
                cleaned_df, temp_cell_fills, all_rows_to_exclude
            )
        
        # Update rows to exclude based on validation decision
        if file_validation['file_status'] == 'Valid' and file_validation['problematic_address_rows']:
            debug_print(f"File deemed valid - removing {len(file_validation['problematic_address_rows'])} problematic address rows")
            all_rows_to_exclude.update(file_validation['problematic_address_rows'])
            
            # Add removed rows to invalid address removals for reporting
            for orig_row in file_validation['problematic_address_rows']:
                if orig_row in cleaned_df['OrigRowNum'].values:
                    row_data = cleaned_df[cleaned_df['OrigRowNum'] == orig_row].iloc[0]
                    invalid_address_removals_converted.append({
                        "OrigRowNum": int(orig_row),
                        "address": str(row_data.get('address', '')),
                        "Error": "Address validation failed - removed per threshold policy"
                    })

        # Debug: Log input data and file path
        debug_print(f"Preparing JSON report: cleaned_df rows={len(cleaned_df)}, errors={len(errors_converted)}, corrections={len(corrected_cells_converted)}, pobox_errors={len(pobox_errors_converted)}, invalid_removals={len(invalid_address_removals_converted)}, non_unique_removals={len(non_unique_row_removals_converted)}, smarty_corrections={len(smarty_corrections_data)}, json_path={vr_json_path}")

        # Build summary (MODIFIED to include file validation status)
        # NEW: Count PR auto-accepts
        pr_auto_accepts = sum(1 for info in corrected_cells_converted.values() if info.get("type") == "PR Address Auto-Accept")

        summary = {
            "Total Rows Processed": int(len(cleaned_df) + len(pobox_errors_converted) + len(non_unique_row_removals_converted) + len(invalid_address_removals_converted) + len(duplicate_removals_converted)),
            "Rows with Corrections": int(len(set(v["row"] for k, v in corrected_cells_converted.items() if v["status"] == "Valid" and v.get("row") in cleaned_df["OrigRowNum"].values))),
            "Rows with Errors": int(len(set(error["Row"] for error in errors_converted if error["Row"] != "N/A" and int(error["Row"]) in cleaned_df["OrigRowNum"].values))),
            "PO Box Rows Removed": int(len(pobox_errors_converted)),
            "Invalid Address Rows Removed": int(len(invalid_address_removals_converted)),
            "Duplicate Rows Removed (Full & Customer-based)": int(len(duplicate_removals_converted)),
            "Removed Duplicate Rows": int(len(non_unique_row_removals_converted)),
            "PR Addresses Auto-Accepted": pr_auto_accepts,  # NEW
            "Total Corrections": int(len(corrected_cells_converted)),
            "Total Errors": int(len(filtered_errors_converted)),
            "Street Ending Errors": int(len(street_ending_errors)),
            "Validation Time (seconds)": round(time.time() - start_time, 2),
            "Validation Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            **smarty_summary,  # Add Smarty summary to main summary
            # File validation status fields
            "File Status": file_validation['file_status'],
            "Validation Reason": file_validation['validation_reason'],
            "Total Subscribers in Final File": file_validation['total_subscribers'],
            "Address Errors Found": file_validation['address_error_count'],
            "Non-Address Errors Found": file_validation['non_address_error_count'],
            "Address Error Percentage": file_validation['address_error_percentage'],
            "Threshold Used": f"{file_validation['threshold_used']['max_error_percentage']}% for {file_validation['threshold_used']['min_subscribers']}-{file_validation['threshold_used']['max_subscribers']} subscribers",
            "Requires Manual Review": file_validation['requires_manual_review']
        }

        # Debug: Log summary metrics
        debug_print(f"Summary metrics: {summary}")
        debug_print(f"File validation status: {file_validation['file_status']} - {file_validation['validation_reason']}")

        # Build corrections data
        corrections_data = [
            {
                "Row": int(cleaned_df["OrigRowNum"].iloc[row_idx]) if row_idx < len(cleaned_df) else "N/A",
                "Column": col_name,
                "Original Value": info["original"],
                "Corrected Value": info["corrected"],
                "Correction Type": info["type"],
                "Status": info["status"]
            }
            for (row_idx, col_name), info in corrected_cells_converted.items()
        ]

        # Load error dictionary
        error_dict = load_error_dictionary()

        # Save Excel report
        with pd.ExcelWriter(vr_excel_path, engine="openpyxl") as writer:
            # Summary tab
            pd.DataFrame(list(summary.items()), columns=["Metric", "Value"]).to_excel(writer, sheet_name="Summary", index=False)
            
            # Corrections tab
            corrections_df = pd.DataFrame(corrections_data).sort_values(by=["Row", "Column"]) if corrections_data else pd.DataFrame(columns=["Row", "Column", "Original Value", "Corrected Value", "Correction Type", "Status"])
            corrections_df.to_excel(writer, sheet_name="Corrections", index=False)
            
            # Smarty Processing Log tab
            if smarty_corrections_data:
                smarty_processing_log_df = pd.DataFrame(smarty_corrections_data).sort_values(by="OrigRowNum")
            else:
                smarty_processing_log_df = pd.DataFrame(columns=[
                    "OrigRowNum", 
                    "Original Address", 
                    "Corrected Address", 
                    "Original ZIP",      # NEW
                    "Corrected ZIP",     # NEW
                    "Status", 
                    "Error Message", 
                    "Smarty Key", 
                    "Timestamp"
                ])

            # Also update the smarty_corrections_data creation in reporting.py:
            smarty_corrections_data = [
                {
                    "OrigRowNum": correction.get("orig_row", "N/A"),
                    "Original Address": correction.get("original_address", ""),
                    "Corrected Address": correction.get("corrected_address", "") if correction.get("success") else "Invalid",
                    "Original ZIP": correction.get("original_zip", ""),        # NEW
                    "Corrected ZIP": correction.get("corrected_zip", ""),      # NEW
                    "Status": "Valid" if correction.get("success") else "Invalid",
                    "Error Message": correction.get("error", "") if not correction.get("success") else "",
                    "Smarty Key": correction.get("smarty_key", ""),
                    "Timestamp": correction.get("timestamp", "")
                }
                for correction in smarty_results.get("smarty_corrections", [])
            ]
            smarty_processing_log_df.to_excel(writer, sheet_name="Smarty Processing Log", index=False)
            
            # Error Reference tab
            if error_dict is not None:
                error_dict.to_excel(writer, sheet_name="Error Reference", index=False)
                debug_print(f"Added Error Reference tab with {len(error_dict)} entries")
            else:
                empty_ref_df = pd.DataFrame(columns=["Error_Message", "Column", "Category", "Description", "Resolution", "Severity"])
                empty_ref_df.to_excel(writer, sheet_name="Error Reference", index=False)
                debug_print("Created empty Error Reference tab (dictionary not found)")
            
            # Errors tab
            filtered_errors_df = pd.DataFrame(filtered_errors_converted).sort_values(by=["Row", "Column"]) if filtered_errors_converted else pd.DataFrame(columns=["Row", "Column", "Error", "Value"])
            filtered_errors_df.to_excel(writer, sheet_name="Errors", index=False)
            
            # Street Ending Errors tab
            street_ending_df = pd.DataFrame(street_ending_errors).sort_values(by=["Row", "Column"]) if street_ending_errors else pd.DataFrame(columns=["Row", "Column", "Error", "Value"])
            street_ending_df.to_excel(writer, sheet_name="Street Ending Errors", index=False)
            
            # PO Box Errors tab
            pobox_df = pd.DataFrame(pobox_errors_converted).sort_values(by="Row") if pobox_errors_converted else pd.DataFrame(columns=["Row", "Column", "Error", "Value"])
            pobox_df.to_excel(writer, sheet_name="PO Box Errors", index=False)
            
            # Invalid Address Removals tab
            invalid_address_df = pd.DataFrame(invalid_address_removals_converted).sort_values(by="OrigRowNum") if invalid_address_removals_converted else pd.DataFrame(columns=["OrigRowNum", "address", "Error"])
            invalid_address_df.to_excel(writer, sheet_name="Invalid Address Removals", index=False)
            
            # Non-Unique Row Removals tab
            non_unique_df = pd.DataFrame(non_unique_row_removals_converted).sort_values(by="OrigRowNum") if non_unique_row_removals_converted else pd.DataFrame(columns=["OrigRowNum", "customer", "lat", "lon", "address", "city", "state", "zip", "download", "upload", "voip_lines_quantity", "business_customer", "technology", "Error"])
            non_unique_df.to_excel(writer, sheet_name="Non-Unique Row Removals", index=False)

            # Duplicate Rows Removed tab (exact duplicates and customer-based duplicates)
            duplicate_removals_df = pd.DataFrame(duplicate_removals_converted).sort_values(by="OrigRowNum") if duplicate_removals_converted else pd.DataFrame(columns=["OrigRowNum", "Reason", "Duplicate_Of_Row", "Customer_ID", "Address", "Download_Speed", "Upload_Speed", "Technology"])
            duplicate_removals_df.to_excel(writer, sheet_name="Duplicate Rows Removed", index=False)

            # Auto-size columns for all sheets
            wb = writer.book
            for sheet in wb.sheetnames:
                ws = wb[sheet]
                for col in ws.columns:
                    max_length = max(len(str(cell.value)) for cell in col if cell.value is not None)
                    ws.column_dimensions[col[0].column_letter].width = min(max_length + 2, 50)

        # Save JSON report
        json_report = {
            "Summary": convert_numpy_types(summary),
            "File Validation Details": convert_numpy_types(file_validation),
            "Corrections": corrections_data,
            "Errors": filtered_errors_converted,
            "Street Ending Errors": street_ending_errors,
            "PO Box Errors": pobox_errors_converted,
            "Invalid Address Removals": invalid_address_removals_converted,
            "Non-Unique Row Removals": non_unique_row_removals_converted,
            "Duplicate Rows Removed": duplicate_removals_converted,
            "Smarty Corrections": smarty_corrections_data
        }

        # Debug: Log JSON serialization attempt
        debug_print(f"Attempting JSON serialization for {vr_json_path}, data size: {len(str(json_report))}")
        try:
            json.dumps(json_report, indent=4, ensure_ascii=False)
            debug_print("JSON serialization successful")
        except Exception as e:
            debug_print(f"JSON serialization failed: {str(e)}")
            raise

        with open(vr_json_path, 'w', encoding='utf-8') as f:
            json.dump(json_report, f, indent=4, ensure_ascii=False)

        debug_print(f"Successfully saved validation report: {vr_excel_path}, {vr_json_path}")
        debug_print(f"Final file status: {file_validation['file_status']}")
        
        # Return validation status along with file paths
        return vr_excel_path, vr_json_path, file_validation
        
    except Exception as e:
        errors.append({
            "Row": "N/A",
            "Column": "N/A",
            "Error": f"Error generating validation report: {str(e)}",
            "Value": "N/A"
        })
        debug_print(f"Exception generating validation report: {traceback.format_exc()}")
        return None, None, {'file_status': 'Error', 'validation_reason': f'Report generation failed: {str(e)}'}