from datetime import date
from functools import cache
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageOps
from transformers import ChineseCLIPModel, ChineseCLIPProcessor

from chinese_clip_search import IMAGE_SUFFIXES, MODEL_DIR, rank_images
from ranking_features import MatchFeatures, make_match_features, parse_location


@cache
def load_clip():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    processor = ChineseCLIPProcessor.from_pretrained(
        MODEL_DIR, local_files_only=True, use_fast=False
    )
    model = ChineseCLIPModel.from_pretrained(
        MODEL_DIR, local_files_only=True, use_safetensors=False
    )
    model.to(device).eval()
    return model, processor


def search_images(query: str, folder: Path):
    candidates = sorted(
        path for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )
    if not candidates:
        return []

    model, processor = load_clip()
    return rank_images(query, candidates, model, processor)[:3]

@torch.inference_mode()
def encode_image(image: Image.Image) -> bytes:
    model, processor = load_clip()

    image = ImageOps.exif_transpose(image).convert("RGB")
    inputs = processor(images=image, return_tensors="pt").to(model.device)

    features = model.get_image_features(**inputs).float()
    vector = torch.nn.functional.normalize(features, dim=-1)[0]

    return vector.cpu().numpy().astype("<f4", copy=False).tobytes()

@torch.inference_mode()
def encode_text(query: str) -> np.ndarray:
    model, processor = load_clip()
    inputs = processor(
        text=query, truncation=True, max_length=52, return_tensors="pt"
    ).to(model.device)

    text_output = model.text_model(**inputs, return_dict=True)
    features = model.text_projection(text_output.last_hidden_state[:, 0, :])
    vector = torch.nn.functional.normalize(features.float(), dim=-1)[0]
    return vector.cpu().numpy()


def build_candidate_features(
    query: str, items: list[dict], *, lost_on: date | None = None, lost_area: str | None = None
) -> list[tuple[dict, MatchFeatures]]:
    if not items:
        return []

    text_vector = encode_text(query)
    lost_location = parse_location(lost_area)
    results = []
    for item in items:
        image_vector = np.frombuffer(item["image_embedding"], dtype="<f4")
        score = float(image_vector @ text_vector)
        features = make_match_features(
            score, lost_on, lost_location, item.get("found_on"), parse_location(item.get("found_area"))
        )
        results.append((item, features))
    return results


def rank_stored_items(
    query: str, items: list[dict], *, lost_on: date | None = None, lost_area: str | None = None
):
    results = build_candidate_features(query, items, lost_on=lost_on, lost_area=lost_area)
    results.sort(key=lambda result: result[1].cosine_similarity, reverse=True)
    return [(item, features.cosine_similarity) for item, features in results[:3]]
