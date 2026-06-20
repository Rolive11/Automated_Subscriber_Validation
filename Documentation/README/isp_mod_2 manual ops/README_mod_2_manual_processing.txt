================================================================================
VALIDATE_SUBSCRIPTION_ISP_MOD_2.PY - MANUAL PROCESSING GUIDE
================================================================================

OVERVIEW
--------
This script manually processes subscriber files for FCC BDC filing when the
automated system fails or needs a manual override. It validates subscriber
data, geocodes addresses, assigns census tracts, and generates output files
for FCC submission.


WHEN TO USE THIS SCRIPT
-----------------------
Use this script when:
- The automated processing service fails to pick up a file
- You need to reprocess a file after database corrections
- Testing new subscriber files before full automation
- Troubleshooting processing issues for specific customers


PREREQUISITES
-------------
Before running this script, ensure:

1. You are on the production server or have access to:
   - /var/www/broadband/uploads/ directory structure
   - PostgreSQL database with proper credentials
   - Google Maps API key for geocoding

2. Environment variables are set:
   - DB_HOST (default: localhost)
   - DB_PORT (default: 5432)
   - DB_NAME (default: broadband)
   - DB_USER (default: broadband)
   - DB_PASSWORD (REQUIRED - no default)
   - SMTP_PASSWORD (REQUIRED for sending emails)
   - GOOGLE_MAPS_API_KEY (REQUIRED for geocoding)
   - SMTP_USER (optional, default: info@regulatorysolutions.us)

3. The subscriber file is already uploaded to:
   /var/www/broadband/uploads/{org_id}/{period}/subscribers/


COMMAND SYNTAX
--------------
python3 validate_subscription_isp_mod_2.py {org_id} {period} {user_email}

PARAMETERS:
  {org_id}      - Organization ID number (e.g., 371, 223)
  {period}      - Filing period in yyyy-mm-dd format (e.g., 2025-12-31)
  {user_email}  - Email address to send results to (must be valid format)


EXAMPLES
--------

Example 1: Process subscriber file for organization 371, December 2025 filing
---------------------------------------------------------------------------
python3 validate_subscription_isp_mod_2.py 371 2025-12-31 customer@example.com

This will:
- Look for CSV files in: /var/www/broadband/uploads/371/2025-12-31/subscribers/
- Process all CSV files found in that directory
- Send results to customer@example.com


Example 2: Process subscriber file for organization 223, June 2025 filing
-------------------------------------------------------------------------
python3 validate_subscription_isp_mod_2.py 223 2025-06-30 admin@company.com

This will:
- Look for CSV files in: /var/www/broadband/uploads/223/2025-06-30/subscribers/
- Process all CSV files found in that directory
- Send results to admin@company.com


Example 3: Reprocess after fixing database issues
--------------------------------------------------
python3 validate_subscription_isp_mod_2.py 500 2025-12-31 support@isp.net

Use this when you've corrected database issues and need to regenerate output files.


WHAT THE SCRIPT DOES
--------------------
The script performs these operations in sequence:

PHASE 1: Code A Validation
  - Calls Code A validation subprocess (FCC format validation)
  - Validates column headers and data format
  - Corrects addresses using USPS/Smarty API
  - Generates corrected Excel files with color-coded errors
  - Returns status: valid, invalid, header_error, or error

PHASE 2: Code B Processing (if Phase 1 passes)
  - Geocodes addresses (if lat/lon missing)
  - Assigns census tracts to each subscriber
  - Creates subscription output files
  - Generates VoIP data files (if applicable)
  - Updates database status


OUTPUT FILES
------------
If processing succeeds, files are created in:
/var/www/broadband/uploads/{org_id}/{period}/subscription_processed/

Files created:
  {org_id}_subscription_processed.csv          - Main subscriber data by tract
  477_{org_id}_subscription_processed.csv      - Form 477 compatible version
  {org_id}_voice_subscription_processed.csv    - VoIP data (if applicable)
  {org_id}_voice_state_data.txt                - VoIP state summaries

Validation artifacts are saved to:
/var/www/broadband/Subscriber_File_Validations/{period}/{org_id}/

Artifacts include:
  {org_id}_Corrected_Subscribers.csv           - Validated CSV file
  {org_id}_Corrected_Subscribers.xlsx          - Excel with corrections
  {org_id}_VR.xlsx                             - Validation Report


EMAILS SENT
-----------
The script automatically sends emails based on processing results:

SUCCESS:
  - User receives: Success email with VR.xlsx validation report attached
  - Admin receives: Phase 1 results (Code A artifacts) AND Phase 2 results (output files)

VALIDATION ERRORS (invalid data):
  - User receives: Modified Excel file with color-coded errors to fix
  - Admin receives: Code A results with debug output

HEADER ERRORS:
  - User receives: Instructions on fixing column headers with original CSV
  - Admin receives: Header error notification with artifacts

GEOCODING ERRORS (partial success):
  - User receives: Success email noting which addresses failed geocoding
  - Admin receives: Phase 2 results with error details

SYSTEM ERRORS:
  - User receives: Error notification
  - Admin receives: Full error details and debug output


DATABASE UPDATES
----------------
The script updates the broadband.filer_processing_status table:

Status values set:
  'processing'                 - At start of validation
  'complete'                   - Successful processing
  'data_validation_failed'     - Code A found data errors
  'header_validation_failed'   - Column header mismatch
  'geocoding_errors'           - Some addresses couldn't be geocoded
  'system_error'               - Technical failure

User messages are also inserted into broadband.messages table for display
in the web interface.


SUBSCRIBER DATA TABLE
---------------------
Creates or replaces table: subscribers.subs_{org_id}

Columns:
  customer, lat, lon, address, address2, city, state, zip, download, upload,
  voip_lines_quantity, business_customer, technology, tech, tract, match,
  bdc_id, type, date, notes


LOGGING
-------
All processing activity is logged to:
  validate_subs.log (in current directory)

Check this file for:
- Processing start/end times
- File paths being processed
- Code A validation results
- Geocoding errors
- Email sending status
- Database operations
- Error messages and stack traces


ERROR HANDLING
--------------
Common errors and solutions:

ERROR: Missing required arguments
  Solution: Provide all 3 arguments: org_id, period, user_email

ERROR: Invalid email format
  Solution: Use a valid email address (e.g., user@domain.com)

ValueError: DB_PASSWORD environment variable not set
  Solution: Set the DB_PASSWORD environment variable before running

ValueError: SMTP_PASSWORD environment variable not set
  Solution: Set the SMTP_PASSWORD environment variable before running

ValueError: GOOGLE_MAPS_API_KEY environment variable not set
  Solution: Set the GOOGLE_MAPS_API_KEY environment variable before running

No files found in subscribers directory
  Solution: Check that CSV file exists in correct directory:
            /var/www/broadband/uploads/{org_id}/{period}/subscribers/

Code A validation timeout
  Solution: File may be too large or Code A hung - check validate_subs.log

Database connection errors
  Solution: Verify database credentials and that PostgreSQL is running

PermissionError: [Errno 13] Permission denied: '/var/www/broadband/Subscriber_File_Validations/{period}'
  Problem: Code A cannot create period subdirectories due to insufficient permissions
  Solution: Fix directory permissions on production server:
            chmod 777 /var/www/broadband/Subscriber_File_Validations
  Verification: ls -ld /var/www/broadband/Subscriber_File_Validations
                (should show drwxrwxrwx)


IMPORTANT NOTES
---------------
1. The script processes ALL CSV files in the subscribers directory for the
   specified org_id and period.

2. Email address provided is used for ALL email communications about this
   processing run.

3. The script will DROP and recreate the subscribers.subs_{org_id} table,
   so any existing data is replaced.

4. Code A validation runs with a 10-minute timeout. Large files may exceed
   this limit.

5. Google Maps geocoding API calls cost money. The script only geocodes
   addresses that are missing lat/lon coordinates.

6. The script updates the processing status in real-time, so the web
   interface will reflect current status.


FILE REQUIREMENTS
-----------------
Subscriber CSV files must contain these 12 columns (in any order):
  - customer
  - lat
  - lon
  - address
  - city
  - state
  - zip
  - download
  - upload
  - voip_lines_quantity
  - business_customer
  - technology

For detailed field requirements, see:
https://regulatorysolutions.us/downloads/subscriber_template_instructionsV2.pdf


TROUBLESHOOTING CHECKLIST
--------------------------
If the script fails:

[ ] Check validate_subs.log for error messages
[ ] Verify all environment variables are set
[ ] Confirm subscriber file exists in correct directory
[ ] Check database connectivity (can you connect manually?)
[ ] Verify file has correct column headers
[ ] Check file permissions on upload directories
[ ] Confirm Code A validation scripts are accessible at /var/www/broadband/
[ ] Test email sending (SMTP credentials valid?)
[ ] Verify Google Maps API key is valid and has quota remaining


SUPPORT
-------
For issues or questions:
- Check validate_subs.log for detailed error information
- Contact: Regulatory Solutions, Inc.
- Phone: 972-836-7107
- Email: rolive@regulatorysolutions.us


VERSION HISTORY
---------------
validate_subscription_isp_mod_2.py - Current stable standalone version
  - Two-phase processing (Code A validation + Code B geocoding)
  - Enhanced email notifications
  - User message system integration
  - Processing status tracking

================================================================================
Last Updated: 2025-12-16
================================================================================
