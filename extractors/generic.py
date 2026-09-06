import re


def extract_generic(text):
    fields = {}

    dates = re.findall(
        r"\b\d{2}[/-]\d{2}[/-]\d{4}\b",
        text
    )

    gender = re.search(
        r"\b(Male|Female|Other)\b",
        text,
        re.IGNORECASE
    )

    possible_numbers = re.findall(
        r"\b[A-Z0-9\-]{6,20}\b",
        text
    )

    if dates:
        fields["detected_dates"] = dates

    if gender:
        fields["gender"] = gender.group()

    if possible_numbers:
        fields["possible_document_numbers"] = possible_numbers[:5]

    return fields