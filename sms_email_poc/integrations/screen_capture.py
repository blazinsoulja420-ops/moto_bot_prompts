import tempfile
import os
from typing import Optional

try:
    import mss
    from PIL import Image
    import pytesseract
except Exception:  # pragma: no cover - optional deps
    mss = None  # type: ignore
    Image = None  # type: ignore
    pytesseract = None  # type: ignore


def capture_screen(save_path: Optional[str] = None) -> Optional[str]:
    """Capture the primary screen and save to `save_path` or a temp file.

    Returns the path to the saved image or None if capture not available.
    """
    if mss is None:
        return None
    if save_path is None:
        fd, save_path = tempfile.mkstemp(suffix='.png')
        os.close(fd)

    with mss.mss() as sct:
        monitor = sct.monitors[1]
        sct_img = sct.grab(monitor)
        img = Image.frombytes('RGB', sct_img.size, sct_img.rgb)
        img.save(save_path)

    return save_path


def ocr_image(image_path: str) -> Optional[str]:
    """Run OCR on an image file and return extracted text, or None if OCR unavailable."""
    if pytesseract is None or Image is None:
        return None
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        return text
    except Exception:
        return None
