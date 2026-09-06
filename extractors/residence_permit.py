import re


def extract_residence_permit(text):
    fields = {}

    permit_number = re.search(
        r"(?:Permit|Card)\s*(?:No|Number)?"
        r"\s*[:\-]?\s*([A-Z0-9\-]+)",
        text,
        re.IGNORECASE
    )

    name_match = re.search(
        r"Name\s*[:\-]?\s*([A-Za-z ]+)",
        text,
        re.IGNORECASE
    )

    nationality = re.search(
        r"Nationality\s*[:\-]?\s*([A-Za-z ]+)",
        text,
        re.IGNORECASE
    )

    dob = re.search(
        r"(?:DOB|Date of Birth)\s*[:\-]?\s*"
        r"(\d{2}[/-]\d{2}[/-]\d{4})",
        text,
        re.IGNORECASE
    )

    expiry = re.search(
        r"(?:Expiry|Valid Until)\s*[:\-]?\s*"
        r"(\d{2}[/-]\d{2}[/-]\d{4})",
        text,
        re.IGNORECASE
    )

    if permit_number:
        fields["permit_number"] = permit_number.group(1)

    if name_match:
        fields["name"] = name_match.group(1).strip()

    if nationality:
        fields["nationality"] = nationality.group(1).strip()

    if dob:
        fields["date_of_birth"] = dob.group(1)

    if expiry:
        fields["expiry_date"] = expiry.group(1)

    return fields