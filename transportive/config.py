"""config.py: models, pin, budgets and prices."""
import os
from pathlib import Path

CODER = os.environ.get("CODER", "opus")                        # one switch: "opus" or "qwen"
MODELS = {"opus": "claude-opus-5-5", "qwen": "Qwen/Qwen3.8-27B-FP8"}
VLLM_URL = os.environ.get("VLLM_URL", "http://127.0.0.1:8000/v1")
SALEOR_PIN = "4cb1609a90eade14b6275a407bc7a00c35698090"           # main, just before the #19812 report
SALEOR, ASSETS = Path("saleor"), Path("assets")
REPLICA_LAG_S = 2.0                                               # recovery_min_apply_delay on the standby
BUDGET = {"turns": 40, "repair_rounds": 3, "credits": 6.0}   # per ticket
CREDITS = {"opus_in_mtok": 4.0, "opus_out_mtok": 20.0, "opus_cache_read_mtok": 0.20, "opus_cache_write_mtok": 5.0,
           "h100_hour": 2.40}                                     # Opus per million tokens, Qwen per GPU hour
COORD_DSN = os.environ.get("COORD_DSN", "postgresql://coord@127.0.0.1:5433/coord")   # leases live here, not in Saleor
