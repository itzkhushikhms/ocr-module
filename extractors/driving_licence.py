import re


def clean(value):
    if not value:
        return None

    value = re.sub(r"\s+", " ", str(value)).strip(" :-")
    return value or None


def extract_driving_licence(text):
    fields = {}

    if not text:
        return fields

    text = str(text)

    # ========================================================
    # NAME
    # ========================================================

    name_patterns = [
        r"(?:Name)\s*[:\-]?\s*([A-Za-z][A-Za-z .'-]{2,60})",
        r"(?:Holder Name)\s*[:\-]?\s*([A-Za-z][A-Za-z .'-]{2,60})"
    ]

    for pattern in name_patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            fields["name"] = clean(
                match.group(1)
            )
            break

    # ========================================================
    # LICENCE NUMBER
    # ========================================================

    licence_patterns = [
        # DL No: OD02 20130003278
        r"(?:DL\s*(?:No|Number)?|Driving\s+Licence\s*(?:No|Number)?|"
        r"Driving\s+License\s*(?:No|Number)?|Licence\s*(?:No|Number)|"
        r"License\s*(?:No|Number))"
        r"\s*[:\-]?\s*([A-Z]{1,4}[\s\-]?[A-Z0-9]{2,20})",

        # Indian-style licence numbers
        # examples: OD02 20130003278, DL-0420110149646
        r"\b([A-Z]{2}\d{2}[\s\-]?\d{4,15})\b",

        r"\b([A-Z]{2}[\-\s]?\d{2}[\-\s]?\d{4}[\-\s]?\d{5,10})\b"
    ]

    for pattern in licence_patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            licence_number = clean(
                match.group(1)
            )

            # Do not accept tiny values like "AN"
            if licence_number:
                compact = re.sub(
                    r"[\s\-]",
                    "",
                    licence_number
                )

                if (
                    len(compact) >= 8
                    and any(
                        ch.isdigit()
                        for ch in compact
                    )
                ):
                    fields["licence_number"] = licence_number.upper()
                    break

    # ========================================================
    # DATE OF BIRTH
    # ========================================================

    dob_patterns = [
        r"(?:DOB|Date\s+of\s+Birth|Birth\s+Date)"
        r"\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})"
    ]

    for pattern in dob_patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            fields["date_of_birth"] = match.group(1)
            break

    # ========================================================
    # DATE OF ISSUE
    # ========================================================

    issue_patterns = [
        r"(?:Date\s+of\s+Issue|Issue\s+Date|DOI)"
        r"\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})"
    ]

    for pattern in issue_patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            fields["issue_date"] = match.group(1)
            break

    # ========================================================
    # EXPIRY / VALIDITY DATE
    # ========================================================

    expiry_patterns = [
        r"(?:Valid\s+Till|Valid\s+Until|Validity|Expiry|Expiry\s+Date)"
        r"\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})"
    ]

    for pattern in expiry_patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            fields["expiry_date"] = match.group(1)
            break

    # ========================================================
    # VEHICLE CLASS
    # ========================================================

    vehicle_patterns = [
        r"(?:Vehicle\s+Class|Class\s+of\s+Vehicle|COV)"
        r"\s*[:\-]?\s*([A-Za-z0-9,\-/ ]{2,50})"
    ]

    for pattern in vehicle_patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            value = clean(
                match.group(1)
            )

            if value:
                fields["vehicle_class"] = value
                break

    # ========================================================
    # BLOOD GROUP
    # ========================================================

    blood_match = re.search(
        r"(?:Blood\s+Group|Blood\s+Grp)"
        r"\s*[:\-]?\s*"
        r"(A|B|AB|O)[+-]",
        text,
        re.IGNORECASE
    )

    if blood_match:
        fields["blood_group"] = blood_match.group(0).split()[-1].upper()

    return fields