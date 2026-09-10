"""Run exactly the same local pipeline as the app, without a hosted-model call."""
import argparse
from pathlib import Path
import sys
import json
import os

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "artifacts" / "cache" / "matplotlib"))
from track_sprint.pipeline import analyze
from track_sprint.schemas import AnalysisConfig

parser = argparse.ArgumentParser()
parser.add_argument("video")
parser.add_argument("--start", type=float)
parser.add_argument("--end", type=float)
parser.add_argument("--config", type=Path, help="AnalysisConfig JSON; overrides interval flags")
parser.add_argument("--side", choices=["left", "right", "unknown"], default="unknown")
parser.add_argument("--direction", choices=["left", "right"], default="left")
parser.add_argument("--model", choices=["full", "heavy"], default="full")
parser.add_argument("--output", default="artifacts/demo")
args = parser.parse_args()
last = [""]
def progress(stage, amount):
    bucket = f"{stage} {int(amount * 10) * 10}%"
    if bucket != last[0]:
        print(bucket, flush=True)
        last[0] = bucket

if args.config:
    config = AnalysisConfig.model_validate(json.loads(args.config.read_text()))
else:
    if args.start is None or args.end is None:
        parser.error("Supply --start and --end, or --config.")
    config = AnalysisConfig(start=args.start, end=args.end,
        near_side=args.side, direction=args.direction, model_variant=args.model)
result = analyze(Path(args.video), config, Path(args.output), ROOT / "models", progress)
print({k: result[k] for k in ("quality", "core_coverage", "frame_count", "review_side", "subject_issues")})
