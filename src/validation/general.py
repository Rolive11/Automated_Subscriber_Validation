"""General column validation functions."""

import re
import pandas as pd
# Removed uszipcode import due to SQLAlchemy compatibility issues
from src.config.settings import VALID_STATES, VALID_TECHNOLOGIES, FORBIDDEN_CHARS
from src.utils.logging import debug_print

def append_general_error_with_tracking(error_msg, orig_row, col_name, value, idx, errors, flagged_cells):
    """Append error and flag cell with OrigRowNum tracking for general validation."""
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
        debug_print(f"General validation error for OrigRowNum={orig_row}, col={col_name}: {error_msg}")


def get_state_from_zip(zip_code):
    """Get state abbreviation from ZIP code using a lookup dictionary."""
    if not zip_code or not re.match(r"^\d{5}(-\d{4})?$", str(zip_code)):
        return None
    
    # Extract 5-digit ZIP code
    zip_5 = str(zip_code).split("-")[0]
    
    # ZIP code to state mapping (3-digit prefixes)
    ZIP_TO_STATE = {
        # Alabama
        "350": "AL", "351": "AL", "352": "AL", "353": "AL", "354": "AL", "355": "AL", "356": "AL", "357": "AL", "358": "AL", "359": "AL", "360": "AL", "361": "AL", "362": "AL", "363": "AL", "364": "AL", "365": "AL", "366": "AL", "367": "AL", "368": "AL", "369": "AL",
        # Alaska
        "995": "AK", "996": "AK", "997": "AK", "998": "AK", "999": "AK",
        # Arizona  
        "850": "AZ", "851": "AZ", "852": "AZ", "853": "AZ", "854": "AZ", "855": "AZ", "856": "AZ", "857": "AZ", "859": "AZ", "860": "AZ", "863": "AZ", "864": "AZ", "865": "AZ",
        # Arkansas
        "716": "AR", "717": "AR", "718": "AR", "719": "AR", "720": "AR", "721": "AR", "722": "AR", "723": "AR", "724": "AR", "725": "AR", "726": "AR", "727": "AR", "728": "AR", "729": "AR",
        # California
        "900": "CA", "901": "CA", "902": "CA", "903": "CA", "904": "CA", "905": "CA", "906": "CA", "907": "CA", "908": "CA", "910": "CA", "911": "CA", "912": "CA", "913": "CA", "914": "CA", "915": "CA", "916": "CA", "917": "CA", "918": "CA", "919": "CA", "920": "CA", "921": "CA", "922": "CA", "923": "CA", "924": "CA", "925": "CA", "926": "CA", "927": "CA", "928": "CA", "930": "CA", "931": "CA", "932": "CA", "933": "CA", "934": "CA", "935": "CA", "936": "CA", "937": "CA", "938": "CA", "939": "CA", "940": "CA", "941": "CA", "942": "CA", "943": "CA", "944": "CA", "945": "CA", "946": "CA", "947": "CA", "948": "CA", "949": "CA", "950": "CA", "951": "CA", "952": "CA", "953": "CA", "954": "CA", "955": "CA", "956": "CA", "957": "CA", "958": "CA", "959": "CA", "960": "CA", "961": "CA",
        # Colorado
        "800": "CO", "801": "CO", "802": "CO", "803": "CO", "804": "CO", "805": "CO", "806": "CO", "807": "CO", "808": "CO", "809": "CO", "810": "CO", "811": "CO", "812": "CO", "813": "CO", "814": "CO", "815": "CO", "816": "CO",
        # Connecticut
        "060": "CT", "061": "CT", "062": "CT", "063": "CT", "064": "CT", "065": "CT", "066": "CT", "067": "CT", "068": "CT", "069": "CT",
        # Delaware
        "197": "DE", "198": "DE", "199": "DE",
        # Florida
        "320": "FL", "321": "FL", "322": "FL", "323": "FL", "324": "FL", "325": "FL", "326": "FL", "327": "FL", "328": "FL", "329": "FL", "330": "FL", "331": "FL", "332": "FL", "333": "FL", "334": "FL", "335": "FL", "336": "FL", "337": "FL", "338": "FL", "339": "FL", "340": "FL", "341": "FL", "342": "FL", "344": "FL", "346": "FL", "347": "FL", "349": "FL",
        # Georgia
        "300": "GA", "301": "GA", "302": "GA", "303": "GA", "304": "GA", "305": "GA", "306": "GA", "307": "GA", "308": "GA", "309": "GA", "310": "GA", "311": "GA", "312": "GA", "313": "GA", "314": "GA", "315": "GA", "316": "GA", "317": "GA", "318": "GA", "319": "GA",
        # Hawaii
        "967": "HI", "968": "HI",
        # Idaho
        "832": "ID", "833": "ID", "834": "ID", "835": "ID", "836": "ID", "837": "ID", "838": "ID",
        # Illinois
        "600": "IL", "601": "IL", "602": "IL", "603": "IL", "604": "IL", "605": "IL", "606": "IL", "607": "IL", "608": "IL", "609": "IL", "610": "IL", "611": "IL", "612": "IL", "613": "IL", "614": "IL", "615": "IL", "616": "IL", "617": "IL", "618": "IL", "619": "IL", "620": "IL", "621": "IL", "622": "IL", "623": "IL", "624": "IL", "625": "IL", "626": "IL", "627": "IL", "628": "IL", "629": "IL",
        # Indiana
        "460": "IN", "461": "IN", "462": "IN", "463": "IN", "464": "IN", "465": "IN", "466": "IN", "467": "IN", "468": "IN", "469": "IN", "470": "IN", "471": "IN", "472": "IN", "473": "IN", "474": "IN", "475": "IN", "476": "IN", "477": "IN", "478": "IN", "479": "IN",
        # Iowa
        "500": "IA", "501": "IA", "502": "IA", "503": "IA", "504": "IA", "505": "IA", "506": "IA", "507": "IA", "508": "IA", "510": "IA", "511": "IA", "512": "IA", "513": "IA", "514": "IA", "515": "IA", "516": "IA", "520": "IA", "521": "IA", "522": "IA", "523": "IA", "524": "IA", "525": "IA", "526": "IA", "527": "IA", "528": "IA",
        # Kansas
        "660": "KS", "661": "KS", "662": "KS", "664": "KS", "665": "KS", "666": "KS", "667": "KS", "668": "KS", "669": "KS", "670": "KS", "671": "KS", "672": "KS", "673": "KS", "674": "KS", "675": "KS", "676": "KS", "677": "KS", "678": "KS", "679": "KS",
        # Kentucky
        "400": "KY", "401": "KY", "402": "KY", "403": "KY", "404": "KY", "405": "KY", "406": "KY", "407": "KY", "408": "KY", "409": "KY", "410": "KY", "411": "KY", "412": "KY", "413": "KY", "414": "KY", "415": "KY", "416": "KY", "417": "KY", "418": "KY", "420": "KY", "421": "KY", "422": "KY", "423": "KY", "424": "KY", "425": "KY", "426": "KY", "427": "KY",
        # Louisiana
        "700": "LA", "701": "LA", "703": "LA", "704": "LA", "705": "LA", "706": "LA", "707": "LA", "708": "LA", "710": "LA", "711": "LA", "712": "LA", "713": "LA", "714": "LA",
        # Maine
        "039": "ME", "040": "ME", "041": "ME", "042": "ME", "043": "ME", "044": "ME", "045": "ME", "046": "ME", "047": "ME", "048": "ME", "049": "ME",
        # Maryland
        "206": "MD", "207": "MD", "208": "MD", "209": "MD", "210": "MD", "211": "MD", "212": "MD", "214": "MD", "215": "MD", "216": "MD", "217": "MD", "218": "MD", "219": "MD", "220": "MD", "221": "MD",
        # Massachusetts
        "010": "MA", "011": "MA", "012": "MA", "013": "MA", "014": "MA", "015": "MA", "016": "MA", "017": "MA", "018": "MA", "019": "MA", "020": "MA", "021": "MA", "022": "MA", "023": "MA", "024": "MA", "025": "MA", "026": "MA", "027": "MA",
        # Michigan
        "480": "MI", "481": "MI", "482": "MI", "483": "MI", "484": "MI", "485": "MI", "486": "MI", "487": "MI", "488": "MI", "489": "MI", "490": "MI", "491": "MI", "492": "MI", "493": "MI", "494": "MI", "495": "MI", "496": "MI", "497": "MI", "498": "MI", "499": "MI",
        # Minnesota
        "550": "MN", "551": "MN", "553": "MN", "554": "MN", "555": "MN", "556": "MN", "557": "MN", "558": "MN", "559": "MN", "560": "MN", "561": "MN", "562": "MN", "563": "MN", "564": "MN", "565": "MN", "566": "MN", "567": "MN",
        # Mississippi
        "386": "MS", "387": "MS", "388": "MS", "389": "MS", "390": "MS", "391": "MS", "392": "MS", "393": "MS", "394": "MS", "395": "MS", "396": "MS", "397": "MS",
        # Missouri
        "630": "MO", "631": "MO", "633": "MO", "634": "MO", "635": "MO", "636": "MO", "637": "MO", "638": "MO", "639": "MO", "640": "MO", "641": "MO", "644": "MO", "645": "MO", "646": "MO", "647": "MO", "648": "MO", "649": "MO", "650": "MO", "651": "MO", "652": "MO", "653": "MO", "654": "MO", "655": "MO", "656": "MO", "657": "MO", "658": "MO",
        # Montana
        "590": "MT", "591": "MT", "592": "MT", "593": "MT", "594": "MT", "595": "MT", "596": "MT", "597": "MT", "598": "MT", "599": "MT",
        # Nebraska
        "680": "NE", "681": "NE", "683": "NE", "684": "NE", "685": "NE", "686": "NE", "687": "NE", "688": "NE", "689": "NE", "690": "NE", "691": "NE", "692": "NE", "693": "NE",
        # Nevada
        "889": "NV", "890": "NV", "891": "NV", "893": "NV", "894": "NV", "895": "NV", "897": "NV", "898": "NV",
        # New Hampshire
        "030": "NH", "031": "NH", "032": "NH", "033": "NH", "034": "NH", "035": "NH", "036": "NH", "037": "NH", "038": "NH",
        # New Jersey
        "070": "NJ", "071": "NJ", "072": "NJ", "073": "NJ", "074": "NJ", "075": "NJ", "076": "NJ", "077": "NJ", "078": "NJ", "079": "NJ", "080": "NJ", "081": "NJ", "082": "NJ", "083": "NJ", "084": "NJ", "085": "NJ", "086": "NJ", "087": "NJ", "088": "NJ", "089": "NJ",
        # New Mexico
        "870": "NM", "871": "NM", "872": "NM", "873": "NM", "874": "NM", "875": "NM", "877": "NM", "878": "NM", "879": "NM", "880": "NM", "881": "NM", "882": "NM", "883": "NM", "884": "NM",
        # New York
        "100": "NY", "101": "NY", "102": "NY", "103": "NY", "104": "NY", "105": "NY", "106": "NY", "107": "NY", "108": "NY", "109": "NY", "110": "NY", "111": "NY", "112": "NY", "113": "NY", "114": "NY", "115": "NY", "116": "NY", "117": "NY", "118": "NY", "119": "NY", "120": "NY", "121": "NY", "122": "NY", "123": "NY", "124": "NY", "125": "NY", "126": "NY", "127": "NY", "128": "NY", "129": "NY", "130": "NY", "131": "NY", "132": "NY", "133": "NY", "134": "NY", "135": "NY", "136": "NY", "137": "NY", "138": "NY", "139": "NY", "140": "NY", "141": "NY", "142": "NY", "143": "NY", "144": "NY", "145": "NY", "146": "NY", "147": "NY", "148": "NY", "149": "NY",
        # North Carolina
        "270": "NC", "271": "NC", "272": "NC", "273": "NC", "274": "NC", "275": "NC", "276": "NC", "277": "NC", "278": "NC", "279": "NC", "280": "NC", "281": "NC", "282": "NC", "283": "NC", "284": "NC", "285": "NC", "286": "NC", "287": "NC", "288": "NC", "289": "NC",
        # North Dakota
        "580": "ND", "581": "ND", "582": "ND", "583": "ND", "584": "ND", "585": "ND", "586": "ND", "587": "ND", "588": "ND",
        # Ohio
        "430": "OH", "431": "OH", "432": "OH", "433": "OH", "434": "OH", "435": "OH", "436": "OH", "437": "OH", "438": "OH", "439": "OH", "440": "OH", "441": "OH", "442": "OH", "443": "OH", "444": "OH", "445": "OH", "446": "OH", "447": "OH", "448": "OH", "449": "OH", "450": "OH", "451": "OH", "452": "OH", "453": "OH", "454": "OH", "455": "OH", "456": "OH", "457": "OH", "458": "OH",
        # Oklahoma
        "730": "OK", "731": "OK", "734": "OK", "735": "OK", "736": "OK", "737": "OK", "738": "OK", "739": "OK", "740": "OK", "741": "OK", "743": "OK", "744": "OK", "745": "OK", "746": "OK", "747": "OK", "748": "OK", "749": "OK",
        # Oregon
        "970": "OR", "971": "OR", "972": "OR", "973": "OR", "974": "OR", "975": "OR", "977": "OR", "978": "OR", "979": "OR",
        # Pennsylvania
        "150": "PA", "151": "PA", "152": "PA", "153": "PA", "154": "PA", "155": "PA", "156": "PA", "157": "PA", "158": "PA", "159": "PA", "160": "PA", "161": "PA", "162": "PA", "163": "PA", "164": "PA", "165": "PA", "166": "PA", "167": "PA", "168": "PA", "169": "PA", "170": "PA", "171": "PA", "172": "PA", "173": "PA", "174": "PA", "175": "PA", "176": "PA", "177": "PA", "178": "PA", "179": "PA", "180": "PA", "181": "PA", "182": "PA", "183": "PA", "184": "PA", "185": "PA", "186": "PA", "187": "PA", "188": "PA", "189": "PA", "190": "PA", "191": "PA", "193": "PA", "194": "PA", "195": "PA", "196": "PA",
        # Rhode Island
        "028": "RI", "029": "RI",
        # South Carolina
        "290": "SC", "291": "SC", "292": "SC", "293": "SC", "294": "SC", "295": "SC", "296": "SC", "297": "SC", "298": "SC", "299": "SC",
        # South Dakota
        "570": "SD", "571": "SD", "572": "SD", "573": "SD", "574": "SD", "575": "SD", "576": "SD", "577": "SD",
        # Tennessee
        "370": "TN", "371": "TN", "372": "TN", "373": "TN", "374": "TN", "375": "TN", "376": "TN", "377": "TN", "378": "TN", "379": "TN", "380": "TN", "381": "TN", "382": "TN", "383": "TN", "384": "TN", "385": "TN",
        # Texas
        "750": "TX", "751": "TX", "752": "TX", "753": "TX", "754": "TX", "755": "TX", "756": "TX", "757": "TX", "758": "TX", "759": "TX", "760": "TX", "761": "TX", "762": "TX", "763": "TX", "764": "TX", "765": "TX", "766": "TX", "767": "TX", "768": "TX", "769": "TX", "770": "TX", "771": "TX", "772": "TX", "773": "TX", "774": "TX", "775": "TX", "776": "TX", "777": "TX", "778": "TX", "779": "TX", "780": "TX", "781": "TX", "782": "TX", "783": "TX", "784": "TX", "785": "TX", "786": "TX", "787": "TX", "788": "TX", "789": "TX", "790": "TX", "791": "TX", "792": "TX", "793": "TX", "794": "TX", "795": "TX", "796": "TX", "797": "TX", "798": "TX", "799": "TX",
        # Utah
        "840": "UT", "841": "UT", "842": "UT", "843": "UT", "844": "UT", "845": "UT", "846": "UT", "847": "UT",
        # Vermont
        "050": "VT", "051": "VT", "052": "VT", "053": "VT", "054": "VT", "056": "VT", "057": "VT", "058": "VT", "059": "VT",
        # Virginia
        "220": "VA", "221": "VA", "222": "VA", "223": "VA", "224": "VA", "225": "VA", "226": "VA", "227": "VA", "228": "VA", "229": "VA", "230": "VA", "231": "VA", "232": "VA", "233": "VA", "234": "VA", "235": "VA", "236": "VA", "237": "VA", "238": "VA", "239": "VA", "240": "VA", "241": "VA", "242": "VA", "243": "VA", "244": "VA", "245": "VA", "246": "VA",
        # Washington
        "980": "WA", "981": "WA", "982": "WA", "983": "WA", "984": "WA", "985": "WA", "986": "WA", "988": "WA", "989": "WA", "990": "WA", "991": "WA", "992": "WA", "993": "WA", "994": "WA",
        # West Virginia
        "247": "WV", "248": "WV", "249": "WV", "250": "WV", "251": "WV", "252": "WV", "253": "WV", "254": "WV", "255": "WV", "256": "WV", "257": "WV", "258": "WV", "259": "WV", "260": "WV", "261": "WV", "262": "WV", "263": "WV", "264": "WV", "265": "WV", "266": "WV", "267": "WV", "268": "WV",
        # Wisconsin
        "530": "WI", "531": "WI", "532": "WI", "533": "WI", "534": "WI", "535": "WI", "537": "WI", "538": "WI", "539": "WI", "540": "WI", "541": "WI", "542": "WI", "543": "WI", "544": "WI", "545": "WI", "546": "WI", "547": "WI", "548": "WI", "549": "WI",
        # Wyoming
        "820": "WY", "821": "WY", "822": "WY", "823": "WY", "824": "WY", "825": "WY", "826": "WY", "827": "WY", "828": "WY", "829": "WY", "830": "WY", "831": "WY",
        # Washington DC
        "200": "DC", "201": "DC", "202": "DC", "203": "DC", "204": "DC", "205": "DC",
        # Puerto Rico
        "006": "PR", "007": "PR", "009": "PR",
        # US Virgin Islands
        "008": "VI",
        # Guam
        "969": "GU",
        # American Samoa
        "967": "AS",
        # Northern Mariana Islands
        "969": "MP"
    }
    
    try:
        # Check 3-digit prefix first
        prefix_3 = zip_5[:3]
        if prefix_3 in ZIP_TO_STATE:
            return ZIP_TO_STATE[prefix_3]
        
        # Check 5-digit exact match for special cases
        if zip_5 in ZIP_TO_STATE:
            return ZIP_TO_STATE[zip_5]
            
        return None
    except Exception as e:
        debug_print(f"Error getting state from ZIP {zip_code}: {str(e)}")
        return None

def validate_and_correct_state(state_val, zip_val, idx, orig_row, errors, corrected_cells, flagged_cells):
    """Validate and correct state using ZIP code."""
    state_val = state_val.strip() if pd.notna(state_val) else ""
    if not state_val:
        # Try to get state from ZIP code before flagging as error
        corrected_state = get_state_from_zip(zip_val)
        if corrected_state:
            corrected_cells[(idx, "state")] = {
                "row": int(orig_row),
                "original": state_val,
                "corrected": corrected_state,
                "type": "State from ZIP Code",
                "status": "Valid"
            }
            debug_print(f"Filled missing state from ZIP for OrigRowNum={orig_row}: ZIP {zip_val} → {corrected_state}")
            return corrected_state
        else:
            append_general_error_with_tracking("Required field: State cannot be empty", orig_row, "state", state_val, idx, errors, flagged_cells)
            return state_val

    if state_val.upper() not in VALID_STATES:
        append_general_error_with_tracking("Invalid State Abbreviation", orig_row, "state", state_val, idx, errors, flagged_cells)
        corrected_state = get_state_from_zip(zip_val)
        if corrected_state:
            corrected_cells[(idx, "state")] = {
                "row": int(orig_row),
                "original": state_val,
                "corrected": corrected_state,
                "type": "State Name to Abbreviation",
                "status": "Valid"
            }
            return corrected_state
        return state_val
    elif state_val != state_val.upper():
        corrected_cells[(idx, "state")] = {
            "row": int(orig_row),
            "original": state_val,
            "corrected": state_val.upper(),
            "type": "State Abbreviation Case Correction",
            "status": "Valid"
        }
        append_general_error_with_tracking("Invalid State Abbreviation", orig_row, "state", state_val, idx, errors, flagged_cells)
        return state_val.upper()
    return state_val

def is_integer(value):
    """Check if a value is an integer."""
    try:
        float_val = float(value)
        return float_val.is_integer()
    except (ValueError, TypeError):
        return False


# Replace the validate_general_columns function in general.py with this corrected version:

def validate_general_columns(cleaned_df, errors, corrected_cells, flagged_cells):
    """Validate non-coordinate columns."""

    # Define required columns (all except lat/lon which can be empty)
    REQUIRED_COLUMNS = ["customer", "address", "city", "state", "zip", "download", "upload", "voip_lines_quantity", "business_customer", "technology"]

    for col in cleaned_df.columns:
        if col in ["OrigRowNum", "lat", "lon"]:
            continue
        values = cleaned_df[col].fillna("").astype(str).str.strip()

        # Check for required field violations first
        if col in REQUIRED_COLUMNS:
            is_blank = values == ""
            for idx, (val, blank) in enumerate(zip(values, is_blank)):
                if blank:
                    orig_row = cleaned_df["OrigRowNum"][idx]

                    # Skip required field errors for address fields if ALL address fields are empty (GPS-only row)
                    if col in ["address", "city", "state", "zip"]:
                        row_data = cleaned_df.iloc[idx]
                        address_empty = pd.isna(row_data.get('address', '')) or str(row_data.get('address', '')).strip() == ""
                        city_empty = pd.isna(row_data.get('city', '')) or str(row_data.get('city', '')).strip() == ""
                        state_empty = pd.isna(row_data.get('state', '')) or str(row_data.get('state', '')).strip() == ""
                        zip_empty = pd.isna(row_data.get('zip', '')) or str(row_data.get('zip', '')).strip() == ""

                        if address_empty and city_empty and state_empty and zip_empty:
                            debug_print(f"Skipping required field error for {col} at OrigRowNum={orig_row}: All address fields empty (GPS-only row)")
                            continue

                    error_msg = f"Required field: {col.capitalize()} cannot be empty"

                    # NEW: For ZIP codes, flag for Smarty processing instead of just erroring
                    if col == "zip":
                        # Check if we have enough address info for Smarty to work with
                        row_data = cleaned_df.iloc[idx]
                        has_address = pd.notna(row_data.get('address', '')) and str(row_data.get('address', '')).strip()
                        has_city = pd.notna(row_data.get('city', '')) and str(row_data.get('city', '')).strip()
                        has_state = pd.notna(row_data.get('state', '')) and str(row_data.get('state', '')).strip()
                        
                        if has_address and has_city and has_state:
                            # Flag for Smarty processing (it can potentially fill in the ZIP)
                            from src.validation.address import append_error_with_tracking
                            append_error_with_tracking(error_msg, orig_row, col, val, idx, errors, flagged_cells)
                            debug_print(f"Flagged missing ZIP for Smarty processing: OrigRowNum={orig_row}")
                        else:
                            # Not enough data for Smarty - just error normally
                            append_general_error_with_tracking(error_msg, orig_row, col, val, idx, errors, flagged_cells)
                    else:
                        # For non-ZIP required fields, error normally
                        append_general_error_with_tracking(error_msg, orig_row, col, val, idx, errors, flagged_cells)
                    
                    # Set to NA but don't record as a correction since this is an error
                    cleaned_df.loc[idx, col] = pd.NA
                    continue  # Skip further validation for empty required fields


        # Column-specific validation for non-empty values
        for idx, val in enumerate(values):
            orig_row = cleaned_df["OrigRowNum"][idx]

            # Skip if we already flagged this as a required field error
            if (idx, col) in flagged_cells and isinstance(flagged_cells[(idx, col)], tuple) and flagged_cells[(idx, col)][0].startswith("Required field:"):
                continue

            # Skip address field validation for GPS-only rows
            if col in ["address", "city", "state", "zip"]:
                row_data = cleaned_df.iloc[idx]
                address_empty = pd.isna(row_data.get('address', '')) or str(row_data.get('address', '')).strip() == ""
                city_empty = pd.isna(row_data.get('city', '')) or str(row_data.get('city', '')).strip() == ""
                state_empty = pd.isna(row_data.get('state', '')) or str(row_data.get('state', '')).strip() == ""
                zip_empty = pd.isna(row_data.get('zip', '')) or str(row_data.get('zip', '')).strip() == ""

                if address_empty and city_empty and state_empty and zip_empty:
                    debug_print(f"Skipping {col} format validation for OrigRowNum={orig_row}: All address fields empty (GPS-only row)")
                    continue

            if col == "customer":
                if val and "," in val:
                    append_general_error_with_tracking("Customer ID contains a comma", orig_row, col, val, idx, errors, flagged_cells)

            elif col == "city" and val:
                if re.search(FORBIDDEN_CHARS, val):
                    append_general_error_with_tracking("City contains forbidden character", orig_row, col, val, idx, errors, flagged_cells)

            elif col == "zip" and val:
                # Auto-correct 9-digit zip codes without hyphen (12345678 -> 12345-6789)
                if re.match(r"^\d{9}$", val):
                    corrected_zip = f"{val[:5]}-{val[5:]}"
                    cleaned_df.loc[idx, col] = corrected_zip
                    corrected_cells[(idx, col)] = {
                        "row": int(cleaned_df["OrigRowNum"].iloc[idx]),
                        "original": val,
                        "corrected": corrected_zip,
                        "type": "ZIP+4 Hyphen Addition",
                        "status": "Valid"
                    }
                elif not re.match(r"^\d{5}(-\d{4})?$", val):
                    append_general_error_with_tracking("Invalid ZIP code format", orig_row, col, val, idx, errors, flagged_cells)
                if re.search(FORBIDDEN_CHARS, val):
                    append_general_error_with_tracking("ZIP code contains forbidden character", orig_row, col, val, idx, errors, flagged_cells)

            elif col in ["download", "upload"] and val:
                try:
                    float_val = float(val)
                    if float_val < 0:
                        cleaned_df.loc[idx, col] = pd.NA
                        corrected_cells[(idx, col)] = {
                            "row": int(cleaned_df["OrigRowNum"].iloc[idx]),
                            "original": val,
                            "corrected": None,
                            "type": "Invalid Speed Replacement",
                            "status": "Valid"
                        }
                        append_general_error_with_tracking(f"{col.capitalize()} speed must be positive", orig_row, col, val, idx, errors, flagged_cells)
                    else:
                        cleaned_df.loc[idx, col] = float_val
                except ValueError:
                    cleaned_df.loc[idx, col] = pd.NA
                    corrected_cells[(idx, col)] = {
                        "row": int(cleaned_df["OrigRowNum"].iloc[idx]),
                        "original": val,
                        "corrected": None,
                        "type": "Invalid Speed Replacement",
                        "status": "Valid"
                    }
                    append_general_error_with_tracking(f"{col.capitalize()} speed must be a number", orig_row, col, val, idx, errors, flagged_cells)

            elif col == "voip_lines_quantity" and val:
                try:
                    float_val = float(val)
                    if float_val >= 0 and is_integer(float_val):
                        int_val = int(float_val)
                        cleaned_df.loc[idx, col] = int_val
                        if val != str(int_val):
                            corrected_cells[(idx, col)] = {
                                "row": int(cleaned_df["OrigRowNum"].iloc[idx]),
                                "original": val,
                                "corrected": int_val,
                                "type": "VoIP Lines Format Correction",
                                "status": "Valid"
                            }
                    else:
                        cleaned_df.loc[idx, col] = pd.NA
                        corrected_cells[(idx, col)] = {
                            "row": int(cleaned_df["OrigRowNum"].iloc[idx]),
                            "original": val,
                            "corrected": None,
                            "type": "Invalid VoIP Lines Replacement",
                            "status": "Valid"
                        }
                        append_general_error_with_tracking("VoIP lines must be a non-negative integer", orig_row, col, val, idx, errors, flagged_cells)
                except ValueError:
                    cleaned_df.loc[idx, col] = pd.NA
                    corrected_cells[(idx, col)] = {
                        "row": int(cleaned_df["OrigRowNum"].iloc[idx]),
                        "original": val,
                        "corrected": None,
                        "type": "Invalid VoIP Lines Replacement",
                        "status": "Valid"
                    }
                    append_general_error_with_tracking("VoIP lines must be a number", orig_row, col, val, idx, errors, flagged_cells)

            elif col == "business_customer" and val:
                normalized_val = val.lower().strip()
                if normalized_val in ["true", "t", "1", "yes", "y"]:
                    cleaned_df.loc[idx, col] = 1
                    if normalized_val != "1":
                        corrected_cells[(idx, col)] = {
                            "row": int(cleaned_df["OrigRowNum"].iloc[idx]),
                            "original": val,
                            "corrected": 1,
                            "type": "Business Customer Normalization",
                            "status": "Valid"
                        }
                elif normalized_val in ["false", "f", "0", "no", "n"]:
                    cleaned_df.loc[idx, col] = 0
                    if normalized_val != "0":
                        corrected_cells[(idx, col)] = {
                            "row": int(cleaned_df["OrigRowNum"].iloc[idx]),
                            "original": val,
                            "corrected": 0,
                            "type": "Business Customer Normalization",
                            "status": "Valid"
                        }
                elif normalized_val:
                    cleaned_df.loc[idx, col] = 0
                    corrected_cells[(idx, col)] = {
                        "row": int(cleaned_df["OrigRowNum"].iloc[idx]),
                        "original": val,
                        "corrected": 0,
                        "type": "Invalid Business Customer Replacement",
                        "status": "Valid"
                    }
                    append_general_error_with_tracking("Business customer must be 0 or 1", orig_row, col, val, idx, errors, flagged_cells)

            elif col == "technology" and val:
                normalized_val = val.lower().strip()

                # Auto-correct common technology entry errors
                technology_corrections = {
                    "licensedbyruleterrestrialfixedwireless": "wireless_gaa",
                    "unlicensedterrestrialfixedwireless": "wireless_unlicensed",
                    "licensedterrestrialfixedwireless": "wireless_pal"
                }

                if normalized_val in technology_corrections:
                    corrected_val = technology_corrections[normalized_val]
                    cleaned_df.loc[idx, col] = corrected_val
                    corrected_cells[(idx, col)] = {
                        "row": int(cleaned_df["OrigRowNum"].iloc[idx]),
                        "original": val,
                        "corrected": corrected_val,
                        "type": "Technology Auto-Correction",
                        "status": "Valid"
                    }
                elif normalized_val not in VALID_TECHNOLOGIES:
                    append_general_error_with_tracking(f"Invalid technology: {', '.join(VALID_TECHNOLOGIES)}", orig_row, col, val, idx, errors, flagged_cells)
                elif normalized_val != val:
                    cleaned_df.loc[idx, col] = normalized_val
                    corrected_cells[(idx, col)] = {
                        "row": int(cleaned_df["OrigRowNum"].iloc[idx]),
                        "original": val,
                        "corrected": normalized_val,
                        "type": "Technology Case Normalization",
                        "status": "Valid"
                    }