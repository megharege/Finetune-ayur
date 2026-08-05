#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pre-flight for tune_ayur.py. No GPU, no model, no data --- runs in seconds.

    python test_tune.py

Checks the search space parses and samples inside its bounds, the stall
detector fires on the cases it should and stays quiet on the ones it should
not, the generated command line is one a trainer can actually parse, and then
runs a real end-to-end search against ``fake_trainer.py`` --- including the
Optuna study and its SQLite resume --- so that when you spend GPU hours the
only new variable is the model.
"""
import json
import math
import os
import random
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import tune_ayur as T                                            # noqa: E402

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print("  %s %s%s" % ("PASS" if cond else "FAIL", name,
                         ("  <- %s" % detail) if detail and not cond else ""))


def section(title):
    print("\n" + title)
    print("-" * len(title))


# ==========================================================================
section("1  search space")
# ==========================================================================

space = T.load_space(os.path.join(HERE, "search_space.json"))
searched, frozen = T.describe_space(space)
check("space parses", len(space) >= 20, "%d params" % len(space))
check("learning_rate is searched", "learning_rate" in searched)
check("something is frozen", len(frozen) > 0, "%d frozen" % len(frozen))

rng = random.Random(0)
bad = []
for _ in range(400):
    cfg = {k: T.sample_random(rng, k, s) for k, s in space.items()}
    for k, s in space.items():
        v = cfg[k]
        if "loguniform" in s or "uniform" in s:
            lo, hi = s.get("loguniform") or s["uniform"]
            if not (lo - 1e-12 <= v <= hi + 1e-12):
                bad.append((k, v))
        elif "categorical" in s and v not in s["categorical"]:
            bad.append((k, v))
        elif "fixed" in s and v != s["fixed"]:
            bad.append((k, v))
check("400 random samples all in range", not bad, str(bad[:3]))

lrs = [T.sample_random(rng, "learning_rate", space["learning_rate"])
       for _ in range(2000)]
lo, hi = space["learning_rate"]["loguniform"]
mid = math.sqrt(lo * hi)
below = sum(1 for x in lrs if x < mid)
check("log-uniform LR is log-uniform, not linear",
      0.45 < below / len(lrs) < 0.55,
      "%.3f below the geometric mean (want ~0.50)" % (below / len(lrs)))

try:
    T.load_space(os.path.join(HERE, "search_space.json") + ".missing")
    check("missing space file raises", False)
except (OSError, IOError):
    check("missing space file raises", True)

with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
    json.dump({"g": {"learning_rate": {"loguniform": [1e-5, 1e-3]},
                     "nonsense": {"typo": 3}}}, fh)
    junk_path = fh.name
try:
    T.load_space(junk_path)
    check("malformed spec raises", False)
except ValueError:
    check("malformed spec raises", True)
os.unlink(junk_path)


# ==========================================================================
section("2  stall detector")
# ==========================================================================

W = dict(window=5, eps=1e-3, min_delta=1e-3, max_loss=20.0)

check("healthy decay -> ok",
      T.diagnose([2.4, 2.1, 1.9, 1.7, 1.55, 1.44, 1.36], **W) == T.Verdict.OK)
check("flat for 5 -> flat",
      T.diagnose([2.4, 2.1, 1.9, 1.9001, 1.9002, 1.9001, 1.9], **W)
      == T.Verdict.FLAT)
check("exactly identical values -> flat",
      T.diagnose([1.5] * 5, **W) == T.Verdict.FLAT)
check("NaN -> diverged",
      T.diagnose([2.4, 2.1, float("nan")], **W) == T.Verdict.DIVERGED)
check("inf -> diverged",
      T.diagnose([2.4, float("inf")], **W) == T.Verdict.DIVERGED)
check("loss above max_loss -> diverged",
      T.diagnose([2.4, 9.0, 44.0], **W) == T.Verdict.DIVERGED)
check("noisy but not improving -> no_progress",
      T.diagnose([2.4, 1.19, 1.31, 1.1895, 1.32, 1.20, 1.31], **W)
      == T.Verdict.NO_PROGRESS,
      "wobbles by 0.13 but beats its prior best by only 0.0005")
check("noisy and still improving -> ok",
      T.diagnose([2.4, 1.19, 1.31, 1.09, 1.22, 1.02, 1.14], **W)
      == T.Verdict.OK,
      "same wobble, but the floor keeps dropping")
check("empty history -> ok", T.diagnose([], **W) == T.Verdict.OK)
check("short history never fires on flatness",
      T.diagnose([1.5, 1.5, 1.5, 1.5], **W) == T.Verdict.OK,
      "4 < window of 5")
check("diverged fires without a full window",
      T.diagnose([float("nan")], **W) == T.Verdict.DIVERGED)
check("converged-then-plateaued is not punished as flat",
      T.diagnose([2.4, 1.8, 1.2, 0.80, 0.61, 0.58, 0.545, 0.52, 0.50], **W)
      == T.Verdict.OK,
      "steady small gains must read as progress")
check("window of 5 needs 5 logs, not 4",
      T.diagnose([0.5, 0.5, 0.5, 0.5], **W) == T.Verdict.OK
      and T.diagnose([0.5] * 5, **W) == T.Verdict.FLAT)

big = dict(W, window=3)
check("window is configurable",
      T.diagnose([1.0, 1.0, 1.0], **big) == T.Verdict.FLAT)


# ==========================================================================
section("3  metrics reader")
# ==========================================================================

tmp = tempfile.mkdtemp(prefix="ayurtune_")
mpath = os.path.join(tmp, "training_metrics.jsonl")
with open(mpath, "w", encoding="utf-8") as fh:
    fh.write(json.dumps({"step": 10, "loss": 2.4}) + "\n")
    fh.write("\n")
    fh.write(json.dumps({"step": 20, "loss": 2.1}) + "\n")
    fh.write(json.dumps({"step": 20, "eval_loss": 2.2}) + "\n")
    fh.write(json.dumps({"step": 30, "loss": float("nan")}).replace("NaN", "NaN")
             + "\n")
    fh.write('{"step": 40, "loss": 1.9')            # truncated mid-write

tr, ev, step = T.read_metrics(mpath)
check("reads train losses", len(tr) == 3, str(tr))
check("reads (step, eval_loss) pairs", ev == [(20, 2.2)], str(ev))
check("tracks last step", step == 30, str(step))
check("survives a truncated final line", True)
check("NaN survives the round trip", math.isnan(tr[-1]))
check("missing file is empty, not an error",
      T.read_metrics(os.path.join(tmp, "nope.jsonl")) == ([], [], 0))


# ==========================================================================
section("4  generated command line")
# ==========================================================================


class Args(object):
    pass


a = Args()
a.trainer = os.path.join(HERE, "fake_trainer.py")
a.model = "nishm27/sarvam-1-TRIM"
a.data_dir = "/kaggle/input/ayursplit"
a.train_file = "train - Hybrid.jsonl"
a.eval_file = "validation - Hybrid.jsonl"
a.max_steps_per_trial = 400
a.eval_steps = 50
a.logging_steps = 10
a.max_train_samples = 8000
a.max_eval_samples = 500
a.seed = 7
a.outdir = tmp
a.keep_checkpoints = False
a.stall_window, a.stall_eps, a.min_delta, a.max_loss = 5, 1e-3, 1e-3, 20.0
a.poll_seconds, a.trial_timeout = 0.05, 0

cfg = {k: T.sample_random(random.Random(1), k, s) for k, s in space.items()}
cmd = T.build_command(cfg, a, os.path.join(tmp, "trial_x"))
flags = [c for c in cmd if c.startswith("--")]

check("every searched HP reaches the trainer",
      all(("--%s" % k) in flags for k in space if k not in T.DERIVED),
      str([k for k in space if k not in T.DERIVED and ("--%s" % k) not in flags]))
check("lora_alpha_mult is not passed as a flag", "--lora_alpha_mult" not in flags)
check("lora_alpha is derived and passed", "--lora_alpha" in flags)
alpha = int(cmd[cmd.index("--lora_alpha") + 1])
check("alpha == r * mult",
      alpha == int(cfg["lora_r"]) * cfg["lora_alpha_mult"],
      "%d vs %s*%s" % (alpha, cfg["lora_r"], cfg["lora_alpha_mult"]))
check("no duplicated flags", len(flags) == len(set(flags)),
      str([f for f in flags if flags.count(f) > 1]))
check("filenames with spaces stay one argv element",
      "train - Hybrid.jsonl" in cmd)
check("save_steps is a multiple of eval_steps (load_best_model_at_end)",
      int(cmd[cmd.index("--save_steps") + 1]) % a.eval_steps == 0)
lr_str = cmd[cmd.index("--learning_rate") + 1]
check("float round-trips at full precision",
      float(lr_str) == cfg["learning_rate"], lr_str)
check("bools render as True/False, not 1/0",
      all(cmd[cmd.index("--%s" % k) + 1] in ("True", "False")
          for k, v in cfg.items() if isinstance(v, bool)))

a.eval_steps = 60                      # 400 is not a multiple of 60
cmd2 = T.build_command(cfg, a, os.path.join(tmp, "trial_x"))
check("save_steps is snapped when it would not divide",
      int(cmd2[cmd2.index("--save_steps") + 1]) % 60 == 0,
      cmd2[cmd2.index("--save_steps") + 1])
a.eval_steps = 50


# ==========================================================================
section("5  CLI guards")
# ==========================================================================


def cli_fails(argv):
    try:
        T.main(argv)
        return False
    except SystemExit as exc:
        return exc.code not in (0, None)


base = ["--data_dir", tmp, "--outdir", os.path.join(tmp, "guard"),
        "--trainer", os.path.join(HERE, "fake_trainer.py")]
check("rejects a stall window the run cannot fill",
      cli_fails(base + ["--max-steps-per-trial", "20", "--logging-steps", "10",
                        "--stall-window", "5"]))
check("rejects --stall-window 1",
      cli_fails(base + ["--stall-window", "1"]))
check("rejects a missing search space",
      cli_fails(base + ["--space", "does_not_exist.json"]))
check("rejects a missing trainer",
      cli_fails(["--data_dir", tmp, "--outdir", os.path.join(tmp, "guard"),
                 "--trainer", "/nonexistent/trainer.py"]))


# ==========================================================================
section("6  end-to-end random search against fake_trainer.py")
# ==========================================================================

e2e = os.path.join(tmp, "e2e")
rc = subprocess.call(
    [sys.executable, os.path.join(HERE, "tune_ayur.py"),
     "--stage", "random", "--trials", "8",
     "--trainer", os.path.join(HERE, "fake_trainer.py"),
     "--data_dir", tmp, "--outdir", e2e,
     "--max-steps-per-trial", "100", "--eval-steps", "25",
     "--logging-steps", "10", "--poll-seconds", "0.15", "--seed", "3"],
    stdout=open(os.path.join(tmp, "random.log"), "w"),
    stderr=subprocess.STDOUT)
check("random stage exits 0", rc == 0, "rc=%d" % rc)

res = json.load(open(os.path.join(e2e, "results.json"), encoding="utf-8"))
statuses = {}
for r in res:
    statuses[r["status"]] = statuses.get(r["status"], 0) + 1
print("     statuses: %s" % statuses)
check("ran 8 trials", len(res) == 8, str(len(res)))
check("some trials completed", statuses.get("ok", 0) > 0)
check("the stall detector fired", statuses.get("stalled", 0) > 0, str(statuses))

verdicts = {r["verdict"] for r in res if r["status"] == "stalled"}
print("     stall verdicts seen: %s" % sorted(verdicts))
check("caught a flat run", T.Verdict.FLAT in verdicts or
      T.Verdict.NO_PROGRESS in verdicts, str(verdicts))
check("caught a diverged run", T.Verdict.DIVERGED in verdicts, str(verdicts))

stalled = [r for r in res if r["status"] == "stalled"]
finished = [r for r in res if r["status"] == "ok"]
if stalled and finished:
    check("stalled trials are killed early, not run to completion",
          max(r["steps"] for r in stalled) < max(r["steps"] for r in finished),
          "stalled max step %d vs ok max step %d"
          % (max(r["steps"] for r in stalled), max(r["steps"] for r in finished)))

best_path = os.path.join(e2e, "best_config.json")
check("best_config.json written", os.path.exists(best_path))
if os.path.exists(best_path):
    best = json.load(open(best_path, encoding="utf-8"))
    check("best is the lowest completed eval loss",
          abs(best["best_eval_loss"]
              - min(r["best_eval_loss"] for r in finished)) < 1e-9)
    check("retrain command is included and complete",
          "--lora_alpha" in best["retrain_command"]
          and "--learning_rate" in best["retrain_command"])
    check("best config carries the caveat about capped steps",
          "ranks configs" in best["caveat"])

leftover = []
for d in os.listdir(e2e):
    p = os.path.join(e2e, d)
    if os.path.isdir(p):
        leftover += [x for x in os.listdir(p) if x.startswith("checkpoint-")]
check("trial checkpoints are swept", not leftover, str(leftover[:3]))


# ==========================================================================
section("7  Bayesian stage + SQLite resume")
# ==========================================================================

try:
    import optuna                                            # noqa: F401
    have_optuna = True
except ImportError:
    have_optuna = False
    print("  SKIP optuna not installed (pip install optuna)")

if have_optuna:
    bdir = os.path.join(tmp, "bayes")
    cmd_b = [sys.executable, os.path.join(HERE, "tune_ayur.py"),
             "--stage", "bayes", "--trials", "5",
             "--trainer", os.path.join(HERE, "fake_trainer.py"),
             "--data_dir", tmp, "--outdir", bdir,
             "--max-steps-per-trial", "100", "--eval-steps", "25",
             "--logging-steps", "10", "--poll-seconds", "0.15",
             "--n-startup", "2", "--seed", "5"]
    rc = subprocess.call(cmd_b, stdout=open(os.path.join(tmp, "bayes1.log"), "w"),
                         stderr=subprocess.STDOUT)
    check("bayes stage exits 0", rc == 0, "rc=%d" % rc)
    check("sqlite study created", os.path.exists(os.path.join(bdir, "study.db")))

    import optuna
    st = optuna.load_study(study_name="ayur",
                           storage="sqlite:///%s" % os.path.join(bdir, "study.db"))
    n1 = len(st.trials)
    check("study recorded 5 trials", n1 == 5, str(n1))
    check("stalled trials are recorded as PRUNED, not as a bad score",
          any(t.state == optuna.trial.TrialState.PRUNED for t in st.trials),
          str([t.state.name for t in st.trials]))

    rc = subprocess.call(cmd_b + ["--resume"],
                         stdout=open(os.path.join(tmp, "bayes2.log"), "w"),
                         stderr=subprocess.STDOUT)
    st2 = optuna.load_study(study_name="ayur",
                            storage="sqlite:///%s" % os.path.join(bdir, "study.db"))
    check("second run resumes the same study rather than restarting",
          len(st2.trials) == n1 + 5, "%d -> %d" % (n1, len(st2.trials)))
    log2 = open(os.path.join(tmp, "bayes2.log"), encoding="utf-8").read()
    check("resume is announced", "resuming study" in log2)


# ==========================================================================
section("8  failure modes are classified, not scored")
# ==========================================================================

a.outdir = os.path.join(tmp, "fails")
os.makedirs(a.outdir, exist_ok=True)
a.trainer = os.path.join(HERE, "fake_trainer.py")

small = dict(cfg)
small["learning_rate"] = 2e-4

orig_build = T.build_command


def build_with(extra):
    def patched(c, args, out):
        return orig_build(c, args, out) + extra
    return patched


T.build_command = build_with(["--oom"])
r_oom = T.run_trial(small, a, "oom")
T.build_command = build_with(["--fail"])
r_fail = T.run_trial(small, a, "fail")
T.build_command = orig_build

check("a CUDA OOM is labelled oom, not a bad score", r_oom["status"] == "oom",
      r_oom["status"])
check("a crash is labelled failed, not a bad score", r_fail["status"] == "failed",
      r_fail["status"])
check("failed trials carry no eval loss", r_fail["best_eval_loss"] is None)

shutil.rmtree(tmp, ignore_errors=True)


# ==========================================================================
section("9  trainer argument parsing survives a library upgrade")
# ==========================================================================
# The tuner passes flags that live in the trainer's own dataclasses
# (group_by_length, max_seq_length, ...). Those names have moved in and out of
# TrainingArguments/SFTConfig across versions, and a collision makes
# HfArgumentParser raise at construction --- inside a subprocess, where it would
# surface only as "every trial failed". finetune_ayur.py cannot be imported
# without torch, so the two functions are lifted out of the source and exercised
# against transformers.TrainingArguments standing in for SFTConfig.

try:
    import ast
    from dataclasses import dataclass, field
    from transformers import HfArgumentParser, TrainingArguments
    import dataclasses as _dc

    src = open(os.path.join(HERE, "finetune_ayur.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    wanted = {"_drop_clashing_fields", "parse_arguments"}
    picked = [n for n in tree.body
              if isinstance(n, ast.FunctionDef) and n.name in wanted]
    check("both parser helpers exist in finetune_ayur.py", len(picked) == 2,
          str([n.name for n in picked]))

    ns = {"dataclasses": _dc, "HfArgumentParser": HfArgumentParser,
          "SFTConfig": TrainingArguments}

    @dataclass
    class Aux:
        seed: int = field(default=7)              # collides with TrainingArguments
        tokenize_num_proc: int = field(default=4)  # does not

    ns.update({"ModelArguments": Aux, "DataArguments": Aux,
               "PerfArguments": Aux, "OptimizerSwitchArguments": Aux})
    exec(compile(ast.Module(body=picked, type_ignores=[]), "<lifted>", "exec"), ns)

    trimmed, dropped = ns["_drop_clashing_fields"](
        Aux, {f.name for f in _dc.fields(TrainingArguments)})
    check("a colliding field is dropped", "seed" in dropped, str(dropped))
    check("a non-colliding field is kept",
          "tokenize_num_proc" in {f.name for f in _dc.fields(trimmed)})

    argv = sys.argv
    sys.argv = ["finetune_ayur.py", "--output_dir", "/tmp/_x",
                "--seed", "1234", "--tokenize_num_proc", "9"]
    try:
        parsed = ns["parse_arguments"]()
        cfg = parsed[-1]
        check("the parser builds despite the collision", True)
        check("the colliding flag still parses", cfg.seed == 1234, str(cfg.seed))
        check("its value is copied back onto the aux dataclass",
              getattr(parsed[0], "seed", None) == 1234,
              "so data_args.max_seq_length keeps working downstream")
        check("non-colliding flags are unaffected",
              parsed[0].tokenize_num_proc == 9)
        check("aux dataclasses that collide with each other also survive",
              all(getattr(o, "tokenize_num_proc", None) == 9
                  for o in parsed[:-1]),
              "four identical dataclasses were passed on purpose")
    finally:
        sys.argv = argv
except ImportError as exc:
    print("  SKIP transformers not installed (%s)" % exc)


# ==========================================================================
print("\n" + "=" * 60)
print("%d passed, %d failed" % (len(PASS), len(FAIL)))
if FAIL:
    print("\nfailed:")
    for f in FAIL:
        print("  - %s" % f)
print("=" * 60)
sys.exit(1 if FAIL else 0)
