"""Address validation functions."""

import re
import pandas as pd
from src.config.settings import PO_BOX, RURAL_ROUTES, STREET_ENDINGS, SPECIFIC_ROAD_PATTERN, FORBIDDEN_CHARS, VALID_STATES, NON_STANDARD_ENDINGS
from src.utils.logging import debug_print
from src.validation.smarty_validation import SMARTY_ELIGIBLE_ERRORS

def append_error_with_tracking(error_msg, orig_row, col_name, value, idx, errors, flagged_cells):
    """Append error and flag cell with OrigRowNum tracking."""
    error_entry = {
        "Row": orig_row,
        "Column": col_name,
        "Error": error_msg,
        "Value": value
    }
    
    # Check for duplicates
    if not any(e["Row"] == error_entry["Row"] and e["Column"] == error_entry["Column"] and e["Error"] == error_entry["Error"] for e in errors):
        errors.append(error_entry)
        
        # Store OrigRowNum with the flagged cell (new format)
        flagged_cells[(idx, col_name)] = (error_msg, orig_row)
        debug_print(f"Address error for OrigRowNum={orig_row}: {error_msg}, Value={value}")

def normalize_compass_directions(address):
    """Convert full compass directions to single letters."""
    if not address:
        return address
    
    # Dictionary for compass direction conversions
    compass_conversions = {
        r'\bNORTH\b': 'N',
        r'\bSOUTH\b': 'S', 
        r'\bEAST\b': 'E',
        r'\bWEST\b': 'W',
        r'\bNORTHEAST\b': 'NE',
        r'\bNORTHWEST\b': 'NW',
        r'\bSOUTHEAST\b': 'SE',
        r'\bSOUTHWEST\b': 'SW'
    }
    
    normalized_address = address
    for pattern, replacement in compass_conversions.items():
        normalized_address = re.sub(pattern, replacement, normalized_address, flags=re.IGNORECASE)
    
    return normalized_address

def validate_address(address, orig_row, idx, errors, corrected_cells, flagged_cells, pobox_errors, rows_to_remove, is_correction=False, non_standard_only=False, state=None):
    """Validate an address and correct non-standard endings."""
    debug_print(f"Validating address for OrigRowNum={orig_row}: '{address}' (is_correction={is_correction}, non_standard_only={non_standard_only})")
    original_address = address
    validation_passed = True

    def append_error(error_msg):
        """Append error with OrigRowNum tracking."""
        append_error_with_tracking(error_msg, orig_row, "address", address, idx, errors, flagged_cells)

    # Pre-filtering: Normalize whitespace
    if pd.notna(address):
        normalized_address = re.sub(r"\s+", " ", address.strip())
        address = normalized_address
        debug_print(f"Normalized whitespace for OrigRowNum={orig_row}: '{original_address}' -> '{address}'")

    # Pre-filtering: Convert to uppercase
    if pd.notna(address):
        upper_address = address.upper()
        if upper_address != address:
            corrected_cells[(idx, "address")] = {
                "row": int(orig_row),
                "original": address,
                "corrected": upper_address,
                "type": "Case Normalization",
                "status": "Valid"
            }
            address = upper_address
            debug_print(f"Converted to uppercase for OrigRowNum={orig_row}: '{original_address}' -> '{address}'")

    # Pre-filtering: Remove forbidden characters (MOVED UP - before other processing)
    if pd.notna(address):
        forbidden_chars_to_remove = r'[@$%*=<>\|\^~`\\\[\]{}\(\)\+".;,]|[^\w\s\.#&!/\'"]'
        cleaned_address = re.sub(forbidden_chars_to_remove, '', address)
        if cleaned_address != address:
            debug_print(f"Removed forbidden characters for OrigRowNum={orig_row}: '{address}' -> '{cleaned_address}'")
            address = cleaned_address

    # Pre-filtering - Normalize compass directions
    if pd.notna(address):
        pre_compass_normalization = address
        address = normalize_compass_directions(address)
        if address != pre_compass_normalization:
            corrected_cells[(idx, "address")] = {
                "row": int(orig_row),
                "original": pre_compass_normalization,
                "corrected": address,
                "type": "Compass Direction Normalization",
                "status": "Valid"
            }
            debug_print(f"Normalized compass directions for OrigRowNum={orig_row}: '{pre_compass_normalization}' -> '{address}'")

    # NEW: Early exit for Puerto Rico (PR) addresses after basic cleanups
    if state and state.upper() == "PR":
        # Record auto-accept for reporting
        corrected_cells[(idx, "address")] = {
            "row": int(orig_row),
            "original": original_address,
            "corrected": address,  # Use the cleaned version
            "type": "PR Address Auto-Accept",
            "status": "Valid"
        }
        debug_print(f"Auto-accepted PR address for OrigRowNum={orig_row}: '{address}'")
        return True  # Skip all further validation

    # Pre-filtering: Check minimum length
    if pd.notna(address) and len(address.replace(" ", "")) < 5:
        error_msg = "Corrected address is still invalid: Address too short" if is_correction else "Address too short"
        append_error(error_msg)
        rows_to_remove.append(orig_row)
        debug_print(f"Marked for removal due to short address for OrigRowNum={orig_row}: '{address}'")
        return False

    # Pre-filtering: Check for non-address patterns
    if pd.notna(address):
        non_address = re.search(r"\b(TBD|N/A|UNKNOWN)\b|\d{3}-\d{3}-\d{4}", address, re.IGNORECASE)
        if non_address:
            error_msg = "Corrected address is still invalid: Non-address content detected" if is_correction else "Non-address content detected"
            append_error(error_msg)
            rows_to_remove.append(orig_row)
            debug_print(f"Marked for removal due to non-address content for OrigRowNum={orig_row}: '{address}'")
            return False

    # Pre-filtering: Convert PR to PVT RD - FIXED TO RECORD AS CORRECTION
    if pd.notna(address):
        pre_pr_conversion = address  # Store address before PR conversion
        address = re.sub(r"(?i)\s+PR\s+", " PVT RD ", address.strip())
        if address != pre_pr_conversion:  # Compare with address just before PR conversion
            # FIXED: Record as correction instead of error
            corrected_cells[(idx, "address")] = {
                "row": int(orig_row),
                "original": pre_pr_conversion,
                "corrected": address,
                "type": "PR to PVT RD Conversion",
                "status": "Valid"
            }
            debug_print(f"PR converted to PVT RD for OrigRowNum={orig_row}: '{pre_pr_conversion}' -> '{address}'")

    # Pre-filtering: Convert Farm to Market patterns to FM
    if pd.notna(address):
        farm_to_market_original = address
        # Convert various Farm to Market patterns to FM
        address = re.sub(r"(?i)\bFarm\s*to\s*Market(?:\s*(?:Road|Rd))?\b", "FM", address)
        # Also handle the specific "FARM TO MARKET RD" pattern
        address = re.sub(r"(?i)\bFarm\s*to\s*Market\s*Rd\b", "FM", address)
    
        if address != farm_to_market_original:
            corrected_cells[(idx, "address")] = {
                "row": int(orig_row),
                "original": farm_to_market_original,
                "corrected": address,
                "type": "Farm to Market to FM",
                "status": "Valid"
            }
            debug_print(f"Farm to Market converted to FM for OrigRowNum={orig_row}: '{farm_to_market_original}' -> '{address}'")

    # Check for blank or whitespace-only
    if not address or address.strip() == "":
        error_msg = "Corrected address is still invalid: Blank or whitespace-only value" if is_correction else "Blank or whitespace-only value"
        append_error(error_msg)
        rows_to_remove.append(orig_row)
        debug_print(f"Marked for removal due to blank address for OrigRowNum={orig_row}: '{address}'")
        return False

    # Check for PO Box
    if re.search(PO_BOX, address, re.IGNORECASE):
        error_msg = "Corrected address is still invalid: PO Boxes not allowed" if is_correction else "PO Boxes not allowed"
        pobox_errors.append({
            "Row": orig_row,
            "Column": "address",
            "Error": error_msg,
            "Value": address
        })
        append_error(error_msg)
        rows_to_remove.append(orig_row)
        debug_print(f"Marked for removal due to PO Box for OrigRowNum={orig_row}: '{address}'")
        return False

    # Validate leading number and street name, allowing optional directional prefixes
    if pd.notna(address) and not is_correction:
        # Regex: Optional directional prefix (with optional space) followed by one or more digits and optional letter suffix
        leading_pattern = r"(?i)^(?:(N|S|E|W|NE|NW|SE|SW)\s?)?[0-9]+[A-Z]?"
        if not re.match(leading_pattern, address):
            error_msg = "Corrected address is still invalid: Address lacks leading number (optionally prefixed by direction) followed by street name" if is_correction else "Address lacks leading number (optionally prefixed by direction) followed by street name"
            append_error(error_msg)
            rows_to_remove.append(orig_row)
            debug_print(f"Marked for removal due to invalid leading number/street name for OrigRowNum={orig_row}: '{address}'")
            return False

        # NEW PRIMARY LOGIC: Street ending validation and extension removal
    # Run the check in Phase 2 unless the address was corrected and validated in Phase 1
    should_check_street_ending = non_standard_only or (not is_correction and ((idx, "address") not in corrected_cells or corrected_cells[(idx, "address")].get("status") != "Valid"))
    if should_check_street_ending:
        debug_print(f"Checking street ending for OrigRowNum={orig_row}: Address='{address}', non_standard_only={non_standard_only}, is_correction={is_correction}, corrected_cells_status={corrected_cells.get((idx, 'address'), {}).get('status', 'N/A')}")

        # NEW: Check if address matches SPECIFIC_ROAD_PATTERN (highways, county roads, etc.) first
        specific_road_match = re.search(SPECIFIC_ROAD_PATTERN, address, re.IGNORECASE)
        if specific_road_match:
            debug_print(f"Specific road pattern matched for OrigRowNum={orig_row}: Address='{address}' (Highway/County Road/etc.)")
            validation_passed = True
        else:
            # Street endings already include required leading space in the pattern
            street_ending_matches = list(re.finditer(rf"(?:{STREET_ENDINGS})(?:\s|$)", address, re.IGNORECASE))
            compass_ending_matches = list(re.finditer(r"\b(?:N|NE|E|SE|S|SW|W|NW)\s+\d+\s+(?:N|NE|E|SE|S|SW|W|NW)\b$", address, re.IGNORECASE))
            number_number_compass_matches = list(re.finditer(r"\b\d+\s+\d+\s+(?:N|NE|E|SE|S|SW|W|NW)\b$", address, re.IGNORECASE))

            if street_ending_matches:
                debug_print(f"Street ending matched for OrigRowNum={orig_row}: Matches={street_ending_matches}")
                last_match = street_ending_matches[-1]
                ending_end = last_match.end()
                remaining = address[ending_end:].strip()

                # Validate street name before the ending
                address_before_ending = address[:last_match.start()].strip()
                # Regex: Optional directional prefix, house number (with optional letter suffix), followed by street name (letters, spaces, hyphens, apostrophes)
                street_name_pattern = r"(?i)^(?:(N|S|E|W|NE|NW|SE|SW)\s?)?\d+[A-Z]?\s+[\w\s'-]+"
                if re.match(street_name_pattern, address_before_ending):
                    debug_print(f"Valid street name found for OrigRowNum={orig_row}: '{address_before_ending}'")
                    validation_passed = True
                else:
                    error_msg = "Invalid street name format before street ending"
                    append_error(error_msg)
                    validation_passed = False
                    debug_print(f"Invalid street name for OrigRowNum={orig_row}: '{address_before_ending}'")

                # Check for permitted extensions after street ending
                if remaining:
                    permitted_pattern = (
                        r"^(?:"
                        r"\b(?:N|S|E|W|NE|NW|SE|SW|North|South|East|West|Northeast|Northwest|Southeast|Southwest)\b"
                        r"|(?:US|STATE)\s+(?:HWY|HIGHWAY|ROUTE|RT)\s+\d+"
                        r"|(?:US|STATE)\s+(?:HWY|HIGHWAY|ROUTE|RT)\s+\d+\s+(?:N|S|E|W|NE|NW|SE|SW|North|South|East|West|Northeast|Northwest|Southeast|Southwest)"
                        r"|\d+\s+(?:N|S|E|W|NE|NW|SE|SW|North|South|East|West|Northeast|Northwest|Southeast|Southwest)"
                        r"|\d+"  # Allow pure numeric extension (e.g., "140" after "CR")
                        r")(?:\s+(?:N|S|E|W|NE|NW|SE|SW|North|South|East|West|Northeast|Northwest|Southeast|Southwest))?$"
                    )
                    is_permitted = re.match(permitted_pattern, remaining, re.IGNORECASE)
                    if is_permitted:
                        validation_passed = True
                        debug_print(f"Permitted extension after street ending for OrigRowNum={orig_row}: '{remaining}'")
                    else:
                        corrected_address = address[:ending_end].strip()
                        corrected_cells[(idx, "address")] = {
                            "row": int(orig_row),
                            "original": address,
                            "corrected": corrected_address,
                            "type": "Non-Permitted Extension Removal After Street Ending",
                            "status": "Valid",
                            "removed_part": remaining
                        }
                        address = corrected_address
                        validation_passed = True
                        debug_print(f"Removed non-permitted extension after street ending for OrigRowNum={orig_row}: '{remaining}' -> Result: '{address}'")
            elif compass_ending_matches:
                debug_print(f"Compass pattern matched for OrigRowNum={orig_row}: Address='{address}'")
                validation_passed = True
            elif number_number_compass_matches:
                debug_print(f"Number-number-compass pattern matched for OrigRowNum={orig_row}: Address='{address}'")
                validation_passed = True
            else:
                error_msg = "Corrected address is still invalid: Lacks standard street ending" if is_correction else "Lacks standard street ending"
                append_error(error_msg)
                debug_print(f"No street ending or compass pattern match for OrigRowNum={orig_row}: Address='{address}'")
                validation_passed = False

    # Check for and remove non-standard endings only if street name is valid
    from src.config.settings import NON_STANDARD_ENDINGS
    if validation_passed:  # Only proceed if the address has a valid street name or ending
        non_standard_match = re.search(NON_STANDARD_ENDINGS, address, re.IGNORECASE)
        if non_standard_match:
            corrected_address = address[:non_standard_match.start(1)].strip()
            debug_print(f"DEBUG: Non-standard ending found in '{address}'")
            debug_print(f"DEBUG: Match groups: {non_standard_match.groups()}")
            debug_print(f"DEBUG: Corrected address: '{corrected_address}'")
            # Ensure the corrected address still has a valid street name (allow letter suffix on house number)
            street_name_check = re.match(r"(?i)^(?:(N|S|E|W|NE|NW|SE|SW)\s?)?\d+[A-Z]?\s+[\w\s\-']+", corrected_address)
            debug_print(f"DEBUG: Street name check result: {street_name_check is not None}")
            if street_name_check:
                corrected_cells[(idx, "address")] = {
                    "row": int(orig_row),
                    "original": address,
                    "corrected": corrected_address,
                    "type": "Non-Standard Ending Removal",
                    "status": "Valid"
                }
                debug_print(f"Removed non-standard ending for OrigRowNum={orig_row}: '{address}' -> '{corrected_address}'")
                address = corrected_address
            else:
                error_msg = "Corrected address lacks valid street name after non-standard ending removal"
                append_error(error_msg)
                validation_passed = False
                debug_print(f"Invalid corrected address after non-standard ending removal for OrigRowNum={orig_row}: '{corrected_address}'")

    # Additional checks for rural routes or specific road patterns
    if re.search(RURAL_ROUTES, address, re.IGNORECASE) or re.search(SPECIFIC_ROAD_PATTERN, address, re.IGNORECASE):
        debug_print(f"Matches RURAL_ROUTES or SPECIFIC_ROAD_PATTERN for OrigRowNum={orig_row}: '{address}'")
        # Don't override previous failure due to missing street ending
        if validation_passed:
            return True

    # Check for house number if street ending exists, allowing optional directional prefixes
    street_ending_match = re.search(rf"\s+(?:{STREET_ENDINGS})\.?(?:\s*$|\s+\S+)", address, re.IGNORECASE)
    if street_ending_match:
        address_before_ending = address[:street_ending_match.start()].strip()
        # Regex: Optional directional prefix (with optional space) followed by one or more digits and optional letter suffix
        house_number_pattern = r"(?i)^(?:(N|S|E|W|NE|NW|SE|SW)\s?)?\d+[A-Z]?"
        if not re.search(house_number_pattern, address_before_ending):
            error_msg = f"Corrected address is still invalid: No house number (optionally prefixed by direction)" if is_correction else "No house number (optionally prefixed by direction)"
            append_error(error_msg)
            rows_to_remove.append(orig_row)
            debug_print(f"Marked for removal due to no house number for OrigRowNum={orig_row}: '{address}'")
            return False

    # Check for forbidden characters (MOVED TO TOP - this is now redundant but kept for safety)
    forbidden = re.search(FORBIDDEN_CHARS, address)
    if forbidden:
        error_msg = "Corrected address is still invalid: Invalid format" if is_correction else "Invalid format"
        append_error(error_msg)
        # Row will be sent to Smarty for validation instead of immediate removal
        debug_print(f"Flagged for Smarty validation due to invalid format for OrigRowNum={orig_row}: '{address}'")
        return False

    # Final street ending check for ALL addresses (including Smarty corrections)
    # NEW: Check if address matches SPECIFIC_ROAD_PATTERN (highways, county roads, etc.) first
    specific_road_match = re.search(SPECIFIC_ROAD_PATTERN, address, re.IGNORECASE)

    if not specific_road_match:
        # Only check for standard street endings if it's not a specific road type
        final_street_ending_matches = list(re.finditer(rf"\s+(?:{STREET_ENDINGS})\b", address, re.IGNORECASE))
        compass_ending_matches = list(re.finditer(r"\b(?:N|NE|E|SE|S|SW|W|NW)\s+\d+\s+(?:N|NE|E|SE|S|SW|W|NW)\b$", address, re.IGNORECASE))
        number_number_compass_matches = list(re.finditer(r"\b\d+\s+\d+\s+(?:N|NE|E|SE|S|SW|W|NW)\b$", address, re.IGNORECASE))

        if not final_street_ending_matches and not compass_ending_matches and not number_number_compass_matches:
            error_msg = "Corrected address is still invalid: Lacks standard street ending" if is_correction else "Lacks standard street ending"
            append_error(error_msg)
            debug_print(f"Final check: No street ending or compass pattern match for OrigRowNum={orig_row}: Address='{address}' (is_correction={is_correction})")
            validation_passed = False
            # Mark for Smarty if not already a Smarty correction
            if is_correction:
                rows_to_remove.append(orig_row)
    else:
        debug_print(f"Final check: Specific road pattern matched for OrigRowNum={orig_row}: Address='{address}' (Highway/County Road/etc.) - skipping standard ending check")

    return validation_passed


# Updated validate_address_column in address.py
def validate_address_column(cleaned_df, errors, corrected_cells, flagged_cells, pobox_errors, rows_to_remove):
    for idx, val in enumerate(cleaned_df["address"].fillna("").astype(str).str.strip()):
        orig_row = cleaned_df["OrigRowNum"][idx]

        # Check if ALL address fields are empty (GPS-only row)
        address_empty = not val or val.strip() == ""
        city_empty = pd.isna(cleaned_df["city"].iloc[idx]) or str(cleaned_df["city"].iloc[idx]).strip() == ""
        state_empty = pd.isna(cleaned_df["state"].iloc[idx]) or str(cleaned_df["state"].iloc[idx]).strip() == ""
        zip_empty = pd.isna(cleaned_df["zip"].iloc[idx]) or str(cleaned_df["zip"].iloc[idx]).strip() == ""

        # If ALL address fields are empty, skip address validation (GPS-only row)
        if address_empty and city_empty and state_empty and zip_empty:
            debug_print(f"Skipping address validation for OrigRowNum={orig_row}: All address fields empty (GPS-only row)")
            continue

        state = cleaned_df["state"][idx]
        is_valid = validate_address(val, orig_row, idx, errors, corrected_cells, flagged_cells, pobox_errors, rows_to_remove, is_correction=False, non_standard_only=False, state=state)
        # Apply correction immediately if valid
        if (idx, "address") in corrected_cells and corrected_cells[(idx, "address")].get("status") == "Valid":
            cleaned_df.loc[idx, "address"] = corrected_cells[(idx, "address")]["corrected"]
            debug_print(f"Applied address correction for OrigRowNum={orig_row}: '{val}' -> '{corrected_cells[(idx, 'address')]['corrected']}'")
            if is_valid:  # Only clear if final validation passed
                errors[:] = [e for e in errors if not (e["Row"] == orig_row and e["Column"] == "address" and e["Error"] in SMARTY_ELIGIBLE_ERRORS)]
                debug_print(f"Cleared Smarty-eligible address errors for OrigRowNum={orig_row} after valid local correction")