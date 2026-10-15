"""Reads the text on a receipt photo locally with RapidOCR. The photo is never sent anywhere."""
import logging
from functools import cache

import numpy as np
from PIL import Image
from rapidocr import RapidOCR

logging.getLogger("RapidOCR").setLevel(logging.WARNING)

# Sent before the receipt text. Without it the model sometimes decides a receipt printed with
# another name ("GUEST: John Smith") isn't the group's bill and returns nothing.
RECEIPT_INTRO = "Scanned receipt of a bill our group shared:\n"


@cache
def engine():
    return RapidOCR()  # loading the models takes about a second, so do it once


def read_receipt(file):
    """Returns the receipt text, one printed line per line, top to bottom."""
    result = engine()(np.array(Image.open(file).convert("RGB")))
    if result.boxes is None:
        return ""

    words = []
    for box, text in zip(result.boxes, result.txts):
        ys = [point[1] for point in box]
        words.append({"x": box[0][0], "y": sum(ys) / 4, "height": max(ys) - min(ys), "text": text})
    words.sort(key=lambda word: word["y"])

    lines = []
    for word in words:
        if lines and abs(word["y"] - lines[-1][0]["y"]) < word["height"] * 0.6:  # same printed line
            lines[-1].append(word)
        else:
            lines.append([word])
    return "\n".join(" ".join(word["text"] for word in sorted(line, key=lambda w: w["x"])) for line in lines)
