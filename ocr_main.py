import sys
import json

from extraction import extract_document


def main():
    if len(sys.argv) != 2:
        print("Usage:")
        print("python ocr_main.py images/document.jpg")
        return

    image_path = sys.argv[1]

    result = extract_document(image_path)

    output = {
        "document_type": result.get("document_type"),
        "document_type_confidence": result.get(
            "document_type_confidence"
        ),
        "ocr_confidence": result.get(
            "ocr_confidence"
        ),
        "fields": result.get(
            "fields",
            {}
        )
    }

    print(
        json.dumps(
            output,
            indent=4,
            ensure_ascii=False
        )
    )


if __name__ == "__main__":
    main()