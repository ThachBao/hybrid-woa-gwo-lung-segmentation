from __future__ import annotations

from typing import Dict, List, Tuple

import cv2
import numpy as np


def multilevel_to_label_map(segmented: np.ndarray) -> np.ndarray:
    values = np.unique(segmented)
    mapping = {int(value): idx for idx, value in enumerate(values)}
    label_map = np.zeros(segmented.shape, dtype=np.int32)
    for value, idx in mapping.items():
        label_map[segmented == value] = idx
    return label_map


def _component_border_touch(component: np.ndarray) -> float:
    h, w = component.shape
    border_pixels = int(component[0, :].sum() + component[-1, :].sum() + component[:, 0].sum() + component[:, -1].sum())
    area = int(component.sum())
    return float(border_pixels / max(area, 1))


def score_regions_for_lung(label_map: np.ndarray, gray: np.ndarray) -> List[Dict]:
    h, w = label_map.shape
    total_area = float(h * w)
    scores: List[Dict] = []

    for label in np.unique(label_map):
        binary = (label_map == label).astype(np.uint8)
        num, cc, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)
        for comp_id in range(1, num):
            x, y, bw, bh, area = stats[comp_id]
            if area <= 0:
                continue
            component = cc == comp_id
            cx, cy = centroids[comp_id]
            area_ratio = float(area / total_area)
            bbox_ratio = float((bw * bh) / total_area)
            mean_intensity = float(np.mean(gray[component]))
            border_touch = _component_border_touch(component.astype(np.uint8))
            x_norm = float(cx / max(w - 1, 1))
            y_norm = float(cy / max(h - 1, 1))

            area_score = np.clip((area_ratio - 0.01) / 0.16, 0.0, 1.0)
            center_score = 1.0 - min(abs(x_norm - 0.5) / 0.5, 1.0)
            vertical_score = 1.0 if 0.18 <= y_norm <= 0.82 else 0.25
            darkness_score = 1.0 - np.clip(mean_intensity / 255.0, 0.0, 1.0)
            border_score = 1.0 - np.clip(border_touch * 6.0, 0.0, 1.0)
            too_large_penalty = 0.25 if area_ratio > 0.45 or bbox_ratio > 0.65 else 1.0

            score = (
                0.28 * area_score
                + 0.18 * center_score
                + 0.16 * vertical_score
                + 0.24 * darkness_score
                + 0.14 * border_score
            ) * too_large_penalty

            scores.append(
                {
                    "label": int(label),
                    "component_id": int(comp_id),
                    "area": int(area),
                    "area_ratio": area_ratio,
                    "bbox": [int(x), int(y), int(bw), int(bh)],
                    "centroid": [float(cx), float(cy)],
                    "centroid_norm": [x_norm, y_norm],
                    "mean_intensity": mean_intensity,
                    "border_touch_ratio": border_touch,
                    "score": float(score),
                    "_component": component,
                }
            )
    return scores


def build_candidate_lung_mask(label_map: np.ndarray, region_scores: List[Dict]) -> np.ndarray:
    h, w = label_map.shape
    filtered = [
        region for region in region_scores
        if 0.008 <= region["area_ratio"] <= 0.45
        and 0.10 <= region["centroid_norm"][0] <= 0.90
        and 0.12 <= region["centroid_norm"][1] <= 0.88
        and region["border_touch_ratio"] < 0.18
    ]
    if not filtered:
        filtered = sorted(region_scores, key=lambda item: item["score"], reverse=True)[:2]
    else:
        left = [r for r in filtered if r["centroid_norm"][0] < 0.52]
        right = [r for r in filtered if r["centroid_norm"][0] >= 0.48]
        selected = []
        if left:
            selected.append(max(left, key=lambda item: item["score"]))
        if right:
            right_best = max(right, key=lambda item: item["score"])
            if right_best not in selected:
                selected.append(right_best)
        if len(selected) < 2:
            for region in sorted(filtered, key=lambda item: item["score"], reverse=True):
                if region not in selected:
                    selected.append(region)
                if len(selected) >= 2:
                    break
        filtered = selected[:2]

    mask = np.zeros((h, w), dtype=np.uint8)
    for region in filtered[:2]:
        mask[region["_component"]] = 255
    return mask


def _keep_lateral_components(mask: np.ndarray) -> Tuple[np.ndarray, Dict]:
    binary = (mask > 0).astype(np.uint8)
    h, w = binary.shape
    num, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)
    components = []
    for idx in range(1, num):
        area = int(stats[idx, cv2.CC_STAT_AREA])
        if area < max(450, int(0.002 * h * w)):
            continue
        x, y, bw, bh = [int(v) for v in stats[idx, :4]]
        cx, cy = centroids[idx]
        x_norm = float(cx / max(w - 1, 1))
        y_norm = float(cy / max(h - 1, 1))
        if not (0.06 <= x_norm <= 0.94 and 0.10 <= y_norm <= 0.88):
            continue
        if bh < int(0.12 * h) or bw < int(0.04 * w):
            continue
        components.append({
            "idx": idx,
            "area": area,
            "bbox": [x, y, bw, bh],
            "centroid_norm": [x_norm, y_norm],
        })

    left = [c for c in components if c["centroid_norm"][0] < 0.52]
    right = [c for c in components if c["centroid_norm"][0] >= 0.48]
    selected = []
    if left:
        selected.append(max(left, key=lambda item: item["area"]))
    if right:
        best_right = max(right, key=lambda item: item["area"])
        if best_right not in selected:
            selected.append(best_right)
    if len(selected) < 2:
        for component in sorted(components, key=lambda item: item["area"], reverse=True):
            if component not in selected:
                selected.append(component)
            if len(selected) >= 2:
                break

    out = np.zeros_like(binary)
    for component in selected[:2]:
        out[labels == component["idx"]] = 1
    return out.astype(np.uint8) * 255, {
        "fallback_components": len(components),
        "fallback_selected_areas": [int(c["area"]) for c in selected[:2]],
    }


def build_intensity_lung_mask(gray: np.ndarray, percentile: float = 40.0) -> Tuple[np.ndarray, Dict]:
    gray_u8 = np.clip(gray, 0, 255).astype(np.uint8)
    h, w = gray_u8.shape
    roi = np.zeros_like(gray_u8, dtype=bool)
    roi[int(0.08 * h): int(0.97 * h), int(0.04 * w): int(0.96 * w)] = True
    body = roi & (gray_u8 > 12)
    threshold_pixels = gray_u8[body] if np.any(body) else gray_u8[roi]
    threshold = float(np.percentile(threshold_pixels, percentile))
    mask = ((gray_u8 <= threshold) & body).astype(np.uint8) * 255

    close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17))
    open_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, close_kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, open_kernel, iterations=1)
    mask, info = _keep_lateral_components(mask)
    info.update({"fallback_percentile": float(percentile), "fallback_threshold": threshold})
    return mask, info


def build_threshold_union_lung_mask(gray: np.ndarray, thresholds) -> Tuple[np.ndarray, Dict]:
    gray_u8 = np.clip(gray, 0, 255).astype(np.uint8)
    h, w = gray_u8.shape
    roi = np.zeros_like(gray_u8, dtype=bool)
    roi[int(0.08 * h): int(0.97 * h), int(0.04 * w): int(0.96 * w)] = True
    body = roi & (gray_u8 > 12)
    close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17))
    open_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))

    best_mask = np.zeros_like(gray_u8)
    best_quality = {"score": -1.0}
    best_info: Dict = {}
    for threshold in [int(v) for v in thresholds]:
        mask = ((gray_u8 <= threshold) & body).astype(np.uint8) * 255
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, close_kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, open_kernel, iterations=1)
        mask, info = _keep_lateral_components(mask)
        quality = score_mask_geometry(mask)
        if float(quality["score"]) > float(best_quality["score"]):
            best_mask = mask
            best_quality = quality
            best_info = {
                **info,
                "threshold_union_cutoff": int(threshold),
                "threshold_union_quality": quality,
            }

    return best_mask, best_info


def score_mask_geometry(mask: np.ndarray) -> Dict:
    binary = (mask > 0).astype(np.uint8)
    h, w = binary.shape
    area_ratio = float(np.count_nonzero(binary) / max(binary.size, 1))
    num, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)
    components = []
    for idx in range(1, num):
        area = int(stats[idx, cv2.CC_STAT_AREA])
        if area <= 0:
            continue
        x, y, bw, bh = [int(v) for v in stats[idx, :4]]
        cx, cy = centroids[idx]
        components.append({
            "area": area,
            "bbox": [x, y, bw, bh],
            "bbox_norm": [
                float(x / max(w - 1, 1)),
                float(y / max(h - 1, 1)),
                float(bw / max(w, 1)),
                float(bh / max(h, 1)),
            ],
            "x_norm": float(cx / max(w - 1, 1)),
            "y_norm": float(cy / max(h - 1, 1)),
        })
    components.sort(key=lambda item: item["area"], reverse=True)
    major = components[:2]

    area_score = 1.0 - min(abs(area_ratio - 0.22) / 0.22, 1.0)
    count_score = 1.0 if len(major) == 2 else (0.45 if len(major) == 1 else 0.0)
    if len(major) == 2:
        xs = sorted(item["x_norm"] for item in major)
        ys = [item["y_norm"] for item in major]
        bottoms = [item["bbox_norm"][1] + item["bbox_norm"][3] for item in major]
        widths = [item["bbox_norm"][2] for item in major]
        separation = xs[1] - xs[0]
        separation_score = np.clip((separation - 0.22) / 0.18, 0.0, 1.0)
        lateral_score = 1.0 - min((abs(xs[0] - 0.34) + abs(xs[1] - 0.66)) / 0.42, 1.0)
        vertical_score = 1.0 - min(sum(abs(y - 0.48) for y in ys) / 0.58, 1.0)
        bottom_score = 1.0 - np.clip((max(bottoms) - 0.78) / 0.18, 0.0, 1.0)
        width_score = 1.0 - np.clip((max(widths) - 0.34) / 0.34, 0.0, 1.0)
        balance = min(major[0]["area"], major[1]["area"]) / max(major[0]["area"], major[1]["area"])
    elif len(major) == 1:
        separation_score = 0.0
        lateral_score = 1.0 - min(abs(major[0]["x_norm"] - 0.5) / 0.5, 1.0)
        vertical_score = 1.0 - min(abs(major[0]["y_norm"] - 0.48) / 0.48, 1.0)
        bottom = major[0]["bbox_norm"][1] + major[0]["bbox_norm"][3]
        bottom_score = 1.0 - np.clip((bottom - 0.78) / 0.18, 0.0, 1.0)
        width_score = 1.0 - np.clip((major[0]["bbox_norm"][2] - 0.34) / 0.34, 0.0, 1.0)
        balance = 0.0
    else:
        separation_score = 0.0
        lateral_score = 0.0
        vertical_score = 0.0
        bottom_score = 0.0
        width_score = 0.0
        balance = 0.0

    score = (
        0.20 * area_score
        + 0.16 * count_score
        + 0.22 * float(separation_score)
        + 0.14 * float(lateral_score)
        + 0.12 * float(vertical_score)
        + 0.08 * float(bottom_score)
        + 0.04 * float(width_score)
        + 0.04 * float(balance)
    )
    return {
        "score": float(score),
        "area_ratio": area_ratio,
        "component_count": len(components),
        "major_component_count": len(major),
        "separation_score": float(separation_score),
        "lateral_score": float(lateral_score),
        "vertical_score": float(vertical_score),
        "bottom_score": float(bottom_score),
        "width_score": float(width_score),
    }


def threshold_regions_to_lung_mask(segmented: np.ndarray, gray: np.ndarray, thresholds) -> Dict:
    label_map = multilevel_to_label_map(segmented)
    region_scores = score_regions_for_lung(label_map, gray)
    candidate = build_candidate_lung_mask(label_map, region_scores)
    candidate_quality = score_mask_geometry(candidate)
    union_candidate, union_info = build_threshold_union_lung_mask(gray, thresholds)
    union_quality = score_mask_geometry(union_candidate)
    selected_source = "threshold_components"
    if float(union_quality["score"]) > float(candidate_quality["score"]):
        candidate = union_candidate
        candidate_quality = union_quality
        selected_source = "threshold_union"
    public_scores = [{k: v for k, v in row.items() if k != "_component"} for row in region_scores]
    return {
        "label_map": label_map,
        "candidate_mask": candidate,
        "region_scores": public_scores,
        "thresholds": [int(v) for v in thresholds],
        "candidate_quality": candidate_quality,
        "threshold_union_info": union_info,
        "selected_source": selected_source,
    }


def segmented_to_lung_mask(segmented: np.ndarray, gray: np.ndarray, thresholds, *, allow_fallback: bool = True) -> Dict:
    result = threshold_regions_to_lung_mask(segmented, gray, thresholds)
    candidate = result["candidate_mask"]
    candidate_quality = result["candidate_quality"]
    if not allow_fallback:
        return {
            **result,
        "fallback_quality": None,
        "fallback_info": None,
        "threshold_union_info": result.get("threshold_union_info"),
        }

    fallback_candidate, fallback_info = build_intensity_lung_mask(gray, percentile=30.0)
    fallback_quality = score_mask_geometry(fallback_candidate)
    candidate_too_small = candidate_quality["area_ratio"] < 0.08 and fallback_quality["area_ratio"] > candidate_quality["area_ratio"]
    if candidate_too_small or fallback_quality["score"] > candidate_quality["score"]:
        candidate = fallback_candidate
        selected_source = "intensity_fallback"
    else:
        selected_source = "threshold_regions"
    return {
        "label_map": result["label_map"],
        "candidate_mask": candidate,
        "region_scores": result["region_scores"],
        "thresholds": result["thresholds"],
        "candidate_quality": candidate_quality,
        "fallback_quality": fallback_quality,
        "fallback_info": fallback_info,
        "threshold_union_info": result.get("threshold_union_info"),
        "selected_source": selected_source,
    }
