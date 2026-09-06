
import cv2
import numpy as np


def load_image(image_path):
    image = cv2.imread(image_path)

    if image is None:
        raise ValueError(
            f"Unable to read image: {image_path}"
        )

    return image


def resize_image(image, max_width=1600):
    height, width = image.shape[:2]

    if width <= max_width:
        return image

    scale = max_width / width

    resized = cv2.resize(
        image,
        None,
        fx=scale,
        fy=scale,
        interpolation=cv2.INTER_AREA
    )

    return resized


def get_original_image(image_path):
    image = load_image(image_path)

    image = resize_image(image)

    return image


def get_fallback_image(image_path):
    image = load_image(image_path)

    image = resize_image(image)

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    denoised = cv2.fastNlMeansDenoising(
        gray,
        None,
        10,
        7,
        21
    )

    sharpen_kernel = np.array([
        [0, -1, 0],
        [-1, 5, -1],
        [0, -1, 0]
    ])

    sharpened = cv2.filter2D(
        denoised,
        -1,
        sharpen_kernel
    )

    processed = cv2.cvtColor(
        sharpened,
        cv2.COLOR_GRAY2BGR
    )

    return processed
