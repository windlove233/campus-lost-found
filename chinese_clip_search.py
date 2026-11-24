import argparse
from pathlib import Path
import sys

from PIL import Image, ImageOps
import torch
from transformers import ChineseCLIPModel, ChineseCLIPProcessor


MODEL_DIR = Path(__file__).resolve().parent / "models" / "chinese-clip-vit-base-patch16"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
BATCH_SIZE = 16


@torch.inference_mode()
def rank_images(
    query: str,
    paths: list[Path],
    model: ChineseCLIPModel,
    processor: ChineseCLIPProcessor,
) -> list[tuple[Path, float]]:
    text = processor(text=query, truncation=True, max_length=52, return_tensors="pt").to(model.device)
    results = []

    for start in range(0, len(paths), BATCH_SIZE):
        images = []
        readable_paths = []
        for path in paths[start : start + BATCH_SIZE]:
            try:
                with Image.open(path) as image:
                    images.append(ImageOps.exif_transpose(image).convert("RGB"))
            except (OSError, Image.DecompressionBombError) as error:
                print(f"跳过无法读取的图片 {path}（{error}）", file=sys.stderr)
                continue
            readable_paths.append(path)

        if not images:
            continue

        batch = processor(images=images, return_tensors="pt").to(model.device)
        outputs = model(**text, **batch)
        scores = (outputs.image_embeds @ outputs.text_embeds[0]).tolist()
        results.extend(zip(readable_paths, scores, strict=True))

    return sorted(results, key=lambda result: result[1], reverse=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="用中文描述搜索本地照片，按相似度显示前三张。")
    parser.add_argument("--query", required=True, help="要寻找的物品描述")
    parser.add_argument("--images", type=Path, required=True, help="照片目录，包含其子目录")
    parser.add_argument("--no-recursive", action="store_true", help="只扫描照片目录的这一层")
    parser.add_argument("--device", choices=("auto", "cuda", "cpu"), default="auto")
    args = parser.parse_args()

    query = args.query.strip()
    if not query:
        parser.error("请输入中文描述。")
    if not args.images.is_dir():
        parser.error(f"找不到照片目录 {args.images}")

    directory = args.images.absolute()
    candidates = directory.iterdir() if args.no_recursive else directory.rglob("*")
    paths = sorted(path for path in candidates if path.suffix.lower() in IMAGE_SUFFIXES and path.is_file())
    if not paths:
        parser.error("照片目录中没有 JPG、PNG、WebP 或 BMP 图片。")
    if not (MODEL_DIR / "pytorch_model.bin").is_file():
        parser.error("本地模型权重缺失，请先运行 setup-chinese-clip.ps1。")

    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda" and not torch.cuda.is_available():
        parser.error("CUDA 不可用，请检查 PyTorch 和 NVIDIA 驱动，或使用 --device cpu。")

    processor = ChineseCLIPProcessor.from_pretrained(MODEL_DIR, local_files_only=True, use_fast=False)
    model = ChineseCLIPModel.from_pretrained(MODEL_DIR, local_files_only=True, use_safetensors=False)
    model.to(device).eval()
    results = rank_images(query, paths, model, processor)
    if not results:
        parser.error("没有可以读取的照片。")

    device_name = torch.cuda.get_device_name(model.device) if device == "cuda" else "CPU"
    print(f"设备 {device_name} | 已比较 {len(results)} 张照片")
    for rank, (path, score) in enumerate(results[:3], start=1):
        print(f"{rank}. {score:.4f}  {path}")


if __name__ == "__main__":
    main()
