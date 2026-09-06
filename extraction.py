import time

from ocr import extract_text

from document_detector import (
    detect_document_type
)

from extractors.passport import (
    extract_passport
)

from extractors.visa import (
    extract_visa
)

from extractors.national_id import (
    extract_national_id
)

from extractors.driving_licence import (
    extract_driving_licence
)

from extractors.residence_permit import (
    extract_residence_permit
)

from extractors.travel_permit import (
    extract_travel_permit
)

from extractors.generic import (
    extract_generic
)


EXTRACTORS = {

    "passport":
        extract_passport,

    "visa":
        extract_visa,

    "national_id":
        extract_national_id,

    "driving_licence":
        extract_driving_licence,

    "residence_permit":
        extract_residence_permit,

    "travel_permit":
        extract_travel_permit,

    "generic":
        extract_generic
}


def extract_document(image_path):

    total_start = time.perf_counter()

    # ---------------------------------
    # 1. OCR timing
    # ---------------------------------

    ocr_start = time.perf_counter()

    ocr_result = extract_text(
        image_path
    )

    ocr_time = (
        time.perf_counter()
        - ocr_start
    )

    text = ocr_result["text"]

    # ---------------------------------
    # 2. Document detection timing
    # ---------------------------------

    detection_start = time.perf_counter()

    detection = detect_document_type(
        text
    )

    detection_time = (
        time.perf_counter()
        - detection_start
    )

    document_type = detection[
        "type"
    ]

    # ---------------------------------
    # 3. Select extractor
    # ---------------------------------

    extractor = EXTRACTORS.get(
        document_type,
        extract_generic
    )

    # ---------------------------------
    # 4. Field extraction timing
    # ---------------------------------

    field_start = time.perf_counter()

    items = ocr_result.get(
        "items",
        []
    )

    if document_type == "visa":

        fields = extractor(
            text,
            items
        )

    else:

        fields = extractor(
            text
        )

    field_time = (
        time.perf_counter()
        - field_start
    )

    # ---------------------------------
    # 5. Total extraction timing
    # ---------------------------------

    total_time = (
        time.perf_counter()
        - total_start
    )

    return {

        "document_type":
            document_type,

        "document_type_confidence":
            detection["confidence"],

        "ocr_confidence":
            ocr_result["confidence"],

        "ocr_variant":
            ocr_result["variant"],

        "fields":
            fields,

        "raw_text":
            text,

        "internal_timings": {

            "ocr_seconds":
                round(
                    ocr_time,
                    3
                ),

            "document_detection_seconds":
                round(
                    detection_time,
                    6
                ),

            "field_extraction_seconds":
                round(
                    field_time,
                    6
                ),

            "total_extraction_seconds":
                round(
                    total_time,
                    3
                )
        }
    }