import re
from datetime import datetime


# ============================================================
# VISA LABELS
# ============================================================

LABELS = {
    "issuing_post": [
        "issuing post",
        "issuing post name",
        "place of issue",
        "issued at"
    ],

    "control_number": [
        "control number",
        "control no",
        "control no."
    ],

    "surname": [
        "surname",
        "family name",
        "last name"
    ],

    "given_names": [
        "given name",
        "given names",
        "first name",
        "forename",
        "forenames"
    ],

    "visa_type": [
        "visa type / class",
        "visa type/class",
        "visa type",
        "visa class",
        "type / class",
        "type/class"
    ],

    "passport_number": [
        "passport number",
        "passport no",
        "passport no.",
        "travel document number"
    ],

    "gender": [
        "sex",
        "gender"
    ],

    "date_of_birth": [
        "date of birth",
        "birth date",
        "dob"
    ],

    "nationality": [
        "nationality",
        "citizenship"
    ],

    "entries": [
        "entries",
        "number of entries",
        "no of entries"
    ],

    "issue_date": [
        "issue date",
        "date of issue",
        "issued on",
        "valid from"
    ],

    "expiry_date": [
        "expiration date",
        "expiry date",
        "date of expiry",
        "valid until",
        "valid to",
        "expires"
    ],

    "duration_of_stay": [
        "duration of stay",
        "stay duration"
    ],

    "annotation": [
        "annotation",
        "remarks",
        "remark"
    ],

    "visa_number": [
        "visa number",
        "visa no",
        "visa no."
    ]
}


# ============================================================
# COUNTRY CODES
# ============================================================

COUNTRY_CODES = {
    "IND", "INDIA",
    "USA", "US", "UNITED STATES",
    "GBR", "UK", "UNITED KINGDOM",
    "CAN", "CANADA",
    "FRA", "FRANCE",
    "DEU", "GERMANY",
    "ITA", "ITALY",
    "ESP", "SPAIN",
    "AUS", "AUSTRALIA",
    "JPN", "JAPAN",
    "CHN", "CHINA",
    "THA", "THAILAND",
    "SGP", "SINGAPORE",
    "NPL", "NEPAL",
    "BGD", "BANGLADESH",
    "PAK", "PAKISTAN",
    "LKA", "SRI LANKA",
    "ARE", "UAE",
    "RUS", "RUSSIA"
}


# ============================================================
# BASIC HELPERS
# ============================================================

def clean(value):

    if value is None:
        return None

    value = str(value).strip()

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    value = value.strip(
        " :-|"
    )

    return value if value else None


def normalize_label(value):

    if not value:
        return ""

    value = str(value).lower()

    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def find_label(value):

    normalized = normalize_label(
        value
    )

    if not normalized:
        return None

    for field, aliases in LABELS.items():

        for alias in aliases:

            if normalized == normalize_label(alias):
                return field

    return None


def is_label(value):

    return find_label(value) is not None


# ============================================================
# DATE NORMALIZATION
# ============================================================

def normalize_date(value):

    value = clean(value)

    if not value:
        return None

    value = value.replace(
        ",",
        " "
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d.%m.%Y",

        "%Y/%m/%d",
        "%Y-%m-%d",
        "%Y.%m.%d",

        "%d %b %Y",
        "%d %B %Y",

        "%b %d %Y",
        "%B %d %Y",

        "%d-%b-%Y",
        "%d-%B-%Y",

        "%d%b%Y",
        "%d%B%Y"
    ]

    for fmt in formats:

        try:

            parsed = datetime.strptime(
                value,
                fmt
            )

            return parsed.strftime(
                "%d/%m/%Y"
            )

        except ValueError:
            continue

    return None


# ============================================================
# FIELD VALIDATION
# ============================================================

def valid_value(field, value):

    value = clean(value)

    if not value:
        return False

    if is_label(value):
        return False

    upper = value.upper()


    # --------------------------------------------------------
    # Dates
    # --------------------------------------------------------

    if field in {
        "date_of_birth",
        "issue_date",
        "expiry_date"
    }:

        return normalize_date(value) is not None


    # --------------------------------------------------------
    # Gender
    # --------------------------------------------------------

    if field == "gender":

        return upper in {
            "M",
            "F",
            "X",
            "MALE",
            "FEMALE"
        }


    # --------------------------------------------------------
    # Entries
    # --------------------------------------------------------

    if field == "entries":

        return bool(
            re.fullmatch(
                r"(MULTIPLE|SINGLE|[1-9][0-9]?)",
                upper
            )
        )


    # --------------------------------------------------------
    # Nationality
    # --------------------------------------------------------

    if field == "nationality":

        if re.search(
            r"\d",
            value
        ):
            return False

        if upper in COUNTRY_CODES:
            return True

        return bool(
            re.fullmatch(
                r"[A-Z][A-Z .'-]{1,35}",
                upper
            )
        )


    # --------------------------------------------------------
    # Passport number
    # --------------------------------------------------------

    if field == "passport_number":

        compact = re.sub(
            r"[^A-Za-z0-9]",
            "",
            value
        )

        if not 5 <= len(compact) <= 15:
            return False

        return any(
            ch.isdigit()
            for ch in compact
        )


    # --------------------------------------------------------
    # Visa number
    # --------------------------------------------------------

    if field == "visa_number":

        compact = re.sub(
            r"[^A-Za-z0-9]",
            "",
            value
        )

        if not 5 <= len(compact) <= 20:
            return False

        return any(
            ch.isdigit()
            for ch in compact
        )


    # --------------------------------------------------------
    # Control number
    # --------------------------------------------------------

    if field == "control_number":

        compact = re.sub(
            r"[^A-Za-z0-9]",
            "",
            value
        )

        if not 4 <= len(compact) <= 30:
            return False

        return any(
            ch.isdigit()
            for ch in compact
        )


    # --------------------------------------------------------
    # Visa type
    # --------------------------------------------------------

    if field == "visa_type":

        if not 1 <= len(value) <= 20:
            return False

        if upper in {
            "M",
            "F",
            "MALE",
            "FEMALE"
        }:
            return False

        return bool(
            re.search(
                r"[A-Za-z0-9]",
                value
            )
        )


    # --------------------------------------------------------
    # Names
    # --------------------------------------------------------

    if field in {
        "surname",
        "given_names"
    }:

        if not 2 <= len(value) <= 60:
            return False

        if re.search(
            r"\d",
            value
        ):
            return False

        return bool(
            re.fullmatch(
                r"[A-Za-zÀ-ÿ .'-]+",
                value
            )
        )


    # --------------------------------------------------------
    # Issuing post
    # --------------------------------------------------------

    if field == "issuing_post":

        return (
            2
            <= len(value)
            <= 80
        )


    # --------------------------------------------------------
    # Annotation
    # --------------------------------------------------------

    if field == "annotation":

        return (
            1
            <= len(value)
            <= 200
        )


    # --------------------------------------------------------
    # Duration
    # --------------------------------------------------------

    if field == "duration_of_stay":

        return bool(
            re.search(
                r"\d",
                value
            )
        )


    return True


# ============================================================
# OCR ITEM NORMALIZATION
# ============================================================

def normalize_items(items):

    if not isinstance(
        items,
        list
    ):
        return []

    result = []

    for index, item in enumerate(items):

        if not isinstance(
            item,
            dict
        ):
            continue

        text = clean(
            item.get("text")
        )

        if not text:
            continue

        confidence = item.get(
            "confidence",
            0
        )

        try:
            confidence = float(
                confidence
            )
        except Exception:
            confidence = 0.0


        bounds = item.get(
            "bounds",
            {}
        )

        if not isinstance(
            bounds,
            dict
        ):
            bounds = {}


        left = bounds.get("left")
        top = bounds.get("top")
        right = bounds.get("right")
        bottom = bounds.get("bottom")


        # ----------------------------------------------------
        # Use box if bounds missing
        # ----------------------------------------------------

        if None in {
            left,
            top,
            right,
            bottom
        }:

            box = item.get("box")

            if (
                not isinstance(box, list)
                or len(box) < 4
            ):
                continue

            try:

                xs = [
                    float(point[0])
                    for point in box
                ]

                ys = [
                    float(point[1])
                    for point in box
                ]

                left = min(xs)
                right = max(xs)

                top = min(ys)
                bottom = max(ys)

            except Exception:
                continue


        try:

            left = float(left)
            top = float(top)
            right = float(right)
            bottom = float(bottom)

        except Exception:
            continue


        width = max(
            1.0,
            right - left
        )

        height = max(
            1.0,
            bottom - top
        )


        result.append(
            {
                "index": index,

                "text": text,

                "confidence": confidence,

                "left": left,
                "top": top,
                "right": right,
                "bottom": bottom,

                "width": width,
                "height": height,

                "center_x": (
                    left + right
                ) / 2,

                "center_y": (
                    top + bottom
                ) / 2
            }
        )

    return result


# ============================================================
# FIELD-SPECIFIC BONUS
# ============================================================

def field_bonus(field, value):

    value = clean(value)

    if not value:
        return -100

    upper = value.upper()

    bonus = 0


    if field == "gender":

        if upper in {
            "M",
            "F",
            "X",
            "MALE",
            "FEMALE"
        }:
            bonus += 100


    elif field == "entries":

        if upper in {
            "MULTIPLE",
            "SINGLE"
        }:
            bonus += 100

        elif re.fullmatch(
            r"[1-9][0-9]?",
            upper
        ):
            bonus += 80


    elif field == "nationality":

        if upper in COUNTRY_CODES:
            bonus += 100

        if re.search(
            r"\d",
            value
        ):
            bonus -= 150


    elif field in {
        "date_of_birth",
        "issue_date",
        "expiry_date"
    }:

        if normalize_date(value):
            bonus += 100


    elif field == "visa_type":

        compact = value.replace(
            " ",
            ""
        )

        if re.fullmatch(
            r"[A-Za-z]{0,3}[0-9]{1,3}[A-Za-z]?",
            compact
        ):
            bonus += 100


    elif field in {
        "visa_number",
        "passport_number",
        "control_number"
    }:

        if any(
            ch.isdigit()
            for ch in value
        ):
            bonus += 50


    return bonus


# ============================================================
# CANDIDATE SCORE
# ============================================================

def score_candidate(
    label_item,
    candidate,
    field
):

    if (
        label_item["index"]
        ==
        candidate["index"]
    ):
        return None


    value = candidate["text"]

    if not valid_value(
        field,
        value
    ):
        return None


    below_gap = (
        candidate["top"]
        -
        label_item["bottom"]
    )

    right_gap = (
        candidate["left"]
        -
        label_item["right"]
    )

    dx = abs(
        candidate["center_x"]
        -
        label_item["center_x"]
    )

    dy = abs(
        candidate["center_y"]
        -
        label_item["center_y"]
    )


    scores = []


    # ========================================================
    # CASE 1:
    # Value directly below label
    # ========================================================

    if (
        -8
        <= below_gap
        <= 90
    ):

        if dx <= 150:

            score = 120

            score -= (
                max(
                    0,
                    below_gap
                )
                * 1.4
            )

            score -= (
                dx
                * 0.3
            )

            scores.append(
                score
            )


    # ========================================================
    # CASE 2:
    # Value to right on same line
    # ========================================================

    if (
        -5
        <= right_gap
        <= 350
        and
        dy <= 35
    ):

        score = 105

        score -= (
            max(
                0,
                right_gap
            )
            * 0.18
        )

        score -= (
            dy
            * 0.8
        )

        scores.append(
            score
        )


    if not scores:
        return None


    score = max(scores)

    score += (
        candidate[
            "confidence"
        ]
        * 10
    )

    score += field_bonus(
        field,
        value
    )

    return score


# ============================================================
# SPATIAL EXTRACTION
# ============================================================

def extract_spatial_fields(items):

    items = normalize_items(
        items
    )

    if not items:
        return {}

    fields = {}

    label_items = []

    for item in items:

        field = find_label(
            item["text"]
        )

        if field:

            label_items.append(
                (
                    field,
                    item
                )
            )


    for field, label_item in label_items:

        candidates = []

        for candidate in items:

            score = score_candidate(
                label_item,
                candidate,
                field
            )

            if score is None:
                continue

            candidates.append(
                (
                    score,
                    candidate
                )
            )


        if not candidates:
            continue


        candidates.sort(
            key=lambda x: x[0],
            reverse=True
        )


        best_score, best_candidate = (
            candidates[0]
        )


        if best_score < 45:
            continue


        value = clean(
            best_candidate["text"]
        )

        if value:

            fields[
                field
            ] = value


    return fields


# ============================================================
# SAME-LINE TEXT EXTRACTION
# ============================================================

def extract_same_line_fields(text):

    result = {}

    if not text:
        return result


    for line in str(text).splitlines():

        line = clean(line)

        if not line:
            continue


        for field, aliases in LABELS.items():

            for alias in aliases:

                pattern = (
                    rf"^\s*"
                    rf"{re.escape(alias)}"
                    rf"\s*[:\-]\s*"
                    rf"(.+)$"
                )

                match = re.match(
                    pattern,
                    line,
                    re.IGNORECASE
                )

                if not match:
                    continue


                value = clean(
                    match.group(1)
                )


                if valid_value(
                    field,
                    value
                ):

                    result[
                        field
                    ] = value

                break


    return result


# ============================================================
# REGEX FALLBACK
# ============================================================

def regex_fallbacks(
    text,
    fields
):

    if not text:
        return fields

    upper = text.upper()


    # --------------------------------------------------------
    # VISA NUMBER
    # --------------------------------------------------------

    if not fields.get(
        "visa_number"
    ):

        match = re.search(
            r"VISA\s*(?:NUMBER|NO)?"
            r"\s*[:\-]?\s*"
            r"([A-Z0-9\-]{5,20})",
            upper
        )

        if match:

            value = match.group(1)

            if valid_value(
                "visa_number",
                value
            ):

                fields[
                    "visa_number"
                ] = value


    # --------------------------------------------------------
    # PASSPORT NUMBER
    # --------------------------------------------------------

    if not fields.get(
        "passport_number"
    ):

        match = re.search(
            r"PASSPORT\s*(?:NUMBER|NO)?"
            r"\s*[:\-]?\s*"
            r"([A-Z0-9]{5,15})",
            upper
        )

        if match:

            value = match.group(1)

            if valid_value(
                "passport_number",
                value
            ):

                fields[
                    "passport_number"
                ] = value


    return fields


# ============================================================
# FINAL CLEANUP
# ============================================================

def finalize(fields):

    result = {}


    for field, value in fields.items():

        value = clean(value)

        if not value:
            continue


        if field in {
            "date_of_birth",
            "issue_date",
            "expiry_date"
        }:

            normalized = normalize_date(
                value
            )

            if normalized:
                value = normalized


        elif field == "gender":

            mapping = {
                "M": "Male",
                "MALE": "Male",
                "F": "Female",
                "FEMALE": "Female",
                "X": "X"
            }

            value = mapping.get(
                value.upper(),
                value
            )


        elif field == "nationality":

            value = value.upper()


        elif field in {
            "visa_number",
            "passport_number",
            "control_number"
        }:

            value = re.sub(
                r"\s+",
                "",
                value
            ).upper()


        result[
            field
        ] = value


    # --------------------------------------------------------
    # Build full name
    # --------------------------------------------------------

    surname = result.get(
        "surname"
    )

    given_names = result.get(
        "given_names"
    )


    if surname and given_names:

        result[
            "name"
        ] = clean(
            f"{given_names} {surname}"
        )

    elif surname:

        result[
            "name"
        ] = surname

    elif given_names:

        result[
            "name"
        ] = given_names


    return result


# ============================================================
# MAIN VISA EXTRACTOR
# ============================================================

def extract_visa(
    text,
    items=None
):
    
    fields = {}


    # ========================================================
    # 1. Extract from plain OCR text
    # ========================================================

    same_line = (
        extract_same_line_fields(
            text
        )
    )

    fields.update(
        same_line
    )


    # ========================================================
    # 2. Extract from coordinate-aware OCR items
    # ========================================================

    actual_items = []


    if isinstance(
        items,
        list
    ):

        actual_items = items


    elif isinstance(
        items,
        dict
    ):

        actual_items = (
            items.get("items")
            or
            items.get("ocr_items")
            or
            items.get("results")
            or []
        )


    if actual_items:

        spatial = extract_spatial_fields(
            actual_items
        )

        # Spatial information has higher priority.
        fields.update(
            spatial
        )


    # ========================================================
    # 3. Regex fallback
    # ========================================================

    fields = regex_fallbacks(
        text,
        fields
    )


    # ========================================================
    # 4. Remove invalid assignments
    # ========================================================

    cleaned = {}


    for field, value in fields.items():

        if valid_value(
            field,
            value
        ):

            cleaned[
                field
            ] = value


    # ========================================================
    # 5. Final formatting
    # ========================================================

    return finalize(
        cleaned
    )


# ============================================================
# OPTIONAL COMPATIBILITY FUNCTION
# ============================================================

def extract_document(
    ocr_result
):

    if isinstance(
        ocr_result,
        dict
    ):

        text = (
            ocr_result.get("text")
            or ""
        )

        items = (
            ocr_result.get("items")
            or
            ocr_result.get("ocr_items")
            or
            ocr_result.get("results")
            or []
        )

    else:

        text = ""

        items = (
            ocr_result
            if isinstance(
                ocr_result,
                list
            )
            else []
        )


    fields = extract_visa(
        text,
        items
    )


    return {
        "document_type": "visa",
        "fields": fields
    }


# ============================================================
# LOCAL TEST
# ============================================================

if __name__ == "__main__":

    sample = [

        {
            "text": "Surname",
            "confidence": 0.99,
            "bounds": {
                "left": 367,
                "top": 197,
                "right": 457,
                "bottom": 218
            }
        },

        {
            "text": "LEFEBVRE",
            "confidence": 0.99,
            "bounds": {
                "left": 366,
                "top": 224,
                "right": 475,
                "bottom": 248
            }
        },

        {
            "text": "Given Name",
            "confidence": 0.97,
            "bounds": {
                "left": 367,
                "top": 256,
                "right": 491,
                "bottom": 282
            }
        },

        {
            "text": "MICHEL",
            "confidence": 0.99,
            "bounds": {
                "left": 366,
                "top": 286,
                "right": 447,
                "bottom": 311
            }
        }
    ]


    test_result = extract_visa(
        "",
        sample
    )


    print(
        test_result
    )