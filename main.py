# ============================================================
# main.py
#
# SIH-188
# AI-Based Fake Identity & Document Screening System
#
# SINGLE ENTRY POINT
#
# DOCUMENT ONLY:
# python main.py images/document.jpg
#
# DOCUMENT + SELFIE:
# python main.py images/document.jpg images/selfy.jpg
# ============================================================

import os
import sys
import json
import time
import inspect
from datetime import datetime


# ============================================================
# PATH SETUP
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TAMPERING_DIR = os.path.join(
    BASE_DIR,
    "tampering"
)

FACE_DIR = os.path.join(
    BASE_DIR,
    "face_verification"
)


for path in [
    BASE_DIR,
    TAMPERING_DIR,
    FACE_DIR
]:
    if path not in sys.path:
        sys.path.insert(0, path)


# ============================================================
# CORE EXTRACTION
# ============================================================

try:
    from extraction import extract_document

except Exception as error:

    print(
        json.dumps(
            {
                "success": False,
                "stage": "startup",
                "error": "Could not import extraction.py",
                "details": str(error)
            },
            indent=4
        )
    )

    sys.exit(1)


# ============================================================
# VALIDATION
# ============================================================

try:
    import validation as validation_module
    VALIDATION_AVAILABLE = True

except Exception:
    validation_module = None
    VALIDATION_AVAILABLE = False


# ============================================================
# TAMPERING
# ============================================================

try:
    from tampering.tampering_detector import detect_tampering
    TAMPERING_AVAILABLE = True

except Exception:

    try:
        from tampering_detector import detect_tampering
        TAMPERING_AVAILABLE = True

    except Exception:
        detect_tampering = None
        TAMPERING_AVAILABLE = False


# ============================================================
# FACE VERIFICATION
# ============================================================

try:
    from face_verification.face_verifier import verify_faces
    FACE_AVAILABLE = True

except Exception:

    try:
        from face_verifier import verify_faces
        FACE_AVAILABLE = True

    except Exception:
        verify_faces = None
        FACE_AVAILABLE = False


# ============================================================
# SUPPORTED INPUT FORMATS
# ============================================================

SUPPORTED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff"
}


# ============================================================
# DOCUMENT TYPES WHERE FACE CHECK MAY APPLY
# ============================================================

FACE_DOCUMENT_TYPES = {
    "passport",
    "visa",
    "national_id",
    "driving_licence",
    "residence_permit",
    "travel_permit",
    "work_permit",
    "border_pass"
}


# ============================================================
# BASIC HELPERS
# ============================================================

def safe_float(value, default=0.0):

    try:
        return float(value)

    except Exception:
        return default


def clamp(value, minimum=0.0, maximum=100.0):

    return max(
        minimum,
        min(maximum, value)
    )


def to_percentage(value):

    value = safe_float(value)

    if 0 <= value <= 1:
        value *= 100

    return round(
        clamp(value),
        2
    )


# ============================================================
# FILE CHECKING
# ============================================================

def validate_input_file(path, label="Document"):

    if not path:

        return {
            "valid": False,
            "message": f"{label} path was not provided."
        }


    if not os.path.isfile(path):

        return {
            "valid": False,
            "message": f"{label} file not found: {path}"
        }


    extension = os.path.splitext(path)[1].lower()


    if extension not in SUPPORTED_IMAGE_EXTENSIONS:

        return {
            "valid": False,
            "message": (
                f"Unsupported {label.lower()} format: "
                f"{extension}"
            )
        }


    return {
        "valid": True,
        "message": None
    }


def get_file_info(path):

    return {
        "name": os.path.basename(path),

        "extension": os.path.splitext(
            path
        )[1].lower(),

        "size_bytes": (
            os.path.getsize(path)
            if os.path.isfile(path)
            else 0
        )
    }


# ============================================================
# STANDARD MODULE RESULTS
# ============================================================

def module_error(message):

    return {
        "status": "ERROR",
        "message": str(message)
    }


def module_not_run(message):

    return {
        "status": "NOT_RUN",
        "message": message
    }


# ============================================================
# FIND VALIDATION FUNCTION
# ============================================================

def find_validation_function():

    if not VALIDATION_AVAILABLE:
        return None


    possible_names = [
        "validate_document",
        "validate_fields",
        "validate"
    ]


    for name in possible_names:

        function = getattr(
            validation_module,
            name,
            None
        )

        if callable(function):
            return function


    return None


# ============================================================
# FALLBACK VALIDATION
# ============================================================

def fallback_validation(document_type, fields):

    rules = {

        "passport": [
            ["name"],
            ["passport_number", "document_number"],
            ["date_of_birth"],
            ["expiry_date"]
        ],

        "visa": [
            ["name"],
            ["passport_number", "document_number"],
            [
                "visa_number",
                "control_number",
                "document_number"
            ],
            ["visa_type"]
        ],

        "national_id": [
            ["name"],
            ["id_number", "document_number"]
        ],

        "driving_licence": [
            ["name"],
            [
                "licence_number",
                "license_number",
                "document_number"
            ]
        ],

        "residence_permit": [
            ["name"],
            ["permit_number", "document_number"]
        ],

        "travel_permit": [
            ["name"],
            [
                "permit_number",
                "authorization_number",
                "document_number"
            ]
        ],

        "work_permit": [
            ["name"],
            ["permit_number", "document_number"]
        ],

        "border_pass": [
            ["name"],
            ["pass_number", "document_number"]
        ]
    }


    requirements = rules.get(
        document_type,
        []
    )


    if not requirements:

        return {
            "status": "REVIEW",
            "missing_fields": [],
            "issues": [
                "No document-specific validation rules are available."
            ],
            "warnings": [],
            "source": "fallback"
        }


    missing = []


    for alternatives in requirements:

        found = False

        for field in alternatives:

            value = fields.get(field)

            if value not in [
                None,
                "",
                [],
                {}
            ]:
                found = True
                break


        if not found:
            missing.append(
                "/".join(alternatives)
            )


    if len(missing) == 0:
        status = "PASS"

    elif len(missing) == 1:
        status = "REVIEW"

    else:
        status = "FAIL"


    return {
        "status": status,
        "missing_fields": missing,
        "issues": (
            ["Required fields are missing."]
            if missing
            else []
        ),
        "warnings": [],
        "source": "fallback"
    }


# ============================================================
# NORMALIZE VALIDATION OUTPUT
# ============================================================

def normalize_validation_result(result):

    if isinstance(result, bool):

        return {
            "status": (
                "PASS"
                if result
                else "FAIL"
            ),
            "missing_fields": [],
            "issues": [],
            "warnings": []
        }


    if not isinstance(result, dict):

        return {
            "status": "REVIEW",
            "missing_fields": [],
            "issues": [
                "Validation returned an unexpected result."
            ],
            "warnings": []
        }


    result = dict(result)


    status = str(
        result.get(
            "status",
            "REVIEW"
        )
    ).upper()


    status_map = {
        "OK": "PASS",
        "SUCCESS": "PASS",
        "VALID": "PASS",

        "INVALID": "FAIL",

        "WARNING": "REVIEW"
    }


    status = status_map.get(
        status,
        status
    )


    if status not in {
        "PASS",
        "FAIL",
        "REVIEW"
    }:
        status = "REVIEW"


    result["status"] = status

    result.setdefault(
        "missing_fields",
        []
    )

    result.setdefault(
        "issues",
        []
    )

    result.setdefault(
        "warnings",
        []
    )


    return result


# ============================================================
# CALL VALIDATION SAFELY
# ============================================================

def run_validation(
    document_type,
    fields,
    raw_text
):

    function = find_validation_function()


    if function is None:

        return fallback_validation(
            document_type,
            fields
        )


    try:

        signature = inspect.signature(
            function
        )

        parameter_names = list(
            signature.parameters.keys()
        )

    except Exception:
        parameter_names = []


    mapping = {
        "document_type": document_type,
        "doc_type": document_type,
        "type": document_type,

        "fields": fields,
        "data": fields,
        "extracted_fields": fields,

        "text": raw_text,
        "raw_text": raw_text
    }


    kwargs = {}


    for parameter in parameter_names:

        if parameter in mapping:

            kwargs[parameter] = (
                mapping[parameter]
            )


    # --------------------------------------------------------
    # Try keyword style
    # --------------------------------------------------------

    if kwargs:

        try:

            result = function(
                **kwargs
            )

            result = normalize_validation_result(
                result
            )

            result["source"] = "validation.py"

            return result

        except Exception:
            pass


    # --------------------------------------------------------
    # Try common positional styles
    # --------------------------------------------------------

    attempts = [
        (
            document_type,
            fields,
            raw_text
        ),

        (
            document_type,
            fields
        ),

        (
            fields,
            document_type
        ),

        (
            fields,
        )
    ]


    for arguments in attempts:

        try:

            result = function(
                *arguments
            )

            result = normalize_validation_result(
                result
            )

            result["source"] = "validation.py"

            return result

        except Exception:
            continue


    fallback = fallback_validation(
        document_type,
        fields
    )

    fallback["warnings"].append(
        "validation.py could not be called successfully."
    )

    return fallback


# ============================================================
# TAMPERING ANALYSIS
# ============================================================

def run_tampering(document_path):

    if not TAMPERING_AVAILABLE:

        return {
            "status": "ERROR",
            "risk_level": "UNKNOWN",
            "risk_score": None,
            "suspicious": None,
            "decision": "MANUAL_REVIEW",
            "reasons": [
                "Tampering module could not be imported."
            ]
        }


    try:

        result = detect_tampering(
            document_path
        )


        if not isinstance(
            result,
            dict
        ):

            raise ValueError(
                "Tampering detector returned invalid data."
            )


        return result


    except Exception as error:

        return {
            "status": "ERROR",
            "risk_level": "UNKNOWN",
            "risk_score": None,
            "suspicious": None,
            "decision": "MANUAL_REVIEW",
            "reasons": [
                f"Tampering analysis failed: {error}"
            ]
        }


# ============================================================
# FACE VERIFICATION
# ============================================================

def run_face_verification(
    document_path,
    selfie_path,
    document_type
):

    if not selfie_path:

        return {
            "status": "NOT_RUN",
            "decision": "NOT_PROVIDED",
            "match": None,
            "similarity": None,
            "risk_level": "UNKNOWN",
            "message": (
                "No selfie image was provided."
            )
        }


    if document_type not in FACE_DOCUMENT_TYPES:

        return {
            "status": "NOT_APPLICABLE",
            "decision": "NOT_APPLICABLE",
            "match": None,
            "similarity": None,
            "risk_level": "UNKNOWN",
            "message": (
                "Face verification is not required "
                "for this document type."
            )
        }


    selfie_check = validate_input_file(
        selfie_path,
        "Selfie"
    )


    if not selfie_check["valid"]:

        return {
            "status": "ERROR",
            "decision": "MANUAL_REVIEW",
            "match": None,
            "similarity": None,
            "risk_level": "UNKNOWN",
            "message": selfie_check["message"]
        }


    if not FACE_AVAILABLE:

        return {
            "status": "ERROR",
            "decision": "MANUAL_REVIEW",
            "match": None,
            "similarity": None,
            "risk_level": "UNKNOWN",
            "message": (
                "Face verification module is unavailable."
            )
        }


    try:

        result = verify_faces(
            document_path,
            selfie_path
        )


        if not isinstance(
            result,
            dict
        ):

            raise ValueError(
                "Face verifier returned invalid data."
            )


        # ----------------------------------------------------
        # Remove misleading probability-style percentage.
        # Raw similarity is safer to report.
        # ----------------------------------------------------

        result.pop(
            "similarity_percentage",
            None
        )


        return result


    except Exception as error:

        return {
            "status": "ERROR",
            "decision": "MANUAL_REVIEW",
            "match": None,
            "similarity": None,
            "risk_level": "UNKNOWN",
            "message": (
                f"Face verification failed: {error}"
            )
        }


# ============================================================
# FINAL RISK ENGINE
# ============================================================

def calculate_final_risk(
    extraction,
    validation,
    tampering,
    face,
    selfie_provided
):

    score = 0.0

    reasons = []


    # ========================================================
    # OCR QUALITY
    # ========================================================

    ocr_confidence = to_percentage(
        extraction.get(
            "ocr_confidence",
            0
        )
    )


    if ocr_confidence < 50:

        score += 20

        reasons.append(
            "OCR confidence is very low."
        )

    elif ocr_confidence < 70:

        score += 10

        reasons.append(
            "OCR confidence is below preferred level."
        )


    # ========================================================
    # DOCUMENT DETECTION QUALITY
    # ========================================================

    document_confidence = to_percentage(
        extraction.get(
            "document_type_confidence",
            0
        )
    )


    if document_confidence < 30:

        score += 20

        reasons.append(
            "Document type could not be identified confidently."
        )

    elif document_confidence < 60:

        score += 10

        reasons.append(
            "Document type identification confidence is moderate."
        )


    # ========================================================
    # VALIDATION
    # ========================================================

    validation_status = str(
        validation.get(
            "status",
            "REVIEW"
        )
    ).upper()


    if validation_status == "FAIL":

        score += 35

        reasons.append(
            "Document field validation failed."
        )


    elif validation_status == "REVIEW":

        score += 15

        reasons.append(
            "Document field validation requires manual review."
        )


    missing_fields = validation.get(
        "missing_fields",
        []
    )


    if missing_fields:

        score += min(
            15,
            len(missing_fields) * 3
        )

        reasons.append(
            "One or more expected document fields are missing."
        )


    # ========================================================
    # TAMPERING
    # ========================================================

    tampering_status = str(
        tampering.get(
            "status",
            "ERROR"
        )
    ).upper()


    tampering_risk = str(
        tampering.get(
            "risk_level",
            "UNKNOWN"
        )
    ).upper()


    tampering_score = safe_float(
        tampering.get(
            "risk_score",
            0
        )
    )


    score += min(
        25,
        tampering_score * 0.25
    )


    if tampering_status == "ERROR":

        score += 10

        reasons.append(
            "Tampering analysis could not be completed."
        )


    if tampering_risk == "HIGH":

        score += 35

        reasons.append(
            "Strong image tampering indicators were detected."
        )


    elif tampering_risk == "MEDIUM":

        score += 18

        reasons.append(
            "Suspicious image manipulation indicators were detected."
        )


    if tampering.get(
        "suspicious"
    ) is True:

        score += 15

        reasons.append(
            "Tampering analysis marked the image as suspicious."
        )


    # ========================================================
    # FACE VERIFICATION
    # ========================================================

    face_status = str(
        face.get(
            "status",
            "NOT_RUN"
        )
    ).upper()


    face_match = face.get(
        "match"
    )


    if selfie_provided:

        if (
            face_status == "NO_MATCH"
            or
            face_match is False
        ):

            score += 40

            reasons.append(
                "Document photograph and selfie did not match."
            )


        elif face_status in {
            "ERROR",
            "NO_FACE",
            "MULTIPLE_FACES",
            "NO_EMBEDDING",
            "REVIEW"
        }:

            score += 20

            reasons.append(
                "Face verification could not produce a reliable result."
            )


        elif (
            face_status == "MATCH"
            or
            face_match is True
        ):

            score -= 5


    # ========================================================
    # FINAL SCORE
    # ========================================================

    score = round(
        clamp(score),
        2
    )


    if score >= 60:

        risk_level = "HIGH"

    elif score >= 30:

        risk_level = "MEDIUM"

    else:

        risk_level = "LOW"


    # ========================================================
    # HARD REVIEW RULES
    # ========================================================

    forced_review = False


    # Validation review/failure cannot be auto-accepted.

    if validation_status in {
        "REVIEW",
        "FAIL"
    }:

        forced_review = True


    # Face mismatch cannot be auto-accepted.

    if (
        selfie_provided
        and
        (
            face_status == "NO_MATCH"
            or
            face_match is False
        )
    ):

        forced_review = True


    # Inconclusive face check requires review.

    if (
        selfie_provided
        and
        face_status in {
            "ERROR",
            "NO_FACE",
            "MULTIPLE_FACES",
            "NO_EMBEDDING",
            "REVIEW"
        }
    ):

        forced_review = True


    # Suspicious tampering requires review.

    if tampering_risk in {
        "HIGH",
        "MEDIUM"
    }:

        forced_review = True


    if tampering.get(
        "suspicious"
    ) is True:

        forced_review = True


    if tampering_status == "ERROR":

        forced_review = True


    # ========================================================
    # FINAL DECISION
    # ========================================================

    if forced_review:

        decision = "MANUAL_REVIEW"

    elif score >= 30:

        decision = "MANUAL_REVIEW"

    else:

        decision = "ACCEPT"


    if not reasons:

        reasons.append(
            "No strong screening risk indicators were detected."
        )


    return {
        "risk_score": score,

        "risk_level": risk_level,

        "decision": decision,

        "reasons": reasons,

        "disclaimer": (
            "This result is an automated screening assessment. "
            "It does not provide definitive proof that a "
            "document is genuine or fake."
        )
    }


# ============================================================
# CLEAN TAMPERING OUTPUT
# ============================================================

def compact_tampering(result):

    if not isinstance(
        result,
        dict
    ):
        return result


    return {
        "status": result.get(
            "status"
        ),

        "risk_score": result.get(
            "risk_score"
        ),

        "risk_level": result.get(
            "risk_level"
        ),

        "suspicious": result.get(
            "suspicious"
        ),

        "decision": result.get(
            "decision"
        ),

        "reasons": result.get(
            "reasons",
            []
        )
    }


# ============================================================
# CLEAN FACE OUTPUT
# ============================================================

def compact_face(result):

    if not isinstance(
        result,
        dict
    ):
        return result


    return {
        "status": result.get(
            "status"
        ),

        "decision": result.get(
            "decision"
        ),

        "match": result.get(
            "match"
        ),

        "similarity": result.get(
            "similarity"
        ),

        "risk_level": result.get(
            "risk_level"
        ),

        "message": result.get(
            "message"
        )
    }


# ============================================================
# COMPLETE SIH SCREENING PIPELINE
# ============================================================

def screen_document(
    document_path,
    selfie_path=None
):

    total_start = time.perf_counter()


    # ========================================================
    # INPUT VALIDATION
    # ========================================================

    document_check = validate_input_file(
        document_path,
        "Document"
    )


    if not document_check["valid"]:

        return {
            "success": False,

            "stage": "input",

            "error": document_check[
                "message"
            ],

            "screening": {
                "risk_level": "UNKNOWN",
                "decision": "MANUAL_REVIEW"
            }
        }


    # ========================================================
    # OCR + DOCUMENT TYPE + FIELD EXTRACTION
    # ========================================================

    extraction_start = time.perf_counter()


    try:

        extraction = extract_document(
            document_path
        )


        if not isinstance(
            extraction,
            dict
        ):

            raise ValueError(
                "Extraction pipeline returned invalid data."
            )


    except Exception as error:

        return {
            "success": False,

            "stage": "extraction",

            "error": str(error),

            "screening": {
                "risk_level": "UNKNOWN",
                "decision": "MANUAL_REVIEW"
            }
        }


    extraction_seconds = (
        time.perf_counter()
        -
        extraction_start
    )


    document_type = extraction.get(
        "document_type",
        "generic"
    )


    fields = extraction.get(
        "fields",
        {}
    )


    if not isinstance(
        fields,
        dict
    ):
        fields = {}


    raw_text = extraction.get(
        "raw_text",
        ""
    )


    # ========================================================
    # VALIDATION
    # ========================================================

    validation_start = time.perf_counter()


    validation = run_validation(
        document_type,
        fields,
        raw_text
    )


    validation_seconds = (
        time.perf_counter()
        -
        validation_start
    )


    # ========================================================
    # TAMPERING ANALYSIS
    # ========================================================

    tampering_start = time.perf_counter()


    tampering = run_tampering(
        document_path
    )


    tampering_seconds = (
        time.perf_counter()
        -
        tampering_start
    )


    # ========================================================
    # FACE VERIFICATION
    # ========================================================

    face_start = time.perf_counter()


    face = run_face_verification(
        document_path,
        selfie_path,
        document_type
    )


    face_seconds = (
        time.perf_counter()
        -
        face_start
    )


    # ========================================================
    # FINAL RISK ENGINE
    # ========================================================

    risk_start = time.perf_counter()


    screening = calculate_final_risk(
        extraction,
        validation,
        tampering,
        face,
        bool(selfie_path)
    )


    risk_seconds = (
        time.perf_counter()
        -
        risk_start
    )


    total_seconds = (
        time.perf_counter()
        -
        total_start
    )


    # ========================================================
    # FINAL REPORT
    # ========================================================

    return {
        "success": True,


        "system": {
            "name": (
                "AI-Based Fake Identity "
                "& Document Screening System"
            ),

            "problem_statement": "SIH-188",

            "processed_at": (
                datetime.now().isoformat(
                    timespec="seconds"
                )
            )
        },


        "input": {
            "document": get_file_info(
                document_path
            ),

            "selfie_provided": bool(
                selfie_path
            )
        },


        "document": {
            "type": document_type,

            "type_confidence": round(
                safe_float(
                    extraction.get(
                        "document_type_confidence",
                        0
                    )
                ),
                4
            )
        },


        "ocr": {
            "confidence": round(
                safe_float(
                    extraction.get(
                        "ocr_confidence",
                        0
                    )
                ),
                4
            ),

            "variant": extraction.get(
                "ocr_variant",
                "unknown"
            ),

            "line_count": extraction.get(
                "ocr_line_count"
            )
        },


        "fields": fields,


        "validation": validation,


        "tampering_detection": (
            compact_tampering(
                tampering
            )
        ),


        "face_verification": (
            compact_face(
                face
            )
        ),


        "screening": screening,


        "timings": {
            "extraction_seconds": round(
                extraction_seconds,
                3
            ),

            "validation_seconds": round(
                validation_seconds,
                3
            ),

            "tampering_seconds": round(
                tampering_seconds,
                3
            ),

            "face_verification_seconds": round(
                face_seconds,
                3
            ),

            "risk_engine_seconds": round(
                risk_seconds,
                6
            ),

            "total_seconds": round(
                total_seconds,
                3
            )
        }
    }


# ============================================================
# HELP
# ============================================================

def print_help():

    print()
    print(
        "=============================================="
    )
    print(
        " SIH-188 Document Screening System"
    )
    print(
        "=============================================="
    )
    print()

    print(
        "Document only:"
    )

    print(
        "python main.py images/document.jpg"
    )

    print()

    print(
        "Document + selfie:"
    )

    print(
        "python main.py images/document.jpg images/selfy.jpg"
    )

    print()


# ============================================================
# COMMAND-LINE ENTRY
# ============================================================

def main():

    if len(sys.argv) < 2:

        print_help()

        return


    if len(sys.argv) > 3:

        print_help()

        return


    document_path = sys.argv[1]


    selfie_path = (
        sys.argv[2]
        if len(sys.argv) == 3
        else None
    )


    try:

        result = screen_document(
            document_path,
            selfie_path
        )


        print(
            json.dumps(
                result,
                indent=4,
                ensure_ascii=False
            )
        )


    except KeyboardInterrupt:

        print(
            json.dumps(
                {
                    "success": False,
                    "error": (
                        "Processing cancelled by user."
                    )
                },
                indent=4
            )
        )


    except Exception as error:

        print(
            json.dumps(
                {
                    "success": False,

                    "stage": "unexpected_error",

                    "error": str(error),

                    "screening": {
                        "risk_level": "UNKNOWN",
                        "decision": "MANUAL_REVIEW"
                    }
                },
                indent=4
            )
        )


# ============================================================
# SINGLE ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()