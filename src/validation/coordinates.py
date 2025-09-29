"""Coordinate (latitude/longitude) validation functions."""

import pandas as pd
from src.config.settings import STATE_LAT_RANGES, STATE_LON_RANGES
from src.utils.logging import debug_print

def append_coordinate_error_with_tracking(error_msg, orig_row, col_name, value, idx, errors, flagged_cells):
    """Append error and flag cell with OrigRowNum tracking for coordinate validation."""
    error_entry = {
        "Row": orig_row,
        "Column": col_name,
        "Error": error_msg,
        "Value": str(value)
    }
    
    # Check for duplicates
    if not any(e["Row"] == error_entry["Row"] and e["Column"] == error_entry["Column"] and e["Error"] == error_entry["Error"] for e in errors):
        errors.append(error_entry)
        
        # Store OrigRowNum with the flagged cell (new format)
        flagged_cells[(idx, col_name)] = (error_msg, orig_row)
        debug_print(f"Coordinate validation error for OrigRowNum={orig_row}, col={col_name}: {error_msg}")

def is_float(value):
    """Check if a value can be converted to float."""
    if pd.isna(value):
        return False
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def reset_paired_coordinate(cleaned_df, idx, col, orig_row, errors, corrected_cells, flagged_cells, original_val, error_msg):
    """Reset paired coordinate to NA."""
    paired_col = "lon" if col == "lat" else "lat"
    paired_val = cleaned_df[paired_col].iloc[idx]
    if pd.notna(paired_val):
        cleaned_df.loc[idx, paired_col] = pd.NA
        corrected_cells[(idx, paired_col)] = {
            "row": int(cleaned_df["OrigRowNum"].iloc[idx]),
            "original": paired_val,
            "corrected": None,
            "type": "Paired Coordinate Reset",
            "status": "Valid"
        }
        append_coordinate_error_with_tracking(f"Paired coordinate reset due to invalid {col}", orig_row, paired_col, paired_val, idx, errors, flagged_cells)


def validate_coordinates(cleaned_df, errors, corrected_cells, flagged_cells):
    """Validate latitude and longitude columns."""
    for idx, row in cleaned_df.iterrows():
        orig_row = row["OrigRowNum"]
        state = row["state"].strip().upper() if pd.notna(row["state"]) else ""
        for col in ["lat", "lon"]:
            val = row[col]
            if pd.isna(val) or val == "":
                continue
            if not is_float(val):
                try:
                    cleaned_val = str(val).strip().strip("'\"")
                    float_val = float(cleaned_val)
                    cleaned_df.loc[idx, col] = float_val
                    is_valid, error_msg = validate_coordinate_value(float_val, col, state)
                    corrected_cells[(idx, col)] = {
                        "row": int(cleaned_df["OrigRowNum"].iloc[idx]),
                        "original": val,
                        "corrected": float_val,
                        "type": "Float Conversion",
                        "status": "Valid" if is_valid else "Still Invalid"
                    }
                    if not is_valid:
                        append_coordinate_error_with_tracking(error_msg, orig_row, col, str(float_val), idx, errors, flagged_cells)
                except ValueError:
                    cleaned_df.loc[idx, col] = pd.NA
                    corrected_cells[(idx, col)] = {
                        "row": int(cleaned_df["OrigRowNum"].iloc[idx]),
                        "original": val,
                        "corrected": None,
                        "type": "Invalid Value Replacement",
                        "status": "Valid"
                    }
                    append_coordinate_error_with_tracking(f"{col.capitalize()} must be a number", orig_row, col, val, idx, errors, flagged_cells)
                    reset_paired_coordinate(cleaned_df, idx, col, orig_row, errors, corrected_cells, flagged_cells, val, f"{col.capitalize()} must be a number")
            else:
                float_val = float(val)
                is_valid, error_msg = validate_coordinate_value(float_val, col, state)
                if not is_valid:
                    neighbor_indices = [idx - 1, idx + 1] if 0 < idx < len(cleaned_df) - 1 else [idx - 1] if idx > 0 else [idx + 1] if idx < len(cleaned_df) - 1 else []
                    valid_neighbors = [float(cleaned_df[col].iloc[n_idx]) for n_idx in neighbor_indices if n_idx >= 0 and is_float(cleaned_df[col].iloc[n_idx])]
                    if valid_neighbors and any(abs(abs(float_val) - abs(n_val)) < 2 for n_val in valid_neighbors):
                        corrected_val = -float_val
                        is_valid, error_msg = validate_coordinate_value(corrected_val, col, state)
                        if is_valid:
                            cleaned_df.loc[idx, col] = corrected_val
                            corrected_cells[(idx, col)] = {
                                "row": int(cleaned_df["OrigRowNum"].iloc[idx]),
                                "original": val,
                                "corrected": corrected_val,
                                "type": "Sign Flip",
                                "status": "Valid"
                            }
                        else:
                            cleaned_df.loc[idx, col] = pd.NA
                            corrected_cells[(idx, col)] = {
                                "row": int(cleaned_df["OrigRowNum"].iloc[idx]),
                                "original": val,
                                "corrected": None,
                                "type": "Invalid Value Replacement",
                                "status": "Valid"
                            }
                            append_coordinate_error_with_tracking(error_msg, orig_row, col, val, idx, errors, flagged_cells)
                            reset_paired_coordinate(cleaned_df, idx, col, orig_row, errors, corrected_cells, flagged_cells, val, error_msg)
                    else:
                        cleaned_df.loc[idx, col] = pd.NA
                        corrected_cells[(idx, col)] = {
                            "row": int(cleaned_df["OrigRowNum"].iloc[idx]),
                            "original": val,
                            "corrected": None,
                            "type": "Invalid Value Replacement",
                            "status": "Valid"
                        }
                        append_coordinate_error_with_tracking(error_msg, orig_row, col, val, idx, errors, flagged_cells)
                        reset_paired_coordinate(cleaned_df, idx, col, orig_row, errors, corrected_cells, flagged_cells, val, error_msg)


def validate_coordinate_value(value, col, state):
    """Validate a coordinate value against state ranges."""
    if col == "lat":
        if state in STATE_LAT_RANGES:
            lat_min, lat_max = STATE_LAT_RANGES[state]
            if state == "AS" and value >= 0 and value != 0:
                return False, "Latitude for AS must be negative"
            if state != "AS" and value < 0 and value != 0:
                return False, f"Latitude for {state} must be positive"
            if not (lat_min <= value <= lat_max):
                return False, f"Latitude for {state} must be between {lat_min} and {lat_max}"
        elif not (-90 <= value <= 90):
            return False, "Latitude must be between -90 and 90"
    elif col == "lon":
        if state in STATE_LON_RANGES:
            lon_min, lon_max = STATE_LON_RANGES[state]
            if state not in ["GU", "MP"] and value > 0:
                return False, f"Longitude for {state} must be negative"
            if not (lon_min <= value <= lon_max):
                return False, f"Longitude for {state} must be between {lon_min} and {lon_max}"
    return True, ""