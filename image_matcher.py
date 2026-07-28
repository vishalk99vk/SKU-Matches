"""
Core image matching logic.

Strategy (combines three signals so near-identical SKUs that differ by a
tiny detail, like an extra dot or a different number on the packaging,
don't get falsely matched):

1. ORB keypoint/feature matching  -> catches fine printed detail differences
2. Color histogram comparison      -> catches overall color/pattern similarity
3. Structural similarity (SSIM)    -> catches layout/shape similarity,
                                       resistant to image-quality differences

The three scores are blended into one confidence score (0-100).
Images are resized to a common canvas before comparison so real product
size differences (which you care about) are preserved via aspect ratio,
while raw pixel-resolution differences (which you don't care about) are
normalized away.
"""

import io
import os
import cv2
import numpy as np
import requests
from PIL import Image
from skimage.metrics import structural_similarity as ssim

REQUEST_TIMEOUT = 15
CANVAS_SIZE = (400, 400)  # normalizes resolution; aspect ratio kept via padding


def load_image(source: str) -> np.ndarray:
    """Load an image from a URL or a local file path into an OpenCV BGR array."""
    if source.startswith("http://") or source.startswith("https://"):
        resp = requests.get(source, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        pil_img = Image.open(io.BytesIO(resp.content)).convert("RGB")
    else:
        if not os.path.exists(source):
            raise FileNotFoundError(f"Image not found: {source}")
        pil_img = Image.open(source).convert("RGB")

    arr = np.array(pil_img)
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def _letterbox(img: np.ndarray, size=CANVAS_SIZE) -> np.ndarray:
    """Resize keeping aspect ratio, pad to a fixed canvas so real product
    proportions (size/shape) are preserved rather than stretched away."""
    h, w = img.shape[:2]
    target_w, target_h = size
    scale = min(target_w / w, target_h / h)
    new_w, new_h = int(w * scale), int(h * scale)
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

    canvas = np.full((target_h, target_w, 3), 255, dtype=np.uint8)
    y_off = (target_h - new_h) // 2
    x_off = (target_w - new_w) // 2
    canvas[y_off:y_off + new_h, x_off:x_off + new_w] = resized
    return canvas


def _orb_score(img1: np.ndarray, img2: np.ndarray) -> float:
    """Feature-keypoint match ratio. Sensitive to fine printed detail
    (e.g. an extra dot / different number on otherwise identical packaging)."""
    orb = cv2.ORB_create(nfeatures=800)
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    kp1, des1 = orb.detectAndCompute(gray1, None)
    kp2, des2 = orb.detectAndCompute(gray2, None)

    if des1 is None or des2 is None or len(kp1) == 0 or len(kp2) == 0:
        return 0.0

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    matches = bf.knnMatch(des1, des2, k=2)

    good = []
    for pair in matches:
        if len(pair) == 2:
            m, n = pair
            if m.distance < 0.75 * n.distance:
                good.append(m)

    denom = min(len(kp1), len(kp2))
    if denom == 0:
        return 0.0
    return min(len(good) / denom, 1.0)


def _color_hist_score(img1: np.ndarray, img2: np.ndarray) -> float:
    """HSV color histogram correlation. Catches overall color/pattern match."""
    hsv1 = cv2.cvtColor(img1, cv2.COLOR_BGR2HSV)
    hsv2 = cv2.cvtColor(img2, cv2.COLOR_BGR2HSV)

    hist1 = cv2.calcHist([hsv1], [0, 1], None, [50, 60], [0, 180, 0, 256])
    hist2 = cv2.calcHist([hsv2], [0, 1], None, [50, 60], [0, 180, 0, 256])
    cv2.normalize(hist1, hist1)
    cv2.normalize(hist2, hist2)

    score = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
    return max(score, 0.0)


def _ssim_score(img1: np.ndarray, img2: np.ndarray) -> float:
    """Structural similarity. Catches overall shape/layout match,
    robust to resolution/quality differences between the two images."""
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    score, _ = ssim(gray1, gray2, full=True)
    return max(score, 0.0)


def compare_images(source1: str, source2: str) -> float:
    """Returns a 0-100 confidence score that the two images are the same SKU."""
    img1 = _letterbox(load_image(source1))
    img2 = _letterbox(load_image(source2))

    orb = _orb_score(img1, img2)
    hist = _color_hist_score(img1, img2)
    struct = _ssim_score(img1, img2)

    # ORB (fine detail) is weighted highest since it's what catches near-duplicate
    # SKUs (e.g. same patch, different mg printed on it).
    confidence = (0.5 * orb + 0.25 * hist + 0.25 * struct) * 100
    return round(confidence, 2)
