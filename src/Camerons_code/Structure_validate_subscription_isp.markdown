# Sequence of Activities in validate_subscription_isp.py

## Introduction
The `validate_subscription_isp.py` script processes subscriber data for broadband Internet Service Providers (ISPs) to generate FCC Form 477 subscription files. It handles two types of input files: detailed subscriber files (processed by `create_subscription`) and pre-aggregated subscription files (processed by `validate_sus`). The script validates input data, normalizes addresses, geocodes locations, checks for errors, and generates output files in a directory structure based on the ISP ID and filing period. It also sends email notifications for errors and logs processing details. The script connects to a PostgreSQL database to store and query data, using the Google Maps API for geocoding and SMTP for email notifications. Below is a list of output files created in the `<period_path>/subscription_processed/` directory, along with their purposes:

- **`processing_errors.txt`**: Lists validation errors (e.g., invalid column counts, zero speeds, invalid tech codes, geocoding failures, or state inconsistencies) for both subscriber and pre-aggregated files.
- **`<isp>_subscription_processed.csv`**: Aggregated subscription data grouped by census tract, technology, download speed, upload speed, total subscribers, and residential subscribers.
- **`477_<isp>_subscription_processed.csv`**: Similar to the above but maps technology code 71 (wireless PAL/educational) to 70 for FCC 477 compliance.
- **`<isp>_voice_subscription_processed.csv`**: Aggregated voice (VoIP) subscription data, grouped by census tract, with total and residential VoIP lines (generated only if VoIP data is present).
- **`<isp>_voice_state_data.txt`**: Summarizes VoIP subscriptions by state and technology code for state filings.

The following sections detail the sequence of activities performed by the script.

## 1. Parse Command-Line Arguments
- **Description**: The script expects two command-line arguments: `ispid` (ISP identifier) and `per` (filing period).
- **Location**: Lines 614–616.
- **Details**: Arguments are accessed via `sys.argv`. The script logs the start time and ISP ID to `validate_subs.log`. Missing or invalid arguments are not explicitly handled and may cause runtime errors.

## 2. Initialize Database Connection and Logging
- **Description**: Establishes a connection to a PostgreSQL database and initializes cursors for querying. Opens `validate_subs.log` for logging execution details.
- **Location**: Lines 618–624.
- **Details**: Connects to the `broadband` database on `localhost:5432` with hardcoded credentials. Creates a standard cursor and a `RealDictCursor` for dictionary-based query results. Logs the start of the script with a timestamp and ISP ID.

## 3. Scan Directory Structure
- **Description**: Scans the directory `/var/www/broadband/uploads/<ispid>/<period>` to locate subscriber (`subscribers`) or pre-aggregated (`oss_subscriptionOLD`) input files.
- **Location**: Lines 627–645.
- **Details**: Iterates through the directory structure to identify files in the `subscribers` or `oss_subscriptionOLD` subdirectories that match the specified `per` (filing period). Calls `create_subscription` for `subscribers` files or `validate_sus` for `oss_subscriptionOLD` files.

## 4. Process Subscriber Files (`create_subscription`)
- **Description**: Processes detailed subscriber files, normalizes addresses, validates data, geocodes locations, and generates aggregated subscription files.
- **Location**: Function `create_subscription` (lines 136–460).
- **Details**:
  - **Copy Input File**: Copies the input file to `<period_path>/<subfile>` for reference (lines 142–147).
  - **Normalize Addresses**: Applies regex substitutions to standardize address formats (e.g., "road" to "RD", "avenue" to "AVE", "north" to "N") and writes the normalized file back to `<period_path>/subscribers/<subfile>` (lines 149–211).
  - **Validate Column Count**: Checks if the CSV has 12 columns (`customer`, `lat`, `lon`, `address`, `address2`, `city`, `state`, `zip`, `download`, `upload`, `voip_lines_quantity`, `business_customer`, `technology`). If not, sends an email with the error and exits (lines 213–225).
  - **Create Database Table**: Drops any existing `subscribers.subs_<isp>` table, creates a new one with columns for subscriber data, and optionally copies non-active records from a previous table (lines 242–262).
  - **Process Rows**:
    - Reads CSV rows, skipping the header (lines 265–267).
    - Validates speeds (`download`, `upload` > 0), technology codes (must be in [0, 10, 11, 12, 20, 30, 40, 41, 42, 43, 44, 50, 60, 70, 71, 72, 90]), and location data (either `lat`/`lon` or complete address fields must be present). Logs errors to `errarr`, `techerr`, or `addrerr` (lines 305–341).
    - Maps technology names (e.g., "fiber" to 50, "wireless_unlicensed" to 70) to FCC codes (lines 283–304).
    - Geocodes addresses using the Google Maps API if `lat`/`lon` are missing (lines 342–348).
    - Determines census tract using PostGIS queries based on `lat`/`lon` and state FIPS code (lines 349–365).
    - Inserts valid rows into `subscribers.subs_<isp>` with `type='Active'` (lines 366–369).
  - **Create Index**: Creates an index on the `customer` column for performance (lines 373–375).
  - **Handle Errors**: If errors exist, writes them to `processing_errors.txt` and sends an email to the ISP contact (retrieved from `broadband.users`). Updates `filer_processing_status` to `subscription_status='errors'` (lines 378–423).
  - **Generate Output Files**:
    - Aggregates data into `<isp>_subscription_processed.csv` (tract, technology, download, upload, total, residential) (lines 426–451).
    - Creates `477_<isp>_subscription_processed.csv` with technology code 71 mapped to 70 (lines 452–463).
    - If VoIP data exists, generates `<isp>_voice_subscription_processed.csv` (tract, service_type, total, residential) (lines 464–487).
    - Generates `<isp>_voice_state_data.txt` summarizing VoIP by state and technology (lines 488–504).
  - **Update Status**: Sets `filer_processing_status` to `subscription_processed=true`, `subscription_status='complete'` if no errors (lines 505–507).

## 5. Process Pre-Aggregated Files (`validate_sus`)
- **Description**: Validates pre-aggregated subscription files (6 columns: `tract`, `tech`, `down`, `up`, `tot`, `res`) and generates output files.
- **Location**: Function `validate_sus` (lines 461–613).
- **Details**:
  - **Validate Column Count**: Checks if the CSV has 6 columns. If not, sends an email with the error and exits (lines 467–478).
  - **Create Temporary Table**: Creates a temporary table `temp_subscription_<isp>` to store data (lines 489–491).
  - **Process Rows**:
    - Reads CSV rows, checking for consistent state codes in `tract` (first two digits). Logs state changes in `stateerr` (lines 496–502).
    - Validates speeds (`down`, `up` > 0) and technology code (`tech` ≠ 0). Logs errors in `errarr` (lines 503–520).
    - Inserts rows into the temporary table (lines 521–523).
  - **Generate Output Files**:
    - Aggregates data into `<isp>_subscription_processed.csv` (tract, tech, down, up, tot, residential) (lines 532–541).
    - Creates `477_<isp>_subscription_processed.csv` with technology code 71 mapped to 70 (lines 542–550).
  - **Handle Errors**: If errors exist (`errarr` or `stateerr`), writes them to `processing_errors.txt` and sends an email to the ISP contact. Updates `filer_processing_status` to `subscription_status='errors'` (lines 555–597).
  - **Update Status**: Sets `filer_processing_status` to `subscription_processed=true`, `subscription_status='complete'` if no errors (lines 598–601).

## 6. Geocode Addresses
- **Description**: Uses the Google Maps API to geocode addresses when `lat`/`lon` are missing in subscriber files.
- **Location**: Function `geoCode` (lines 24–42).
- **Details**: Constructs an address string (`address,city,state zip`) and queries the Google Maps API with a hardcoded API key. Returns latitude and longitude or `None` if geocoding fails. Logs geocoding errors in `addrerr`.

## 7. Send Email Notifications
- **Description**: Sends email notifications to ISP contacts for validation errors, attaching error details.
- **Location**: Function `sendEmail` (lines 44–80).
- **Details**: Uses `smtplib` with SSL to send emails via Gmail SMTP. Constructs a MIME message with a subject, body (error details), and BCC. Logs email sending to `validate_subs.log`. Uses hardcoded credentials for authentication.

## 8. Finalize and Close
- **Description**: Closes the database connection and logs completion to `validate_subs.log`.
- **Location**: Lines 646–649.
- **Details**: Commits any remaining database changes, closes the connection, and logs the completion with ISP ID and timestamp.