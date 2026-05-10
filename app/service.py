import numpy as np
from PIL import Image
import bentoml
from bentoml.io import Image as BentoImage
from bentoml.io import JSON

svc = bentoml.Service("yolo_demo")


@svc.api(input=BentoImage(), output=JSON())
def predict(img: Image.Image):
    arr = np.array(img.convert("RGB"))
    score = float(arr.mean() / 255.0)
    return {"label": "barcode_or_box" if score > 0.3 else "background", "confidence": score}
