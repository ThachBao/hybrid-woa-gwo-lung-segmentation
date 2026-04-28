from __future__ import annotations

import io
import json
import os
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _read_yaml(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return default if data is None else data


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _to_rel_posix(path: Path) -> str:
    return path.as_posix()


def _safe_iso(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    text = str(value)
    try:
        return datetime.fromisoformat(text).isoformat()
    except Exception:
        return None


def _is_visible_algo(name: Any) -> bool:
    return str(name or "").upper() != "OTSU"


class RunHistory:
    """Represents one saved run under outputs/runs."""

    def __init__(self, run_dir: str):
        self.run_dir = Path(run_dir)
        self.run_name = self.run_dir.name
        self.config = self._load_config()
        self.summary = self._load_summary()
        self.mode = self._detect_mode()
        self.timestamp = self._extract_timestamp()
        self.warning_messages = self._collect_warnings()

    def _load_config(self) -> Dict[str, Any]:
        for config_name in ("config.yaml", "config_used.yaml"):
            data = _read_yaml(self.run_dir / config_name, {})
            if isinstance(data, dict) and data:
                return data
        return {}

    def _load_summary(self) -> Dict[str, Any]:
        data = _read_json(self.run_dir / "summary.json", {})
        return data if isinstance(data, dict) else {}

    def _detect_mode(self) -> str:
        mode = self.config.get("mode") or self.summary.get("mode") or self.config.get("eval_mode")
        if mode == "cxr_demo":
            return "cxr_demo"
        if mode == "single_image_multi_seed":
            return "single_image_multi_seed"
        return "single"

    def _extract_timestamp(self) -> Optional[datetime]:
        for raw in (
            self.config.get("created_at"),
            self.summary.get("created_at"),
            self.config.get("timestamp"),
            self.summary.get("timestamp"),
        ):
            if raw:
                try:
                    return datetime.fromisoformat(str(raw))
                except Exception:
                    pass
        parts = self.run_name.split("__")
        if parts:
            try:
                return datetime.strptime(parts[0], "%Y%m%d_%H%M%S")
            except Exception:
                pass
        legacy = self.run_name.split("_")
        if len(legacy) >= 2:
            try:
                return datetime.strptime(f"{legacy[0]}_{legacy[1]}", "%Y%m%d_%H%M%S")
            except Exception:
                pass
        return None

    def _collect_warnings(self) -> List[str]:
        warnings: List[str] = []
        required = ["config.yaml", "summary.json", "gray.png"]
        missing = [name for name in required if not (self.run_dir / name).exists()]
        if missing:
            warnings.append("Run cũ không có đủ dữ liệu chi tiết theo schema mới")
        if self.mode == "single_image_multi_seed":
            for name in ("results.json", "wilcoxon.json"):
                if not (self.run_dir / name).exists():
                    warnings.append("Run cũ không có đủ dữ liệu chi tiết theo schema mới")
                    break
        return list(dict.fromkeys(warnings))

    def _algorithm_dirs(self) -> List[Path]:
        base = self.run_dir / "algorithms"
        if base.exists():
            return sorted([p for p in base.iterdir() if p.is_dir()], key=lambda p: p.name)
        legacy = []
        for child in self.run_dir.iterdir():
            if child.is_dir() and child.name not in {"algorithms", "__pycache__", ".git"}:
                legacy.append(child)
        return sorted(legacy, key=lambda p: p.name)

    def _load_single_algorithms(self) -> Dict[str, Any]:
        algorithms: Dict[str, Any] = {}
        for algo_dir in self._algorithm_dirs():
            algo_name = algo_dir.name
            result = _read_json(algo_dir / "result.json", {})
            if not result:
                result = _read_json(algo_dir / "best.json", {})
            history = _read_jsonl(algo_dir / "history.jsonl")
            images = {}
            for filename, key in (
                ("segmented.png", "segmented"),
                ("overlay.png", "overlay"),
                ("histogram.png", "histogram"),
                ("gray.png", "gray"),
            ):
                path = algo_dir / filename
                if path.exists():
                    images[key] = _to_rel_posix(path)
            algorithms[algo_name] = {
                "name": algo_name,
                "result": result,
                "best_result": result,
                "history": history,
                "images": images,
            }
        return algorithms

    def _load_multi_seed_algorithms(self) -> Dict[str, Any]:
        algorithms: Dict[str, Any] = {}
        summary_stats = self.summary.get("summary_statistics", {})
        for algo_dir in self._algorithm_dirs():
            algo_name = algo_dir.name
            result = _read_json(algo_dir / "result.json", {})
            if not result:
                result = _read_json(algo_dir / "best.json", {})
            per_seed = _read_json(algo_dir / "per_seed.json", [])
            if not per_seed:
                per_seed = _read_jsonl(algo_dir / "history.jsonl")
            images = {}
            for filename, key in (
                ("segmented.png", "segmented"),
                ("overlay.png", "overlay"),
                ("boxplot.png", "boxplot"),
                ("gray.png", "gray"),
            ):
                path = algo_dir / filename
                if path.exists():
                    images[key] = _to_rel_posix(path)
            algorithms[algo_name] = {
                "name": algo_name,
                "result": result,
                "best_result": result,
                "per_seed": per_seed,
                "summary_stat": summary_stats.get(algo_name, {}),
                "images": images,
            }
        return algorithms

    def _preview_metrics(self) -> Dict[str, Any]:
        if self.mode == "cxr_demo":
            return {
                "case_id": self.summary.get("case_id") or self.config.get("case_id"),
                "fe": self.summary.get("fe"),
                "dsc": self.summary.get("dsc"),
                "time": self.summary.get("time"),
            }
        if self.mode == "single_image_multi_seed":
            ranking = self.summary.get("ranking_primary") or []
            summary_stats = self.summary.get("summary_statistics", {})
            ranking = [row for row in ranking if _is_visible_algo(row.get("algorithm"))]
            summary_stats = {k: v for k, v in summary_stats.items() if _is_visible_algo(k)}
            best_algo = ranking[0]["algorithm"] if ranking else next(iter(summary_stats.keys()), None)
            stat = summary_stats.get(best_algo, {}) if best_algo else {}
            return {
                "best_algorithm": best_algo,
                "fe_mean": stat.get("fe_mean"),
                "fe_sd": stat.get("fe_sd"),
                "boundary_dsc_mean": stat.get("boundary_dsc_mean"),
            }
        ranking = self.summary.get("ranking") or []
        ranking = [row for row in ranking if _is_visible_algo(row.get("algorithm"))]
        algo_summary = self.summary.get("algorithms_summary", {})
        best_algo = ranking[0]["algorithm"] if ranking else self.summary.get("best_overall_algo")
        if not _is_visible_algo(best_algo):
            best_algo = next((name for name in algo_summary.keys() if _is_visible_algo(name)), None)
            if best_algo is None:
                best_algo = next((name for name in (self.summary.get("results", {}) or {}).keys() if _is_visible_algo(name)), None)
        stat = algo_summary.get(best_algo, {}) if best_algo else {}
        legacy_stat = (self.summary.get("results", {}) or {}).get(best_algo, {}) if best_algo else {}
        metrics = legacy_stat.get("metrics", {}) if isinstance(legacy_stat, dict) else {}
        return {
            "best_algorithm": best_algo,
            "fe": stat.get("fe", legacy_stat.get("entropy")),
            "boundary_dsc": stat.get("boundary_dsc", metrics.get("boundary_dsc")),
            "psnr": stat.get("psnr", metrics.get("psnr")),
            "ssim": stat.get("ssim", metrics.get("ssim")),
        }

    def get_summary(self) -> Dict[str, Any]:
        algorithms = self.config.get("selected_algorithms") or self.config.get("algorithms") or []
        if isinstance(algorithms, dict):
            algorithms = [k for k, v in algorithms.items() if v]
        algorithms = [algo for algo in algorithms if _is_visible_algo(algo)]
        image_id = self.config.get("image_id") or self.summary.get("image_id") or self.config.get("image_name")
        if self.mode == "cxr_demo":
            image_id = self.summary.get("case_id") or self.config.get("case_id") or image_id
        source_single_run_dir = self.config.get("source_single_run_dir") or self.summary.get("source_single_run_dir")
        source_single_run_name = None
        if source_single_run_dir:
            source_single_run_name = Path(str(source_single_run_dir).rstrip("\\/")).name
        return {
            "run_name": self.run_name,
            "mode": self.mode,
            "run_type": "cxr_demo" if self.mode == "cxr_demo" else ("multi_seed" if self.mode == "single_image_multi_seed" else "single"),
            "image_id": image_id,
            "image_name": self.config.get("image_name") or self.summary.get("image_name") or image_id,
            "created_at": self.timestamp.isoformat() if self.timestamp else _safe_iso(self.summary.get("created_at")),
            "timestamp": self.timestamp.isoformat() if self.timestamp else _safe_iso(self.summary.get("created_at")),
            "k": self.config.get("k"),
            "n_seeds": self.summary.get("n_seeds") or self.config.get("n_seeds") or len(self.config.get("seeds", []) or []),
            "algorithms": algorithms,
            "preview_metrics": self._preview_metrics(),
            "source_single_run_name": source_single_run_name,
            "warnings": self.warning_messages,
        }

    def get_run_detail(self) -> Dict[str, Any]:
        gray_path = self.run_dir / "gray.png"
        benchmark = _read_json(self.run_dir / "benchmark.json", None)
        histogram = _read_json(self.run_dir / "histogram.json", None)
        assets: Dict[str, Any] = {
            "gray": _to_rel_posix(gray_path) if gray_path.exists() else None,
            "benchmark": _to_rel_posix(self.run_dir / "benchmark.json") if (self.run_dir / "benchmark.json").exists() else None,
            "histogram": _to_rel_posix(self.run_dir / "histogram.json") if (self.run_dir / "histogram.json").exists() else None,
        }
        if self.mode == "cxr_demo":
            for filename, key in (
                ("preprocessed.png", "preprocessed"),
                ("mask.png", "mask"),
                ("overlay.png", "overlay"),
                ("gt_mask.png", "gt_mask"),
                ("convergence.json", "convergence"),
                ("thresholds.json", "thresholds"),
                ("metrics.json", "metrics"),
            ):
                path = self.run_dir / filename
                if path.exists():
                    assets[key] = _to_rel_posix(path)

        detail: Dict[str, Any] = {
            "mode": self.mode,
            "run_name": self.run_name,
            "config": self.config,
            "summary": self.summary,
            "assets": assets,
            "warnings": self.warning_messages,
        }

        if self.mode == "cxr_demo":
            detail["detail"] = {
                "metrics": _read_json(self.run_dir / "metrics.json", {}),
                "thresholds": _read_json(self.run_dir / "thresholds.json", {}),
                "convergence": _read_json(self.run_dir / "convergence.json", {}),
                "qc_info": self.summary.get("qc_info", {}),
            }
        elif self.mode == "single_image_multi_seed":
            detail["detail"] = {
                "results": _read_json(self.run_dir / "results.json", []),
                "wilcoxon": _read_json(self.run_dir / "wilcoxon.json", {}),
                "algorithms": self._load_multi_seed_algorithms(),
                "deterministic_baseline": self.summary.get("deterministic_baseline"),
                "stochastic_summary": self.summary.get("stochastic_summary"),
            }
        else:
            detail["detail"] = {
                "algorithms": self._load_single_algorithms(),
                "benchmark": benchmark,
                "histogram": histogram,
            }
        return detail


class HistoryManager:
    """Lists and exports runs under outputs/runs."""

    def __init__(self, base_dir: str = "outputs/runs"):
        self.base_dir = Path(base_dir)

    def list_runs(self, sort_by: str = "time") -> List[RunHistory]:
        if not self.base_dir.exists():
            return []
        runs: List[RunHistory] = []
        for item in self.base_dir.iterdir():
            if item.is_dir():
                try:
                    runs.append(RunHistory(str(item)))
                except Exception as exc:
                    print(f"Error loading {item}: {exc}")
        if sort_by == "time":
            runs.sort(key=lambda r: r.timestamp or datetime.min, reverse=True)
        else:
            runs.sort(key=lambda r: r.run_name)
        return runs

    def get_run(self, run_name: str) -> Optional[RunHistory]:
        run_dir = self.base_dir / run_name
        if run_dir.exists() and run_dir.is_dir():
            return RunHistory(str(run_dir))
        return None

    def get_run_detail(self, run_name: str) -> Optional[Dict[str, Any]]:
        run = self.get_run(run_name)
        return run.get_run_detail() if run else None

    def export_run(self, run_name: str) -> io.BytesIO:
        run = self.get_run(run_name)
        if run is None:
            raise FileNotFoundError(run_name)

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for file_path in run.run_dir.rglob("*"):
                if file_path.is_file():
                    arcname = Path(run_name) / file_path.relative_to(run.run_dir)
                    zf.write(file_path, arcname.as_posix())
        buffer.seek(0)
        return buffer

    def export_summary(self, output_path: str = "outputs/runs_summary.json") -> str:
        runs = self.list_runs()
        summary = {
            "total_runs": len(runs),
            "generated_at": datetime.utcnow().isoformat(),
            "runs": [r.get_summary() for r in runs],
        }
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        return output_path
