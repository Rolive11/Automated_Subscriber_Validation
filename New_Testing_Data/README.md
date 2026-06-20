# Subscriber Validation Test Files

Created: January 5, 2026

## Purpose

These test files are designed to test all validation scenarios in the subscriber validation system, including the updated BCC email functionality.

---

## Test Files

### 01_valid_subscribers.csv ✅
**Expected Result:** Exit Code 0 (Success)

**Contents:**
- 10 valid subscriber records
- All required columns present
- Valid coordinates within state boundaries
- Valid addresses
- Various technology types (fiber, wireless_unlicensed)
- Mix of residential and business customers
- Some with VoIP lines

**What to Test:**
- System processes successfully
- Admin receives success notification email
- Files saved to correct directory
- Database status updated to 'complete'

---

### 02_header_error_missing_columns.csv ❌
**Expected Result:** Exit Code 2 (Header Error)

**Contents:**
- Wrong column names (latitude instead of lat, zipcode instead of zip, etc.)
- Missing required columns

**What to Test:**
- System detects header mismatch
- Customer receives header error email with:
  - List of required columns
  - Instructions on how to fix
  - Original file attached
  - Template reference
- Admin receives header error notification
- **NEW:** Admin receives BCC copy of customer email
- Database status updated to 'header_validation_failed'

---

### 03_header_error_misspelled.csv ❌
**Expected Result:** Exit Code 2 (Header Error)

**Contents:**
- Misspelled column names (custumer, adress, tecnology)

**What to Test:**
- System detects misspelled headers
- Same email behavior as 02_header_error
- **NEW:** Admin receives BCC copy of customer email

---

### 04_address_validation_issues.csv ⚠️
**Expected Result:** Exit Code 1 (Data Validation Failed)

**Contents:**
- Typos in street names
- Misspelled cities
- Wrong zip codes
- Incomplete addresses
- Non-existent streets
- Missing zip codes
- Extra spaces
- PO Boxes
- Missing apartment numbers
- Rural routes

**What to Test:**
- System attempts Smarty.com validation
- Code A validation detects address issues
- Customer receives corrected Excel file with:
  - RED cells for errors
  - GREEN cells for auto-corrections
  - Instructions on what to fix
- Admin receives validation results with error summary
- **NEW:** Admin receives BCC copy of customer email
- Database status updated to 'data_validation_failed'

---

### 05_missing_coordinates_geocoding.csv ⚠️
**Expected Result:** Exit Code 0 with geocoding attempts

**Contents:**
- Records with blank lat/lon
- Records with partial coordinates
- Valid addresses that can be geocoded
- Mix of complete and incomplete coordinate data

**What to Test:**
- System attempts Google Maps geocoding for blank coordinates
- Geocoding errors logged if addresses can't be geocoded
- Customer receives geocoding error email if applicable
- **NEW:** Admin receives BCC copy of geocoding error email
- Database status updated accordingly

---

### 06_data_validation_errors.csv ❌
**Expected Result:** Exit Code 1 (Data Validation Failed)

**Contents:**
- Invalid state codes (XX)
- Out of range latitude (999.0000)
- Out of range longitude (999.0000)
- Negative download speeds
- Negative upload speeds
- Invalid technology types
- Non-numeric values in numeric fields
- Invalid business flags
- Blank required fields

**What to Test:**
- Code A validation catches all data errors
- Customer receives corrected Excel with RED cells
- Validation Report shows all errors
- Admin receives error summary
- **NEW:** Admin receives BCC copy of customer email
- Database status updated to 'data_validation_failed'

---

### 07_mixed_issues.csv ⚠️
**Expected Result:** Exit Code 1 (Data Validation Failed)

**Contents:**
- Combination of valid and invalid records
- Mix of address issues, missing coordinates, data errors
- Tests system's ability to handle multiple error types

**What to Test:**
- System processes valid records
- System flags all invalid records
- Excel output shows color-coded issues
- Validation Report categorizes all errors
- Admin receives comprehensive error summary
- **NEW:** Admin receives BCC copy of customer email

---

## How to Test

### Command Line Testing

```bash
cd /var/www/broadband

# Test valid file
python3 validate_subscription_isp_mod_3.py 123 2025-12-31 test@example.com
# Upload: 01_valid_subscribers.csv to /var/www/broadband/uploads/123/2025-12-31/subscribers/

# Test header error
python3 validate_subscription_isp_mod_3.py 124 2025-12-31 test@example.com
# Upload: 02_header_error_missing_columns.csv to /var/www/broadband/uploads/124/2025-12-31/subscribers/

# Repeat for other test files with different org_ids
```

### What to Check After Each Test

#### Email Testing (PRIMARY FOCUS)
1. ✅ **Admin email received** - You should get the admin notification
2. ✅ **BCC copy of customer email** - **NEW:** You should ALSO receive a copy of the email sent to the customer
3. ✅ **Email content matches** - Verify the customer email has the right attachments and instructions

#### File Output Testing
1. Files saved to: `/var/www/broadband/Subscriber_File_Validations/{period}/{org_id}/`
2. Files include:
   - `{org_id}_Corrected_Subscribers.xlsx` (color-coded)
   - `{org_id}_VR.xlsx` (validation report)
   - `{org_id}_Original.csv` (backup)

#### Database Testing
1. Check `broadband.filer_processing_status` table
2. Verify status values:
   - `'complete'` for valid files
   - `'data_validation_failed'` for data errors
   - `'header_validation_failed'` for header errors
   - `'geocoding_errors'` for geocoding issues

#### Log Testing
1. Check: `/var/www/broadband/validate_subs.log`
2. Verify:
   - `[SEND EMAIL] BCC list:` shows your email
   - `[SEND ADMIN EMAIL] BCC list:` shows your email
   - No errors in SMTP transmission

---

## Expected Email Counts Per Test

| Test File | Admin Emails | Customer Emails | Total Emails You Receive |
|-----------|--------------|-----------------|--------------------------|
| 01_valid | 2 (Code A + Code B) | 1 (success) | 3 (admin x2 + BCC of success) |
| 02_header_error | 1 | 1 (header error) | 2 (admin + BCC of customer) |
| 03_header_error | 1 | 1 (header error) | 2 (admin + BCC of customer) |
| 04_address_issues | 1 | 1 (validation failed) | 2 (admin + BCC of customer) |
| 05_missing_coords | 2 | 0-1 (if geocoding fails) | 2-3 depending on geocoding |
| 06_data_errors | 1 | 1 (validation failed) | 2 (admin + BCC of customer) |
| 07_mixed_issues | 1 | 1 (validation failed) | 2 (admin + BCC of customer) |

**IMPORTANT:** With the BCC fix applied, you should receive at MINIMUM 2 emails for any validation that sends a customer email (1 admin notification + 1 BCC copy of customer email).

---

## Success Criteria

✅ System processes all test files without crashes
✅ Correct exit codes returned
✅ Database status updated correctly
✅ Output files generated in correct locations
✅ Admin receives notification emails for all tests
✅ **Admin receives BCC copies of all customer emails** ← NEW REQUIREMENT
✅ Customer emails have correct content and attachments
✅ Logs show proper BCC list configuration
✅ No SMTP errors in logs

---

## Troubleshooting

### If you don't receive BCC copies:

1. Verify production file is updated:
   ```bash
   grep "all_recipients" /var/www/broadband/validate_subscription_isp_mod_3.py
   ```
   Should show TWO lines with `all_recipients`

2. Check email config exists:
   ```bash
   cat /var/www/broadband/src/config/email_config.json
   ```
   Should show your email in `bcc_addresses`

3. Check logs for BCC confirmation:
   ```bash
   grep "BCC list:" /var/www/broadband/validate_subs.log
   ```
   Should show your email in BCC list

4. Verify SMTP_PASSWORD is set:
   ```bash
   echo $SMTP_PASSWORD
   ```

---

## Notes

- All test files use realistic US addresses and coordinates
- Technology types include: fiber, wireless_unlicensed
- Business customer flag: 0 = residential, 1 = business
- Download/upload speeds in Mbps
- VoIP lines quantity: 0 or higher

---

### 08_csv_with_origrownum.csv ⚠️
**Expected Result:** Exit Code 0 (Success - OrigRowNum removed automatically)

**Contents:**
- 10 valid subscriber records
- CSV file format
- **Has OrigRowNum column in Column A** (simulates user forgetting to remove it)
- All other data is valid

**What to Test:**
- System detects OrigRowNum column in CSV file
- OrigRowNum column is automatically removed
- Original CSV backed up as `*_original.csv`
- Validation proceeds successfully with cleaned file
- Admin receives success notification email
- Database status updated to 'complete'
- **NEW:** Logs show `[CSV CLEANING] Detected and removed OrigRowNum column`

---

### 09_excel_with_origrownum.xlsx ⚠️
**Expected Result:** Exit Code 0 (Success - Excel converted + OrigRowNum removed)

**Contents:**
- 10 valid subscriber records
- Excel (.xlsx) file format
- **Has OrigRowNum column in Column A** (simulates user forgetting to remove it)
- All other data is valid

**What to Test:**
- System detects Excel file format
- System converts Excel to CSV automatically
- OrigRowNum column is automatically removed during conversion
- Original Excel backed up as `*_original.xlsx`
- Validation proceeds successfully with cleaned CSV
- Admin receives success notification email
- Database status updated to 'complete'
- **NEW:** Logs show `[EXCEL CONVERSION]` and `[EXCEL CLEANING] Detected and removed OrigRowNum column`

---

### 10_excel_clean_no_origrownum.xlsx ✅
**Expected Result:** Exit Code 0 (Success - Excel converted, no cleaning needed)

**Contents:**
- 5 valid subscriber records
- Excel (.xlsx) file format
- **No OrigRowNum column** (clean file)
- All required columns present with valid data

**What to Test:**
- System detects Excel file format
- System converts Excel to CSV automatically
- No column removal needed
- Original Excel backed up as `*_original.xlsx`
- Validation proceeds successfully
- Admin receives success notification email
- Database status updated to 'complete'
- **NEW:** Logs show `[EXCEL CONVERSION]` but no cleaning messages

---

### 11_csv_clean_no_origrownum.csv ✅
**Expected Result:** Exit Code 0 (Success - no changes needed)

**Contents:**
- 5 valid subscriber records
- CSV file format
- **No OrigRowNum column** (clean file)
- All required columns present with valid data

**What to Test:**
- System detects CSV file format
- System checks for OrigRowNum column (not found)
- File passes through unchanged (no backup created)
- Validation proceeds successfully
- Admin receives success notification email
- Database status updated to 'complete'
- **NEW:** Logs show `[CSV CHECK] No OrigRowNum column found - file is clean`

---

## New Test Files Summary

These four new test files (08-11) specifically test the **Excel-to-CSV conversion** and **OrigRowNum auto-removal** functionality added January 9, 2026.

| Test File | Format | OrigRowNum? | Expected Behavior |
|-----------|--------|-------------|-------------------|
| 08_csv_with_origrownum.csv | CSV | ✅ Yes | Remove OrigRowNum, backup CSV, validate |
| 09_excel_with_origrownum.xlsx | Excel | ✅ Yes | Convert to CSV, remove OrigRowNum, backup Excel, validate |
| 10_excel_clean_no_origrownum.xlsx | Excel | ❌ No | Convert to CSV, backup Excel, validate |
| 11_csv_clean_no_origrownum.csv | CSV | ❌ No | Pass through unchanged, validate |

**All four files should result in Exit Code 0 (Success)** because the system now handles format conversion and column cleanup automatically.

---

**Last Updated:** January 9, 2026
**Created By:** Claude (Automated Testing Suite)
**Purpose:** Test BCC email functionality + comprehensive validation scenarios + Excel/CSV handling
