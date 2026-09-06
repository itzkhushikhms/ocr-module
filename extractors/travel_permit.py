import re


def extract_travel_permit(text):
    fields = {}

    permit_number = re.search(
        r"(?:Permit|Authorization|Authorisation)"
        r"\s*(?:No|Number)?\s*[:\-]?\s*([A-Z0-9\-]+)",
        text,
        re.IGNORECASE
    )

    name_match = re.search(
        r"Name\s*[:\-]?\s*([A-Za-z ]+)",
        text,
        re.IGNORECASE
    )

    passport_number = re.search(
        r"\b[A-Z][0-9]{7}\b",
        text
    )

    validity = re.search(
        r"(?:Valid Until|Valid To|Expiry)\s*[:\-]?\s*"
        r"(\d{2}[/-]\d{2}[/-]\d{4})",
        text,
        re.IGNORECASE
    )

    if permit_number:
        fields["permit_number"] = permit_number.group(1)

    if name_match:
        fields["name"] = name_match.group(1).strip()

    if passport_number:
        fields["passport_number"] = passport_number.group()

    if validity:
        fields["valid_until"] = validity.group(1)

    return fields