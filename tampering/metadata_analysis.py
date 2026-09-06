import os
from PIL import Image, ExifTags


def analyze_metadata(image_path):
    """
    Analyze basic image metadata for possible signs of editing.

    Important:
    Metadata alone cannot prove that a document is fake.
    It only provides suspicious signals.
    """

    result = {
        "status": "OK",
        "suspicious": False,
        "risk_score": 0,
        "reasons": [],
        "metadata": {}
    }

    # Check file exists
    if not os.path.exists(image_path):
        return {
            "status": "ERROR",
            "suspicious": False,
            "risk_score": 0,
            "reasons": ["Image file not found"],
            "metadata": {}
        }

    try:
        with Image.open(image_path) as image:

            # Basic information
            result["metadata"]["format"] = image.format
            result["metadata"]["width"] = image.width
            result["metadata"]["height"] = image.height
            result["metadata"]["mode"] = image.mode

            # Read EXIF
            exif_data = image.getexif()

            readable_exif = {}

            if exif_data:
                for tag_id, value in exif_data.items():

                    tag_name = ExifTags.TAGS.get(
                        tag_id,
                        str(tag_id)
                    )

                    # Convert to string so JSON serialization is safe
                    readable_exif[tag_name] = str(value)

            result["metadata"]["exif"] = readable_exif

            # -----------------------------------------
            # Check software information
            # -----------------------------------------

            software = readable_exif.get(
                "Software",
                ""
            )

            if software:

                software_lower = software.lower()

                editing_keywords = [
                    "photoshop",
                    "gimp",
                    "lightroom",
                    "snapseed",
                    "canva"
                ]

                for keyword in editing_keywords:

                    if keyword in software_lower:

                        result["suspicious"] = True
                        result["risk_score"] += 25

                        result["reasons"].append(
                            f"Image metadata mentions editing software: {software}"
                        )

                        break

            # -----------------------------------------
            # No EXIF information
            # -----------------------------------------

            if not readable_exif:

                # Missing EXIF is common for downloaded,
                # scanned, compressed or converted images.
                # Therefore it is only a weak signal.

                result["reasons"].append(
                    "No EXIF metadata found"
                )

            # -----------------------------------------
            # Final status
            # -----------------------------------------

            result["risk_score"] = min(
                result["risk_score"],
                100
            )

            if result["risk_score"] >= 50:

                result["status"] = "SUSPICIOUS"

            elif result["risk_score"] > 0:

                result["status"] = "REVIEW"

            else:

                result["status"] = "OK"

            return result

    except Exception as error:

        return {
            "status": "ERROR",
            "suspicious": False,
            "risk_score": 0,
            "reasons": [
                f"Metadata analysis failed: {str(error)}"
            ],
            "metadata": {}
        }


# ------------------------------------------------------------
# Standalone testing
# ------------------------------------------------------------

if __name__ == "__main__":

    import sys
    import json

    if len(sys.argv) < 2:

        print("Please provide an image path.")
        print(
            "Example: python tampering/metadata_analysis.py "
            "images/Indianpassportbiopage2025.jpg"
        )

    else:

        image_path = sys.argv[1]

        result = analyze_metadata(
            image_path
        )

        print(
            json.dumps(
                result,
                indent=4,
                ensure_ascii=False
            )
        )