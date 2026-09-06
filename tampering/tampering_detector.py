import json
import os
import sys

from metadata_analysis import analyze_metadata
from image_analysis import analyze_image


def clamp(value, minimum=0, maximum=100):
    return max(minimum, min(maximum, value))


def detect_tampering(image_path):
    """
    Combine metadata analysis and image-level analysis.

    This does not prove REAL/FAKE.
    It gives a risk-based tampering assessment.
    """

    if not os.path.isfile(image_path):
        return {
            "status": "ERROR",
            "risk_score": 0,
            "risk_level": "UNKNOWN",
            "decision": "MANUAL_REVIEW",
            "suspicious": False,
            "reasons": ["Image file not found."],
            "metadata_analysis": {},
            "image_analysis": {}
        }

    metadata_result = analyze_metadata(image_path)
    image_result = analyze_image(image_path)

    metadata_score = metadata_result.get("risk_score", 0)
    image_score = image_result.get("risk_score", 0)

    # Image evidence is more important than metadata
    combined_score = (
        image_score * 0.8
        +
        metadata_score * 0.2
    )

    combined_score = round(
        clamp(combined_score),
        2
    )

    reasons = []

    for reason in metadata_result.get("reasons", []):
        if reason != "No EXIF metadata found":
            reasons.append(reason)

    for reason in image_result.get("reasons", []):
        if reason != "No strong image-level tampering indicators detected.":
            reasons.append(reason)

    if (
        metadata_result.get("status") == "ERROR"
        or image_result.get("status") == "ERROR"
    ):
        return {
            "status": "ERROR",
            "risk_score": combined_score,
            "risk_level": "UNKNOWN",
            "decision": "MANUAL_REVIEW",
            "suspicious": False,
            "reasons": reasons or [
                "One or more tampering checks could not be completed."
            ],
            "metadata_analysis": metadata_result,
            "image_analysis": image_result
        }

    if combined_score >= 60:
        status = "SUSPICIOUS"
        risk_level = "HIGH"
        decision = "MANUAL_REVIEW"
        suspicious = True

    elif combined_score >= 30:
        status = "REVIEW"
        risk_level = "MEDIUM"
        decision = "MANUAL_REVIEW"
        suspicious = True

    else:
        status = "OK"
        risk_level = "LOW"
        decision = "NO_STRONG_TAMPERING_INDICATORS"
        suspicious = False

    if not reasons:
        reasons.append(
            "No strong tampering indicators were detected by current checks."
        )

    return {
        "status": status,
        "risk_score": combined_score,
        "risk_level": risk_level,
        "decision": decision,
        "suspicious": suspicious,
        "reasons": reasons,
        "metadata_analysis": metadata_result,
        "image_analysis": image_result
    }


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Please provide an image path.")
        print()
        print(
            "Example: python tampering/tampering_detector.py "
            "images/Visa-Card-Image.webp"
        )

    else:
        result = detect_tampering(
            sys.argv[1]
        )

        print(
            json.dumps(
                result,
                indent=4,
                ensure_ascii=False
            )
        )