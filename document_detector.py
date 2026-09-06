# ============================================================
# document_detector.py
#
# Weighted document type detection
#
# Supports:
# - Passport
# - Visa
# - National ID
# - Driving Licence
# - Residence Permit
# - Travel Permit
# - Work Permit
# - Border Pass
#
# ============================================================


import re


# ============================================================
# DOCUMENT KEYWORDS
# ============================================================

DOCUMENT_KEYWORDS = {

    "passport": {

        # Strong passport indicators
        "passport": 8,
        "passport no": 5,
        "passport number": 4,
        "document no": 2,
        "document number": 2,

        # Passport biographical-page labels
        "place of birth": 2,
        "date of expiry": 2,
        "date of issue": 2,

        # Weak/common fields
        "surname": 1,
        "given names": 1,
        "nationality": 1
    },


    "visa": {

        # Very strong visa indicators
        "visa": 12,
        "visa type": 8,
        "visa type/class": 10,
        "visa class": 8,

        # Common visa-only clues
        "entries": 6,
        "duration of stay": 6,
        "issuing post": 6,
        "control number": 5,
        "annotation": 3,

        "valid until": 4,
        "valid from": 4,

        "expiration date": 3,
        "issue date": 2,

        # A visa often contains passport number,
        # but this must NOT make it a passport.
        "passport number": 1
    },


    "national_id": {

        "national id": 10,
        "national identity": 10,
        "identity card": 10,
        "identification card": 9,
        "aadhaar": 12,
        "aadhar": 12,
        "unique identification": 8,
        "uid": 4,

        "identity number": 5,
        "id number": 4,

        "date of birth": 1,
        "address": 2
    },


    "driving_licence": {

        "driving licence": 12,
        "driving license": 12,
        "driver licence": 10,
        "driver license": 10,

        "dl no": 7,
        "dl number": 7,

        "licence no": 5,
        "license no": 5,

        "class of vehicle": 8,
        "vehicle class": 7,

        "validity": 2
    },


    "residence_permit": {

        "residence permit": 12,
        "resident permit": 12,
        "residence card": 10,
        "resident card": 10,

        "permit number": 5,
        "permit no": 5,

        "type of permit": 4,
        "residence status": 4
    },


    "work_permit": {

        "work permit": 12,
        "employment permit": 10,
        "work authorization": 10,
        "work authorisation": 10,

        "employer": 5,
        "occupation": 4,
        "employment": 3,

        "permit number": 4
    },


    "travel_permit": {

        "travel permit": 12,
        "travel authorization": 12,
        "travel authorisation": 12,
        "travel document": 7,

        "authorization number": 5,
        "authorisation number": 5,

        "purpose of travel": 3
    },


    "border_pass": {

        "border pass": 12,
        "border permit": 10,
        "entry permit": 9,
        "entry pass": 9,

        "entry point": 6,
        "border crossing": 6,
        "checkpoint": 4,

        "pass number": 5
    }
}


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text):

    if not text:
        return ""

    text = text.lower()

    # Replace new lines/tabs with spaces
    text = re.sub(
        r"[\n\r\t]+",
        " ",
        text
    )

    # Collapse repeated spaces
    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# COUNT KEYWORD OCCURRENCES
# ============================================================

def count_keyword_occurrences(
    clean_text,
    keyword
):

    # Phrase matching with word boundaries where possible
    pattern = re.escape(
        keyword.lower()
    )

    matches = re.findall(
        pattern,
        clean_text
    )

    return len(matches)


# ============================================================
# DETECT PASSPORT MRZ
# ============================================================

def has_passport_mrz(text):

    """
    Detects typical passport MRZ lines.

    Passport TD3 MRZ usually begins with:
    P<
    """

    lines = text.upper().splitlines()

    for line in lines:

        cleaned = (
            line
            .replace(" ", "")
            .strip()
        )

        if (
            cleaned.startswith("P<")
            and len(cleaned) >= 30
        ):
            return True

    return False


# ============================================================
# DETECT VISA-LIKE STRUCTURE
# ============================================================

def has_strong_visa_structure(clean_text):

    """
    If multiple visa-specific labels appear,
    give visa a strong bonus.
    """

    visa_signals = [

        "visa",
        "visa type",
        "entries",
        "issuing post",
        "control number",
        "duration of stay"
    ]

    count = 0

    for signal in visa_signals:

        if signal in clean_text:
            count += 1

    return count >= 2


# ============================================================
# DETECT DOCUMENT TYPE
# ============================================================

def detect_document_type(text):

    clean_text = normalize_text(
        text
    )

    scores = {}

    matched_keywords = {}


    # --------------------------------------------------------
    # Keyword scoring
    # --------------------------------------------------------

    for document_type, keywords in (
        DOCUMENT_KEYWORDS.items()
    ):

        score = 0
        matched = []

        for keyword, weight in (
            keywords.items()
        ):

            occurrences = (
                count_keyword_occurrences(
                    clean_text,
                    keyword
                )
            )

            if occurrences > 0:

                # Add only a limited bonus for repeated words
                contribution = (
                    weight
                    * min(
                        occurrences,
                        2
                    )
                )

                score += contribution

                matched.append(
                    keyword
                )

        scores[
            document_type
        ] = score

        matched_keywords[
            document_type
        ] = matched


    # ========================================================
    # STRUCTURAL BONUSES
    # ========================================================

    # --------------------------------------------------------
    # Passport MRZ bonus
    # --------------------------------------------------------

    if has_passport_mrz(
        text
    ):

        scores[
            "passport"
        ] += 10


    # --------------------------------------------------------
    # Strong visa combination bonus
    # --------------------------------------------------------

    if has_strong_visa_structure(
        clean_text
    ):

        scores[
            "visa"
        ] += 15


    # --------------------------------------------------------
    # Visa should win when VISA appears strongly
    # together with visa-specific fields
    # --------------------------------------------------------

    if (
        "visa" in clean_text
        and (
            "visa type" in clean_text
            or "entries" in clean_text
            or "issuing post" in clean_text
            or "control number" in clean_text
        )
    ):

        scores[
            "visa"
        ] += 10


    # --------------------------------------------------------
    # Passport number alone must not dominate
    # --------------------------------------------------------

    if (
        "passport number"
        in clean_text
        and "visa" in clean_text
    ):

        scores[
            "passport"
        ] = max(
            0,
            scores["passport"] - 3
        )


    # ========================================================
    # FIND WINNER
    # ========================================================

    best_document = max(
        scores,
        key=scores.get
    )

    best_score = (
        scores[
            best_document
        ]
    )


    # ========================================================
    # UNKNOWN DOCUMENT
    # ========================================================

    if best_score <= 0:

        return {

            "type":
                "generic",

            "confidence":
                0.0,

            "scores":
                scores,

            "matched_keywords":
                matched_keywords
        }


    # ========================================================
    # CONFIDENCE
    # ========================================================

    sorted_scores = sorted(
        scores.values(),
        reverse=True
    )

    second_score = (
        sorted_scores[1]
        if len(sorted_scores) > 1
        else 0
    )


    # --------------------------------------------------------
    # Confidence based mainly on separation
    # between first and second candidate
    # --------------------------------------------------------

    margin = (
        best_score
        - second_score
    )

    confidence = (
        best_score
        /
        (
            best_score
            + second_score
            + 1
        )
    )


    # Small bonus when winner is clearly ahead
    if margin >= 10:

        confidence += 0.10

    elif margin >= 5:

        confidence += 0.05


    confidence = min(
        confidence,
        1.0
    )


    # ========================================================
    # FINAL RESULT
    # ========================================================

    return {

        "type":
            best_document,

        "confidence":
            round(
                confidence,
                3
            ),

        "scores":
            scores,

        "matched_keywords":
            matched_keywords
    }


# ============================================================
# LOCAL TEST
# ============================================================

if __name__ == "__main__":

    sample_visa = """
    VISA
    UNITED STATES
    Issuing Post Name
    Control Number
    Surname
    Given Name
    Visa Type / Class
    Passport Number
    Entries
    Issue Date
    Expiration Date
    """

    print(
        detect_document_type(
            sample_visa
        )
    )