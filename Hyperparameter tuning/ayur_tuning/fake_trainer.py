#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A stand-in for finetune_ayur.py that needs no GPU, no model and no data.

It accepts the same command line (anything it does not recognise is ignored,
exactly as a real trainer with extra dataclass fields would) and writes a
``training_metrics.jsonl`` with a synthetic loss curve whose shape depends on
the learning rate:

    lr > 3.5e-4    diverges --- loss climbs, then NaN
    lr < 8.0e-5    flat     --- loss barely moves
    otherwise      converges, best around 2e-4

That gives the tuner all three stall verdicts plus healthy trials to rank, so
``test_tune.py`` can exercise the whole search end to end in a few seconds on a
laptop. Use it to check the tuner's plumbing before spending GPU hours:

    python tune_ayur.py --stage random --trials 6 --trainer fake_trainer.py \\
        --data_dir . --max-steps-per-trial 100 --poll-seconds 0.2
"""
import argparse
import json
import math
import os
import sys
import time


def loss_curve(step, total, lr, lora_r, dropout):
    """Synthetic loss. Deterministic, no numpy, mildly realistic."""
    if lr > 3.5e-4:                                   # too hot
        if step > total * 0.3:
            return float("nan")
        return 2.4 + 6.0 * (step / total)
    if lr < 8.0e-5:                                   # too cold
        return 2.4 - 1e-5 * step
    # A well-behaved run: exponential decay toward a floor that is lowest near
    # lr=2e-4, slightly lower for bigger adapters, slightly higher with dropout.
    floor = 0.55 + 12.0 * (math.log10(lr) - math.log10(2e-4)) ** 2
    floor += 0.25 * dropout - 0.03 * math.log2(max(lora_r, 1))
    decay = math.exp(-3.2 * step / max(total, 1))
    wobble = 0.02 * math.sin(step / 7.0)
    return max(floor + (2.4 - floor) * decay + wobble, 0.05)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output_dir", required=True)
    p.add_argument("--learning_rate", type=float, default=2e-4)
    p.add_argument("--lora_r", type=int, default=16)
    p.add_argument("--lora_dropout", type=float, default=0.05)
    p.add_argument("--max_steps", type=int, default=100)
    p.add_argument("--logging_steps", type=int, default=10)
    p.add_argument("--eval_steps", type=int, default=50)
    p.add_argument("--save_steps", type=int, default=100)
    p.add_argument("--step_seconds", type=float, default=0.004)
    p.add_argument("--fail", action="store_true", help="simulate a hard crash")
    p.add_argument("--oom", action="store_true", help="simulate a CUDA OOM")
    a, unknown = p.parse_known_args()

    os.makedirs(a.output_dir, exist_ok=True)
    if a.oom:
        sys.stderr.write("torch.cuda.OutOfMemoryError: CUDA out of memory.\n")
        return 1
    if a.fail:
        raise RuntimeError("simulated crash before the first log")

    print("fake_trainer: lr=%.3e r=%d dropout=%.3f steps=%d "
          "(ignored %d extra flags)"
          % (a.learning_rate, a.lora_r, a.lora_dropout, a.max_steps,
             len(unknown)))

    path = os.path.join(a.output_dir, "training_metrics.jsonl")
    with open(path, "w", encoding="utf-8") as fh:
        for step in range(1, a.max_steps + 1):
            time.sleep(a.step_seconds)
            if step % a.logging_steps == 0:
                loss = loss_curve(step, a.max_steps, a.learning_rate,
                                  a.lora_r, a.lora_dropout)
                fh.write(json.dumps({"step": step, "loss": round(loss, 6),
                                     "learning_rate": a.learning_rate,
                                     "grad_norm": 0.9}) + "\n")
                fh.flush()
            if step % a.eval_steps == 0:
                loss = loss_curve(step, a.max_steps, a.learning_rate,
                                  a.lora_r, a.lora_dropout)
                fh.write(json.dumps({"step": step,
                                     "eval_loss": round(loss + 0.05, 6)}) + "\n")
                fh.flush()
        # a checkpoint dir, so the tuner's cleanup has something to sweep
        ckpt = os.path.join(a.output_dir, "checkpoint-%d" % a.max_steps)
        os.makedirs(ckpt, exist_ok=True)
        with open(os.path.join(ckpt, "adapter_model.safetensors"), "wb") as cf:
            cf.write(b"\0" * 1024)
    print("fake_trainer: wrote %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
