import argparse
from dataclasses import asdict
from datetime import date
import json
from pathlib import Path

from mysql.connector import Error as MySQLError

from database import list_found_items
from image_search import build_candidate_features
from ranking_features import FEATURE_NAMES


def build_dataset(manifest: dict, items: list[dict]) -> dict:
    if not isinstance(manifest, dict):
        raise ValueError("样本清单应为 JSON 对象。")
    groups = manifest.get("groups")
    queries = manifest.get("queries")
    if not isinstance(groups, list) or not isinstance(queries, list):
        raise ValueError("样本清单需要 groups 和 queries 两个列表。")

    items_by_id = {item["id"]: item for item in items}
    object_splits = {}
    photo_objects = {}
    candidates = {"train": [], "test": []}
    for group in groups:
        if not isinstance(group, dict):
            raise ValueError("groups 的每一项应为 JSON 对象。")
        object_id = group.get("object_id")
        split = group.get("split")
        item_ids = group.get("found_item_ids")
        if not isinstance(object_id, str) or not object_id.strip() or object_id in object_splits:
            raise ValueError(f"实物编号为空或重复：{object_id!r}")
        if split not in ("train", "test"):
            raise ValueError(f"{object_id} 的 split 须填写 train 或 test。")
        if not isinstance(item_ids, list) or not item_ids:
            raise ValueError(f"{object_id} 须至少包含一条招领记录。")
        object_splits[object_id] = split
        for item_id in item_ids:
            if type(item_id) is not int or item_id not in items_by_id:
                raise ValueError(f"找不到招领编号 {item_id!r}。请核对已发布的物品编号。")
            if item_id in photo_objects:
                raise ValueError(f"招领编号 {item_id} 在清单中重复。")
            item = items_by_id[item_id]
            if len(item["image_embedding"] or b"") != 2048:
                raise ValueError(f"招领编号 {item_id} 缺少完整的图片向量。")
            photo_objects[item_id] = object_id
            candidates[split].append(item)

    for split in candidates:
        if list(object_splits.values()).count(split) < 2:
            raise ValueError(f"{split} 至少需要两件不同实物，才能同时生成正负样本。")

    parsed_queries = []
    for index, entry in enumerate(queries, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"第 {index} 条寻物描述应为 JSON 对象。")
        object_id = entry.get("object_id")
        query = entry.get("query")
        lost_area = entry.get("lost_area")
        raw_date = entry.get("lost_on")
        if not isinstance(object_id, str) or object_id not in object_splits:
            raise ValueError(f"第 {index} 条寻物描述对应的实物编号未知。")
        if not isinstance(query, str) or not query.strip():
            raise ValueError(f"第 {index} 条寻物描述为空。")
        if lost_area is not None and (not isinstance(lost_area, str) or len(lost_area.strip()) > 100):
            raise ValueError(f"第 {index} 条寻物描述的丢失地点须为最多 100 字的文本。")
        try:
            lost_on = date.fromisoformat(raw_date.strip()) if raw_date is not None else None
        except (AttributeError, ValueError) as error:
            raise ValueError(f"第 {index} 条寻物描述的丢失日期须填写 YYYY-MM-DD 或 null。") from error
        parsed_queries.append((object_id, query.strip(), lost_on, lost_area))

    if {object_splits[object_id] for object_id, *_ in parsed_queries} != set(candidates):
        raise ValueError("train 和 test 都需要至少一条寻物描述。")

    rows = []
    for index, (object_id, query, lost_on, lost_area) in enumerate(parsed_queries, start=1):
        split = object_splits[object_id]
        for item, features in build_candidate_features(
            query, candidates[split], lost_on=lost_on, lost_area=lost_area
        ):
            candidate_object_id = photo_objects[item["id"]]
            rows.append({
                "split": split,
                "query_index": index,
                "object_id": object_id,
                "candidate_id": item["id"],
                "candidate_object_id": candidate_object_id,
                "features": asdict(features),
                "label": int(object_id == candidate_object_id),
            })
    return {"feature_names": FEATURE_NAMES, "rows": rows}


def main():
    parser = argparse.ArgumentParser(description="从招领记录导出逻辑回归训练和评测样本")
    parser.add_argument("manifest", type=Path, help="已标注的样本清单")
    parser.add_argument("output", type=Path, help="输出数据集 JSON 路径")
    args = parser.parse_args()
    if args.manifest.resolve() == args.output.resolve():
        parser.error("输出路径必须与样本清单不同。")
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
        dataset = build_dataset(manifest, list_found_items())
        output = json.dumps(dataset, ensure_ascii=False, indent=2, allow_nan=False)
        args.output.write_text(output + "\n", encoding="utf-8")
    except (OSError, ValueError, MySQLError) as error:
        parser.error(str(error))

    rows = dataset["rows"]
    for split in ("train", "test"):
        split_rows = [row for row in rows if row["split"] == split]
        positives = sum(row["label"] for row in split_rows)
        print(f"{split}: {len(split_rows)} 对，正例 {positives}，负例 {len(split_rows) - positives}")


if __name__ == "__main__":
    main()
