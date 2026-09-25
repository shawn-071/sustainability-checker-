"""
disease_model.py
----------------
Plant disease classification using the PlantVillage-trained
MobileNetV2 model on Hugging Face.

Image preprocessing is performed locally with PIL + torch rather
than relying on a model-specific Transformers image processor.
This avoids processor-config compatibility problems with the
model repository.
"""

from PIL import Image
from transformers import AutoModelForImageClassification
import torch
import torch.nn.functional as F

MODEL_NAME = "linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification"

IMAGE_SIZE = 224
IMAGE_MEAN = torch.tensor([0.5, 0.5, 0.5]).view(3, 1, 1)
IMAGE_STD = torch.tensor([0.5, 0.5, 0.5]).view(3, 1, 1)


def load_model(local_files_only: bool = False):
    """
    Download/load the disease model.

    Returns:
        model
    """
    model = AutoModelForImageClassification.from_pretrained(
        MODEL_NAME,
        local_files_only=local_files_only,
    )
    model.eval()

    return model


def _preprocess(image: Image.Image) -> torch.Tensor:
    """
    Convert a PIL image into the tensor expected by the model.

    The original model uses:
      - RGB
      - resize
      - center crop
      - scale 0-255 -> 0-1
      - mean/std normalization of 0.5
    """

    image = image.convert("RGB")

    # Resize while keeping the aspect ratio.
    image.thumbnail((256, 256), Image.Resampling.BILINEAR)

    # Put the image on a 256x256 canvas.
    canvas = Image.new("RGB", (256, 256))
    left = (256 - image.width) // 2
    top = (256 - image.height) // 2
    canvas.paste(image, (left, top))

    # Center crop to 224x224.
    left = (256 - IMAGE_SIZE) // 2
    top = (256 - IMAGE_SIZE) // 2

    image = canvas.crop(
        (
            left,
            top,
            left + IMAGE_SIZE,
            top + IMAGE_SIZE,
        )
    )

    # PIL -> torch tensor.
    # Shape: H,W,C -> C,H,W
    pixels = torch.tensor(
        list(image.getdata()),
        dtype=torch.float32,
    ).reshape(IMAGE_SIZE, IMAGE_SIZE, 3)

    tensor = pixels.permute(2, 0, 1) / 255.0

    # Normalize using the model's expected values.
    tensor = (tensor - IMAGE_MEAN) / IMAGE_STD

    # Add batch dimension.
    return tensor.unsqueeze(0)


def predict(image: Image.Image, model, top_k: int = 3):
    """
    Run disease prediction.

    Returns:
        list of dictionaries containing plant, disease,
        raw label and confidence.
    """

    inputs = _preprocess(image)

    with torch.no_grad():
        outputs = model(pixel_values=inputs)

        probabilities = F.softmax(
            outputs.logits,
            dim=-1,
        )[0]

    k = min(top_k, probabilities.shape[0])

    top_probs, top_idxs = torch.topk(
        probabilities,
        k=k,
    )

    results = []

    for probability, index in zip(
        top_probs.tolist(),
        top_idxs.tolist(),
    ):
        raw_label = model.config.id2label[index]

        plant, disease = _parse_label(raw_label)

        results.append(
            {
                "plant": plant,
                "disease": disease,
                "raw_label": raw_label,
                "confidence": probability,
            }
        )

    return results


def _parse_label(raw_label: str):
    """
    Convert model labels into (plant, disease).

    IMPORTANT: this model's real labels are underscore-separated in
    the PlantVillage convention, e.g.:

        "Tomato___Late_blight"       -> ("Tomato", "Late Blight")
        "Potato___Early_blight"      -> ("Potato", "Early Blight")
        "Apple___healthy"            -> ("Apple", "Healthy")
        "Tomato___Tomato_mosaic_virus" -> ("Tomato", "Tomato Mosaic Virus")

    (A previous version of this function expected labels shaped like
    "Tomato with Late Blight", which never actually matches this
    model's output -- every prediction was silently falling through to
    "Unknown". If you swap in a different model later, print
    model.config.id2label once and re-check this function against it.)
    """

    label = str(raw_label).strip()

    if "___" in label:
        plant_raw, disease_raw = label.split("___", 1)
    else:
        # Fallback for an unexpected label shape -- keeps the app
        # running instead of crashing, just won't look as clean.
        return label, "Unknown"

    plant = plant_raw.replace("_", " ").replace("(", "").replace(")", "").strip()

    disease_clean = disease_raw.replace("_", " ").strip()
    if disease_clean.lower() == "healthy":
        disease = "Healthy"
    else:
        disease = disease_clean.title()

    return plant, disease
