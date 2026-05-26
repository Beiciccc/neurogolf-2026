#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import random
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import onnx
import onnx.numpy_helper as onh
import onnxruntime as ort

from validate_candidate import decode_output, grid_to_onehot, resolve_path, sha256_bytes, task_examples


ROOT = Path(__file__).resolve().parents[1]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except Exception:
        return str(path)


def read_zip_tasks(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as zf:
        return {
            os.path.basename(member): zf.read(member)
            for member in zf.namelist()
            if os.path.basename(member).startswith("task") and os.path.basename(member).endswith(".onnx")
        }


def initializer_map(model: onnx.ModelProto) -> dict[str, np.ndarray]:
    return {init.name: onh.to_array(init) for init in model.graph.initializer}


def conv_bias_issues(model: onnx.ModelProto) -> list[dict[str, Any]]:
    initializers = initializer_map(model)
    issues: list[dict[str, Any]] = []
    for node in model.graph.node:
        if node.op_type != "Conv" or len(node.input) < 3 or not node.input[2]:
            continue
        weight = initializers.get(node.input[1])
        bias = initializers.get(node.input[2])
        if weight is None or bias is None:
            issues.append(
                {
                    "node": node.name or node.output[0] if node.output else "",
                    "reason": "missing-weight-or-bias-initializer",
                    "weight": node.input[1],
                    "bias": node.input[2],
                }
            )
            continue
        out_channels = int(weight.shape[0]) if weight.ndim >= 1 else 0
        bias_len = int(bias.reshape(-1).shape[0])
        if out_channels != bias_len:
            issues.append(
                {
                    "node": node.name or node.output[0] if node.output else "",
                    "reason": "conv-bias-length-mismatch",
                    "weight": node.input[1],
                    "bias": node.input[2],
                    "out_channels": out_channels,
                    "bias_len": bias_len,
                    "weight_shape": list(weight.shape),
                    "bias_shape": list(bias.shape),
                }
            )
    return issues


def run_examples_repeated(raw: bytes, task: str, repeat: int, shuffle_seed: int) -> dict[str, Any]:
    examples = task_examples(task)
    if not examples:
        return {"ok": True, "reason": "skipped:no-public-examples", "example_count": 0, "failures": []}
    failures: list[dict[str, Any]] = []
    with tempfile.NamedTemporaryFile(suffix=".onnx", delete=False) as tmp:
        tmp.write(raw)
        tmp_path = tmp.name
    try:
        session = ort.InferenceSession(tmp_path, providers=["CPUExecutionProvider"])
        input_name = session.get_inputs()[0].name
        output_name = session.get_outputs()[0].name
        order = list(range(len(examples)))
        rng = random.Random(shuffle_seed)
        for rep in range(repeat):
            rng.shuffle(order)
            for idx in order:
                example = examples[idx]
                got = session.run([output_name], {input_name: grid_to_onehot(example["input"])})[0]
                pred = decode_output(got)
                if pred != example["output"]:
                    failures.append(
                        {
                            "repeat": rep,
                            "example_index": idx,
                            "shape": list(got.shape),
                            "reason": "public-mismatch",
                        }
                    )
                    if len(failures) >= 10:
                        return {
                            "ok": False,
                            "reason": "too-many-failures",
                            "example_count": len(examples),
                            "failures": failures,
                        }
        return {"ok": not failures, "reason": "ok" if not failures else "mismatch", "example_count": len(examples), "failures": failures}
    except Exception as exc:
        return {
            "ok": False,
            "reason": f"runtime-error:{type(exc).__name__}:{str(exc)[:240]}",
            "example_count": len(examples),
            "failures": failures,
        }
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def scan_task(task: str, raw: bytes, repeat: int, shuffle_seed: int, skip_public: bool) -> dict[str, Any]:
    row: dict[str, Any] = {
        "task": task,
        "sha256": sha256_bytes(raw),
        "bytes": len(raw),
        "ok": True,
        "errors": [],
    }
    try:
        model = onnx.load_model_from_string(raw)
    except Exception as exc:
        row["ok"] = False
        row["errors"].append(f"onnx-load:{type(exc).__name__}:{str(exc)[:200]}")
        return row
    bias = conv_bias_issues(model)
    row["conv_bias_issue_count"] = len(bias)
    row["conv_bias_issues"] = bias
    if bias:
        row["ok"] = False
        row["errors"].append("conv-bias-issues")
    if skip_public:
        row["repeated_public_examples"] = {
            "ok": True,
            "reason": "skipped:public-repeat-disabled",
            "example_count": 0,
            "failures": [],
        }
    else:
        repeated = run_examples_repeated(raw, task, repeat, shuffle_seed)
        row["repeated_public_examples"] = repeated
        if not repeated.get("ok"):
            row["ok"] = False
            row["errors"].append(str(repeated.get("reason") or "repeated-public-failed"))
    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", help="submission.zip artifact to scan")
    parser.add_argument("--task", action="append", default=[], help="Optional taskNNN.onnx filter; may be repeated")
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--shuffle-seed", type=int, default=20260526)
    parser.add_argument("--skip-public", action="store_true", help="Only run static stability lint such as Conv bias checks.")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    artifact = resolve_path(args.artifact)
    tasks = read_zip_tasks(artifact)
    selected = set(args.task)
    if selected:
        tasks = {task: raw for task, raw in tasks.items() if task in selected}
    rows = [scan_task(task, raw, args.repeat, args.shuffle_seed, args.skip_public) for task, raw in sorted(tasks.items())]
    payload = {
        "timestamp_utc": utc_now(),
        "artifact_path": rel(artifact),
        "artifact_task_count": len(tasks),
        "repeat": args.repeat,
        "skip_public": args.skip_public,
        "ok": all(row.get("ok") for row in rows),
        "failed_task_count": sum(1 for row in rows if not row.get("ok")),
        "conv_bias_issue_task_count": sum(1 for row in rows if row.get("conv_bias_issue_count")),
        "failed_tasks": [row for row in rows if not row.get("ok")],
        "tasks": rows,
    }
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        out = args.out if args.out.is_absolute() else ROOT / args.out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("artifact_path", "artifact_task_count", "repeat", "ok", "failed_task_count", "conv_bias_issue_task_count")}, indent=2, ensure_ascii=False))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
