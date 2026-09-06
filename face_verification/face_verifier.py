import json
import math
import os
import sys

import numpy as np

from face_detector import get_primary_face_embedding


# ============================================================
# CONFIGURATION
# ============================================================

MATCH_THRESHOLD = 0.45
REVIEW_THRESHOLD = 0.30


# ============================================================
# HELPERS
# ============================================================

def cosine_similarity(vector_a, vector_b):
    """
    Compare two normalized face embeddings.
    Returns similarity from roughly -1 to 1.
    Higher means more similar.
    """

    a = np.asarray(
        vector_a,
        dtype=np.float32
    )

    b = np.asarray(
        vector_b,
        dtype=np.float32
    )

    if a.shape != b.shape:
        raise ValueError(
            "Face embeddings have different dimensions."
        )

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        raise ValueError(
            "Invalid zero-length face embedding."
        )

    similarity = np.dot(a, b) / (
        norm_a * norm_b
    )

    return float(similarity)


def similarity_to_percentage(similarity):
    """
    Convert cosine similarity into a simple 0-100 display score.
    This is for presentation only.
    """

    value = (
        similarity + 1.0
    ) / 2.0

    value = max(
        0.0,
        min(
            1.0,
            value
        )
    )

    return round(
        value * 100,
        2
    )


# ============================================================
# MAIN VERIFICATION FUNCTION
# ============================================================

def verify_faces(
    document_image_path,
    selfie_image_path
):
    """
    Compare the primary face from a document
    against the primary face from a selfie/photo.
    """

    if not os.path.isfile(
        document_image_path
    ):
        return {
            "status": "ERROR",
            "decision": "MANUAL_REVIEW",
            "match": None,
            "similarity": None,
            "similarity_percentage": None,
            "message": "Document image not found."
        }

    if not os.path.isfile(
        selfie_image_path
    ):
        return {
            "status": "ERROR",
            "decision": "MANUAL_REVIEW",
            "match": None,
            "similarity": None,
            "similarity_percentage": None,
            "message": "Selfie image not found."
        }

    document_result = (
        get_primary_face_embedding(
            document_image_path
        )
    )

    selfie_result = (
        get_primary_face_embedding(
            selfie_image_path
        )
    )

    if not document_result.get(
        "success"
    ):
        return {
            "status": document_result.get(
                "status",
                "ERROR"
            ),
            "decision": "MANUAL_REVIEW",
            "match": None,
            "similarity": None,
            "similarity_percentage": None,
            "message": (
                "Could not obtain a usable face "
                "from the document image."
            ),
            "document_face": document_result,
            "selfie_face": selfie_result
        }

    if not selfie_result.get(
        "success"
    ):
        return {
            "status": selfie_result.get(
                "status",
                "ERROR"
            ),
            "decision": "MANUAL_REVIEW",
            "match": None,
            "similarity": None,
            "similarity_percentage": None,
            "message": (
                "Could not obtain a usable face "
                "from the selfie image."
            ),
            "document_face": document_result,
            "selfie_face": selfie_result
        }

    try:
        similarity = cosine_similarity(
            document_result["embedding"],
            selfie_result["embedding"]
        )

    except Exception as error:
        return {
            "status": "ERROR",
            "decision": "MANUAL_REVIEW",
            "match": None,
            "similarity": None,
            "similarity_percentage": None,
            "message": str(error),
            "document_face": document_result,
            "selfie_face": selfie_result
        }

    similarity = round(
        similarity,
        4
    )

    percentage = (
        similarity_to_percentage(
            similarity
        )
    )

    if similarity >= MATCH_THRESHOLD:
        status = "MATCH"
        decision = "FACE_MATCH"
        match = True
        risk_level = "LOW"

    elif similarity >= REVIEW_THRESHOLD:
        status = "REVIEW"
        decision = "MANUAL_REVIEW"
        match = None
        risk_level = "MEDIUM"

    else:
        status = "NO_MATCH"
        decision = "FACE_MISMATCH"
        match = False
        risk_level = "HIGH"

    return {
        "status": status,
        "decision": decision,
        "match": match,
        "risk_level": risk_level,
        "similarity": similarity,
        "similarity_percentage": percentage,
        "thresholds": {
            "match_threshold": MATCH_THRESHOLD,
            "review_threshold": REVIEW_THRESHOLD
        },
        "message": (
            "Face comparison completed successfully."
        ),
        "document_face": {
            "status": document_result.get(
                "status"
            ),
            "quality": (
                document_result
                .get(
                    "face",
                    {}
                )
                .get(
                    "quality"
                )
            )
        },
        "selfie_face": {
            "status": selfie_result.get(
                "status"
            ),
            "quality": (
                selfie_result
                .get(
                    "face",
                    {}
                )
                .get(
                    "quality"
                )
            )
        }
    }


# ============================================================
# LOCAL TEST
# ============================================================

if __name__ == "__main__":

    if len(sys.argv) < 3:
        print(
            "Please provide document image "
            "and selfie image."
        )

        print()

        print(
            "Example:"
        )

        print(
            "python face_verification/face_verifier.py "
            "images/document.jpg "
            "images/selfie.jpg"
        )

    else:
        document_image = sys.argv[1]
        selfie_image = sys.argv[2]

        result = verify_faces(
            document_image,
            selfie_image
        )

        print(
            json.dumps(
                result,
                indent=4,
                ensure_ascii=False
            )
        )