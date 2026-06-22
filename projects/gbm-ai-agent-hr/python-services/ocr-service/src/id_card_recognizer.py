from .paddleocr_engine import PaddleOCREngine


class IDCardRecognizer:
    """Stub for ID card OCR recognition."""

    def __init__(self):
        self.engine = PaddleOCREngine(lang="ch")

    def recognize(self, image_path: str) -> dict:
        # TODO: implement ID card field extraction
        raw = self.engine.recognize(image_path)
        raise NotImplementedError
