from datetime import datetime
import re


# --------------------------------------------------
# Required fields for each document type
# --------------------------------------------------

REQUIRED_FIELDS = {

    "passport": [
        "name",
        "passport_number",
        "date_of_birth",
        "nationality",
        "expiry_date"
    ],

    "visa": [
        "visa_number",
        "visa_type"
    ],

    "national_id": [
        "name",
        "national_id_number",
        "date_of_birth"
    ],

    "driving_licence": [
        "name",
        "licence_number",
        "date_of_birth"
    ],

    "residence_permit": [
        "name",
        "permit_number"
    ],

    "travel_permit": [
        "name",
        "permit_number"
    ]
}


# --------------------------------------------------
# Date parsing
# --------------------------------------------------

def parse_date(value):

    if not value:
        return None

    value = str(value).strip()

    formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%d %m %Y",
        "%d/%m/%y",
        "%d-%m-%y"
    ]

    for format_string in formats:

        try:
            return datetime.strptime(
                value,
                format_string
            )

        except ValueError:
            continue

    return None


# --------------------------------------------------
# Name validation
# --------------------------------------------------

def validate_name(name):

    if not name:
        return False

    name = str(name).strip()

    if len(name) < 3:
        return False

    # Name should contain mainly alphabetic characters
    if not re.fullmatch(
        r"[A-Za-z .'-]+",
        name
    ):
        return False

    # At least two alphabetic characters
    letters = re.sub(
        r"[^A-Za-z]",
        "",
        name
    )

    if len(letters) < 2:
        return False

    return True


# --------------------------------------------------
# Gender validation
# --------------------------------------------------

def validate_gender(gender):

    if not gender:
        return True

    value = str(gender).strip().lower()

    valid_values = {
        "male",
        "female",
        "other",
        "m",
        "f",
        "x"
    }

    return value in valid_values


# --------------------------------------------------
# National ID validation
# --------------------------------------------------

def validate_national_id_number(value):

    if not value:
        return False

    # Remove spaces and hyphens
    cleaned = re.sub(
        r"[\s-]",
        "",
        str(value)
    )

    # General national-ID rule:
    # numeric ID between 8 and 16 digits
    if not cleaned.isdigit():
        return False

    if len(cleaned) < 8:
        return False

    if len(cleaned) > 16:
        return False

    # Reject obviously repeated garbage
    if len(set(cleaned)) == 1:
        return False

    return True


# --------------------------------------------------
# Passport number validation
# --------------------------------------------------

def validate_passport_number(value):

    if not value:
        return False

    cleaned = re.sub(
        r"[\s-]",
        "",
        str(value).upper()
    )

    # Generic passport format
    return bool(
        re.fullmatch(
            r"[A-Z0-9]{6,12}",
            cleaned
        )
    )


# --------------------------------------------------
# Licence / permit validation
# --------------------------------------------------

def validate_document_number(value):

    if not value:
        return False

    cleaned = re.sub(
        r"[\s-]",
        "",
        str(value).upper()
    )

    return bool(
        re.fullmatch(
            r"[A-Z0-9]{5,20}",
            cleaned
        )
    )


# --------------------------------------------------
# Address validation
# --------------------------------------------------

def validate_address(address):

    if not address:
        return True

    address = str(address).strip()

    if len(address) < 8:
        return False

    return True


# --------------------------------------------------
# Main validation function
# --------------------------------------------------

def validate_document(
    document_type,
    fields,
    ocr_confidence=None,
    document_confidence=None
):

    issues = []
    warnings = []
    missing_fields = []

    if not isinstance(fields, dict):

        return {
            "status": "REVIEW",
            "missing_fields": [],
            "issues": [
                "Extracted fields are not in valid dictionary format"
            ],
            "warnings": []
        }


    # --------------------------------------------------
    # Required field validation
    # --------------------------------------------------

    required_fields = REQUIRED_FIELDS.get(
        document_type,
        []
    )

    for field in required_fields:

        value = fields.get(field)

        if value is None:
            missing_fields.append(field)

        elif isinstance(value, str) and not value.strip():
            missing_fields.append(field)


    if missing_fields:

        issues.append(
            "Missing required fields"
        )


    # --------------------------------------------------
    # Name validation
    # --------------------------------------------------

    if "name" in fields:

        if not validate_name(
            fields.get("name")
        ):

            issues.append(
                "Name format appears invalid"
            )


    # --------------------------------------------------
    # DOB validation
    # --------------------------------------------------

    dob_value = fields.get(
        "date_of_birth"
    )

    if dob_value:

        dob = parse_date(
            dob_value
        )

        if not dob:

            warnings.append(
                "Date of birth format could not be validated"
            )

        else:

            now = datetime.now()

            if dob > now:

                issues.append(
                    "Date of birth is in the future"
                )

            else:

                age = (
                    now.year
                    - dob.year
                    - (
                        (now.month, now.day)
                        <
                        (dob.month, dob.day)
                    )
                )

                if age > 120:

                    issues.append(
                        "Date of birth produces unrealistic age"
                    )


    # --------------------------------------------------
    # Expiry validation
    # --------------------------------------------------

    expiry_value = (
        fields.get("expiry_date")
        or fields.get("valid_until")
    )

    if expiry_value:

        expiry_date = parse_date(
            expiry_value
        )

        if not expiry_date:

            warnings.append(
                "Expiry date format could not be validated"
            )

        elif expiry_date.date() < datetime.now().date():

            issues.append(
                "Document appears expired"
            )


    # --------------------------------------------------
    # Issue-date validation
    # --------------------------------------------------

    issue_value = (
        fields.get("issue_date")
        or fields.get("valid_from")
    )

    if issue_value:

        issue_date = parse_date(
            issue_value
        )

        if not issue_date:

            warnings.append(
                "Issue date format could not be validated"
            )

        elif issue_date > datetime.now():

            issues.append(
                "Issue date is in the future"
            )


    # --------------------------------------------------
    # Issue date vs expiry date
    # --------------------------------------------------

    if issue_value and expiry_value:

        issue_date = parse_date(
            issue_value
        )

        expiry_date = parse_date(
            expiry_value
        )

        if (
            issue_date
            and expiry_date
            and expiry_date <= issue_date
        ):

            issues.append(
                "Expiry date must be later than issue date"
            )


    # --------------------------------------------------
    # Gender validation
    # --------------------------------------------------

    gender = fields.get(
        "gender"
    )

    if gender:

        if not validate_gender(
            gender
        ):

            warnings.append(
                "Gender value could not be validated"
            )


    # --------------------------------------------------
    # National ID number validation
    # --------------------------------------------------

    if document_type == "national_id":

        id_number = fields.get(
            "national_id_number"
        )

        if id_number:

            if not validate_national_id_number(
                id_number
            ):

                issues.append(
                    "National ID number format appears invalid"
                )


    # --------------------------------------------------
    # Passport validation
    # --------------------------------------------------

    elif document_type == "passport":

        passport_number = fields.get(
            "passport_number"
        )

        if passport_number:

            if not validate_passport_number(
                passport_number
            ):

                issues.append(
                    "Passport number format appears invalid"
                )


    # --------------------------------------------------
    # Driving licence validation
    # --------------------------------------------------

    elif document_type == "driving_licence":

        licence_number = fields.get(
            "licence_number"
        )

        if licence_number:

            if not validate_document_number(
                licence_number
            ):

                issues.append(
                    "Driving licence number format appears invalid"
                )


    # --------------------------------------------------
    # Permit validation
    # --------------------------------------------------

    elif document_type in {
        "residence_permit",
        "travel_permit"
    }:

        permit_number = fields.get(
            "permit_number"
        )

        if permit_number:

            if not validate_document_number(
                permit_number
            ):

                issues.append(
                    "Permit number format appears invalid"
                )


    # --------------------------------------------------
    # Address validation
    # --------------------------------------------------

    address = fields.get(
        "address"
    )

    if address:

        if not validate_address(
            address
        ):

            warnings.append(
                "Address appears incomplete"
            )


    # --------------------------------------------------
    # OCR confidence validation
    # --------------------------------------------------

    if ocr_confidence is not None:

        try:

            ocr_confidence = float(
                ocr_confidence
            )

            if ocr_confidence < 0.50:

                issues.append(
                    "OCR confidence is very low"
                )

            elif ocr_confidence < 0.70:

                warnings.append(
                    "OCR confidence is low; manual review recommended"
                )

            elif ocr_confidence < 0.80:

                warnings.append(
                    "OCR confidence is moderate"
                )

        except (
            TypeError,
            ValueError
        ):

            warnings.append(
                "OCR confidence could not be interpreted"
            )


    # --------------------------------------------------
    # Document-type confidence validation
    # --------------------------------------------------

    if document_confidence is not None:

        try:

            document_confidence = float(
                document_confidence
            )

            if document_confidence < 0.50:

                issues.append(
                    "Document type detection confidence is very low"
                )

            elif document_confidence < 0.70:

                warnings.append(
                    "Document type detection confidence is low"
                )

        except (
            TypeError,
            ValueError
        ):

            warnings.append(
                "Document detection confidence could not be interpreted"
            )


    # --------------------------------------------------
    # Final status
    # --------------------------------------------------

    if issues:

        status = "REVIEW"

    elif warnings:

        status = "PASS_WITH_WARNING"

    else:

        status = "PASS"


    return {

        "status":
            status,

        "missing_fields":
            missing_fields,

        "issues":
            issues,

        "warnings":
            warnings

    }
