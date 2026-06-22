try:
    from paddleocr import PaddleOCR
except ImportError:
    PaddleOCR = None


class PaddleOCREngine:
    """Basic PaddleOCR engine wrapper."""

    def __init__(self, lang: str = "ch", use_angle_cls: bool = True, use_gpu: bool = False):
        self.lang = lang
        self._ocr = None

    def _ensure_loaded(self):
        if self._ocr is None and PaddleOCR is not None:
            self._ocr = PaddleOCR(
                use_angle_cls=True,
                lang=self.lang,
                use_gpu=False,
                show_log=False,
            )
        return self._ocr

    def recognize(self, image_path: str) -> list:
        engine = self._ensure_loaded()
        if engine is None:
            raise RuntimeError("PaddleOCR is not installed")
        result = engine.ocr(image_path, cls=True)
        lines = []
        for block in result or []:
            for line in block:
                text, confidence = line[1]
                lines.append({"text": text, "confidence": confidence})
        return lines
