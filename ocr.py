
# ============================================================
# ocr.py
#
# Generic OCR module for SIH-188
#
# Returns:
# - complete OCR text
# - average OCR confidence
# - detected text items
# - bounding-box coordinates
# - preprocessing variant used
# - line count
#
# Works for:
# Passport
# Visa
# National ID
# Driving Licence
# Residence Permit
# Travel Permit
# etc.
# ============================================================

from paddleocr import PaddleOCR

from preprocessing import (
    get_original_image,
    get_fallback_image
)


# ============================================================
# OCR ENGINE
# ============================================================

ocr_engine = PaddleOCR(

    lang="en",

    # --------------------------------------------------------
    # Windows workaround
    # Keep this because your system required it
    # --------------------------------------------------------
    enable_mkldnn=False,

    # --------------------------------------------------------
    # Lightweight PP-OCRv5 models
    # --------------------------------------------------------
    text_detection_model_name="PP-OCRv5_mobile_det",

    text_recognition_model_name="PP-OCRv5_mobile_rec",

    # --------------------------------------------------------
    # Speed optimization
    # --------------------------------------------------------
    use_doc_orientation_classify=False,

    use_doc_unwarping=False,

    use_textline_orientation=False
)


# ============================================================
# SAFE CONVERSION
# ============================================================

def safe_to_list(value):
    """
    Converts NumPy/Paddle values into normal Python lists.
    """

    if value is None:
        return None

    try:
        return value.tolist()

    except AttributeError:
        return value


# ============================================================
# NORMALIZE BOX
# ============================================================

def normalize_box(box):
    """
    Converts OCR polygon/box into:

    [
        [x1, y1],
        [x2, y2],
        [x3, y3],
        [x4, y4]
    ]

    Returns None if no usable box exists.
    """

    if box is None:
        return None

    box = safe_to_list(
        box
    )

    if not isinstance(
        box,
        (list, tuple)
    ):
        return None

    normalized = []

    try:

        for point in box:

            if (
                isinstance(
                    point,
                    (list, tuple)
                )
                and len(point) >= 2
            ):

                normalized.append(
                    [
                        float(point[0]),
                        float(point[1])
                    ]
                )

        if normalized:
            return normalized

    except Exception:
        return None

    return None


# ============================================================
# BOX CENTER
# ============================================================

def get_box_center(box):
    """
    Returns the center point of a box.

    Useful later for matching labels to values.
    """

    if not box:
        return None, None

    try:

        xs = [
            point[0]
            for point in box
        ]

        ys = [
            point[1]
            for point in box
        ]

        center_x = sum(xs) / len(xs)
        center_y = sum(ys) / len(ys)

        return center_x, center_y

    except Exception:

        return None, None


# ============================================================
# BOX BOUNDS
# ============================================================

def get_box_bounds(box):
    """
    Returns:
        left, top, right, bottom
    """

    if not box:
        return None

    try:

        xs = [
            point[0]
            for point in box
        ]

        ys = [
            point[1]
            for point in box
        ]

        return {
            "left": min(xs),
            "top": min(ys),
            "right": max(xs),
            "bottom": max(ys)
        }

    except Exception:
        return None


# ============================================================
# GET VALUE FROM OCR PAGE
# ============================================================

def get_page_value(
    page,
    key,
    default=None
):
    """
    PaddleOCR result objects can behave slightly differently
    between versions.

    This helper safely tries dictionary-style access.
    """

    try:

        value = page.get(
            key,
            default
        )

        return value

    except Exception:
        pass

    try:

        value = page[key]

        return value

    except Exception:
        return default


# ============================================================
# RUN OCR ON ONE IMAGE
# ============================================================

def run_ocr_on_image(image):
    """
    Runs PaddleOCR once.

    Returns:

    {
        "text": "...",
        "confidence": 0.91,
        "items": [...],
        "line_count": ...
    }
    """

    result = ocr_engine.predict(
        image
    )

    all_texts = []
    all_scores = []
    all_items = []


    # ========================================================
    # PROCESS EACH PAGE
    # ========================================================

    for page in result:

        # ----------------------------------------------------
        # OCR recognized text
        # ----------------------------------------------------

        page_texts = get_page_value(
            page,
            "rec_texts",
            []
        )

        page_scores = get_page_value(
            page,
            "rec_scores",
            []
        )


        # ----------------------------------------------------
        # OCR boxes
        #
        # PaddleOCR versions may provide rec_polys,
        # dt_polys or rec_boxes.
        # ----------------------------------------------------

        page_boxes = get_page_value(
            page,
            "rec_polys",
            None
        )

        if page_boxes is None:

            page_boxes = get_page_value(
                page,
                "dt_polys",
                None
            )

        if page_boxes is None:

            page_boxes = get_page_value(
                page,
                "rec_boxes",
                []
            )


        # ----------------------------------------------------
        # Convert Paddle / NumPy objects
        # ----------------------------------------------------

        page_texts = (
            safe_to_list(
                page_texts
            )
            or []
        )

        page_scores = (
            safe_to_list(
                page_scores
            )
            or []
        )

        page_boxes = (
            safe_to_list(
                page_boxes
            )
            or []
        )


        # ====================================================
        # LOOP THROUGH OCR TEXTS
        # ====================================================

        for index, raw_text in enumerate(
            page_texts
        ):

            text = str(
                raw_text
            ).strip()

            if not text:
                continue


            # ------------------------------------------------
            # Confidence
            # ------------------------------------------------

            confidence = None

            if index < len(
                page_scores
            ):

                try:

                    confidence = float(
                        page_scores[index]
                    )

                    all_scores.append(
                        confidence
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    confidence = None


            # ------------------------------------------------
            # Bounding box
            # ------------------------------------------------

            box = None

            if index < len(
                page_boxes
            ):

                box = normalize_box(
                    page_boxes[index]
                )


            # ------------------------------------------------
            # Geometry
            # ------------------------------------------------

            center_x = None
            center_y = None
            bounds = None

            if box:

                center_x, center_y = (
                    get_box_center(
                        box
                    )
                )

                bounds = get_box_bounds(
                    box
                )


            # ------------------------------------------------
            # Add regular OCR text
            # ------------------------------------------------

            all_texts.append(
                text
            )


            # ------------------------------------------------
            # Add spatial OCR item
            # ------------------------------------------------

            item = {

                "text":
                    text,

                "confidence":
                    (
                        round(
                            confidence,
                            4
                        )
                        if confidence
                        is not None
                        else None
                    ),

                "box":
                    box,

                "center":
                    {
                        "x":
                            center_x,

                        "y":
                            center_y
                    },

                "bounds":
                    bounds
            }

            all_items.append(
                item
            )


    # ========================================================
    # COMPLETE PLAIN TEXT
    #
    # Keep OCR's original order here so your existing
    # passport / visa / national-ID extractors are not broken.
    # ========================================================

    complete_text = "\n".join(
        all_texts
    )


    # ========================================================
    # AVERAGE OCR CONFIDENCE
    # ========================================================

    if all_scores:

        average_confidence = (
            sum(all_scores)
            /
            len(all_scores)
        )

    else:

        average_confidence = 0.0


    average_confidence = round(
        average_confidence,
        3
    )


    # ========================================================
    # RESULT
    # ========================================================

    return {

        "text":
            complete_text,

        "confidence":
            average_confidence,

        "items":
            all_items,

        "line_count":
            len(all_items)
    }


# ============================================================
# CHECK WHETHER OCR RESULT IS USABLE
# ============================================================

def is_usable_result(result):
    """
    Decide whether OCR on the original image is good enough.

    If yes, don't waste time running OCR again.
    """

    if not isinstance(
        result,
        dict
    ):
        return False


    text = result.get(
        "text",
        ""
    )

    confidence = result.get(
        "confidence",
        0.0
    )

    line_count = result.get(
        "line_count",
        0
    )


    if not text.strip():
        return False


    if line_count < 2:
        return False


    # Keep the threshold you were already using.
    if confidence < 0.60:
        return False


    return True


# ============================================================
# CHOOSE BETTER OCR RESULT
# ============================================================

def choose_better_result(
    original_result,
    fallback_result
):
    """
    Used only when fallback OCR was necessary.
    """

    original_confidence = (
        original_result.get(
            "confidence",
            0.0
        )
    )

    fallback_confidence = (
        fallback_result.get(
            "confidence",
            0.0
        )
    )


    original_lines = (
        original_result.get(
            "line_count",
            0
        )
    )

    fallback_lines = (
        fallback_result.get(
            "line_count",
            0
        )
    )


    # --------------------------------------------------------
    # Primary decision: confidence
    # --------------------------------------------------------

    if (
        fallback_confidence
        >
        original_confidence + 0.03
    ):

        return fallback_result


    # --------------------------------------------------------
    # Secondary decision:
    # similar confidence but fallback found much more text
    # --------------------------------------------------------

    if (
        fallback_confidence
        >=
        original_confidence - 0.03
        and
        fallback_lines
        >
        original_lines * 1.25
    ):

        return fallback_result


    return original_result


# ============================================================
# MAIN OCR FUNCTION
# ============================================================

def extract_text(image_path):
    """
    Main function used by main.py.

    Returns:

    {
        "text": "...",
        "confidence": 0.91,
        "variant": "original",
        "line_count": 20,
        "items": [...]
    }
    """


    # ========================================================
    # STEP 1
    # TRY ORIGINAL IMAGE
    # ========================================================

    try:

        original_image = (
            get_original_image(
                image_path
            )
        )


        original_result = (
            run_ocr_on_image(
                original_image
            )
        )


        original_result[
            "variant"
        ] = "original"


    except Exception as error:

        print(
            f"OCR failed for original image: {error}"
        )

        original_result = {

            "text":
                "",

            "confidence":
                0.0,

            "variant":
                "original",

            "line_count":
                0,

            "items":
                []
        }


    # ========================================================
    # STEP 2
    # IF ORIGINAL IS GOOD, RETURN IT
    #
    # Avoid second OCR run.
    # ========================================================

    if is_usable_result(
        original_result
    ):

        return original_result


    # ========================================================
    # STEP 3
    # FALLBACK PREPROCESSING
    # ========================================================

    try:

        fallback_image = (
            get_fallback_image(
                image_path
            )
        )


        fallback_result = (
            run_ocr_on_image(
                fallback_image
            )
        )


        fallback_result[
            "variant"
        ] = "fallback"


    except Exception as error:

        print(
            f"OCR failed for fallback image: {error}"
        )

        fallback_result = {

            "text":
                "",

            "confidence":
                0.0,

            "variant":
                "fallback",

            "line_count":
                0,

            "items":
                []
        }


    # ========================================================
    # STEP 4
    # PICK BEST OCR RESULT
    # ========================================================

    best_result = choose_better_result(
        original_result,
        fallback_result
    )


    return best_result


# ============================================================
# OPTIONAL LOCAL TEST
# ============================================================

if __name__ == "__main__":

    import sys
    import json


    if len(sys.argv) < 2:

        print(
            "Usage:"
        )

        print(
            "python ocr.py images/document.jpg"
        )

    else:

        image_path = sys.argv[1]

        result = extract_text(
            image_path
        )

        print(
            json.dumps(
                result,
                indent=4,
                ensure_ascii=False
            )
        )