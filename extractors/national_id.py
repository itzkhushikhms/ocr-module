import re


# -------------------------------------------------
# Basic text cleaning
# -------------------------------------------------

def clean_line(value):

    if not value:
        return None

    value = value.strip()

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value


# -------------------------------------------------
# Extract name
# -------------------------------------------------

def extract_name(text):

    # Try labelled patterns first
    patterns = [
        r"(?i)\bname\s*[:\-]?\s*([A-Za-z][A-Za-z .'-]{2,60})",
        r"(?i)\bholder\s*name\s*[:\-]?\s*([A-Za-z][A-Za-z .'-]{2,60})"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text
        )

        if match:

            name = clean_line(
                match.group(1)
            )

            if name:
                return name

    # -------------------------------------------------
    # Fallback:
    # search for a reasonable person-name line
    # -------------------------------------------------

    lines = [
        clean_line(line)
        for line in text.splitlines()
        if clean_line(line)
    ]

    blocked_words = {
        "government",
        "india",
        "aadhaar",
        "identity",
        "identification",
        "address",
        "male",
        "female",
        "other",
        "dob",
        "date of birth",
        "year of birth",
        "uidai"
    }

    for line in lines:

        lower_line = line.lower()

        if any(
            word in lower_line
            for word in blocked_words
        ):
            continue

        # Ignore lines containing numbers
        if re.search(
            r"\d",
            line
        ):
            continue

        # Only alphabetic name-like lines
        if re.fullmatch(
            r"[A-Za-z][A-Za-z .'-]{2,50}",
            line
        ):

            words = line.split()

            if 2 <= len(words) <= 5:
                return line

    return None


# -------------------------------------------------
# Extract DOB
# -------------------------------------------------

def extract_date_of_birth(text):

    patterns = [

        r"(?i)\b(?:dob|date of birth)\s*[:\-]?\s*(\d{2}[/-]\d{2}[/-]\d{4})",

        r"(?i)\b(?:dob|date of birth)\s*[:\-]?\s*(\d{4}[/-]\d{2}[/-]\d{2})",

        r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text
        )

        if match:
            return match.group(1)

    return None


# -------------------------------------------------
# Extract gender
# -------------------------------------------------

def extract_gender(text):

    match = re.search(
        r"\b(Male|Female|Other|M|F)\b",
        text,
        re.IGNORECASE
    )

    if not match:
        return None

    value = match.group(1).lower()

    if value in (
        "m",
        "male"
    ):
        return "Male"

    if value in (
        "f",
        "female"
    ):
        return "Female"

    return "Other"


# -------------------------------------------------
# Extract national ID number
# -------------------------------------------------

def extract_national_id_number(text):

    # -------------------------------------------------
    # Aadhaar-style 12-digit number
    # -------------------------------------------------

    aadhaar_matches = re.findall(
        r"\b\d{4}\s?\d{4}\s?\d{4}\b",
        text
    )

    for value in aadhaar_matches:

        digits = re.sub(
            r"\D",
            "",
            value
        )

        if len(digits) == 12:

            return (
                f"{digits[0:4]} "
                f"{digits[4:8]} "
                f"{digits[8:12]}"
            )

    # -------------------------------------------------
    # Generic labelled National ID
    # -------------------------------------------------

    labelled_patterns = [

        r"(?i)\b(?:national\s*id|id\s*number|identification\s*number)\s*[:\-]?\s*([A-Z0-9\- ]{6,20})",

        r"(?i)\baadhaar\s*(?:no|number)?\s*[:\-]?\s*(\d[\d\s]{10,15}\d)"
    ]

    for pattern in labelled_patterns:

        match = re.search(
            pattern,
            text
        )

        if match:

            candidate = clean_line(
                match.group(1)
            )

            if candidate:
                return candidate

    # -------------------------------------------------
    # Generic fallback
    # -------------------------------------------------

    candidates = re.findall(
        r"\b[A-Z0-9][A-Z0-9\- ]{7,20}\b",
        text,
        re.IGNORECASE
    )

    for candidate in candidates:

        cleaned = re.sub(
            r"[^A-Za-z0-9]",
            "",
            candidate
        )

        digit_count = sum(
            character.isdigit()
            for character in cleaned
        )

        if (
            8 <= len(cleaned) <= 16
            and digit_count >= 6
        ):

            return clean_line(
                candidate
            )

    return None


# -------------------------------------------------
# Extract address
# -------------------------------------------------

def extract_address(text):

    lines = [
        clean_line(line)
        for line in text.splitlines()
        if clean_line(line)
    ]

    address_lines = []

    collecting = False

    stop_words = [
        "www.",
        ".gov",
        "help@",
        "uidai",
        "aadhaar no",
        "aadhaar number",
        "national id",
        "date of birth",
        "dob",
        "male",
        "female",
        "other"
    ]

    for line in lines:

        lower_line = line.lower()

        # ---------------------------------------------
        # Start collecting after "Address"
        # ---------------------------------------------

        if "address" in lower_line:

            collecting = True

            after_label = re.sub(
                r"(?i)^.*?address\s*[:\-]?\s*",
                "",
                line
            )

            after_label = clean_line(
                after_label
            )

            if after_label:
                address_lines.append(
                    after_label
                )

            continue

        # ---------------------------------------------
        # Sometimes address starts with S/O, D/O etc.
        # ---------------------------------------------

        if (
            not collecting
            and re.match(
                r"(?i)^(s/o|d/o|w/o|c/o)\b",
                line
            )
        ):

            collecting = True

        # ---------------------------------------------
        # Collect address lines
        # ---------------------------------------------

        if collecting:

            if any(
                word in lower_line
                for word in stop_words
            ):
                break

            # Stop on long pure-number/footer lines
            digits_only = re.sub(
                r"\D",
                "",
                line
            )

            if (
                len(digits_only) >= 12
                and len(line.split()) <= 3
            ):
                break

            address_lines.append(
                line
            )

        # Don't allow huge address capture
        if len(address_lines) >= 5:
            break

    if not address_lines:
        return None

    address = ", ".join(
        address_lines
    )

    address = clean_line(
        address
    )

    return address


# -------------------------------------------------
# Main National ID extractor
# -------------------------------------------------

def extract_national_id(text):

    fields = {}

    name = extract_name(
        text
    )

    dob = extract_date_of_birth(
        text
    )

    gender = extract_gender(
        text
    )

    national_id_number = (
        extract_national_id_number(
            text
        )
    )

    address = extract_address(
        text
    )

    # -------------------------------------------------
    # Add only fields that were actually found
    # -------------------------------------------------

    if name:
        fields["name"] = name

    if dob:
        fields[
            "date_of_birth"
        ] = dob

    if gender:
        fields[
            "gender"
        ] = gender

    if national_id_number:
        fields[
            "national_id_number"
        ] = national_id_number

    if address:
        fields[
            "address"
        ] = address

    return fields