import csv
import psycopg2
from psycopg2.extras import RealDictCursor
import sys
import os
import shutil
from datetime import datetime
import smtplib
import ssl
import email
import glob
import subprocess
import math
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests
import googlemaps
from time import time, sleep
import re

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, rely on system environment variables
    pass


def truncate(f, n):
    return math.floor(f * 10 ** n) / 10 ** n


def geoCode(address_or_zipcode):

    lat, lng = None, None
    api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    if not api_key:
        raise ValueError("GOOGLE_MAPS_API_KEY environment variable not set")
    gmaps = googlemaps.Client(key=api_key)

    geocode_result = gmaps.geocode(address_or_zipcode)
    # print(geocode_result)
    results = geocode_result[0]['geometry']['location']
    lat = results['lat']
    lng = results['lng']
    # print('lat lng ' + str(lat) + ' ' + str(lng))

    # base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    # endpoint = f"{base_url}?address={address_or_zipcode}&amp;key={api_key}"
    # see how our endpoint includes our API key? Yes this is yet another reason to restrict the key
    # r = requests.get(endpoint)
    # print(r)
    # print("status code " + str(r.status_code))
    # if r.status_code not in range(200, 299):
    #    print('status code not in range')
    #    return None, None
    # try:
    #    '''
    #    This try block incase any of our inputs are invalid. This is done instead
    #    of actually writing out handlers for all kinds of responses.
    #    '''
    # print('got geocode response ')
    # results = r.json()['results'][0]
    # print("results " + results)
    # lat = results['geometry']['location']['lat']
    # lng = results['geometry']['location']['lng']
    # except:
    #    print('pass')
    #    pass  '''
    return lat, lng


def sendEmail(customer, name, emessage, attachment_path=None, subject=None):
    """Send email to customer with optional file attachment."""
    with open('validate_subs.log', 'a') as f:
        print(f'sending email error log for customer {customer}\n', file=f)
    port = 465  # For SSL
    customer = 'ccrum@murcevilo.com'
    # Create a secure SSL context
    context = ssl.create_default_context()

    message = MIMEMultipart()
    message["From"] = 'info@regulatorysolutions.us'
    message["To"] = customer
    default_subject = 'Automated Message - Subscriber File Processing Update'
    message["Subject"] = subject if subject else default_subject
    # Recommended for mass emails
    message["Bcc"] = 'cscrumconsulting@gmail.com'

    # Add body to email
    message.attach(MIMEText(emessage, "plain"))

    # Add file attachment if provided
    if attachment_path and os.path.exists(attachment_path):
        try:
            with open(attachment_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())

            # Encode file in ASCII characters to send by email
            encoders.encode_base64(part)

            # Add header as key/value pair to attachment part
            filename = os.path.basename(attachment_path)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename= {filename}",
            )

            # Add attachment to message
            message.attach(part)

            with open('validate_subs.log', 'a') as f:
                print(f'Added user attachment: {filename}\n', file=f)

        except Exception as e:
            with open('validate_subs.log', 'a') as f:
                print(f'Failed to attach file {attachment_path}: {str(e)}\n', file=f)
    elif attachment_path:
        with open('validate_subs.log', 'a') as f:
            print(f'User attachment file not found: {attachment_path}\n', file=f)

    text = message.as_string()

    smtp_user = os.getenv('SMTP_USER', 'info@regulatorysolutions.us')
    smtp_password = os.getenv('SMTP_PASSWORD')
    if not smtp_password:
        raise ValueError("SMTP_PASSWORD environment variable not set")

    with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, customer, text)

    with open('validate_subs.log', 'a') as f:
        print(f'User email sent successfully to {customer}\n', file=f)

    return


def sendEmailToAdmin(subject, message, attachment_paths=None,
                     admin_email='rolive@regulatorysolutions.us'):
    """Send email to admin with optional file attachments."""
    try:
        with open('validate_subs.log', 'a') as f:
            print(f'Sending admin email: {subject}\n', file=f)

        port = 465  # For SSL
        context = ssl.create_default_context()

        email_message = MIMEMultipart()
        email_message["From"] = 'info@regulatorysolutions.us'
        email_message["To"] = admin_email
        email_message["Subject"] = subject
        email_message["Bcc"] = 'cscrumconsulting@gmail.com'

        # Add body to email
        email_message.attach(MIMEText(message, "plain"))

        # Add file attachments if provided
        if attachment_paths:
            for file_path in attachment_paths:
                if os.path.exists(file_path):
                    try:
                        with open(file_path, "rb") as attachment:
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(attachment.read())

                        # Encode file in ASCII characters to send by email
                        encoders.encode_base64(part)

                        # Add header as key/value pair to attachment part
                        filename = os.path.basename(file_path)
                        part.add_header(
                            "Content-Disposition",
                            f"attachment; filename= {filename}",
                        )

                        # Add attachment to message
                        email_message.attach(part)

                        with open('validate_subs.log', 'a') as f:
                            print(f'Added attachment: {filename}\n', file=f)

                    except Exception as e:
                        with open('validate_subs.log', 'a') as f:
                            print(f'Failed to attach file {file_path}: {str(e)}\n', file=f)
                else:
                    with open('validate_subs.log', 'a') as f:
                        print(
                            f'Attachment file not found: {file_path}\n', file=f)

        # Convert message to string and send
        text = email_message.as_string()

        smtp_user = os.getenv('SMTP_USER', 'info@regulatorysolutions.us')
        smtp_password = os.getenv('SMTP_PASSWORD')
        if not smtp_password:
            raise ValueError("SMTP_PASSWORD environment variable not set")

        with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, admin_email, text)

        with open('validate_subs.log', 'a') as f:
            print(f'Admin email sent successfully to {admin_email}\n', file=f)

    except Exception as e:
        with open('validate_subs.log', 'a') as f:
            print(f'Failed to send admin email: {str(e)}\n', file=f)
        # Don't raise exception - email failure shouldn't break the main
        # process


def call_code_a_validation(org_id, period, subscriber_file_path):
    """
    Call Code A validation subprocess and handle results.

    Args:
        org_id (str): Organization ID
        period (str): Filing period
        subscriber_file_path (str): Full path to subscriber CSV file

    Returns:
        dict: {
            'status': 'valid'|'invalid'|'error',
            'return_code': int,
            'csv_path': str or None,
            'excel_path': str or None,
            'artifact_paths': list,
            'error_message': str or None,
            'stdout': str,
            'stderr': str
        }
    """

    # Build Code A command
    base_output_dir = f"/var/www/broadband/uploads/{org_id}/{period}"
    code_a_base_dir = "/var/www/broadband"

    cmd = [
        "python3",
        "-m",
        "src.main",
        subscriber_file_path,
        str(org_id)
    ]

    with open('validate_subs.log', 'a') as f:
        print(f'Calling Code A validation from {code_a_base_dir}: {" ".join(cmd)}\n', file=f)

    try:
        # Execute Code A subprocess with correct working directory
        result = subprocess.run(
            cmd,
            cwd=code_a_base_dir,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        return_code = result.returncode
        stdout = result.stdout
        stderr = result.stderr

        with open('validate_subs.log', 'a') as f:
            print(
                f'Code A completed with return code: {return_code}\n',
                file=f)
            if stdout:
                print(f'Code A stdout: {stdout}\n', file=f)
            if stderr:
                print(f'Code A stderr: {stderr}\n', file=f)

        # Find all artifacts created by Code A
        # Code A saves files to company_id directory relative to its working directory
        validation_results_dir = os.path.join(code_a_base_dir, str(org_id))
        artifact_paths = []

        if os.path.exists(validation_results_dir):
            # Get all files in company_id directory
            artifact_paths = glob.glob(f"{validation_results_dir}/*")
            with open('validate_subs.log', 'a') as f:
                print(f'Found {len(artifact_paths)} Code A artifacts in {validation_results_dir}\n',file=f)
                for path in artifact_paths:
                    print(f'  - {os.path.basename(path)}\n', file=f)
        else:
            with open('validate_subs.log', 'a') as f:
                print(f'Warning: Code A output directory not found: {validation_results_dir}\n', file=f)

        # Determine file paths for key outputs
        csv_path = None
        excel_path = None

        for path in artifact_paths:
            filename = os.path.basename(path)
            if filename.endswith('_Corrected_Subscribers.csv'):
                csv_path = path
            elif filename.endswith('_Corrected_Subscribers.xlsx'):
                excel_path = path

        # Interpret return code
        if return_code == 0:
            status = 'valid'
            error_message = None
        elif return_code == 1:
            status = 'invalid'
            error_message = "File requires manual review before submission"
        else:
            status = 'error'
            error_message = f"Code A validation failed with return code {return_code}"
            if stderr:
                error_message += f": {stderr}"

        return {
            'status': status,
            'return_code': return_code,
            'csv_path': csv_path,
            'excel_path': excel_path,
            'artifact_paths': artifact_paths,
            'error_message': error_message,
            'stdout': stdout,
            'stderr': stderr
        }

    except subprocess.TimeoutExpired:
        error_msg = "Code A validation timed out after 10 minutes"
        with open('validate_subs.log', 'a') as f:
            print(f'Code A timeout error: {error_msg}\n', file=f)

        return {
            'status': 'error',
            'return_code': 124,  # Standard timeout exit code
            'csv_path': None,
            'excel_path': None,
            'artifact_paths': [],
            'error_message': error_msg,
            'stdout': '',
            'stderr': error_msg
        }

    except Exception as e:
        error_msg = f"Failed to execute Code A validation: {str(e)}"
        with open('validate_subs.log', 'a') as f:
            print(f'Code A execution error: {error_msg}\n', file=f)

        return {
            'status': 'error',
            'return_code': 999,  # Custom error code
            'csv_path': None,
            'excel_path': None,
            'artifact_paths': [],
            'error_message': error_msg,
            'stdout': '',
            'stderr': str(e)
        }


def create_subscription(subfile, filename, isp, periodpath, period):
    print(
        "subfile ",
        subfile,
        " filename ",
        filename,
        " isp ",
        isp,
        " periodpath ",
        periodpath)
    subscrfile = periodpath + "/subscribers/" + subfile

    # === NEW: PHASE 1 - CODE A VALIDATION ===
    print("========================================")
    print("PHASE 1: Calling Code A for validation")
    print("========================================")

    # Call Code A validation
    validation_result = call_code_a_validation(isp, period, subscrfile)

    # Email all artifacts to admin regardless of outcome
    subject = f"Code A Validation Results - Org {isp}, Period {period}"
    if validation_result['status'] == 'valid':
        message = f"Code A validation completed successfully for Org {isp}.\n\nFile Status: VALID - Ready for geocoding and processing.\n\nReturn Code: {validation_result['return_code']}\n\nProcessed File: {validation_result['csv_path']}"
    elif validation_result['status'] == 'invalid':
        # Include full stdout for debugging why validation failed
        message = f"Code A validation completed for Org {isp}.\n\nFile Status: INVALID - Requires manual review.\n\nReason: {validation_result['error_message']}\n\nReturn Code: {validation_result['return_code']}\n\n{'='*60}\nDEBUG OUTPUT (stdout):\n{'='*60}\n{validation_result['stdout']}\n\n{'='*60}\nERROR OUTPUT (stderr):\n{'='*60}\n{validation_result['stderr']}\n\nCorrected file has been sent to user for review."
    else:  # error
        message = f"Code A validation FAILED for Org {isp}.\n\nFile Status: ERROR\n\nError: {validation_result['error_message']}\n\nReturn Code: {validation_result['return_code']}\n\n{'='*60}\nDEBUG OUTPUT (stdout):\n{'='*60}\n{validation_result['stdout']}\n\n{'='*60}\nERROR OUTPUT (stderr):\n{'='*60}\n{validation_result['stderr']}"

    sendEmailToAdmin(subject, message, validation_result['artifact_paths'])

    # Handle validation results
    if validation_result['status'] == 'invalid':
        # File needs manual review - send corrected Excel to user and stop
        # processing
        print("========================================")
        print("PHASE 1 RESULT: INVALID - Sending corrected file to user")
        print("========================================")

        # Get user email and name
        sql = """Select email,name from broadband.users where org_id = """ + isp + """ limit 1"""
        ps_cursor.execute(sql)
        userems = ps_cursor.fetchall()
        customer = ''
        cname = ''
        for em in userems:
            customer = em["email"]
            cname = em["name"]

        # Create user message
        user_message = f"""Dear {cname},

Your subscriber file needs manual review before FCC submission.

We have attached a corrected Excel file with color-coded cells:
- Red and Pink cells: these cells must be corrected; Or, a row with a red or pink cell may be deleted by the user. The subscriber assigned to the deleted row will not be represented in your subscriber data submitted to the FCC.
- Green/Yellow cells: Leave unchanged

Please:
1. Open the attached Excel file
2. Only modify data in RED and PINK cells
3. Save as CSV format
4. Re-upload the corrected file

For your convenience, detailed field requirements are available at:
https://regulatorysolutions.us/downloads/subscriber_template_instructionsV2.pdf

Best regards,
The Regulatory Solutions Team"""

        # Send corrected Excel file to user with attachment
        excel_attachment = validation_result['excel_path'] if validation_result['excel_path'] and os.path.exists(
            validation_result['excel_path']) else None
        custom_subject = f'Subscriber File Validation - Manual Review Required'
        sendEmail(
            customer,
            cname,
            user_message,
            excel_attachment,
            custom_subject)

        if excel_attachment:
            with open('validate_subs.log', 'a') as f:
                print(f'Sent corrected Excel file to user: {os.path.basename(excel_attachment)}\n',file=f)
        else:
            with open('validate_subs.log', 'a') as f:
                print(
                    f'Warning: No Excel file available to send to user for org {isp}\n',
                    file=f)

        # Update database status
        sql = """Update filer_processing_status set subscription_processed = true, subscription_status = 'validation_failed' where org_id = """ + \
            isp + """ and filing_period = '""" + period + """' """
        cursor.execute(sql)
        conn.commit()

        return  # Stop processing

    elif validation_result['status'] == 'error':
        # Code A failed - stop processing
        print("========================================")
        print("PHASE 1 RESULT: ERROR - Code A validation failed")
        print("========================================")

    # Get user email and name
    sql = """Select email,name from broadband.users where org_id = """ + isp + """ limit 1"""
    ps_cursor.execute(sql)
    userems = ps_cursor.fetchall()
    customer = ''
    cname = ''
    for em in userems:
        customer = em["email"]
        cname = em["name"]

    # Create user error message
    error_message = f"""Dear {cname},

    We encountered a technical issue while processing your subscriber file that prevented validation from completing.

    This is typically due to file format issues such as:
    - Missing required columns
    - Incorrect file structure
    - File encoding problems

    Please verify your file follows the subscriber template format and re-upload, or contact our support team for assistance.

    For your convenience, detailed field requirements are available at:
    https://regulatorysolutions.us/downloads/subscriber_template_instructionsV2.pdf

    Best regards,
    The Regulatory Solutions Team"""

    # Send error notification to user
    sendEmail(customer, cname, error_message, None,
              'Subscriber File Processing Error')

    # Update database status
    sql = """Update filer_processing_status set subscription_processed = true, subscription_status = 'validation_error' where org_id = """ + \
        isp + """ and filing_period = '""" + period + """' """
    cursor.execute(sql)
    conn.commit()

    return  # Stop processing

    # If we get here, validation_result['status'] == 'valid'
    print("========================================")
    print("PHASE 1 RESULT: VALID - Proceeding with geocoding and processing")
    print("========================================")

    # Use Code A's corrected CSV file for further processing
    if not validation_result['csv_path'] or not os.path.exists(
            validation_result['csv_path']):
        print("ERROR: Code A corrected CSV file not found")
        return

    subscrfile = validation_result['csv_path']  # Use Code A's output
    print(f"Using Code A corrected file: {subscrfile}")

    # === PHASE 2: CODE B GEOCODING AND DATABASE PROCESSING ===
    print("========================================")
    print("PHASE 2: Starting geocoding and database processing")
    print("========================================")

    # Validate column count (Code A should have ensured this, but double-check)
    with open(subscrfile) as csv_file:
        rowtest = csv.reader(csv_file, delimiter=',')
        ncols = len(next(rowtest))
        if ncols != 12:
            print(
                "    ERROR: Code A output should have 12 cols but has " +
                str(ncols))
            # This should not happen if Code A worked correctly
            sql = """Update filer_processing_status set subscription_processed = true, subscription_status = 'format_error' where org_id = """ + \
                isp + """ and filing_period = '""" + period + """' """
            cursor.execute(sql)
            conn.commit()
            return

    # Continue with Code B's database operations (geocoding, tract assignment,
    # etc.)
    now = datetime.now()
    date_time = now.strftime("%m/%d/%Y, %H:%M:%S")
    addrerr = []  # Only geocoding errors now

    with open(subscrfile) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        next(csv_reader)

        sql = """SELECT EXISTS (
                        SELECT 1
                        FROM pg_tables
                        WHERE schemaname = 'subscibers'
                        AND tablename = 'subs_""" + str(isp) + """'
                        );"""
        cursor.execute(sql)
        se = cursor.fetchone()
        subsexist = se[0]
        print("subsexist" + str(subsexist))
        if (subsexist == True):
            print("getting leads from subs")
            sql = """Select * into subscribers.subs_""" + \
                str(isp) + """_temp from subscribers.subs_""" + \
                str(isp) + """ where type != 'Active' """
            cursor.execute(sql)

        sql = """Drop table if exists subscribers.subs_""" + isp
        cursor.execute(sql)
        sql = """CREATE TABLE subscribers.subs_""" + isp + \
            """ (customer text,lat numeric,lon numeric,address text,address2 text,city text,state text,zip text,download numeric,upload numeric,voip_lines_quantity integer,business_customer numeric,technology integer,tech text,tract text, match boolean,bdc_id integer,type text, date timestamp without time zone,notes text)"""
        cursor.execute(sql)
        conn.commit()
        subsarr = []
        state = ''
        voipneeded = False
        line_count = 0

        for row in csv_reader:
            customer = row[0]
            lat = row[1]
            lon = row[2]
            address = row[3].upper()
            city = row[4].upper()
            state = row[5].upper()
            zip = row[6]
            down = row[7]
            up = row[8]
            voip = row[9]
            if voip == '':
                voip = int(0)
                print('voip 0')
            if int(voip) > 0:
                voipneeded = True
            business = row[10]
            techname = row[11]
            print('techname ', techname)

            # Technology code mapping (keep this since it's Code B specific)
            tech = 1
            if techname == 'wireless_unlicensed':
                tech = 70
            if techname == 'wireless_gaa':
                tech = 72
            if techname == 'wireless_pal':
                tech = 71
            if techname == 'wireless_educational':
                tech = 71
            if techname == 'fiber':
                tech = 50
            if techname == 'cable':
                tech = 43
            if techname == 'ethernet':
                tech = 10
            if techname == 'adsl2':
                tech = 11
            if techname == 'voip':
                tech = 1

            print(lat, lon, address, city, state, zip, str(tech))

            # GEOCODING: Only geocode if lat/lon are missing (Code A validated
            # addresses)
            if lat == '' or lon == '' and (
                    address != '' and city != '' and state != '' and zip != ''):
                addr = address + ',' + city + ',' + state + ' ' + zip
                (lt, ln) = geoCode(addr)
                if lt is None or ln is None:
                    rowerr = line_count + 1
                    print("error geocoding row " + str(rowerr))
                    errstr = 'error geocoding row ' + \
                        str(rowerr) + ' addr: ' + addr
                    addrerr.append(errstr)
                else:
                    lat = lt
                    lon = ln

            # Census tract assignment (only if we have coordinates)
            if lat != '' and lon != '':
                print("lat/lon" + str(lat) + " " + str(lon))
                statefp = 0
                if state != 'VI':
                    sql = """select statefp10 from census_data.states where ST_Intersects(geom,ST_setSRID(ST_Makepoint(%s,%s),4326))"""
                    cursor.execute(sql, (lon, lat))
                    print(sql, lon, lat)
                    sfp = cursor.fetchone()
                    print(sfp)
                    statefp = sfp[0]
                else:
                    statefp = '78'
                print("statefp " + statefp)
                sql = """Select geoid from census_data.tracts20 where statefp = %s and ST_Intersects(ST_SetSRID(ST_MakePoint(%s,%s),4326), geog)"""
                print(sql, lat, lon)
                cursor.execute(sql, (statefp, float(lon), float(lat)))
                t = cursor.fetchone()
                tract = t[0]
                print("tract " + tract)
                sql = """Insert into subscribers.subs_""" + isp + """ (customer,lat,lon,address,city,state,zip,download,upload,voip_lines_quantity,business_customer,technology,tech,tract,type,date)
                        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
                cursor.execute(
                    sql,
                    (customer,
                     lat,
                     lon,
                     address,
                     city,
                     state,
                     zip,
                     down,
                     up,
                     voip,
                     business,
                     tech,
                     techname,
                     tract,
                     'Active',
                     date_time))
                conn.commit()
            line_count += 1
            print({line_count}, end='\r')
        print(f'Processed {line_count} lines.')
        conn.commit()
        print("creating index on subs table ")
        sql = """create index subs_""" + \
            str(isp) + """_customer_index on subscribers.subs_""" + \
            str(isp) + """ (customer);"""
        cursor.execute(sql)
        conn.commit()

        # Handle geocoding errors (only errors now, Code A handled validation)
        if len(addrerr) > 0:
            errf = periodpath + "/subscription_processed/processing_errors.txt"
            dirExist = os.path.exists(periodpath + "/subscription_processed/")
            if dirExist == False:
                os.umask(0)
                os.makedirs(
                    periodpath +
                    "/subscription_processed/",
                    mode=0o777)
            isExist = os.path.exists(errf)

            if (isExist):
                os.remove(errf)
            errfil = open(
                periodpath +
                "/subscription_processed/processing_errors.txt",
                "a")
            errfil.write('Date: ' + date_time + '\n')

            # Send email about geocoding errors
            sql = """Select email,name from broadband.users where org_id = """ + isp + """ limit 1"""
            ps_cursor.execute(sql)
            userems = ps_cursor.fetchall()
            customer = ''
            cname = ''
            for em in userems:
                customer = em["email"]
                cname = em["name"]
            em_message = 'Dear ' + cname + \
                ', \nYour subscriber file passed validation but we encountered geocoding errors for some addresses:\n\nDate: ' + date_time + '\n'

            for errs in addrerr:
                errfil.write(errs + "\n")
                em_message += errs + "\n"

            em_message += '\nThese addresses could not be geocoded and may need manual coordinate entry. The rest of your file has been processed successfully.\n\nBest Regards,\n\nThe Regulatory Solutions Team'
            print(
                "sending geocoding error email to  " +
                customer +
                " " +
                cname)
            sendEmail(customer, cname, em_message, None,
                      'Subscriber File Processing - Geocoding Issues')
            errfil.close()

            sql = """Update filer_processing_status set subscription_processed = true, subscription_status = 'geocoding_errors' where org_id = """ + \
                isp + """ and filing_period = '""" + period + """' """
            cursor.execute(sql)
            conn.commit()

        else:
            # SUCCESS - continue with existing Code B processing
            if (subsexist == True):
                sql = """insert into subscribers.subs_""" + isp + \
                    """ select * from subscribers.subs_""" + isp + """_temp """
                cursor.execute(sql)
                conn.commit()

            sql = """Drop table if exists subscribers.subs_""" + isp + """_temp """
            cursor.execute(sql)
            conn.commit()

            # Continue with successful processing - create output files
            tmpout = "/tmp/" + isp + "_subscription_processed.csv"
            outfil = periodpath + "/subscription_processed/" + \
                isp + "_subscription_processed.csv"
            dirExist = os.path.exists(periodpath + "/subscription_processed/")
            if dirExist == False:
                os.umask(0)
                os.makedirs(
                    periodpath +
                    "/subscription_processed/",
                    mode=0o777)
            isExist = os.path.exists(outfil)

            if (isExist):
                os.remove(outfil)

            sql = """COPY (Select tract,
                            technology,
                            download,
                            upload,
                            count(customer) as total,
                            count(customer) - sum(business_customer) as residential
                            from subscribers.subs_""" + isp + """ where technology > 1 and type = 'Active'
                            group by tract,technology,download,upload
                            order by tract, download, upload) to '""" + tmpout + """' with CSV DELIMITER ','  """
            cursor.execute(sql)
            fcnt = 1
            with open(tmpout, 'r') as f:
                lines = f.readlines()
                lenl = len(lines)
                with open(outfil, 'w') as fo:
                    for l in lines:
                        if "\n" in l:
                            print("found new line")
                            nlpos = l.find("\n")
                            nl = l[:nlpos]
                            print("nl", nl)
                            if fcnt < lenl:
                                nl = nl + "\n"
                            fo.write(nl)
                            fcnt += 1

            # Create 477 version (change 71 to 70)
            tmpout = "/tmp/477_" + isp + "_subscription_processed.csv"
            outfil = periodpath + "/subscription_processed/477_" + \
                isp + "_subscription_processed.csv"
            sql = """COPY (Select tract,
                            case when technology = 71 then 70
                            else technology
                            end as techcode,
                            download,
                            upload,
                            count(customer) as total,
                            count(customer) - sum(business_customer) as residential
                            from subscribers.subs_""" + isp + """ where technology > 1
                             group by tract,techcode,download,upload) to '""" + tmpout + """' with CSV DELIMITER ','  """
            cursor.execute(sql)
            with open(tmpout) as f:
                contents = f.read()
            with open(outfil, "w") as fo:
                print(contents, file=fo)

            # Handle VoIP processing if needed
            if voipneeded == True:
                tmpout = "/tmp/" + isp + "voice_subscription_processed.csv"
                outfil = periodpath + "/subscription_processed/" + \
                    isp + "_voice_subscription_processed.csv"
                isExist = os.path.exists(outfil)
                if (isExist):
                    os.remove(outfil)

                sql = """COPY (Select tract,
                        '1' as service_type,
                        sum(voip_lines_quantity) as total,
                        sum(voip_lines_quantity) - (sum(business_customer * voip_lines_quantity)) as residential
                        from subscribers.subs_""" + isp + """ where voip_lines_quantity > 0 group by tract order by tract) to '""" + tmpout + """' with CSV DELIMITER ','  """
                cursor.execute(sql)
                fcnt = 1
                with open(tmpout, 'r') as f:
                    lines = f.readlines()
                    lenl = len(lines)
                    with open(outfil, 'w') as fo:
                        for l in lines:
                            if "\n" in l:
                                print("found new line")
                                nlpos = l.find("\n")
                                nl = l[:nlpos]
                                print("nl", nl)
                                if fcnt < lenl:
                                    nl = nl + "\n"
                                fo.write(nl)
                                fcnt += 1

                # Create voice state data
                outfil = periodpath + "/subscription_processed/" + isp + "_voice_state_data.txt"
                sleep(5)
                sql = 'select distinct substring(tract,1,2) as statefips from subscribers.subs_' + str(
                    isp)
                print(sql)
                ps_cursor.execute(sql)
                states = ps_cursor.fetchall()
                for state in states:
                    contents = ''
                    contents = "state " + str(state["statefips"]) + "\n"
                    print("adding voip for state " + str(state["statefips"]))
                    sql = """Select
                            case when technology >= 71 then 70
                            else technology
                            end as techcode,
                            sum(voip_lines_quantity) as total
                            from subscribers.subs_""" + isp + """ where voip_lines_quantity > 0 and substring(tract,1,2) = '""" + state["statefips"] + """' group by techcode  """
                    cursor.execute(sql)
                    techsums = cursor.fetchall()
                    if techsums is not None:
                        for t in techsums:
                            contents += "tech code " + \
                                str(t[0]) + ": " + str(t[1]) + "\n"
                        with open(outfil, "a") as ts:
                            print(contents, file=ts)

            # Update final status to complete
            sql = """Update filer_processing_status set subscription_processed = true, subscription_status = 'complete' where org_id = """ + \
                isp + """ and filing_period = '""" + period + """' """
            cursor.execute(sql)
            conn.commit()

    return


ispid = sys.argv[1]
per = sys.argv[2]


now = datetime.now()
x = now.strftime("%m/%d/%Y, %H:%M:%S")

with open('validate_subs.log', 'a') as f:
    print(x, file=f)
    print('validate_subscription_isp run for ' + ispid + '\n', file=f)


db_host = os.getenv('DB_HOST', 'localhost')
db_port = os.getenv('DB_PORT', '5432')
db_name = os.getenv('DB_NAME', 'broadband')
db_user = os.getenv('DB_USER', 'broadband')
db_password = os.getenv('DB_PASSWORD')
if not db_password:
    raise ValueError("DB_PASSWORD environment variable not set")

conn = psycopg2.connect(
    database=db_name,
    user=db_user,
    password=db_password,
    host=db_host,
    port=db_port
)
ps_cursor = conn.cursor(cursor_factory=RealDictCursor)
cursor = conn.cursor()

# get all the wisps so we can check for aps done later
# sql = """Select org_id from broadband.fixed_wireless_data where ap_data = true""";
# ps_cursor.execute(sql);
# completeisps = ps_cursor.fetchall()
# ps_cursor.close()


dir_path = r'/var/www/broadband/uploads'
procisp = 0
endperiod = ''
for path in os.listdir(dir_path):
    if os.path.isdir(os.path.join(dir_path, path)):
        # at isp directory
        print("isp ", os.path.basename(path))
        procisp = os.path.basename(path)

        if procisp == ispid:
            isppth = dir_path + '/' + os.path.basename(path)
            for isp in os.listdir(isppth):
                if os.path.isdir(os.path.join(isppth, isp)):
                    # at period directory
                    endperiod = os.path.basename(isp)
                    print("    period ", endperiod)
                    print("    ", os.path.basename(isp))
                    periodpath = isppth + '/' + os.path.basename(isp)
                    for period in os.listdir(periodpath):
                        if os.path.isdir(os.path.join(periodpath, period)):
                            print("       ", os.path.basename(period))
                            # sleep(3)
                            dirname = os.path.basename(period)

                            if dirname == 'subscribers' and endperiod == per:
                                print(
                                    "          building subscription file from subscribers for isp ", procisp)
                                # go build subscription file
                                subpath = periodpath + '/' + \
                                    os.path.basename(period)
                                print("subpath", subpath)
                                for subfile in os.listdir(subpath):
                                    print("subfile", subfile)
                                    if os.path.isfile(
                                            os.path.join(subpath, subfile)):
                                        sfile = os.path.basename(subfile)
                                        print("sfile", sfile)
                                        print(
                                            "          processing subscribers file ", subfile)
                                        create_subscription(
                                            subfile, sfile, procisp, periodpath, endperiod)

conn.close()
with open('validate_subs.log', 'a') as f:
    print('validate_subscription_isp run done for ' + ispid + '\n', file=f)
