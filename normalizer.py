import re


def clean_text(text):

    if not text:
        return None

    text = text.strip()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text


def normalize_gender(value):

    if not value:
        return None

    value = value.lower().strip()

    gender_map = {

        "m": "Male",
        "male": "Male",

        "f": "Female",
        "female": "Female",

        "other": "Other"
    }

    return gender_map.get(
        value,
        value.title()
    )


def normalize_document_number(
        value
):

    if not value:
        return None

    value = value.upper()

    value = re.sub(
        r"\s+",
        "",
        value
    )

    return value