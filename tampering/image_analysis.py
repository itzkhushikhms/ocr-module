import os
import cv2
import math
import numpy as np
from PIL import Image, ImageChops, ImageEnhance


# ============================================================
# CONFIGURATION
# ============================================================

MIN_IMAGE_WIDTH = 150
MIN_IMAGE_HEIGHT = 150

ELA_JPEG_QUALITY = 90

EDGE_BLOCK_SIZE = 32
NOISE_BLOCK_SIZE = 32

LOW_VARIANCE_THRESHOLD = 8.0
HIGH_VARIANCE_THRESHOLD = 45.0

SUSPICIOUS_EDGE_RATIO_THRESHOLD = 0.18
SUSPICIOUS_NOISE_RATIO_THRESHOLD = 0.22

MAX_RISK_SCORE = 100


# ============================================================
# GENERIC HELPERS
# ============================================================

def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def file_exists(image_path):
    return isinstance(image_path, str) and os.path.isfile(image_path)


def load_cv_image(image_path):
    image = cv2.imread(image_path)

    if image is None:
        raise ValueError("Unable to read image.")

    return image


def validate_image_dimensions(image):
    height, width = image.shape[:2]

    if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
        raise ValueError(
            f"Image resolution too small for reliable analysis: "
            f"{width}x{height}"
        )

    return width, height


# ============================================================
# BLUR ANALYSIS
# ============================================================

def analyze_blur(image):
    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    laplacian = cv2.Laplacian(
        gray,
        cv2.CV_64F
    )

    variance = laplacian.var()

    if variance < 40:
        level = "HIGH_BLUR"
        score = 10

    elif variance < 80:
        level = "MODERATE_BLUR"
        score = 5

    else:
        level = "NORMAL"
        score = 0

    return {
        "laplacian_variance": round(float(variance), 3),
        "level": level,
        "risk_score": score
    }


# ============================================================
# EDGE CONSISTENCY ANALYSIS
# ============================================================

def analyze_edge_consistency(image):
    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    edges = cv2.Canny(
        gray,
        80,
        180
    )

    height, width = edges.shape

    block_scores = []

    for y in range(
        0,
        height,
        EDGE_BLOCK_SIZE
    ):

        for x in range(
            0,
            width,
            EDGE_BLOCK_SIZE
        ):

            block = edges[
                y:min(
                    y + EDGE_BLOCK_SIZE,
                    height
                ),
                x:min(
                    x + EDGE_BLOCK_SIZE,
                    width
                )
            ]

            if block.size == 0:
                continue

            density = np.count_nonzero(
                block
            ) / block.size

            block_scores.append(
                float(density)
            )

    if not block_scores:
        return {
            "mean_edge_density": 0.0,
            "std_edge_density": 0.0,
            "suspicious_ratio": 0.0,
            "risk_score": 0
        }

    mean_density = np.mean(
        block_scores
    )

    std_density = np.std(
        block_scores
    )

    suspicious_count = 0

    for value in block_scores:

        if value > (
            mean_density
            +
            2.5 * std_density
        ):
            suspicious_count += 1

    suspicious_ratio = (
        suspicious_count
        /
        len(block_scores)
    )

    risk_score = 0

    if suspicious_ratio > 0.30:
        risk_score = 20

    elif suspicious_ratio > SUSPICIOUS_EDGE_RATIO_THRESHOLD:
        risk_score = 12

    elif suspicious_ratio > 0.10:
        risk_score = 5

    return {
        "mean_edge_density": round(
            float(mean_density),
            5
        ),
        "std_edge_density": round(
            float(std_density),
            5
        ),
        "suspicious_ratio": round(
            float(suspicious_ratio),
            5
        ),
        "risk_score": risk_score
    }


# ============================================================
# NOISE CONSISTENCY ANALYSIS
# ============================================================

def analyze_noise_consistency(image):
    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    blurred = cv2.GaussianBlur(
        gray,
        (5, 5),
        0
    )

    noise = cv2.absdiff(
        gray,
        blurred
    )

    height, width = noise.shape

    variances = []

    for y in range(
        0,
        height,
        NOISE_BLOCK_SIZE
    ):

        for x in range(
            0,
            width,
            NOISE_BLOCK_SIZE
        ):

            block = noise[
                y:min(
                    y + NOISE_BLOCK_SIZE,
                    height
                ),
                x:min(
                    x + NOISE_BLOCK_SIZE,
                    width
                )
            ]

            if block.size == 0:
                continue

            variance = np.var(
                block
            )

            variances.append(
                float(variance)
            )

    if not variances:
        return {
            "mean_noise_variance": 0.0,
            "std_noise_variance": 0.0,
            "suspicious_ratio": 0.0,
            "risk_score": 0
        }

    mean_variance = np.mean(
        variances
    )

    std_variance = np.std(
        variances
    )

    suspicious = 0

    for value in variances:

        too_low = (
            value
            <
            max(
                LOW_VARIANCE_THRESHOLD,
                mean_variance
                -
                2.0 * std_variance
            )
        )

        too_high = (
            value
            >
            max(
                HIGH_VARIANCE_THRESHOLD,
                mean_variance
                +
                2.5 * std_variance
            )
        )

        if too_low or too_high:
            suspicious += 1

    suspicious_ratio = (
        suspicious
        /
        len(variances)
    )

    risk_score = 0

    if suspicious_ratio > 0.35:
        risk_score = 20

    elif suspicious_ratio > SUSPICIOUS_NOISE_RATIO_THRESHOLD:
        risk_score = 12

    elif suspicious_ratio > 0.12:
        risk_score = 5

    return {
        "mean_noise_variance": round(
            float(mean_variance),
            4
        ),
        "std_noise_variance": round(
            float(std_variance),
            4
        ),
        "suspicious_ratio": round(
            float(suspicious_ratio),
            5
        ),
        "risk_score": risk_score
    }


# ============================================================
# COMPRESSION GRID ANALYSIS
# ============================================================

def analyze_jpeg_blocking(image):
    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    ).astype(
        np.float32
    )

    height, width = gray.shape

    vertical_diffs = []
    horizontal_diffs = []

    for x in range(
        8,
        width,
        8
    ):
        diff = np.mean(
            np.abs(
                gray[:, x]
                -
                gray[:, x - 1]
            )
        )

        vertical_diffs.append(
            diff
        )

    for y in range(
        8,
        height,
        8
    ):
        diff = np.mean(
            np.abs(
                gray[y, :]
                -
                gray[y - 1, :]
            )
        )

        horizontal_diffs.append(
            diff
        )

    if not vertical_diffs:
        vertical_mean = 0.0
    else:
        vertical_mean = float(
            np.mean(
                vertical_diffs
            )
        )

    if not horizontal_diffs:
        horizontal_mean = 0.0
    else:
        horizontal_mean = float(
            np.mean(
                horizontal_diffs
            )
        )

    blocking_strength = (
        vertical_mean
        +
        horizontal_mean
    ) / 2.0

    risk_score = 0

    if blocking_strength > 30:
        risk_score = 15

    elif blocking_strength > 20:
        risk_score = 8

    elif blocking_strength > 14:
        risk_score = 3

    return {
        "vertical_block_strength": round(
            vertical_mean,
            3
        ),
        "horizontal_block_strength": round(
            horizontal_mean,
            3
        ),
        "blocking_strength": round(
            blocking_strength,
            3
        ),
        "risk_score": risk_score
    }


# ============================================================
# ERROR LEVEL ANALYSIS
# ============================================================

def analyze_ela(image_path):
    try:
        original = Image.open(
            image_path
        ).convert(
            "RGB"
        )

        import tempfile

        with tempfile.NamedTemporaryFile(
            suffix=".jpg",
            delete=False
        ) as temp_file:

            temp_path = temp_file.name

        try:
            original.save(
                temp_path,
                "JPEG",
                quality=ELA_JPEG_QUALITY
            )

            recompressed = Image.open(
                temp_path
            ).convert(
                "RGB"
            )

            difference = ImageChops.difference(
                original,
                recompressed
            )

            diff_array = np.asarray(
                difference
            ).astype(
                np.float32
            )

            mean_error = float(
                np.mean(
                    diff_array
                )
            )

            max_error = float(
                np.max(
                    diff_array
                )
            )

            std_error = float(
                np.std(
                    diff_array
                )
            )

            high_error_ratio = float(
                np.mean(
                    diff_array > 25
                )
            )

            risk_score = 0

            if high_error_ratio > 0.15:
                risk_score = 20

            elif high_error_ratio > 0.08:
                risk_score = 12

            elif high_error_ratio > 0.04:
                risk_score = 5

            return {
                "mean_error": round(
                    mean_error,
                    3
                ),
                "max_error": round(
                    max_error,
                    3
                ),
                "std_error": round(
                    std_error,
                    3
                ),
                "high_error_ratio": round(
                    high_error_ratio,
                    5
                ),
                "risk_score": risk_score
            }

        finally:
            if os.path.exists(
                temp_path
            ):
                os.remove(
                    temp_path
                )

    except Exception as error:
        return {
            "mean_error": 0.0,
            "max_error": 0.0,
            "std_error": 0.0,
            "high_error_ratio": 0.0,
            "risk_score": 0,
            "error": str(error)
        }


# ============================================================
# COPY-MOVE STYLE DUPLICATE REGION ANALYSIS
# ============================================================

def analyze_duplicate_regions(image):
    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    detector = cv2.ORB_create(
        nfeatures=1500
    )

    keypoints, descriptors = detector.detectAndCompute(
        gray,
        None
    )

    if descriptors is None or len(keypoints) < 10:
        return {
            "keypoints": len(
                keypoints
            ) if keypoints else 0,
            "duplicate_matches": 0,
            "risk_score": 0
        }

    matcher = cv2.BFMatcher(
        cv2.NORM_HAMMING,
        crossCheck=True
    )

    matches = matcher.match(
        descriptors,
        descriptors
    )

    duplicate_matches = 0

    for match in matches:

        if match.queryIdx == match.trainIdx:
            continue

        point1 = keypoints[
            match.queryIdx
        ].pt

        point2 = keypoints[
            match.trainIdx
        ].pt

        distance = math.dist(
            point1,
            point2
        )

        if (
            match.distance < 25
            and distance > 40
        ):
            duplicate_matches += 1

    risk_score = 0

    if duplicate_matches > 25:
        risk_score = 20

    elif duplicate_matches > 12:
        risk_score = 12

    elif duplicate_matches > 5:
        risk_score = 5

    return {
        "keypoints": len(
            keypoints
        ),
        "duplicate_matches": int(
            duplicate_matches
        ),
        "risk_score": risk_score
    }


# ============================================================
# COLOR INCONSISTENCY ANALYSIS
# ============================================================

def analyze_color_consistency(image):
    lab = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2LAB
    )

    l_channel, a_channel, b_channel = cv2.split(
        lab
    )

    a_std = float(
        np.std(
            a_channel
        )
    )

    b_std = float(
        np.std(
            b_channel
        )
    )

    chroma_std = (
        a_std
        +
        b_std
    ) / 2.0

    risk_score = 0

    if chroma_std > 45:
        risk_score = 10

    elif chroma_std > 35:
        risk_score = 5

    return {
        "a_channel_std": round(
            a_std,
            3
        ),
        "b_channel_std": round(
            b_std,
            3
        ),
        "chroma_std": round(
            chroma_std,
            3
        ),
        "risk_score": risk_score
    }


# ============================================================
# MAIN IMAGE ANALYSIS
# ============================================================

def analyze_image(image_path):
    result = {
        "status": "OK",
        "suspicious": False,
        "risk_score": 0,
        "risk_level": "LOW",
        "reasons": [],
        "checks": {}
    }

    if not file_exists(
        image_path
    ):
        return {
            "status": "ERROR",
            "suspicious": False,
            "risk_score": 0,
            "risk_level": "UNKNOWN",
            "reasons": [
                "Image file not found."
            ],
            "checks": {}
        }

    try:
        image = load_cv_image(
            image_path
        )

        width, height = validate_image_dimensions(
            image
        )

        result["image_info"] = {
            "width": width,
            "height": height
        }

        blur = analyze_blur(
            image
        )

        edge = analyze_edge_consistency(
            image
        )

        noise = analyze_noise_consistency(
            image
        )

        blocking = analyze_jpeg_blocking(
            image
        )

        ela = analyze_ela(
            image_path
        )

        duplicate = analyze_duplicate_regions(
            image
        )

        color = analyze_color_consistency(
            image
        )

        result["checks"] = {
            "blur": blur,
            "edge_consistency": edge,
            "noise_consistency": noise,
            "compression": blocking,
            "ela": ela,
            "duplicate_regions": duplicate,
            "color_consistency": color
        }

        total_score = (
            blur.get(
                "risk_score",
                0
            )
            +
            edge.get(
                "risk_score",
                0
            )
            +
            noise.get(
                "risk_score",
                0
            )
            +
            blocking.get(
                "risk_score",
                0
            )
            +
            ela.get(
                "risk_score",
                0
            )
            +
            duplicate.get(
                "risk_score",
                0
            )
            +
            color.get(
                "risk_score",
                0
            )
        )

        total_score = clamp(
            total_score,
            0,
            MAX_RISK_SCORE
        )

        result["risk_score"] = total_score

        if blur["risk_score"] > 0:
            result["reasons"].append(
                "Image quality is blurry or low-detail."
            )

        if edge["risk_score"] >= 12:
            result["reasons"].append(
                "Unusual edge-density inconsistency detected."
            )

        if noise["risk_score"] >= 12:
            result["reasons"].append(
                "Noise pattern varies unusually across the image."
            )

        if blocking["risk_score"] >= 8:
            result["reasons"].append(
                "Compression/blocking artifacts are unusually strong."
            )

        if ela.get(
            "risk_score",
            0
        ) >= 12:
            result["reasons"].append(
                "Error-level analysis found unusually inconsistent regions."
            )

        if duplicate["risk_score"] >= 12:
            result["reasons"].append(
                "Possible duplicated image regions detected."
            )

        if color["risk_score"] >= 10:
            result["reasons"].append(
                "Unusual color-distribution inconsistency detected."
            )

        if total_score >= 60:

            result["status"] = "SUSPICIOUS"
            result["suspicious"] = True
            result["risk_level"] = "HIGH"

        elif total_score >= 30:

            result["status"] = "REVIEW"
            result["suspicious"] = True
            result["risk_level"] = "MEDIUM"

        else:

            result["status"] = "OK"
            result["suspicious"] = False
            result["risk_level"] = "LOW"

        if not result["reasons"]:
            result["reasons"].append(
                "No strong image-level tampering indicators detected."
            )

        return result

    except Exception as error:

        return {
            "status": "ERROR",
            "suspicious": False,
            "risk_score": 0,
            "risk_level": "UNKNOWN",
            "reasons": [
                f"Image analysis failed: {str(error)}"
            ],
            "checks": {}
        }


# ============================================================
# LOCAL TEST
# ============================================================

if __name__ == "__main__":

    import sys
    import json

    if len(
        sys.argv
    ) < 2:

        print(
            "Please provide an image path."
        )

        print(
            "Example:"
        )

        print(
            "python tampering/image_analysis.py "
            "images/Visa-Card-Image.webp"
        )

    else:

        result = analyze_image(
            sys.argv[1]
        )

        print(
            json.dumps(
                result,
                indent=4,
                ensure_ascii=False
            )
        )
        