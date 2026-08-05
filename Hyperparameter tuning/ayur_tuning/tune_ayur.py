#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hyperparameter search for AyurLLM QLoRA, with a stall detector.
===============================================================

Wraps ``finetune_ayur.py``. Every hyperparameter lives in ``search_space.json``;
anything marked ``{"fixed": v}`` is passed through untouched, anything else is
searched. The tuner prints which parameters are free and which are frozen in its
first ten lines of output, so a space you meant to search but froze by accident
is visible immediately rather than after forty trials.

    python tune_ayur.py --stage baseline --data_dir /kaggle/input/ayursplit ...
    python tune_ayur.py --stage random --trials 15 ...
    python tune_ayur.py --stage bayes  --trials 25 ...

THE STALL DETECTOR
------------------
The requirement: a trial must not be left running with a loss that does not
move. Three failure modes get caught, all common and all invisible if you only
look at the final number:

  FLAT         the last --stall-window logged losses span less than --stall-eps.
               A learning rate near zero, an adapter attached to nothing, or a
               frozen base model with no trainable parameters.
  DIVERGED     loss is NaN, inf, or above --max-loss. Learning rate too high;
               the run is dead and every further step is wasted GPU time.
  NO-PROGRESS  loss wobbles but has not beaten its previous best by --min-delta
               across the whole window. Separates "stuck" from merely "noisy".

A stalled trial is killed immediately, its diagnosis recorded, and it is
reported to Optuna as *pruned* rather than as a completed trial with a bad
score. That distinction matters: a pruned trial tells TPE "no information
here", a completed bad trial tells it "this region is bad". A trial that went
flat because the LR was 1e-9 is evidence about the LR, not about the rest of the
region it was sampled from, and scoring it would steer the sampler away from
perfectly good neighbourhoods.

WHY TRIALS RUN AS SUBPROCESSES
------------------------------
Each trial is a fresh ``python finetune_ayur.py``. In-process is easier to write
and wrong in practice: PEFT adapters, optimizer state and the CUDA caching
allocator all leave residue, so trial 1 succeeds, trial 4 OOMs, and you conclude
that trial 4's hyperparameters need too much memory. They did not. A subprocess
gets a clean CUDA context every time, so an OOM is real information.

MULTI-FIDELITY
--------------
Trials stop at --max-steps-per-trial (default 400) on a --max_train_samples
subsample. That is ample to separate a good learning rate from a bad one and
nowhere near enough to finish training. Combined with the pruner most of the
search costs a fraction of one real run. The search *ranks configs*; it does not
produce a model. Retrain the winner properly --- the last thing the summary
prints is the exact command.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import shutil
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))


# ==========================================================================
# Search space
# ==========================================================================

SPEC_KINDS = {"fixed", "loguniform", "uniform", "categorical", "int"}


def load_space(path: str) -> Dict[str, Dict[str, Any]]:
    """Flatten the grouped JSON into one {param: spec} dict."""
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    flat: Dict[str, Dict[str, Any]] = {}
    for group, params in raw.items():
        if group.startswith("_") or not isinstance(params, dict):
            continue
        for name, spec in params.items():
            if name.startswith("_"):
                continue
            if not isinstance(spec, dict) or not (SPEC_KINDS & set(spec)):
                raise ValueError("bad spec for %r in group %r: %r"
                                 % (name, group, spec))
            flat[name] = spec
    if "learning_rate" not in flat:
        raise ValueError("%s defines no learning_rate" % path)
    return flat


def describe_space(space: Dict[str, Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    searched, frozen = [], []
    for name, spec in sorted(space.items()):
        (frozen if "fixed" in spec else searched).append(name)
    return searched, frozen


def sample_optuna(trial, name: str, spec: Dict[str, Any]):
    if "fixed" in spec:
        return spec["fixed"]
    if "loguniform" in spec:
        lo, hi = spec["loguniform"]
        return trial.suggest_float(name, lo, hi, log=True)
    if "uniform" in spec:
        lo, hi = spec["uniform"]
        return trial.suggest_float(name, lo, hi)
    if "categorical" in spec:
        return trial.suggest_categorical(name, spec["categorical"])
    if "int" in spec:
        lo, hi, step = (list(spec["int"]) + [1])[:3]
        return trial.suggest_int(name, lo, hi, step=step)
    raise ValueError("unrecognised spec for %r: %r" % (name, spec))


def sample_random(rng, name: str, spec: Dict[str, Any]):
    """Stage-1 random search, no sampler in the loop."""
    if "fixed" in spec:
        return spec["fixed"]
    if "loguniform" in spec:
        lo, hi = spec["loguniform"]
        return math.exp(rng.uniform(math.log(lo), math.log(hi)))
    if "uniform" in spec:
        lo, hi = spec["uniform"]
        return rng.uniform(lo, hi)
    if "categorical" in spec:
        return rng.choice(spec["categorical"])
    if "int" in spec:
        lo, hi, step = (list(spec["int"]) + [1])[:3]
        return lo + step * rng.randrange(0, (hi - lo) // step + 1)
    raise ValueError("unrecognised spec for %r: %r" % (name, spec))


# ==========================================================================
# Stall detection
# ==========================================================================

class Verdict:
    OK = "ok"
    FLAT = "flat"
    DIVERGED = "diverged"
    NO_PROGRESS = "no_progress"
    TIMEOUT = "timeout"
    OPTUNA = "pruned_by_optuna"


STALL_VERDICTS = (Verdict.FLAT, Verdict.DIVERGED, Verdict.NO_PROGRESS)


def diagnose(losses: List[float], window: int = 5, eps: float = 1e-3,
             min_delta: float = 1e-3, max_loss: float = 20.0) -> str:
    """Decide whether a loss history is worth continuing.

    Deliberately conservative. It needs a full window before it can fire on
    flatness, so the noisy first few steps of a healthy run cannot kill it, and
    it measures progress against the best value seen *before* the window rather
    than against the window's own first value. Without that second detail a run
    that improved steadily and then settled at a good loss reads as "no
    progress", when what it actually did was converge.
    """
    if not losses:
        return Verdict.OK

    last = losses[-1]
    if math.isnan(last) or math.isinf(last) or last > max_loss:
        return Verdict.DIVERGED          # fires on the first bad value, no window
    if len(losses) < window:
        return Verdict.OK

    tail = losses[-window:]
    if max(tail) - min(tail) < eps:
        return Verdict.FLAT

    prior_best = min(losses[:-window]) if len(losses) > window else tail[0]
    if prior_best - min(tail) < min_delta:
        return Verdict.NO_PROGRESS
    return Verdict.OK


def read_metrics(path: str) -> Tuple[List[float], List[Tuple[int, float]], int]:
    """(train_losses, [(step, eval_loss)], last_step) from the trainer's JSONL.

    Tolerates a half-written final line: the file is being appended to while we
    read it, so the last record is routinely truncated. Bad lines are skipped
    rather than aborting the read --- raising here would kill a healthy trial
    over something that fixes itself ten seconds later.
    """
    train: List[float] = []
    evals: List[Tuple[int, float]] = []
    last_step = 0
    if not os.path.exists(path):
        return train, evals, last_step
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError:
        return train, evals, last_step

    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(rec, dict):
            continue
        try:
            step = int(rec.get("step", 0) or 0)
        except (TypeError, ValueError):
            step = 0
        last_step = max(last_step, step)
        if "loss" in rec:
            try:
                train.append(float(rec["loss"]))
            except (TypeError, ValueError):
                pass
        if "eval_loss" in rec:
            try:
                evals.append((step, float(rec["eval_loss"])))
            except (TypeError, ValueError):
                pass
    return train, evals, last_step


# ==========================================================================
# One trial
# ==========================================================================

DERIVED = {"lora_alpha_mult"}      # consumed by the tuner, not a trainer flag


def build_command(cfg: Dict[str, Any], a, out_dir: str) -> List[str]:
    """Translate a sampled config into a finetune_ayur.py command line."""
    lora_r = int(cfg["lora_r"])
    alpha = int(lora_r * cfg.get("lora_alpha_mult", 2))

    # load_best_model_at_end is hardcoded on in the trainer, and transformers
    # then requires save_steps to be a whole multiple of eval_steps. Saving once
    # at the end satisfies that and writes one checkpoint instead of eight.
    save_steps = a.max_steps_per_trial
    if save_steps % a.eval_steps:
        save_steps = a.eval_steps * max(1, save_steps // a.eval_steps)

    cmd = [
        sys.executable, a.trainer,
        "--model_name_or_path", a.model,
        "--data_dir", a.data_dir,
        "--train_file", a.train_file,
        "--eval_file", a.eval_file,
        "--output_dir", out_dir,
        "--max_steps", str(a.max_steps_per_trial),
        "--logging_steps", str(a.logging_steps),
        "--eval_strategy", "steps",
        "--eval_steps", str(a.eval_steps),
        "--save_strategy", "steps",
        "--save_steps", str(save_steps),
        "--save_total_limit", "1",
        "--report_to", "none",
        "--seed", str(a.seed),
        "--lora_alpha", str(alpha),
    ]
    if a.max_train_samples:
        cmd += ["--max_train_samples", str(a.max_train_samples)]
    if a.max_eval_samples:
        cmd += ["--max_eval_samples", str(a.max_eval_samples)]

    for key, val in cfg.items():
        if key in DERIVED:
            continue
        if isinstance(val, bool):
            cmd += ["--%s" % key, "True" if val else "False"]
        elif isinstance(val, float):
            cmd += ["--%s" % key, repr(val)]
        else:
            cmd += ["--%s" % key, str(val)]
    return cmd


def sweep_checkpoints(out_dir: str) -> None:
    """Delete adapter checkpoints written during a trial.

    A rank-64 adapter on a 2B model is a few hundred MB. Twenty-five trials of
    them fill /kaggle/working and the run dies on the last trial with a disk
    error that looks nothing like its cause. The search only ever reads the
    metrics file; the weights are noise.
    """
    for path in glob.glob(os.path.join(out_dir, "checkpoint-*")):
        shutil.rmtree(path, ignore_errors=True)
    for name in ("adapter_model.safetensors", "adapter_model.bin",
                 "optimizer.pt", "scheduler.pt"):
        try:
            os.remove(os.path.join(out_dir, name))
        except OSError:
            pass


def run_trial(cfg: Dict[str, Any], a, trial_id: str, report=None) -> Dict[str, Any]:
    """Launch a trial, watch its loss, kill it if it stalls."""
    out_dir = os.path.join(a.outdir, "trial_%s" % trial_id)
    os.makedirs(out_dir, exist_ok=True)
    metrics_path = os.path.join(out_dir, "training_metrics.jsonl")
    if os.path.exists(metrics_path):
        os.remove(metrics_path)          # stale file from a previous attempt

    cmd = build_command(cfg, a, out_dir)
    log_path = os.path.join(out_dir, "trial.log")
    log = open(log_path, "w", encoding="utf-8")
    log.write(" ".join(cmd) + "\n\n")
    log.flush()

    started = time.time()
    proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, cwd=HERE)

    verdict, killed, n_reported = Verdict.OK, False, 0
    while proc.poll() is None:
        time.sleep(a.poll_seconds)
        train, evals, step = read_metrics(metrics_path)

        verdict = diagnose(train, a.stall_window, a.stall_eps,
                           a.min_delta, a.max_loss)
        if verdict != Verdict.OK:
            print("      STALL [%s] at step %d --- killing trial" % (verdict, step),
                  flush=True)
            proc.kill()
            killed = True
            break

        # Feed Optuna every new eval so its pruner can act mid-trial.
        if report is not None and len(evals) > n_reported:
            try:
                for ev_step, ev_loss in evals[n_reported:]:
                    report(ev_loss, ev_step)
                n_reported = len(evals)
            except Exception:                     # optuna.TrialPruned
                print("      pruned by Optuna at step %d" % step, flush=True)
                proc.kill()
                killed, verdict = True, Verdict.OPTUNA
                break

        if a.trial_timeout and time.time() - started > a.trial_timeout:
            print("      TIMEOUT after %.0fs --- killing trial"
                  % (time.time() - started), flush=True)
            proc.kill()
            killed, verdict = True, Verdict.TIMEOUT
            break

    try:
        proc.wait(timeout=60)
    except subprocess.TimeoutExpired:
        proc.terminate()
    log.close()

    train, evals, step = read_metrics(metrics_path)
    rc = proc.returncode
    eval_losses = [v for _, v in evals]
    best_eval = min(eval_losses) if eval_losses else None

    if killed:
        status = "stalled" if verdict in STALL_VERDICTS else "pruned"
    elif rc == 0 and best_eval is not None:
        status = "ok"
    else:
        # A crash with no metrics is an infrastructure failure, not a verdict on
        # the hyperparameters. Conflating the two teaches the sampler that
        # "lora_r=64 is bad" when what happened is that lora_r=64 did not fit.
        tail = ""
        try:
            with open(log_path, encoding="utf-8", errors="replace") as fh:
                tail = fh.read()[-4000:]
        except OSError:
            pass
        status = "oom" if ("CUDA out of memory" in tail
                           or "OutOfMemoryError" in tail) else "failed"

    if not a.keep_checkpoints:
        sweep_checkpoints(out_dir)

    return {
        "trial": trial_id,
        "status": status,
        "verdict": verdict,
        "best_eval_loss": best_eval,
        "best_train_loss": min(train) if train else None,
        "final_train_loss": train[-1] if train else None,
        "n_train_logs": len(train),
        "n_evals": len(evals),
        "steps": step,
        "seconds": round(time.time() - started, 1),
        "returncode": rc,
        "effective_batch": int(cfg.get("per_device_train_batch_size", 1))
                           * int(cfg.get("gradient_accumulation_steps", 1)),
        "log": log_path,
        "config": cfg,
    }


def one_line(cfg: Dict[str, Any]) -> str:
    eff = (int(cfg.get("per_device_train_batch_size", 1))
           * int(cfg.get("gradient_accumulation_steps", 1)))
    return ("lr=%.2e r=%s ax%s drop=%.3f wd=%.3f warm=%.3f %s len=%s batch=%d"
            % (cfg["learning_rate"], cfg["lora_r"], cfg.get("lora_alpha_mult", 2),
               cfg["lora_dropout"], cfg["weight_decay"], cfg["warmup_ratio"],
               cfg["lr_scheduler_type"], cfg["max_seq_length"], eff))


# ==========================================================================
# Stages
# ==========================================================================

BASELINE = {
    "learning_rate": 2e-4, "lr_scheduler_type": "cosine", "warmup_ratio": 0.03,
    "weight_decay": 0.01, "optim": "paged_adamw_8bit", "adam_beta1": 0.9,
    "adam_beta2": 0.999, "adam_epsilon": 1e-8, "max_grad_norm": 1.0,
    "num_train_epochs": 1, "label_smoothing_factor": 0.0,
    "per_device_train_batch_size": 2, "gradient_accumulation_steps": 8,
    "lora_r": 16, "lora_alpha_mult": 2, "lora_dropout": 0.05,
    "max_seq_length": 1024,
}


def stage_baseline(a, space):
    cfg = {k: s["fixed"] for k, s in space.items() if "fixed" in s}
    cfg.update({k: v for k, v in BASELINE.items() if k in space})
    print("\nBASELINE  %s" % one_line(cfg))
    res = run_trial(cfg, a, "baseline")
    print("   -> %s | eval %s | %d logs | %d steps | %.0fs"
          % (res["status"], res["best_eval_loss"], res["n_train_logs"],
             res["steps"], res["seconds"]))
    if res["status"] != "ok":
        print("\n   The baseline did not train cleanly. Fix that before searching ---")
        print("   a search over a broken setup only finds the least broken corner.")
        print("   Log: %s" % res["log"])
    return [res]


def stage_random(a, space, n, done=()):
    import random
    rng = random.Random(a.seed)
    results = list(done)
    seen = {r["trial"] for r in results}
    for i in range(n):
        cfg = {k: sample_random(rng, k, s) for k, s in space.items()}
        tid = "rand%02d" % i
        if tid in seen:
            print("\n[random %d/%d] %s already done --- skipping" % (i + 1, n, tid))
            continue
        print("\n[random %d/%d] %s" % (i + 1, n, one_line(cfg)), flush=True)
        res = run_trial(cfg, a, tid)
        print("   -> %s | eval %s | %d steps | %.0fs"
              % (res["status"], res["best_eval_loss"], res["steps"], res["seconds"]))
        results.append(res)
        save_results(a, results)
    return results


def stage_bayes(a, space, n, done=()):
    import optuna
    from optuna.pruners import HyperbandPruner, MedianPruner
    from optuna.samplers import TPESampler

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    pruner = (HyperbandPruner(min_resource=a.eval_steps,
                              max_resource=a.max_steps_per_trial,
                              reduction_factor=3)
              if a.pruner == "hyperband"
              else MedianPruner(n_startup_trials=a.n_startup,
                                n_warmup_steps=a.eval_steps))

    storage = "sqlite:///%s" % os.path.join(a.outdir, "study.db")
    study = optuna.create_study(
        study_name=a.study_name, storage=storage, load_if_exists=True,
        direction="minimize",
        sampler=TPESampler(seed=a.seed, n_startup_trials=a.n_startup),
        pruner=pruner)
    if study.trials:
        print("\nresuming study %r: %d trials already recorded"
              % (a.study_name, len(study.trials)))

    results = list(done)

    def objective(trial):
        cfg = {k: sample_optuna(trial, k, s) for k, s in space.items()}
        print("\n[optuna %d] %s" % (trial.number, one_line(cfg)), flush=True)

        def report(value, step):
            trial.report(value, step)
            if trial.should_prune():
                raise optuna.TrialPruned()

        res = run_trial(cfg, a, "opt%03d" % trial.number, report=report)
        res["optuna_trial"] = trial.number
        results.append(res)
        save_results(a, results)
        print("   -> %s | eval %s | %d steps | %.0fs"
              % (res["status"], res["best_eval_loss"], res["steps"], res["seconds"]))

        if res["status"] != "ok" or res["best_eval_loss"] is None:
            raise optuna.TrialPruned()
        return res["best_eval_loss"]

    # catch= stops one exploding trial from ending a 25-trial overnight run.
    study.optimize(objective, n_trials=n, catch=(Exception,))
    return results, study


# ==========================================================================
# Reporting
# ==========================================================================

def save_results(a, results) -> None:
    path = os.path.join(a.outdir, "results.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=2, default=str)
    os.replace(tmp, path)                 # never leave a half-written results.json


def load_results(a) -> List[Dict[str, Any]]:
    path = os.path.join(a.outdir, "results.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def retrain_command(a, cfg: Dict[str, Any]) -> str:
    alpha = int(int(cfg["lora_r"]) * cfg.get("lora_alpha_mult", 2))
    return "\n".join([
        "python finetune_ayur.py \\",
        "    --model_name_or_path %s \\" % a.model,
        '    --data_dir "%s" \\' % a.data_dir,
        '    --train_file "%s" --eval_file "%s" \\' % (a.train_file, a.eval_file),
        "    --output_dir ./ayur_best \\",
        "    --learning_rate %.4e --lr_scheduler_type %s --warmup_ratio %.4f \\"
        % (cfg["learning_rate"], cfg["lr_scheduler_type"], cfg["warmup_ratio"]),
        "    --weight_decay %.4f --max_grad_norm %.3f \\"
        % (cfg["weight_decay"], cfg["max_grad_norm"]),
        "    --optim %s --adam_beta2 %s \\" % (cfg["optim"], cfg["adam_beta2"]),
        "    --lora_r %d --lora_alpha %d --lora_dropout %.4f \\"
        % (int(cfg["lora_r"]), alpha, cfg["lora_dropout"]),
        "    --max_seq_length %d \\" % int(cfg["max_seq_length"]),
        "    --per_device_train_batch_size %d --gradient_accumulation_steps %d \\"
        % (int(cfg["per_device_train_batch_size"]),
           int(cfg["gradient_accumulation_steps"])),
        "    --num_train_epochs 2 --logging_steps 10 --save_steps 200",
    ])


def summarise(a, results, study=None):
    ok = [r for r in results
          if r.get("status") == "ok" and r.get("best_eval_loss") is not None]
    ok.sort(key=lambda r: r["best_eval_loss"])

    print("\n" + "=" * 76)
    print("SEARCH SUMMARY  --- %d trials" % len(results))
    print("=" * 76)
    print("outcomes      : %s" % dict(Counter(r.get("status") for r in results)))
    stalled = [r for r in results if r.get("status") == "stalled"]
    if stalled:
        print("stall reasons : %s" % dict(Counter(r["verdict"] for r in stalled)))
        print("                killed on the spot and reported to the sampler as")
        print("                pruned, not as a bad score --- a flat trial says")
        print("                nothing about the region it was drawn from.")
    print("gpu time      : %.2f h across all trials"
          % (sum(r.get("seconds", 0) for r in results) / 3600.0))

    if not ok:
        print("\nNo trial completed. Read trial.log in the newest trial_* folder;")
        print("the first traceback in it is almost always the whole story.")
        return None

    print("\ntop %d by validation loss:" % min(5, len(ok)))
    print("  %-8s %-10s %-4s %-6s %-6s %-6s %-21s %-5s %s"
          % ("eval", "lr", "r", "drop", "wd", "warm", "sched", "len", "batch"))
    for r in ok[:5]:
        c = r["config"]
        print("  %-8.4f %-10.2e %-4s %-6.3f %-6.3f %-6.3f %-21s %-5s %d"
              % (r["best_eval_loss"], c["learning_rate"], c["lora_r"],
                 c["lora_dropout"], c["weight_decay"], c["warmup_ratio"],
                 c["lr_scheduler_type"], c["max_seq_length"], r["effective_batch"]))

    best = ok[0]
    cmd = retrain_command(a, best["config"])
    payload = {
        "best_eval_loss": best["best_eval_loss"],
        "trial": best["trial"],
        "config": best["config"],
        "lora_alpha": int(int(best["config"]["lora_r"])
                          * best["config"].get("lora_alpha_mult", 2)),
        "effective_batch": best["effective_batch"],
        "retrain_command": cmd,
        "caveat": ("trials were capped at %d steps on %s train samples. This "
                   "ranks configs; it is not a trained model. Retrain before "
                   "believing the loss."
                   % (a.max_steps_per_trial, a.max_train_samples or "all")),
    }
    with open(os.path.join(a.outdir, "best_config.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)

    print("\nbest -> %s" % os.path.join(a.outdir, "best_config.json"))
    print("\nretrain it properly:\n")
    print(cmd)

    if study is not None:
        try:
            import optuna
            imp = optuna.importance.get_param_importances(study)
            print("\nparameter importance (share of variance explained):")
            for k, v in list(imp.items())[:8]:
                print("   %-30s %.3f" % (k, v))
            print('   Anything near zero was not worth searching. Freeze it with')
            print('   {"fixed": ...} and spend those trials on what moved.')
        except Exception as exc:
            print("\n(importance unavailable: %s)" % type(exc).__name__)
    return best


# ==========================================================================
# CLI
# ==========================================================================

def build_argparser():
    p = argparse.ArgumentParser(
        description="Hyperparameter search for AyurLLM QLoRA, with a stall detector.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("--stage", choices=["baseline", "random", "bayes"], default="random",
                   help="baseline: one sanity run. random: broad sweep. "
                        "bayes: TPE + pruning, run it after random.")
    p.add_argument("--trials", type=int, default=15)
    p.add_argument("--space", default="search_space.json")
    p.add_argument("--outdir", default="/kaggle/working/ayur_tune")
    p.add_argument("--study-name", dest="study_name", default="ayur")
    p.add_argument("--trainer", default=os.path.join(HERE, "finetune_ayur.py"))
    p.add_argument("--resume", action="store_true",
                   help="keep results.json and skip finished random trials")

    p.add_argument("--model", default="nishm27/sarvam-1-TRIM")
    p.add_argument("--data_dir", required=True)
    p.add_argument("--train_file", default="train.json")
    p.add_argument("--eval_file", default="validation.json")

    p.add_argument("--max-steps-per-trial", dest="max_steps_per_trial",
                   type=int, default=400)
    p.add_argument("--eval-steps", dest="eval_steps", type=int, default=50)
    p.add_argument("--logging-steps", dest="logging_steps", type=int, default=10)
    p.add_argument("--max_train_samples", type=int, default=8000,
                   help="subsample per trial; the search ranks configs and does "
                        "not need the whole corpus")
    p.add_argument("--max_eval_samples", type=int, default=500)

    g = p.add_argument_group("stall detection")
    g.add_argument("--stall-window", dest="stall_window", type=int, default=5,
                   help="consecutive logged losses to judge (your '5 iterations')")
    g.add_argument("--stall-eps", dest="stall_eps", type=float, default=1e-3,
                   help="window range below this counts as flat")
    g.add_argument("--min-delta", dest="min_delta", type=float, default=1e-3,
                   help="improvement over prior best needed to count as progress")
    g.add_argument("--max-loss", dest="max_loss", type=float, default=20.0,
                   help="above this, or NaN/inf, the run is diverged")
    g.add_argument("--poll-seconds", dest="poll_seconds", type=float, default=10.0)
    g.add_argument("--trial-timeout", dest="trial_timeout", type=float, default=0,
                   help="wall-clock seconds per trial; 0 disables")

    p.add_argument("--pruner", choices=["median", "hyperband"], default="median")
    p.add_argument("--n-startup", dest="n_startup", type=int, default=5,
                   help="random trials before TPE / the pruner use history")
    p.add_argument("--keep-checkpoints", dest="keep_checkpoints",
                   action="store_true", help="do not delete trial adapters")
    p.add_argument("--seed", type=int, default=20260803)
    return p


def main(argv=None):
    a = build_argparser().parse_args(argv)

    if not os.path.isabs(a.space):
        a.space = os.path.abspath(a.space if os.path.exists(a.space)
                                  else os.path.join(HERE, a.space))
    if not os.path.exists(a.space):
        raise SystemExit("search space not found: %s" % a.space)
    if not os.path.exists(a.trainer):
        raise SystemExit("trainer not found: %s" % a.trainer)
    if a.stall_window < 2:
        raise SystemExit("--stall-window must be at least 2")
    if a.max_steps_per_trial < a.stall_window * a.logging_steps:
        raise SystemExit(
            "--max-steps-per-trial %d cannot produce %d logs at --logging-steps "
            "%d, so the stall detector would never see a full window."
            % (a.max_steps_per_trial, a.stall_window, a.logging_steps))

    os.makedirs(a.outdir, exist_ok=True)
    space = load_space(a.space)
    searched, frozen = describe_space(space)

    print("=" * 76)
    print("AyurLLM hyperparameter search --- stage: %s" % a.stage)
    print("=" * 76)
    print("model      : %s" % a.model)
    print("data       : %s   (%s / %s)" % (a.data_dir, a.train_file, a.eval_file))
    print("trainer    : %s" % a.trainer)
    print("budget     : %d trials x %d steps x %s train samples"
          % (a.trials, a.max_steps_per_trial, a.max_train_samples or "all"))
    print("stall rule : kill when the last %d logged losses span < %g,"
          % (a.stall_window, a.stall_eps))
    print("             or fail to beat the prior best by %g," % a.min_delta)
    print("             or go NaN/inf/above %g." % a.max_loss)
    print("             at --logging-steps %d that window is %d steps."
          % (a.logging_steps, a.stall_window * a.logging_steps))
    print("\nSEARCHED (%2d): %s" % (len(searched), ", ".join(searched)))
    print("FROZEN   (%2d): %s" % (len(frozen), ", ".join(frozen)))

    with open(os.path.join(a.outdir, "run_meta.json"), "w", encoding="utf-8") as fh:
        json.dump({"started": datetime.now().isoformat(timespec="seconds"),
                   "stage": a.stage, "args": vars(a),
                   "searched": searched, "frozen": frozen},
                  fh, indent=2, default=str)

    done = load_results(a) if a.resume else []
    study = None
    if a.stage == "baseline":
        results = stage_baseline(a, space)
    elif a.stage == "random":
        results = stage_random(a, space, a.trials, done)
    else:
        results, study = stage_bayes(a, space, a.trials, done)

    save_results(a, results)
    summarise(a, results, study)


if __name__ == "__main__":
    main()
