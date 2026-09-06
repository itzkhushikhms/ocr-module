import re
from datetime import datetime


# --------------------------------------------------
# Helper: clean OCR text
# --------------------------------------------------

def clean_text(text):
    if not text:
        return ""

    text = text.replace("\r", "\n")

    lines = []

    for line in text.split("\n"):
        line = line.strip()

        if line:
            lines.append(line)

    return "\n".join(lines)


# --------------------------------------------------
# Helper: normalize date
# --------------------------------------------------

def normalize_date(value):
    if not value:
        return None

    value = value.strip()

    formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d.%m.%Y"
    ]

    for fmt in formats:
        try:
            date_obj = datetime.strptime(
                value,
                fmt
            )

            return date_obj.strftime(
                "%d/%m/%Y"
            )

        except ValueError:
            continue

    return value


# --------------------------------------------------
# Helper: parse MRZ YYMMDD date
# --------------------------------------------------

def parse_mrz_date(value, is_expiry=False):
    if not value:
        return None

    if not re.fullmatch(
        r"\d{6}",
        value
    ):
        return None

    try:
        yy = int(value[0:2])
        mm = int(value[2:4])
        dd = int(value[4:6])

        current_year = (
            datetime.now().year % 100
        )

        if is_expiry:
            if yy < 70:
                year = 2000 + yy
            else:
                year = 1900 + yy

        else:
            if yy <= current_year:
                year = 2000 + yy
            else:
                year = 1900 + yy

        date_obj = datetime(
            year,
            mm,
            dd
        )

        return date_obj.strftime(
            "%d/%m/%Y"
        )

    except ValueError:
        return None


# --------------------------------------------------
# Helper: find probable MRZ lines
# --------------------------------------------------

def find_mrz_lines(text):
    mrz_lines = []

    for line in text.split("\n"):

        cleaned = (
            line.upper()
            .replace(" ", "")
        )

        if len(cleaned) < 30:
            continue

        allowed_chars = re.sub(
            r"[A-Z0-9<]",
            "",
            cleaned
        )

        if len(allowed_chars) <= 3:
            mrz_lines.append(cleaned)

    return mrz_lines


# --------------------------------------------------
# Helper: clean MRZ field
# --------------------------------------------------

def clean_mrz_field(value):
    if not value:
        return None

    value = (
        value
        .replace("<", " ")
        .strip()
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value or None


# --------------------------------------------------
# Parse passport MRZ
# --------------------------------------------------

def parse_mrz(text):
    fields = {}

    mrz_lines = find_mrz_lines(
        text
    )

    if len(mrz_lines) < 2:
        return fields

    first_line = None
    second_line = None

    for i in range(
        len(mrz_lines) - 1
    ):
        line1 = mrz_lines[i]
        line2 = mrz_lines[i + 1]

        if (
            line1.startswith("P")
            and len(line1) >= 40
            and len(line2) >= 40
        ):
            first_line = line1
            second_line = line2
            break

    if not first_line or not second_line:
        return fields

    # ----------------------------------------------
    # First MRZ line
    # P<INDLASTNAME<<FIRSTNAME
    # ----------------------------------------------

    try:

        name_part = first_line[5:]

        if "<<" in name_part:

            surname, given_names = (
                name_part.split(
                    "<<",
                    1
                )
            )

            surname = clean_mrz_field(
                surname
            )

            given_names = clean_mrz_field(
                given_names
            )

            full_name_parts = []

            if given_names:
                full_name_parts.append(
                    given_names
                )

            if surname:
                full_name_parts.append(
                    surname
                )

            if full_name_parts:
                fields["name"] = (
                    " ".join(
                        full_name_parts
                    )
                )

    except Exception:
        pass

    # ----------------------------------------------
    # Second MRZ line
    # ----------------------------------------------

    try:

        passport_number = (
            second_line[0:9]
            .replace("<", "")
            .strip()
        )

        if passport_number:
            fields[
                "passport_number"
            ] = passport_number

        nationality = (
            second_line[10:13]
            .replace("<", "")
            .strip()
        )

        if nationality:
            fields[
                "nationality"
            ] = nationality

        dob_raw = (
            second_line[13:19]
        )

        dob = parse_mrz_date(
            dob_raw,
            is_expiry=False
        )

        if dob:
            fields[
                "date_of_birth"
            ] = dob

        gender_raw = (
            second_line[20:21]
        )

        if gender_raw == "M":
            fields[
                "gender"
            ] = "Male"

        elif gender_raw == "F":
            fields[
                "gender"
            ] = "Female"

        elif gender_raw in [
            "X",
            "<"
        ]:
            fields[
                "gender"
            ] = "Unspecified"

        expiry_raw = (
            second_line[21:27]
        )

        expiry_date = (
            parse_mrz_date(
                expiry_raw,
                is_expiry=True
            )
        )

        if expiry_date:
            fields[
                "expiry_date"
            ] = expiry_date

    except Exception:
        pass

    return fields


# --------------------------------------------------
# Visible label extraction
# --------------------------------------------------

def extract_visible_fields(text):
    fields = {}

    # ----------------------------------------------
    # Name
    # ----------------------------------------------

    name_patterns = [
        r"(?:Name|Given Names?)\s*[:\-]?\s*([A-Za-z][A-Za-z .'-]{2,60})",
        r"Surname\s*[:\-]?\s*([A-Za-z][A-Za-z .'-]{2,60})"
    ]

    for pattern in name_patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            value = match.group(1).strip()

            value = value.split("\n")[0]

            if len(value) >= 3:
                fields[
                    "name"
                ] = value
                break

    # ----------------------------------------------
    # Passport number
    # ----------------------------------------------

    passport_patterns = [
        r"(?:Passport\s*(?:No|Number|#)?)\s*[:\-]?\s*([A-Z0-9]{6,12})",
        r"\b([A-Z][0-9]{6,8})\b"
    ]

    for pattern in passport_patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            value = (
                match.group(1)
                .upper()
                .strip()
            )

            fields[
                "passport_number"
            ] = value

            break

    # ----------------------------------------------
    # Nationality
    # ----------------------------------------------

    nationality_match = re.search(
        r"Nationality\s*[:\-]?\s*([A-Za-z]{3,30})",
        text,
        re.IGNORECASE
    )

    if nationality_match:

        fields[
            "nationality"
        ] = (
            nationality_match
            .group(1)
            .strip()
            .upper()
        )

    # ----------------------------------------------
    # DOB
    # ----------------------------------------------

    dob_patterns = [
        r"(?:Date\s*of\s*Birth|DOB)\s*[:\-]?\s*(\d{2}[\/\-.]\d{2}[\/\-.]\d{4})",
        r"(?:Date\s*of\s*Birth|DOB)\s*[:\-]?\s*(\d{4}[\/\-.]\d{2}[\/\-.]\d{2})"
    ]

    for pattern in dob_patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            fields[
                "date_of_birth"
            ] = normalize_date(
                match.group(1)
            )

            break

    # ----------------------------------------------
    # Expiry date
    # ----------------------------------------------

    expiry_patterns = [
        r"(?:Date\s*of\s*Expiry|Expiry\s*Date|Expiry|Valid\s*Until)\s*[:\-]?\s*(\d{2}[\/\-.]\d{2}[\/\-.]\d{4})",
        r"(?:Date\s*of\s*Expiry|Expiry\s*Date|Expiry|Valid\s*Until)\s*[:\-]?\s*(\d{4}[\/\-.]\d{2}[\/\-.]\d{2})"
    ]

    for pattern in expiry_patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            fields[
                "expiry_date"
            ] = normalize_date(
                match.group(1)
            )

            break

    # ----------------------------------------------
    # Issue date
    # ----------------------------------------------

    issue_patterns = [
        r"(?:Date\s*of\s*Issue|Issue\s*Date|Issued\s*On)\s*[:\-]?\s*(\d{2}[\/\-.]\d{2}[\/\-.]\d{4})",
        r"(?:Date\s*of\s*Issue|Issue\s*Date|Issued\s*On)\s*[:\-]?\s*(\d{4}[\/\-.]\d{2}[\/\-.]\d{2})"
    ]

    for pattern in issue_patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            fields[
                "issue_date"
            ] = normalize_date(
                match.group(1)
            )

            break

    # ----------------------------------------------
    # Gender
    # ----------------------------------------------

    gender_match = re.search(
        r"(?:Sex|Gender)\s*[:\-]?\s*(Male|Female|M|F|X)",
        text,
        re.IGNORECASE
    )

    if gender_match:

        gender = (
            gender_match
            .group(1)
            .upper()
        )

        if gender == "M":
            fields["gender"] = "Male"

        elif gender == "F":
            fields["gender"] = "Female"

        elif gender == "X":
            fields["gender"] = "Unspecified"

        else:
            fields[
                "gender"
            ] = gender.capitalize()

    # ----------------------------------------------
    # Place of birth
    # ----------------------------------------------

    pob_match = re.search(
        r"(?:Place\s*of\s*Birth|Birth\s*Place)\s*[:\-]?\s*([A-Za-z][A-Za-z .,'-]{2,60})",
        text,
        re.IGNORECASE
    )

    if pob_match:

        place = (
            pob_match
            .group(1)
            .strip()
            .split("\n")[0]
        )

        fields[
            "place_of_birth"
        ] = place

    return fields


# --------------------------------------------------
# Merge normal fields + MRZ fields
# --------------------------------------------------

def merge_fields(
    visible_fields,
    mrz_fields
):

    final_fields = (
        visible_fields.copy()
    )

    for key, value in (
        mrz_fields.items()
    ):

        if (
            key not in final_fields
            or not final_fields[key]
        ):
            final_fields[
                key
            ] = value

    return final_fields


# --------------------------------------------------
# MAIN PASSPORT EXTRACTOR
# --------------------------------------------------

def extract_passport(text):

    text = clean_text(
        text
    )

    visible_fields = (
        extract_visible_fields(
            text
        )
    )

    mrz_fields = (
        parse_mrz(
            text
        )
    )

    fields = merge_fields(
        visible_fields,
        mrz_fields
    )

    return fields


# --------------------------------------------------
# Local test only
# --------------------------------------------------

if __name__ == "__main__":

    sample_text = """
    REPUBLIC OF INDIA
    PASSPORT

    Name: TEST USER
    Passport No: P1234567
    Nationality: INDIAN
    Date of Birth: 05/07/2002
    Sex: F
    Place of Birth: BHUBANESWAR
    Date of Issue: 10/08/2022
    Date of Expiry: 09/08/2032

    P<INDTEST<<USER<<<<<<<<<<<<<<<<<<<<<<<<
    P1234567<0IND0207059F3208097<<<<<<<<<<<<
    """

    result = extract_passport(
        sample_text
    )

    print(result)