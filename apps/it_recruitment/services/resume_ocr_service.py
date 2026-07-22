"""OCR text extraction for scanned PDFs and Image resumes."""

import logging
from pathlib import Path

from apps.core.services.base import BaseService

logger = logging.getLogger(__name__)

class ResumeOCRService(BaseService):
    """
    Handles extracting text from images and scanned PDFs using Tesseract OCR.
    Configured to preserve column structures and layouts.
    """

    def extract_text(self, file_path: Path) -> str:
        """
        Extract text via OCR. Supports PDF (by converting to images) and Image files.
        """
        ext = file_path.suffix.lower()
        if ext == ".pdf":
            return self._extract_from_pdf(file_path)
        elif ext in (".png", ".jpg", ".jpeg", ".webp", ".tiff"):
            return self._extract_from_image(file_path)
        else:
            raise ValueError(f"Unsupported OCR file type: {ext}")

    def _extract_from_image(self, file_path: Path) -> str:
        try:
            from PIL import Image
            import pytesseract
        except ImportError:
            logger.error("OCR dependencies (Pillow, pytesseract) not installed.")
            return ""

        try:
            image = Image.open(str(file_path))
            # psm 1: Automatic page segmentation with OSD. 
            # psm 4: Assume a single column of text of variable sizes.
            # We use psm 4 to help preserve columns sequentially or 1 for full auto.
            text = pytesseract.image_to_string(image, config="--psm 1")
            return text.strip()
        except pytesseract.TesseractNotFoundError:
            logger.error("Tesseract-OCR binary is not installed on the host system.")
            raise RuntimeError("The OCR engine is not installed on this server.")
        except Exception as e:
            logger.error("Failed to run OCR on image: %s", e)
            return ""

    def _extract_from_pdf(self, file_path: Path) -> str:
        try:
            from pdf2image import convert_from_path
            import pytesseract
        except ImportError:
            logger.error("OCR dependencies (pdf2image, pytesseract) not installed.")
            return ""

        try:
            # Convert first 5 pages to avoid massive processing times
            images = convert_from_path(str(file_path), dpi=200, first_page=1, last_page=5)
            full_text = []
            for img in images:
                text = pytesseract.image_to_string(img, config="--psm 1")
                full_text.append(text)
            return "\n".join(full_text).strip()
        except pytesseract.TesseractNotFoundError:
            logger.error("Tesseract-OCR binary is not installed on the host system.")
            raise RuntimeError("The OCR engine is not installed on this server.")
        except Exception as e:
            logger.error("Failed to run OCR on PDF: %s", e)
            return ""
