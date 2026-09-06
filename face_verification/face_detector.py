import json
import os
import sys

import cv2
import numpy as np

from insightface.app import FaceAnalysis


# ============================================================
# MODEL INITIALIZATION
# ============================================================

_FACE_APP = None


def get_face_app():
    """
    Load the InsightFace model only once.
    Uses CPUExecutionProvider so it works without GPU.
    """

    global _FACE_APP

    if _FACE_APP is None:
        _FACE_APP = FaceAnalysis(
            name="buffalo_l",
            providers=["CPUExecutionProvider"]
        )

        _FACE_APP.prepare(
            ctx_id=-1,
            det_size=(640, 640)
        )

    return _FACE_APP


# ============================================================
# HELPERS
# ============================================================

def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def safe_int(value, default=0):
    try:
        return int(round(float(value)))
    except Exception:
        return default


def load_image(image_path):
    """
    Load an image safely.
    """

    if not isinstance(image_path, str):
        raise ValueError("Image path must be a string.")

    if not os.path.isfile(image_path):
        raise FileNotFoundError(
            f"Image file not found: {image_path}"
        )

    image = cv2.imread(image_path)

    if image is None:
        raise ValueError(
            "The image could not be read."
        )

    return image


def normalize_embedding(embedding):
    """
    Convert face embedding into a normalized vector.
    """

    if embedding is None:
        return None

    vector = np.asarray(
        embedding,
        dtype=np.float32
    )

    norm = np.linalg.norm(vector)

    if norm <= 0:
        return None

    return vector / norm


def face_area(bbox):
    """
    Calculate face bounding-box area.
    """

    x1, y1, x2, y2 = bbox

    width = max(
        0,
        x2 - x1
    )

    height = max(
        0,
        y2 - y1
    )

    return width * height


# ============================================================
# CONVERT INSIGHTFACE RESULT
# ============================================================

def convert_face(face):
    bbox_raw = getattr(
        face,
        "bbox",
        None
    )

    if bbox_raw is None:
        return None

    bbox = [
        safe_int(bbox_raw[0]),
        safe_int(bbox_raw[1]),
        safe_int(bbox_raw[2]),
        safe_int(bbox_raw[3])
    ]

    detection_score = safe_float(
        getattr(
            face,
            "det_score",
            0.0
        )
    )

    embedding = getattr(
        face,
        "embedding",
        None
    )

    normalized_embedding = normalize_embedding(
        embedding
    )

    landmarks = getattr(
        face,
        "kps",
        None
    )

    landmark_values = []

    if landmarks is not None:
        try:
            for point in landmarks:
                landmark_values.append(
                    [
                        safe_float(point[0]),
                        safe_float(point[1])
                    ]
                )
        except Exception:
            landmark_values = []

    return {
        "bbox": {
            "left": bbox[0],
            "top": bbox[1],
            "right": bbox[2],
            "bottom": bbox[3]
        },
        "width": max(
            0,
            bbox[2] - bbox[0]
        ),
        "height": max(
            0,
            bbox[3] - bbox[1]
        ),
        "area": face_area(
            bbox
        ),
        "confidence": round(
            detection_score,
            4
        ),
        "landmarks": landmark_values,
        "embedding": (
            normalized_embedding.tolist()
            if normalized_embedding is not None
            else None
        )
    }


# ============================================================
# FACE QUALITY
# ============================================================

def calculate_face_quality(
    face_data,
    image_width,
    image_height
):
    """
    Basic quality assessment.

    This does NOT determine identity.
    It only checks whether the detected face
    is large/clear enough for comparison.
    """

    score = 100

    reasons = []

    face_width = face_data.get(
        "width",
        0
    )

    face_height = face_data.get(
        "height",
        0
    )

    confidence = face_data.get(
        "confidence",
        0
    )

    image_area = max(
        1,
        image_width * image_height
    )

    face_size_ratio = (
        face_data.get(
            "area",
            0
        )
        /
        image_area
    )

    if confidence < 0.5:
        score -= 40

        reasons.append(
            "Low face detection confidence."
        )

    elif confidence < 0.7:
        score -= 20

        reasons.append(
            "Moderate face detection confidence."
        )

    if face_width < 60 or face_height < 60:
        score -= 35

        reasons.append(
            "Detected face is very small."
        )

    elif face_width < 100 or face_height < 100:
        score -= 15

        reasons.append(
            "Detected face is relatively small."
        )

    if face_size_ratio < 0.005:
        score -= 25

        reasons.append(
            "Face occupies a very small part of the image."
        )

    score = max(
        0,
        min(
            100,
            score
        )
    )

    if score >= 75:
        level = "GOOD"

    elif score >= 50:
        level = "ACCEPTABLE"

    else:
        level = "POOR"

    return {
        "score": score,
        "level": level,
        "face_size_ratio": round(
            face_size_ratio,
            6
        ),
        "reasons": reasons
    }


# ============================================================
# MAIN FACE DETECTOR
# ============================================================

def detect_faces(image_path):
    """
    Detect faces in an image.

    Returns all detected faces and identifies
    the largest face as the primary face.
    """

    try:
        image = load_image(
            image_path
        )

        height, width = image.shape[:2]

        app = get_face_app()

        faces = app.get(
            image
        )

        converted_faces = []

        for face in faces:
            converted = convert_face(
                face
            )

            if converted is None:
                continue

            converted["quality"] = (
                calculate_face_quality(
                    converted,
                    width,
                    height
                )
            )

            converted_faces.append(
                converted
            )

        converted_faces.sort(
            key=lambda item: item.get(
                "area",
                0
            ),
            reverse=True
        )

        if len(converted_faces) == 0:
            return {
                "status": "NO_FACE",
                "face_count": 0,
                "image": {
                    "width": width,
                    "height": height
                },
                "primary_face": None,
                "faces": [],
                "message": "No face was detected."
            }

        primary_face = converted_faces[0]

        if len(converted_faces) == 1:
            status = "OK"
            message = "One face detected."

        else:
            status = "MULTIPLE_FACES"
            message = (
                f"{len(converted_faces)} faces detected. "
                "The largest face was selected as primary."
            )

        return {
            "status": status,
            "face_count": len(
                converted_faces
            ),
            "image": {
                "width": width,
                "height": height
            },
            "primary_face": primary_face,
            "faces": converted_faces,
            "message": message
        }

    except Exception as error:
        return {
            "status": "ERROR",
            "face_count": 0,
            "primary_face": None,
            "faces": [],
            "message": str(error)
        }


# ============================================================
# GET PRIMARY FACE EMBEDDING
# ============================================================

def get_primary_face_embedding(
    image_path
):
    """
    Convenience function for face_verifier.py.
    """

    result = detect_faces(
        image_path
    )

    if result.get(
        "status"
    ) not in {
        "OK",
        "MULTIPLE_FACES"
    }:
        return {
            "success": False,
            "status": result.get(
                "status",
                "ERROR"
            ),
            "embedding": None,
            "face": None,
            "message": result.get(
                "message",
                ""
            )
        }

    primary_face = result.get(
        "primary_face"
    )

    if not primary_face:
        return {
            "success": False,
            "status": "NO_FACE",
            "embedding": None,
            "face": None,
            "message": "No primary face available."
        }

    embedding = primary_face.get(
        "embedding"
    )

    if not embedding:
        return {
            "success": False,
            "status": "NO_EMBEDDING",
            "embedding": None,
            "face": primary_face,
            "message": "Face embedding could not be generated."
        }

    return {
        "success": True,
        "status": "OK",
        "embedding": embedding,
        "face": primary_face,
        "message": "Face embedding generated successfully."
    }


# ============================================================
# LOCAL TEST
# ============================================================

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print(
            "Please provide an image path."
        )

        print()

        print(
            "Example:"
        )

        print(
            "python face_verification/face_detector.py "
            "images/test_face.jpg"
        )

    else:
        result = detect_faces(
            sys.argv[1]
        )

        # Avoid printing the huge embedding
        # during normal terminal testing.

        printable = dict(
            result
        )

        if printable.get(
            "primary_face"
        ):
            primary = dict(
                printable["primary_face"]
            )

            if primary.get(
                "embedding"
            ) is not None:
                primary["embedding"] = (
                    f"<{len(primary['embedding'])}-dimensional embedding>"
                )

            printable["primary_face"] = primary

        printable_faces = []

        for face in printable.get(
            "faces",
            []
        ):
            face_copy = dict(
                face
            )

            if face_copy.get(
                "embedding"
            ) is not None:
                face_copy["embedding"] = (
                    f"<{len(face_copy['embedding'])}-dimensional embedding>"
                )

            printable_faces.append(
                face_copy
            )

        printable["faces"] = (
            printable_faces
        )

        print(
            json.dumps(
                printable,
                indent=4,
                ensure_ascii=False
            )
        )
        