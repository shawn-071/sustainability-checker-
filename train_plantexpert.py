"""Build a small, balanced MobileNetV2 model from PlantExpertVQA.

The full source dataset is large. This script streams rows, keeps a capped
number of unique images per crop-condition label, and stores the sample and
trained weights outside the Streamlit runtime. It never copies the full
dataset into this repository.
"""

from __future__ import annotations

import argparse
import json
import random
import re
from collections import defaultdict
from io import BytesIO
from pathlib import Path

from datasets import load_dataset
from PIL import Image, ImageOps
import torch
from torch.utils.data import DataLoader, Dataset
from transformers import AutoImageProcessor, AutoModelForImageClassification


DATASET_NAME = "Project-AgML/PlantExpertVQA"
BASE_MODEL = "linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification"


def parse_metadata(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def label_part(value):
    """Make a clean, readable name for model labels."""
    value = re.sub(r"[_\s]+", " ", str(value or "")).strip()
    return value.title()


def image_key(metadata, row):
    key = metadata.get("image_id") or metadata.get("file_names") or row.get("id")
    if isinstance(key, (list, tuple)):
        key = "|".join(str(part) for part in key)
    return str(key) if key else ""


def as_pil_image(value):
    if isinstance(value, (list, tuple)):
        if not value:
            return None
        value = value[0]
    if isinstance(value, Image.Image):
        return value.convert("RGB")
    if isinstance(value, dict):
        raw = value.get("bytes")
        if raw:
            with Image.open(BytesIO(raw)) as image:
                return image.convert("RGB")
        path = value.get("path")
        if path and Path(path).is_file():
            with Image.open(path) as image:
                return image.convert("RGB")
    return None


def extract_sample(args, sample_root):
    counts = defaultdict(int)
    seen = set()
    dataset = load_dataset(DATASET_NAME, split="train", streaming=True)
    dataset = dataset.shuffle(seed=args.seed, buffer_size=10_000)

    print(
        f"Streaming at most {args.max_records:,} rows; saving up to "
        f"{args.samples_per_class} unique images per crop-condition class."
    )
    for row_number, row in enumerate(dataset, start=1):
        if row_number > args.max_records:
            break
        if row_number % 10_000 == 0:
            print(f"Scanned {row_number:,} rows; collected {sum(counts.values()):,} images.")

        metadata = parse_metadata(row.get("raw_metadata"))
        crop = label_part(metadata.get("crop"))
        disease = label_part(metadata.get("disease") or metadata.get("category"))
        if not crop or not disease:
            continue

        unique_id = image_key(metadata, row)
        label = f"{crop}___{disease}"
        if not unique_id or unique_id in seen or counts[label] >= args.samples_per_class:
            continue

        image = as_pil_image(row.get("images"))
        if image is None:
            continue

        seen.add(unique_id)
        label_dir = sample_root / re.sub(r"[^A-Za-z0-9_-]+", "_", label)
        label_dir.mkdir(parents=True, exist_ok=True)
        image.save(label_dir / f"{counts[label]:04d}.jpg", format="JPEG", quality=92)
        counts[label] += 1

        if len(counts) >= 203 and all(count >= args.samples_per_class for count in counts.values()):
            break

    usable = {label: count for label, count in counts.items() if count >= args.min_per_class}
    dropped = len(counts) - len(usable)
    if not usable:
        raise RuntimeError(
            "No classes reached the minimum sample count. Increase --max-records "
            "or check that the dataset is available."
        )
    if dropped:
        print(f"Skipped {dropped} sparse classes with fewer than {args.min_per_class} images.")
    print(f"Collected {sum(usable.values()):,} unique images across {len(usable)} classes.")
    return usable


class LeafImageDataset(Dataset):
    def __init__(self, samples, processor, training=False):
        self.samples = samples
        self.processor = processor
        self.training = training

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):
        path, label_id = self.samples[index]
        with Image.open(path) as source:
            image = source.convert("RGB")
        if self.training and random.random() < 0.5:
            image = ImageOps.mirror(image)
        pixel_values = self.processor(images=image, return_tensors="pt")["pixel_values"][0]
        return pixel_values, label_id


def make_splits(sample_root, usable, seed):
    rng = random.Random(seed)
    labels = sorted(usable, key=str.casefold)
    label_to_id = {label: index for index, label in enumerate(labels)}
    train_samples = []
    validation_samples = []

    for label in labels:
        label_dir = sample_root / re.sub(r"[^A-Za-z0-9_-]+", "_", label)
        paths = sorted(label_dir.glob("*.jpg"))
        rng.shuffle(paths)
        validation_count = max(1, round(len(paths) * 0.2))
        validation_samples.extend((path, label_to_id[label]) for path in paths[:validation_count])
        train_samples.extend((path, label_to_id[label]) for path in paths[validation_count:])

    return labels, label_to_id, train_samples, validation_samples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples-per-class", type=int, default=25)
    parser.add_argument("--min-per-class", type=int, default=5)
    parser.add_argument("--max-records", type=int, default=120_000)
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--output-dir", type=Path, default=Path("plantexpert-training"))
    args = parser.parse_args()
    if args.samples_per_class < args.min_per_class or args.max_records <= 0:
        parser.error("samples-per-class must be at least min-per-class, and max-records must be positive")
    random.seed(args.seed)
    torch.manual_seed(args.seed)

    output_dir = args.output_dir
    sample_root = output_dir / "sample_images"
    model_dir = output_dir / "model"
    if sample_root.exists() and any(sample_root.iterdir()):
        raise SystemExit(f"{sample_root} already contains a sample; choose a new --output-dir.")
    sample_root.mkdir(parents=True, exist_ok=True)

    usable = extract_sample(args, sample_root)
    labels, label_to_id, train_samples, validation_samples = make_splits(
        sample_root, usable, args.seed
    )
    processor = AutoImageProcessor.from_pretrained(BASE_MODEL)
    model = AutoModelForImageClassification.from_pretrained(
        BASE_MODEL,
        num_labels=len(labels),
        ignore_mismatched_sizes=True,
    )
    model.config.id2label = {index: label for index, label in enumerate(labels)}
    model.config.label2id = label_to_id

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    train_loader = DataLoader(
        LeafImageDataset(train_samples, processor, training=True),
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=0,
        pin_memory=device.type == "cuda",
    )
    validation_loader = DataLoader(
        LeafImageDataset(validation_samples, processor),
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=0,
        pin_memory=device.type == "cuda",
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-5)

    print(f"Training {len(labels)} classes on {device}; validation uses held-out images.")
    for epoch in range(args.epochs):
        model.train()
        total_loss = 0.0
        for pixel_values, target in train_loader:
            pixel_values = pixel_values.to(device)
            target = target.to(device)
            optimizer.zero_grad(set_to_none=True)
            output = model(pixel_values=pixel_values, labels=target)
            output.loss.backward()
            optimizer.step()
            total_loss += float(output.loss.detach().cpu())

        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for pixel_values, target in validation_loader:
                output = model(pixel_values=pixel_values.to(device))
                correct += int((output.logits.argmax(dim=-1).cpu() == target).sum())
                total += int(target.numel())
        accuracy = correct / total if total else 0.0
        print(
            f"Epoch {epoch + 1}/{args.epochs}: "
            f"training loss {total_loss / max(1, len(train_loader)):.4f}; "
            f"held-out top-1 accuracy {accuracy:.1%} ({correct}/{total})."
        )

    model_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(model_dir, safe_serialization=True)
    processor.save_pretrained(model_dir)
    (model_dir / "training-labels.json").write_text(
        json.dumps(labels, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (model_dir / "DATASET_ATTRIBUTION.txt").write_text(
        "PlantExpertVQA: https://huggingface.co/datasets/Project-AgML/PlantExpertVQA\n"
        "Dataset license listed by the dataset repository: CC BY-NC 4.0.\n"
        "This model was fine-tuned from the PlantVillage MobileNetV2 model. Review both source licenses before reuse.\n",
        encoding="utf-8",
    )
    print(f"Saved model and image processor to: {model_dir.resolve()}")
    print("Do not present these screening scores as diagnostic certainty.")


if __name__ == "__main__":
    main()
