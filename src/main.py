#!/usr/bin/env python3
"""Main entry point for the subscriber validation application."""

import argparse
import sys
from src.utils.logging import setup_logging, debug_print
from src.utils.file_handling import validate_subscriber_file
from src.config.settings import EXPECTED_COLUMNS


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Validate subscriber CSV file")
    parser.add_argument("input_csv", help="Path to input CSV file")
    parser.add_argument("company_id", help="Company ID for output directory")
    return parser.parse_args()


def main():
    """Execute the subscriber validation process."""
    args = parse_args()
    setup_logging()

    debug_print(f"Starting validation for {args.input_csv} with company_id={args.company_id}")

    try:
        # Run validation process (now returns file validation status)
        cleaned_df, errors, file_validation = validate_subscriber_file(args.input_csv, args.company_id)
        
        # Log completion summary
        debug_print(f"Validation completed. Processed {len(cleaned_df)} rows with {len(errors)} errors.")
        debug_print(f"Final file status: {file_validation.get('file_status', 'Unknown')}")
        
        # Determine exit code based on file validation status
        file_status = file_validation.get('file_status', 'Invalid')
        requires_review = file_validation.get('requires_manual_review', True)
        
        if file_status == 'Valid' and not requires_review:
            # File is ready for FCC BDC submission
            print(f"\n🎉 Process completed successfully - File ready for submission!")
            debug_print("Exiting with success code (0)")
            sys.exit(0)
            
        elif file_status == 'Invalid' or requires_review:
            # File needs manual review before submission
            print(f"\n📋 Process completed - Manual review required before submission")
            debug_print("Exiting with review required code (1)")
            sys.exit(1)
            
        else:
            # Unexpected status
            print(f"\n⚠️  Process completed with unexpected status: {file_status}")
            debug_print(f"Exiting with unexpected status code (2): {file_status}")
            sys.exit(2)
            
    except Exception as e:
        # Handle processing errors
        debug_print(f"Script failed with error: {str(e)}")
        print(f"\n❌ Processing failed: {str(e)}")
        print(f"📋 Check the error logs for detailed information")
        
        import traceback
        traceback.print_exc()
        debug_print("Exiting with error code (3)")
        sys.exit(3)


if __name__ == "__main__":
    main()