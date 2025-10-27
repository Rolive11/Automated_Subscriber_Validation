"""Smarty API validation functions for address correction."""

import requests
import time
import json
import hashlib
import re
from datetime import datetime
import pandas as pd
import os
SMARTY_API_URL = "https://us-street.api.smarty.com/street-address"

from src.config.settings import (
    SMARTY_AUTH_ID, SMARTY_AUTH_TOKEN, SMARTY_USAGE_LOG_PATH, DEBUG_MODE,
    SMARTY_BATCH_SIZE, SMARTY_MIN_BATCH_SIZE, SMARTY_BATCH_TIMEOUT, SMARTY_BATCH_MAX_PAYLOAD_BYTES,
    SMARTY_MAX_RETRIES, SMARTY_RATE_LIMIT_DELAY, SMARTY_TIMEOUT_SECONDS
)
from src.utils.logging import debug_print

SMARTY_ELIGIBLE_ERRORS = [
    "Lacks standard street ending",
    "Invalid format",
    "Required field: Zip cannot be empty",  # Smarty can fill in missing ZIP from address/city/state
    "Required field: City cannot be empty",  # Smarty can fill in missing city from address/zip
    "Required field: State cannot be empty"  # Smarty can fill in missing state from address/zip
]

def chunk_candidates(candidates):
    """
    Split candidates into batches, respecting size limits.
    
    Args:
        candidates (list): List of candidate dicts.
    
    Returns:
        list: List of batch lists (each <= SMARTY_BATCH_SIZE and < max payload bytes).
    """
    batches = []
    current_batch = []
    for candidate in candidates:
        current_batch.append(candidate)
        if len(current_batch) == SMARTY_BATCH_SIZE:
            payload, payload_size = prepare_batch_payload(current_batch)
            if payload_size > SMARTY_BATCH_MAX_PAYLOAD_BYTES:
                # If oversized, split further (rare, but safe)
                debug_print(f"Oversized batch ({payload_size} bytes) - splitting")
                mid = len(current_batch) // 2
                batches.append(current_batch[:mid])
                current_batch = current_batch[mid:]
            else:
                batches.append(current_batch)
                current_batch = []
    
    if current_batch:
        batches.append(current_batch)
    
    debug_print(f"Created {len(batches)} batches from {len(candidates)} candidates")
    return batches

def prepare_batch_payload(batch):
    """
    Prepare JSON payload for a batch and calculate its size.
    
    Args:
        batch (list): List of candidate dicts.
    
    Returns:
        tuple: (json_payload_str, size_in_bytes)
    """
    payload_list = []
    for candidate in batch:
        params = {
            'street': str(candidate['address']).strip(),
            'city': str(candidate['city']).strip(),
            'state': str(candidate['state']).strip(),
            'match': 'enhanced'
        }
        if candidate['zip'] and str(candidate['zip']).strip():
            params['zipcode'] = str(candidate['zip']).strip()
        payload_list.append(params)
    
    payload_str = json.dumps(payload_list)
    payload_size = len(payload_str.encode('utf-8'))
    return payload_str, payload_size

def validate_with_smarty_batch(batch):
    """
    Validate a batch of addresses using Smarty API.
    
    Args:
        batch (list): List of candidate dicts.
    
    Returns:
        list: List of result dicts per address.
    """
    if not batch:
        debug_print("Empty batch received - returning empty results")
        return []

    if not SMARTY_AUTH_ID or not SMARTY_AUTH_TOKEN:
        debug_print("Smarty API credentials not configured")
        return [{
            'success': False,
            'corrected_address': None,
            'corrected_zip': None,
            'corrected_city': None,
            'corrected_state': None,
            'smarty_key': None,
            'error': 'API credentials not configured',
            'raw_response': None
        } for _ in batch]

    # Prepare payload
    payload_str, payload_size = prepare_batch_payload(batch)
    debug_print(f"Sending batch of {len(batch)} addresses, payload size: {payload_size} bytes")

    headers = {'Content-Type': 'application/json'}
    params = {
        'auth-id': SMARTY_AUTH_ID,
        'auth-token': SMARTY_AUTH_TOKEN
    }

    for attempt in range(SMARTY_MAX_RETRIES):
        try:
            if attempt > 0:
                time.sleep(SMARTY_RATE_LIMIT_DELAY * (2 ** attempt))

            response = requests.post(
                SMARTY_API_URL,
                params=params,
                headers=headers,
                data=payload_str,
                timeout=SMARTY_BATCH_TIMEOUT
            )

            debug_print(f"Smarty batch response status: {response.status_code}")
            debug_print(f"Raw Smarty response text: {response.text}")

            if response.status_code == 401:
                return [{
                    'success': False,
                    'corrected_address': None,
                    'corrected_zip': None,
            'corrected_city': None,
            'corrected_state': None,
            'smarty_key': None,
                    'error': 'Authentication failed - check API credentials',
                    'raw_response': None
                } for _ in batch]
            elif response.status_code == 402:
                return [{
                    'success': False,
                    'corrected_address': None,
                    'corrected_zip': None,
            'corrected_city': None,
            'corrected_state': None,
            'smarty_key': None,
                    'error': 'Payment required - check Smarty account balance',
                    'raw_response': None
                } for _ in batch]
            elif response.status_code == 413:
                debug_print(f"Payload too large ({payload_size} bytes) - splitting batch")
                if len(batch) > 1:
                    mid = len(batch) // 2
                    return (validate_with_smarty_batch(batch[:mid]) +
                            validate_with_smarty_batch(batch[mid:]))
                else:
                    return [{
                        'success': False,
                        'corrected_address': None,
                        'corrected_zip': None,
            'corrected_city': None,
            'corrected_state': None,
            'smarty_key': None,
                        'error': 'Payload too large for single address',
                        'raw_response': None
                    }]
            elif response.status_code == 429:
                debug_print(f"Rate limited on attempt {attempt + 1}")
                if attempt < SMARTY_MAX_RETRIES - 1:
                    continue
                return [{
                    'success': False,
                    'corrected_address': None,
                    'corrected_zip': None,
            'corrected_city': None,
            'corrected_state': None,
            'smarty_key': None,
                    'error': 'Rate limited by Smarty API',
                    'raw_response': None
                } for _ in batch]
            elif response.status_code != 200:
                debug_print(f"Smarty API error: {response.status_code} - {response.text}")
                if attempt < SMARTY_MAX_RETRIES - 1:
                    continue
                return [{
                    'success': False,
                    'corrected_address': None,
                    'corrected_zip': None,
            'corrected_city': None,
            'corrected_state': None,
            'smarty_key': None,
                    'error': f'HTTP {response.status_code}: {response.text}',
                    'raw_response': None
                } for _ in batch]

            # Parse JSON response
            try:
                json_response = response.json()
            except json.JSONDecodeError as e:
                debug_print(f"Failed to parse batch JSON response: {e}")
                if attempt < SMARTY_MAX_RETRIES - 1:
                    continue
                return [{
                    'success': False,
                    'corrected_address': None,
                    'corrected_zip': None,
            'corrected_city': None,
            'corrected_state': None,
            'smarty_key': None,
                    'error': 'Invalid JSON response from Smarty API',
                    'raw_response': None
                } for _ in batch]

            # Group matches by input_index to create per-address results
            results_per_address = [[] for _ in batch]
            for match in json_response:
                input_idx = match.get('input_index')
                if input_idx is not None and 0 <= input_idx < len(batch):
                    results_per_address[input_idx].append(match)
                else:
                    debug_print(f"Invalid input_index {input_idx} in response - skipping match")

            # Process each address's results
            results = []
            for idx, per_address_results in enumerate(results_per_address):
                if not per_address_results:
                    debug_print(f"No matches for batch index {idx}: {batch[idx]['address']}")
                    results.append({
                        'success': False,
                        'corrected_address': None,
                        'corrected_zip': None,
            'corrected_city': None,
            'corrected_state': None,
            'smarty_key': None,
                        'error': 'No valid address match found',
                        'raw_response': per_address_results
                    })
                    continue

                # Extract first match (Smarty returns sorted by best match)
                first_match = per_address_results[0]
                
                # Build corrected address
                corrected_address = ""
                if 'delivery_line_1' in first_match:
                    raw_address = first_match['delivery_line_1']
                    corrected_address = clean_smarty_address_for_bdc(raw_address)
                    if raw_address != corrected_address:
                        debug_print(f"Cleaned Smarty address for BDC: '{raw_address}' -> '{corrected_address}'")

                # Get SmartyKey if available
                smarty_key = first_match.get('metadata', {}).get('smarty_key')

                # Extract ZIP code and ensure 5-digit format
                corrected_zip = None
                if 'components' in first_match and 'zipcode' in first_match['components']:
                    full_zip = first_match['components']['zipcode']
                    corrected_zip = str(full_zip)[:5] if full_zip else None
                    debug_print(f"Smarty ZIP code formatted for FCC BDC: '{full_zip}' -> '{corrected_zip}' (5-digit compliance)")
                else:
                    # Try alternate ZIP field names
                    if 'components' in first_match:
                        # Check for zip9, plus4_code, or other variations
                        if 'zip9' in first_match['components']:
                            corrected_zip = str(first_match['components']['zip9'])[:5]
                            debug_print(f"Smarty ZIP extracted from zip9 field: '{corrected_zip}'")
                        elif 'default_city_name' in first_match.get('metadata', {}):
                            # Sometimes ZIP is in metadata
                            debug_print(f"WARNING: ZIP not in components, checking metadata")

                    if not corrected_zip:
                        # Try to extract from last_line (format: "City ST ZIP" or "City ST ZIP-PLUS4")
                        if 'last_line' in first_match:
                            last_line = first_match['last_line']
                            # Extract ZIP from last_line using regex (5 digits at end)
                            import re
                            zip_match = re.search(r'\b(\d{5})(?:-\d{4})?\b', last_line)
                            if zip_match:
                                corrected_zip = zip_match.group(1)
                                debug_print(f"Smarty ZIP extracted from last_line '{last_line}': '{corrected_zip}'")

                        if not corrected_zip:
                            # Log when ZIP is missing from all expected fields
                            debug_print(f"WARNING: Smarty response missing ZIP code for address: {batch[idx]['address']}")
                            debug_print(f"  Available components: {list(first_match.get('components', {}).keys())}")
                            debug_print(f"  Available metadata keys: {list(first_match.get('metadata', {}).keys())}")
                            debug_print(f"  Full response keys: {list(first_match.keys())}")
                            debug_print(f"  last_line: '{first_match.get('last_line', 'N/A')}'")
                            debug_print(f"  analysis: {first_match.get('analysis', {})}")

                # Extract city and state from Smarty response
                corrected_city = None
                corrected_state = None
                if 'components' in first_match:
                    if 'city_name' in first_match['components']:
                        corrected_city = first_match['components']['city_name']
                        debug_print(f"Smarty returned city: '{corrected_city}'")
                    if 'state_abbreviation' in first_match['components']:
                        corrected_state = first_match['components']['state_abbreviation']
                        debug_print(f"Smarty returned state: '{corrected_state}'")

                if corrected_address:
                    debug_print(f"Smarty API success: '{batch[idx]['address']}' -> '{corrected_address}'" + (f", ZIP: {corrected_zip}" if corrected_zip else "") + (f", City: {corrected_city}" if corrected_city else "") + (f", State: {corrected_state}" if corrected_state else ""))
                    results.append({
                        'success': True,
                        'corrected_address': corrected_address.upper(),
                        'corrected_zip': corrected_zip,
                        'corrected_city': corrected_city,
                        'corrected_state': corrected_state,
                        'smarty_key': smarty_key,
                        'error': None,
                        'raw_response': per_address_results
                    })
                else:
                    debug_print("Smarty API response missing delivery_line_1")
                    results.append({
                        'success': False,
                        'corrected_address': None,
                        'corrected_zip': None,
                        'corrected_city': None,
                        'corrected_state': None,
                        'smarty_key': None,
                        'error': 'Invalid response format from Smarty API',
                        'raw_response': per_address_results
                    })

            debug_print(f"Batch processed: {len(results)} results, {sum(r['success'] for r in results)} successes")
            return results

        except requests.exceptions.Timeout:
            debug_print(f"Smarty batch timeout, attempt {attempt + 1}")
            if attempt < SMARTY_MAX_RETRIES - 1:
                continue
            return [{
                'success': False,
                'corrected_address': None,
                'corrected_zip': None,
            'corrected_city': None,
            'corrected_state': None,
            'smarty_key': None,
                'error': 'Request timeout',
                'raw_response': None
            } for _ in batch]
        except requests.exceptions.ConnectionError:
            debug_print(f"Smarty batch connection error, attempt {attempt + 1}")
            if attempt < SMARTY_MAX_RETRIES - 1:
                continue
            return [{
                'success': False,
                'corrected_address': None,
                'corrected_zip': None,
            'corrected_city': None,
            'corrected_state': None,
            'smarty_key': None,
                'error': 'Connection error',
                'raw_response': None
            } for _ in batch]
        except Exception as e:
            debug_print(f"Unexpected Smarty batch error: {str(e)}")
            if attempt < SMARTY_MAX_RETRIES - 1:
                continue
            return [{
                'success': False,
                'corrected_address': None,
                'corrected_zip': None,
            'corrected_city': None,
            'corrected_state': None,
            'smarty_key': None,
                'error': f'Unexpected error: {str(e)}',
                'raw_response': None
            } for _ in batch]
    
    # If we get here, all retries failed
    return [{
        'success': False,
        'corrected_address': None,
        'corrected_zip': None,
            'corrected_city': None,
            'corrected_state': None,
            'smarty_key': None,
        'error': 'All retry attempts failed',
        'raw_response': None
    } for _ in batch]


def should_send_to_smarty(error_type):
    """
    Determine if an error type should be sent to Smarty for validation.
    
    Args:
        error_type (str): The error message/type to check
        
    Returns:
        bool: True if this error type should be sent to Smarty
    """
    return error_type in SMARTY_ELIGIBLE_ERRORS

def clean_smarty_address_for_bdc(address):
    """
    Remove unit/apartment designators from Smarty-corrected addresses for FCC BDC compatibility.
    
    Args:
        address (str): Address returned from Smarty API (delivery_line_1 only)
        
    Returns:
        str: Cleaned address without unit designators
    """
    if not address:
        return address
    
    # Pattern to match and remove unit designators that may appear in delivery_line_1
    # This covers: # 40, APT 40, UNIT 40, STE 40, etc.
    unit_pattern = r'(?:\.\s*)?(?:#|SPC|SPACE|APT|APARTMENT|UNIT|SUITE|STE|ROOM|RM|FLOOR|FL|OFFICE|OFC|DEPT|DEPARTMENT|BLDG|BUILDING)\s*[A-Z0-9]+(?:\s+[A-Z0-9]+)*(?:\s*$|$)'
    
    cleaned_address = re.sub(unit_pattern, ' ', address, flags=re.IGNORECASE)
    
    # Clean up any double spaces and trim
    cleaned_address = re.sub(r'\s+', ' ', cleaned_address).strip()
    
    return cleaned_address

def validate_with_smarty(address, city, state, zip_code):
    """
    Validate a single address using Smarty API.
    
    Args:
        address (str): Street address
        city (str): City name
        state (str): State abbreviation
        zip_code (str): ZIP code (may be empty for missing ZIP cases)
        
    Returns:
        dict: {
            'success': bool,
            'corrected_address': str or None,
            'corrected_zip': str or None,  # Always 5-digit format for FCC BDC compliance
            'smarty_key': str or None,
            'error': str or None,
            'raw_response': dict or None
        }
    """
    if not SMARTY_AUTH_ID or not SMARTY_AUTH_TOKEN:
        debug_print("Smarty API credentials not configured")
        return {
            'success': False,
            'corrected_address': None,
            'corrected_zip': None,
            'corrected_city': None,
            'corrected_state': None,
            'smarty_key': None,
            'error': 'API credentials not configured',
            'raw_response': None
        }
    
    # Prepare request parameters (ZIP may be empty)
    params = {
        'auth-id': SMARTY_AUTH_ID,
        'auth-token': SMARTY_AUTH_TOKEN,
        'street': str(address).strip(),
        'city': str(city).strip(),
        'state': str(state).strip(),
        'match': 'enhanced'
    }
    
    # Only add ZIP if it's not empty
    if zip_code and str(zip_code).strip():
        params['zipcode'] = str(zip_code).strip()
    
    # Remove empty parameters
    params = {k: v for k, v in params.items() if v}
    
    debug_print(f"Smarty API request for: {address}, {city}, {state}" + (f", {zip_code}" if zip_code else " (no ZIP)"))

    
    for attempt in range(SMARTY_MAX_RETRIES):
        try:
            # Rate limiting
            if attempt > 0:
                time.sleep(SMARTY_RATE_LIMIT_DELAY * (2 ** attempt))  # Exponential backoff
            
            response = requests.get(
                SMARTY_API_URL,
                params=params,
                timeout=SMARTY_TIMEOUT_SECONDS
            )
            
            debug_print(f"Smarty API response status: {response.status_code}")
            
            # Handle HTTP errors
            if response.status_code == 401:
                return {
                    'success': False,
                    'corrected_address': None,
                    'corrected_zip': None,
            'corrected_city': None,
            'corrected_state': None,
            'smarty_key': None,
                    'error': 'Authentication failed - check API credentials',
                    'raw_response': None
                }
            elif response.status_code == 402:
                return {
                    'success': False,
                    'corrected_address': None,
                    'corrected_zip': None,
            'corrected_city': None,
            'corrected_state': None,
            'smarty_key': None,
                    'error': 'Payment required - check Smarty account balance',
                    'raw_response': None
                }
            elif response.status_code == 429:
                debug_print(f"Smarty API rate limited, attempt {attempt + 1}")
                if attempt < SMARTY_MAX_RETRIES - 1:
                    continue  # Retry
                return {
                    'success': False,
                    'corrected_address': None,
                    'corrected_zip': None,
            'corrected_city': None,
            'corrected_state': None,
            'smarty_key': None,
                    'error': 'Rate limited by Smarty API',
                    'raw_response': None
                }
            elif response.status_code != 200:
                debug_print(f"Smarty API error: {response.status_code} - {response.text}")
                if attempt < SMARTY_MAX_RETRIES - 1:
                    continue  # Retry
                return {
                    'success': False,
                    'corrected_address': None,
                    'corrected_zip': None,
            'corrected_city': None,
            'corrected_state': None,
            'smarty_key': None,
                    'error': f'HTTP {response.status_code}: {response.text}',
                    'raw_response': None
                }
            
            # Parse JSON response
            try:
                json_response = response.json()
            except json.JSONDecodeError as e:
                debug_print(f"Failed to parse Smarty API JSON response: {e}")
                if attempt < SMARTY_MAX_RETRIES - 1:
                    continue  # Retry
                return {
                    'success': False,
                    'corrected_address': None,
                    'corrected_zip': None,
            'corrected_city': None,
            'corrected_state': None,
            'smarty_key': None,
                    'error': 'Invalid JSON response from Smarty API',
                    'raw_response': None
                }
            
            debug_print(f"Smarty API JSON response: {json_response}")
            
            # Handle empty response (no match found)
            if not json_response or len(json_response) == 0:
                debug_print("Smarty API returned no matches")
                return {
                    'success': False,
                    'corrected_address': None,
                    'corrected_zip': None,
            'corrected_city': None,
            'corrected_state': None,
            'smarty_key': None,
                    'error': 'No valid address match found',
                    'raw_response': json_response
                }
            
            # Extract address components from first match
            first_match = json_response[0]
            
            # Build corrected address (using only delivery_line_1)
            corrected_address = ""
            if 'delivery_line_1' in first_match:
                raw_address = first_match['delivery_line_1']
    
                # Clean the address for FCC BDC compatibility (remove unit designators)
                corrected_address = clean_smarty_address_for_bdc(raw_address)
    
                if raw_address != corrected_address:
                    debug_print(f"Cleaned Smarty address for BDC: '{raw_address}' -> '{corrected_address}'")

            # Get SmartyKey if available
            smarty_key = first_match.get('metadata', {}).get('smarty_key')

            if corrected_address:
                # FIXED: Extract ZIP code and ensure 5-digit format for FCC BDC compliance
                corrected_zip = None
                if 'components' in first_match and 'zipcode' in first_match['components']:
                    full_zip = first_match['components']['zipcode']
                    # Always truncate to 5 digits for FCC BDC compliance
                    corrected_zip = str(full_zip)[:5] if full_zip else None
                    debug_print(f"Smarty ZIP code formatted for FCC BDC: '{full_zip}' -> '{corrected_zip}' (5-digit compliance)")
        
                debug_print(f"Smarty API success: '{address}' -> '{corrected_address}'" + (f", ZIP: {corrected_zip}" if corrected_zip else ""))
                return {
                    'success': True,
                    'corrected_address': corrected_address.upper(),  # Match system convention
                    'corrected_zip': corrected_zip,  # 5-digit format for FCC BDC compliance
                    'smarty_key': smarty_key,
                    'error': None,
                    'raw_response': json_response
                }
            else:
                debug_print("Smarty API response missing delivery_line_1")
                return {
                    'success': False,
                    'corrected_address': None,
                    'corrected_zip': None,
            'corrected_city': None,
            'corrected_state': None,
            'smarty_key': None,
                    'error': 'Invalid response format from Smarty API',
                    'raw_response': json_response
                }
                
        except requests.exceptions.Timeout:
            debug_print(f"Smarty API timeout, attempt {attempt + 1}")
            if attempt < SMARTY_MAX_RETRIES - 1:
                continue  # Retry
            return {
                'success': False,
                'corrected_address': None,
                'corrected_zip': None,
            'corrected_city': None,
            'corrected_state': None,
            'smarty_key': None,
                'error': 'Request timeout',
                'raw_response': None
            }
            
        except requests.exceptions.ConnectionError:
            debug_print(f"Smarty API connection error, attempt {attempt + 1}")
            if attempt < SMARTY_MAX_RETRIES - 1:
                continue  # Retry
            return {
                'success': False,
                'corrected_address': None,
                'corrected_zip': None,
            'corrected_city': None,
            'corrected_state': None,
            'smarty_key': None,
                'error': 'Connection error',
                'raw_response': None
            }
            
        except Exception as e:
            debug_print(f"Unexpected Smarty API error: {str(e)}")
            if attempt < SMARTY_MAX_RETRIES - 1:
                continue  # Retry
            return {
                'success': False,
                'corrected_address': None,
                'corrected_zip': None,
            'corrected_city': None,
            'corrected_state': None,
            'smarty_key': None,
                'error': f'Unexpected error: {str(e)}',
                'raw_response': None
            }
    
    # If we get here, all retries failed
    return {
        'success': False,
        'corrected_address': None,
        'corrected_zip': None,
            'corrected_city': None,
            'corrected_state': None,
            'smarty_key': None,
        'error': 'All retry attempts failed',
        'raw_response': None
    }


def log_smarty_usage(api_calls, successful_corrections, failed_corrections, company_id, processing_time=None, batches_sent=0):
    try:
        # Ensure log directory exists
        log_dir = os.path.dirname(SMARTY_USAGE_LOG_PATH)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Prepare log entry
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'company_id': company_id,
            'api_calls': api_calls,
            'successful_corrections': successful_corrections,
            'failed_corrections': failed_corrections,
            'success_rate': (successful_corrections / api_calls * 100) if api_calls > 0 else 0,
            'processing_time_seconds': processing_time,
            'batches_sent': batches_sent  # NEW
        }
        
        # Check if log file exists and has header
        file_exists = os.path.exists(SMARTY_USAGE_LOG_PATH)
        
        with open(SMARTY_USAGE_LOG_PATH, 'a', encoding='utf-8') as f:
            if not file_exists:
                # Write header with new column
                f.write("Timestamp,Company_ID,API_Calls,Successful_Corrections,Failed_Corrections,Success_Rate,Processing_Time_Seconds,Batches_Sent\n")
            
            # Write log entry with new field
            f.write(f"{log_entry['timestamp']},{log_entry['company_id']},{log_entry['api_calls']},{log_entry['successful_corrections']},{log_entry['failed_corrections']},{log_entry['success_rate']:.2f},{log_entry['processing_time_seconds']},{log_entry['batches_sent']}\n")
        
        debug_print(f"Smarty usage logged: {api_calls} calls, {successful_corrections} successes, {batches_sent} batches")
        
    except Exception as e:
        debug_print(f"Failed to log Smarty usage: {str(e)}")
        # Don't raise exception - logging failure shouldn't break the process


def process_smarty_corrections(cleaned_df, errors, corrected_cells, flagged_cells, company_id, base_filename):
    """
    Main function to process addresses through Smarty API and handle results.
    
    This function only attempts to correct addresses and flags failures for later decision-making.
    No removal decisions are made here - that is handled by the final validation step.
    
    Args:
        cleaned_df (pd.DataFrame): The cleaned subscriber DataFrame
        errors (list): List of error dictionaries
        corrected_cells (dict): Dictionary tracking cell corrections
        flagged_cells (dict): Dictionary tracking flagged cells
        company_id (str): Company identifier for logging
        base_filename (str): Base filename for output files
        
    Returns:
        dict: {
            'addresses_sent': int,
            'successful_corrections': int,
            'failed_corrections': int,
            'action_taken': str,
            'smarty_corrections': list,
            'batches_sent': int,  # NEW: Track number of batches
            'processing_time': float
        }
    """
    start_time = time.time()
    
    debug_print("Starting Smarty API batch processing")
    
    # Initialize results
    results = {
        'addresses_sent': 0,
        'successful_corrections': 0,
        'failed_corrections': 0,
        'action_taken': 'FLAG_FAILURES_FOR_REVIEW',
        'smarty_corrections': [],
        'batches_sent': 0,  # NEW: Track batches
        'processing_time': 0.0
    }
    
    try:
        # DEBUG: Log all flagged_cells before filtering
        debug_print(f"=== SMARTY CANDIDATE COLLECTION START ===")
        debug_print(f"Total flagged_cells entries: {len(flagged_cells)}")
        for (row_idx, col_name), cell_data in flagged_cells.items():
            if isinstance(cell_data, tuple):
                error_msg, orig_row = cell_data
            else:
                error_msg = cell_data
                orig_row = "Unknown"
            debug_print(f"  flagged_cells entry: OrigRowNum={orig_row}, col={col_name}, error='{error_msg}'")

        # Find addresses flagged for Smarty processing
        smarty_candidates = []
        for (row_idx, col_name), cell_data in flagged_cells.items():
            if isinstance(cell_data, tuple):
                error_msg, orig_row_stored = cell_data
            else:
                error_msg = cell_data
                orig_row_stored = None
                if row_idx < len(cleaned_df):
                    orig_row_stored = cleaned_df["OrigRowNum"].iloc[row_idx]

            debug_print(f"Checking flagged cell: row_idx={row_idx}, col_name={col_name}, error_msg='{error_msg}', orig_row={orig_row_stored}, should_send={should_send_to_smarty(error_msg)}")

            if should_send_to_smarty(error_msg):
                if row_idx < len(cleaned_df):
                    row_data = cleaned_df.iloc[row_idx]
                    state = str(row_data.get('state', '')).strip().upper()
                    if state == "PR":
                        debug_print(f"Skipping Smarty for PR address: OrigRowNum={orig_row_stored}")
                        continue  # NEW: Skip PR addresses
                    
                    # CHECK FOR LOCAL CORRECTIONS FIRST
                    address = str(row_data.get('address', '')).strip()
                    if (row_idx, 'address') in corrected_cells and corrected_cells[(row_idx, 'address')].get('status') == 'Valid':
                        # Use the locally corrected address instead of the original
                        corrected_address = corrected_cells[(row_idx, 'address')]['corrected']
                        debug_print(f"Using locally corrected address for Smarty: OrigRowNum={orig_row_stored}, '{address}' -> '{corrected_address}'")
                        address = corrected_address
                    
                    candidate = {
                        'row_idx': row_idx,
                        'orig_row': int(row_data['OrigRowNum']),
                        'address': address,  # Now uses the corrected address if available
                        'city': str(row_data.get('city', '')).strip(),
                        'state': state,
                        'zip': str(row_data.get('zip', '')).strip(),
                        'error_msg': error_msg,
                        'error_column': col_name
                    }
                    smarty_candidates.append(candidate)
                    debug_print(f"Added Smarty candidate: OrigRowNum={candidate['orig_row']}, address='{candidate['address']}', error='{error_msg}', column='{col_name}'")
                else:
                    debug_print(f"Skipping flagged cell: row_idx {row_idx} >= DataFrame length {len(cleaned_df)}")
        
        results['addresses_sent'] = len(smarty_candidates)
        debug_print(f"Found {len(smarty_candidates)} addresses for Smarty batch validation")
        
        if len(smarty_candidates) == 0:
            debug_print("No addresses eligible for Smarty processing")
            results['processing_time'] = time.time() - start_time
            return results
        
        # NEW: Process candidates in batches
        batches = chunk_candidates(smarty_candidates)
        results['batches_sent'] = len(batches)
        
        for batch_idx, batch in enumerate(batches):
            debug_print(f"Processing batch {batch_idx + 1}/{len(batches)} with {len(batch)} addresses")
            
            # Call batch validation
            batch_results = validate_with_smarty_batch(batch)
            
            # Ensure results align with batch size
            if len(batch_results) != len(batch):
                debug_print(f"Error: Batch {batch_idx + 1} returned {len(batch_results)} results, expected {len(batch)}")
                results['failed_corrections'] += len(batch)
                for candidate in batch:
                    results['smarty_corrections'].append({
                        'orig_row': candidate['orig_row'],
                        'original_address': candidate['address'],
                        'corrected_address': None,
                        'original_zip': candidate['zip'],
                        'corrected_zip': None,
                        'success': False,
                        'error': 'Batch result mismatch',
                        'smarty_key': None,
                        'timestamp': datetime.now().isoformat()
                    })
                continue
            
            # Process each result in the batch
            for candidate, smarty_result in zip(batch, batch_results):
                debug_print(f"Processing result for OrigRowNum {candidate['orig_row']}: {candidate['address']}")
                
                # Prepare correction entry for reporting
                correction_entry = {
                    'orig_row': candidate['orig_row'],
                    'original_address': candidate['address'],
                    'corrected_address': smarty_result['corrected_address'],
                    'original_city': candidate['city'],
                    'corrected_city': smarty_result.get('corrected_city', ''),
                    'original_state': candidate['state'],
                    'corrected_state': smarty_result.get('corrected_state', ''),
                    'original_zip': candidate['zip'],
                    'corrected_zip': smarty_result['corrected_zip'],
                    'reason_sent': candidate['error_msg'],  # NEW: Why was this sent to Smarty
                    'error_column': candidate['error_column'],  # NEW: Which column had the error
                    'success': smarty_result['success'],
                    'error': smarty_result['error'],
                    'smarty_key': smarty_result['smarty_key'],
                    'timestamp': datetime.now().isoformat()
                }
                
                results['smarty_corrections'].append(correction_entry)
                
                if smarty_result['success']:
                    # Successful correction
                    results['successful_corrections'] += 1
                    
                    # Post-process Smarty's corrected address to remove non-standard endings
                    corrected_address = smarty_result['corrected_address']
                    from src.config.settings import NON_STANDARD_ENDINGS
                    match = re.search(NON_STANDARD_ENDINGS, corrected_address, re.IGNORECASE)
                    if match:
                        corrected_address = corrected_address[:match.start()].strip()
                        debug_print(f"Removed non-standard ending from Smarty result for OrigRowNum {candidate['orig_row']}: '{corrected_address}'")
                    
                    # Update the DataFrame with the post-processed address
                    cleaned_df.loc[candidate['row_idx'], 'address'] = corrected_address
                    
                    # Update ZIP code if Smarty provided one
                    if smarty_result['corrected_zip']:
                        cleaned_df.loc[candidate['row_idx'], 'zip'] = smarty_result['corrected_zip']

                        # Record ZIP correction
                        corrected_cells[(candidate['row_idx'], 'zip')] = {
                            "row": candidate['orig_row'],
                            "original": candidate['zip'] or '',
                            "corrected": smarty_result['corrected_zip'],
                            "type": "Smarty ZIP Code Correction",
                            "status": "Valid",
                            "smarty_key": smarty_result['smarty_key'],
                            "timestamp": datetime.now().isoformat()
                        }
                        debug_print(f"Smarty updated ZIP code for OrigRowNum {candidate['orig_row']}: '{candidate['zip']}' -> '{smarty_result['corrected_zip']}'")

                    # Update city if Smarty provided one
                    if smarty_result.get('corrected_city'):
                        cleaned_df.loc[candidate['row_idx'], 'city'] = smarty_result['corrected_city'].upper()

                        # Record city correction
                        corrected_cells[(candidate['row_idx'], 'city')] = {
                            "row": candidate['orig_row'],
                            "original": candidate['city'] or '',
                            "corrected": smarty_result['corrected_city'].upper(),
                            "type": "Smarty City Correction",
                            "status": "Valid",
                            "smarty_key": smarty_result['smarty_key'],
                            "timestamp": datetime.now().isoformat()
                        }
                        debug_print(f"Smarty updated city for OrigRowNum {candidate['orig_row']}: '{candidate['city']}' -> '{smarty_result['corrected_city']}'")

                    # Update state if Smarty provided one
                    if smarty_result.get('corrected_state'):
                        cleaned_df.loc[candidate['row_idx'], 'state'] = smarty_result['corrected_state'].upper()

                        # Record state correction
                        corrected_cells[(candidate['row_idx'], 'state')] = {
                            "row": candidate['orig_row'],
                            "original": candidate['state'] or '',
                            "corrected": smarty_result['corrected_state'].upper(),
                            "type": "Smarty State Correction",
                            "status": "Valid",
                            "smarty_key": smarty_result['smarty_key'],
                            "timestamp": datetime.now().isoformat()
                        }
                        debug_print(f"Smarty updated state for OrigRowNum {candidate['orig_row']}: '{candidate['state']}' -> '{smarty_result['corrected_state']}'")

                    # Record the address correction
                    corrected_cells[(candidate['row_idx'], 'address')] = {
                        "row": candidate['orig_row'],
                        "original": candidate['address'],
                        "corrected": corrected_address,
                        "type": "Smarty Address Correction with Non-Standard Ending Removal" if match else "Smarty Address Correction",
                        "status": "Valid",
                        "smarty_key": smarty_result['smarty_key'],
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Remove all address-related flagged cells and errors
                    flagged_error_removed = False
                    if (candidate['row_idx'], 'address') in flagged_cells:
                        del flagged_cells[(candidate['row_idx'], 'address')]
                        flagged_error_removed = True
                        debug_print(f"Removed flagged address error for OrigRowNum {candidate['orig_row']} after successful Smarty correction")

                    if smarty_result['corrected_zip'] and (candidate['row_idx'], 'zip') in flagged_cells:
                        del flagged_cells[(candidate['row_idx'], 'zip')]
                        flagged_error_removed = True
                        debug_print(f"Removed flagged ZIP error for OrigRowNum {candidate['orig_row']} after successful Smarty ZIP correction")

                    if smarty_result.get('corrected_city') and (candidate['row_idx'], 'city') in flagged_cells:
                        del flagged_cells[(candidate['row_idx'], 'city')]
                        flagged_error_removed = True
                        debug_print(f"Removed flagged city error for OrigRowNum {candidate['orig_row']} after successful Smarty city correction")

                    if smarty_result.get('corrected_state') and (candidate['row_idx'], 'state') in flagged_cells:
                        del flagged_cells[(candidate['row_idx'], 'state')]
                        flagged_error_removed = True
                        debug_print(f"Removed flagged state error for OrigRowNum {candidate['orig_row']} after successful Smarty state correction")

                    # Clear all address-related errors from errors list (address, zip, city, state)
                    errors[:] = [e for e in errors if not (e["Row"] == candidate['orig_row'] and e["Column"] in ["address", "zip", "city", "state"])]
                    debug_print(f"Cleared address-related errors for OrigRowNum {candidate['orig_row']} after successful Smarty correction")
                    
                    if not flagged_error_removed:
                        debug_print(f"No flagged errors found to remove for OrigRowNum {candidate['orig_row']}")
                    
                    debug_print(f"Smarty success for OrigRowNum {candidate['orig_row']}: '{candidate['address']}' -> '{corrected_address}'")
                    
                    debug_print(f"Smarty success for OrigRowNum {candidate['orig_row']}: '{candidate['address']}' -> '{smarty_result['corrected_address']}'")
                
                else:
                    # Failed correction - flag for final validation decision
                    results['failed_corrections'] += 1
                    
                    # Update flagged cells with Smarty failure message
                    flagged_cells[(candidate['row_idx'], 'address')] = ("Smarty Validation Failed - Returned for Review", candidate['orig_row'])
                    
                    # Add error entry for tracking
                    errors.append({
                        "Row": candidate['orig_row'],
                        "Column": "address",
                        "Error": "Smarty Validation Failed - Returned for Review",
                        "Value": candidate['address']
                    })
                    
                    debug_print(f"Smarty failed for OrigRowNum {candidate['orig_row']}: {smarty_result['error']} - flagged for final validation decision")
        
        debug_print(f"Smarty batch processing complete: {results['successful_corrections']} successes, {results['failed_corrections']} failures, {results['batches_sent']} batches")
        debug_print("All Smarty failures flagged for final validation decision - no removal decisions made")
        
        # Log API usage
        processing_time = time.time() - start_time
        results['processing_time'] = processing_time
        
        log_smarty_usage(
            results['addresses_sent'],
            results['successful_corrections'],
            results['failed_corrections'],
            company_id,
            processing_time
        )
        
        debug_print(f"Smarty processing completed in {processing_time:.2f} seconds")
        
        return results
        
    except Exception as e:
        debug_print(f"Error in Smarty batch processing: {str(e)}")
        # Log the error but don't break the main process
        errors.append({
            "Row": "N/A",
            "Column": "N/A", 
            "Error": f"Smarty API batch processing error: {str(e)}",
            "Value": "N/A"
        })
        
        # Return safe default results
        results['processing_time'] = time.time() - start_time
        return results

def test_smarty_connection():
    """
    Test Smarty API connection and credentials.
    
    Returns:
        dict: Test results with success status and details
    """
    debug_print("Testing Smarty API connection")
    
    test_result = validate_with_smarty(
        "1600 Amphitheatre Pkwy",
        "Mountain View", 
        "CA",
        "94043"
    )
    
    if test_result['success']:
        debug_print("Smarty API test successful")
        return {
            'success': True,
            'message': 'Smarty API connection successful',
            'corrected_address': test_result['corrected_address']
        }
    else:
        debug_print(f"Smarty API test failed: {test_result['error']}")
        return {
            'success': False,
            'message': f"Smarty API test failed: {test_result['error']}",
            'corrected_address': None
        }