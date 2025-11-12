# Changes to validate_subscription_isp_mod_2.py

## Summary
Modified script to accept user email address as a command line parameter instead of looking it up from the database.

## Command Line Usage

### OLD:
```bash
python3 validate_subscription_isp_mod_2.py {isp_id} yyyy-mm-dd
```

### NEW:
```bash
python3 validate_subscription_isp_mod_2.py {isp_id} yyyy-mm-dd {user_email}
```

### Example:
```bash
python3 validate_subscription_isp_mod_2.py 123 2025-06-30 user@example.com
```

## Changes Made

### 1. Command Line Argument Handling (Lines ~1492-1515)
- Added check for 3 required arguments
- Added email format validation using regex
- Added helpful usage message if arguments are missing or invalid
- Enhanced logging to include user email

### 2. Function Signature Update (Line 574)
- Updated `create_subscription()` function signature to accept `user_email` parameter
- Function now receives: `(subfile, filename, isp, periodpath, period, user_email)`

### 3. Email Usage Throughout Script
Replaced all database email lookups with provided email in 5 locations:

#### a. Invalid File Handler (~Lines 625-646)
- Uses `user_email` directly instead of database query
- Still retrieves user name from database for personalization
- Falls back to "Customer" if name not found

#### b. Header Error Handler (~Lines 753-774)
- Uses `user_email` directly instead of database query
- Still retrieves user name from database for personalization
- Falls back to "Customer" if name not found

#### c. Validation Error Handler (~Lines 846-867)
- Uses `user_email` directly instead of database query
- Still retrieves user name from database for personalization
- Falls back to "Customer" if name not found

#### d. Geocoding Errors Handler (~Lines 1151-1172)
- Uses `user_email` directly instead of database query
- Still retrieves user name from database for personalization
- Falls back to "Customer" if name not found

#### e. Success Email Handler (~Lines 1386-1411)
- Uses `user_email` directly instead of database query
- Still retrieves user name from database for personalization
- Falls back to "Customer" if name not found

### 4. Function Call Update (Line 1615)
- Updated call to `create_subscription()` to pass `user_email` parameter

## Benefits

1. **Flexibility**: Email address can be different from what's stored in database
2. **Testing**: Easier to test with different email addresses without modifying database
3. **Security**: No need to expose database user table to external scripts
4. **Reliability**: Script works even if database user table is unavailable
5. **Override**: Allows admin to send notifications to specific addresses

## Backwards Compatibility

**BREAKING CHANGE**: This is NOT backwards compatible. All calls to this script MUST now include the email address parameter.

## Error Handling

- Script validates email format using regex pattern
- Exits with code 1 if email is invalid
- Provides clear error messages and usage instructions
- Still attempts to retrieve user name from database for personalization
- Falls back to "Customer" if name lookup fails
- Logs all email operations to validate_subs.log

## Testing Recommendations

1. Test with valid email address:
   ```bash
   python3 validate_subscription_isp_mod_2.py 123 2025-06-30 test@example.com
   ```

2. Test with invalid email address (should fail):
   ```bash
   python3 validate_subscription_isp_mod_2.py 123 2025-06-30 invalid-email
   ```

3. Test with missing email parameter (should fail):
   ```bash
   python3 validate_subscription_isp_mod_2.py 123 2025-06-30
   ```

4. Verify all email types are sent correctly:
   - Invalid file email (with Excel attachment)
   - Header error email (with original CSV)
   - Validation error email
   - Geocoding error email
   - Success email (with VR.xlsx)

