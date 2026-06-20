# Quick Guide: New Test Files (08-11)

**Created:** January 9, 2026
**Purpose:** Test Excel-to-CSV conversion and OrigRowNum auto-removal functionality

---

## Test Files Overview

### 08_csv_with_origrownum.csv
- **Type:** CSV file with OrigRowNum column
- **Records:** 10 valid subscribers
- **Tests:** CSV cleaning (OrigRowNum removal)
- **Expected:** Success (Column removed, file cleaned)

### 09_excel_with_origrownum.xlsx
- **Type:** Excel file with OrigRowNum column
- **Records:** 10 valid subscribers
- **Tests:** Excel conversion + OrigRowNum removal
- **Expected:** Success (Converted to CSV, column removed)

### 10_excel_clean_no_origrownum.xlsx
- **Type:** Clean Excel file (no OrigRowNum)
- **Records:** 5 valid subscribers
- **Tests:** Excel conversion only
- **Expected:** Success (Converted to CSV, no cleaning needed)

### 11_csv_clean_no_origrownum.csv
- **Type:** Clean CSV file (no OrigRowNum)
- **Records:** 5 valid subscribers
- **Tests:** Pass-through validation
- **Expected:** Success (No changes needed)

---

## Quick Test Commands

```bash
cd /var/www/broadband

# Test 08: CSV with OrigRowNum
python3 validate_subscription_isp_mod_3.py 208 2025-12-31 test@example.com
# Upload: 08_csv_with_origrownum.csv to /var/www/broadband/uploads/208/2025-12-31/subscribers/

# Test 09: Excel with OrigRowNum
python3 validate_subscription_isp_mod_3.py 209 2025-12-31 test@example.com
# Upload: 09_excel_with_origrownum.xlsx to /var/www/broadband/uploads/209/2025-12-31/subscribers/

# Test 10: Clean Excel
python3 validate_subscription_isp_mod_3.py 210 2025-12-31 test@example.com
# Upload: 10_excel_clean_no_origrownum.xlsx to /var/www/broadband/uploads/210/2025-12-31/subscribers/

# Test 11: Clean CSV
python3 validate_subscription_isp_mod_3.py 211 2025-12-31 test@example.com
# Upload: 11_csv_clean_no_origrownum.csv to /var/www/broadband/uploads/211/2025-12-31/subscribers/
```

---

## What to Check After Each Test

### 1. Exit Code
```bash
echo $?
# Should be 0 for all four tests
```

### 2. Log Messages
```bash
tail -50 /var/www/broadband/validate_subs.log
```

**For Test 08 (CSV with OrigRowNum), look for:**
```
[CSV CHECK] Org 208: Detected CSV file: 08_csv_with_origrownum.csv
[CSV CHECK] Checking for OrigRowNum column...
[CSV CLEANING] Org 208: Detected and removed OrigRowNum column
[CSV CLEANING] OrigRowNum column found - cleaning file...
[CSV CLEANING] Original CSV backed up as: 08_csv_with_origrownum_original.csv
[CSV CLEANING] Successfully cleaned CSV file
[CSV CLEANING] Original columns: 13, Final columns: 12
```

**For Test 09 (Excel with OrigRowNum), look for:**
```
[EXCEL CONVERSION] Org 209: Detected Excel file: 09_excel_with_origrownum.xlsx
[EXCEL CONVERSION] Converting to CSV format...
[EXCEL CLEANING] Org 209: Detected and removed OrigRowNum column
[EXCEL CONVERSION] Successfully converted to: 09_excel_with_origrownum.csv
[EXCEL CONVERSION] Original columns: 13, Final columns: 12
[EXCEL CONVERSION] Original Excel backed up as: 09_excel_with_origrownum_original.xlsx
```

**For Test 10 (Clean Excel), look for:**
```
[EXCEL CONVERSION] Org 210: Detected Excel file: 10_excel_clean_no_origrownum.xlsx
[EXCEL CONVERSION] Converting to CSV format...
[EXCEL CONVERSION] Successfully converted to: 10_excel_clean_no_origrownum.csv
[EXCEL CONVERSION] Original columns: 12, Final columns: 12
[EXCEL CONVERSION] Original Excel backed up as: 10_excel_clean_no_origrownum_original.xlsx
```

**For Test 11 (Clean CSV), look for:**
```
[CSV CHECK] Org 211: Detected CSV file: 11_csv_clean_no_origrownum.csv
[CSV CHECK] Checking for OrigRowNum column...
[CSV CHECK] No OrigRowNum column found - file is clean
[CSV CHECK] Columns: 12, Rows: 5
```

### 3. Output Files
```bash
# Check validation output directory
ls -lh /var/www/broadband/Subscriber_File_Validations/2025-12-31/20[8-9]/

# Verify backup files created (only for tests 08 and 09)
# Test 08: Should have 08_csv_with_origrownum_original.csv
# Test 09: Should have 09_excel_with_origrownum_original.xlsx
# Test 10: Should have 10_excel_clean_no_origrownum_original.xlsx
# Test 11: Should NOT have backup (file was clean)
```

### 4. Email Notifications
All four tests should send:
- 2 admin emails (Code A + Code B notifications)
- 1 customer success email
- **Total: 3 emails** (admin receives BCC copy of customer email)

### 5. Database Status
```sql
SELECT org_id, period, status, last_updated
FROM broadband.filer_processing_status
WHERE org_id IN (208, 209, 210, 211)
ORDER BY org_id;
```

All four should show `status = 'complete'`

---

## Success Criteria

| Test | Format | OrigRowNum | Exit Code | Backup Created | Columns Before | Columns After | Status |
|------|--------|------------|-----------|----------------|----------------|---------------|--------|
| 08 | CSV | Yes | 0 | Yes (CSV) | 13 | 12 | complete |
| 09 | Excel | Yes | 0 | Yes (Excel) | 13 | 12 | complete |
| 10 | Excel | No | 0 | Yes (Excel) | 12 | 12 | complete |
| 11 | CSV | No | 0 | No | 12 | 12 | complete |

---

## Expected Improvements

These test files verify that the system now:

✅ **Accepts Excel files** - Users don't need to convert manually
✅ **Removes OrigRowNum automatically** - Users don't need to delete Column A
✅ **Backs up original files** - Safety net for troubleshooting
✅ **Logs all operations** - Clear audit trail
✅ **Reduces user errors** - Automatic handling of common mistakes

**Expected Impact:** 50-75% reduction in validation failures due to format/column issues

---

## File Locations

**Test Files:**
```
/Users/robertolive/Documents/RSI_Projects/Automated_Subscriber_Validation/New_Testing_Data/
├── 08_csv_with_origrownum.csv
├── 09_excel_with_origrownum.xlsx
├── 10_excel_clean_no_origrownum.xlsx
└── 11_csv_clean_no_origrownum.csv
```

**Production Code:**
```
/var/www/broadband/validate_subscription_isp_mod_3.py
```

**Key Functions:**
- `_detect_and_remove_index_column()` (lines 581-606)
- `prepare_subscriber_file()` (lines 609-753)

---

**Created:** January 9, 2026
**Status:** Ready for testing
**Next Step:** Deploy code to production and run these tests
