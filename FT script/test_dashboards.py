#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Renders the training dashboards from synthetic metrics --- no GPU, no torch.
============================================================================

Plotting bugs only surface at the very end of a run, after the expensive part is
already done. This exercises `build_dashboard_figure` and
`plot_training_dashboards` with a realistic metrics trace and a populated GPU
monitor, so a broken axis or a missing key is caught in seconds rather than after
an hour of training.

`finetune_ayur` imports torch, trl and peft at module scope, which are not
installable on every box. Rather than duplicate the plotting code here (where it
would rot), the heavy imports are stubbed just well enough for the module to load
and the plotting functions to run against the real implementation.

    python test_dashboards.py --out ./dashboard_preview
"""
from __future__ import annotations

import argparse
import importlib.machinery
import math
import os
import random
import sys
import types


def _stub_module(name):
    """A module object complete enough for importlib.util.find_spec().

    transformers probes for torch with find_spec, which raises if a module in
    sys.modules has __spec__ set to None --- so a bare types.ModuleType is not
    enough of a fake.
    """
    m = types.ModuleType(name)
    m.__spec__ = importlib.machinery.ModuleSpec(name, None)
    m.__version__ = "0.0.0-stub"
    return m


def install_stubs():
    """Minimal fakes for the imports finetune_ayur pulls at module scope."""
    if "torch" not in sys.modules:
        torch = _stub_module("torch")
        torch.bfloat16 = "bfloat16"
        torch.float16 = "float16"

        class _Cuda:
            @staticmethod
            def is_available():
                return False

            @staticmethod
            def memory_allocated():
                return 0

            @staticmethod
            def memory_reserved():
                return 0

            @staticmethod
            def max_memory_allocated():
                return 0

            @staticmethod
            def is_bf16_supported():
                return False

            @staticmethod
            def get_device_capability():
                return (0, 0)

            @staticmethod
            def utilization():
                return 0.0

            @staticmethod
            def empty_cache():
                pass

            @staticmethod
            def reset_peak_memory_stats():
                pass

        torch.cuda = _Cuda()
        torch.cuda.OutOfMemoryError = type("OutOfMemoryError", (Exception,), {})
        torch.optim = types.SimpleNamespace(AdamW=object, SGD=object, RMSprop=object)
        torch.backends = types.SimpleNamespace(
            cuda=types.SimpleNamespace(matmul=types.SimpleNamespace(allow_tf32=False)),
            cudnn=types.SimpleNamespace(allow_tf32=False))
        torch.no_grad = lambda: types.SimpleNamespace(
            __enter__=lambda s: None, __exit__=lambda s, *a: None)
        sys.modules["torch"] = torch

    for name, attrs in [
        ("datasets", ["Dataset"]),
        ("peft", ["LoraConfig", "prepare_model_for_kbit_training"]),
        ("trl", ["SFTConfig", "SFTTrainer"]),
    ]:
        if name not in sys.modules:
            m = _stub_module(name)
            for a in attrs:
                setattr(m, a, type(a, (), {}))
            sys.modules[name] = m

    # transformers is present for tokenizers but may lack the torch-backed names
    try:
        import transformers  # noqa: F401
        for a in ("AutoModelForCausalLM", "BitsAndBytesConfig", "TrainerCallback",
                  "PreTrainedTokenizerBase", "HfArgumentParser", "AutoTokenizer"):
            if not hasattr(sys.modules["transformers"], a):
                setattr(sys.modules["transformers"], a, type(a, (), {}))
        if "transformers.trainer_utils" not in sys.modules:
            tu = _stub_module("transformers.trainer_utils")
            tu.get_last_checkpoint = lambda d: None
            sys.modules["transformers.trainer_utils"] = tu
    except ImportError:
        m = _stub_module("transformers")
        for a in ("AutoModelForCausalLM", "AutoTokenizer", "BitsAndBytesConfig",
                  "HfArgumentParser", "TrainerCallback", "PreTrainedTokenizerBase"):
            setattr(m, a, type(a, (), {}))
        sys.modules["transformers"] = m
        tu = _stub_module("transformers.trainer_utils")
        tu.get_last_checkpoint = lambda d: None
        sys.modules["transformers.trainer_utils"] = tu


def synthetic_metrics(n_steps=1200, log_every=10):
    """A trace shaped like a real run: decaying loss, warmup+cosine LR, noise."""
    rnd = random.Random(7)
    hist = []
    warm = int(0.03 * n_steps)
    for s in range(log_every, n_steps + 1, log_every):
        frac = s / n_steps
        loss = 1.9 * math.exp(-3.2 * frac) + 0.32 + rnd.gauss(0, 0.025)
        lr = (2e-4 * s / warm if s < warm
              else 2e-4 * 0.5 * (1 + math.cos(math.pi * (s - warm) / (n_steps - warm))))
        hist.append({"step": s, "epoch": round(2 * frac, 3), "loss": round(loss, 4),
                     "learning_rate": lr,
                     "grad_norm": round(abs(rnd.gauss(0.8, 0.25)), 4),
                     "train_samples_per_second": round(rnd.gauss(11.5, 0.8), 2)})
        if s % 200 == 0:
            hist.append({"step": s, "epoch": round(2 * frac, 3),
                         "eval_loss": round(loss + rnd.gauss(0.04, 0.02), 4)})
    return hist


class FakeGPUMonitor:
    """Populated stand-in for GPUSpikeMonitor, with realistic spiky VRAM."""
    def __init__(self, seconds=900):
        rnd = random.Random(11)
        self.timestamps, self.allocated_gb, self.reserved_gb = [], [], []
        base = 9.4
        for t in range(seconds):
            spike = 2.6 if t % 47 == 0 else (1.1 if t % 13 == 0 else 0.0)
            a = base + spike + rnd.gauss(0, 0.12)
            self.timestamps.append(float(t))
            self.allocated_gb.append(round(max(a, 0.1), 3))
            self.reserved_gb.append(round(max(a + 1.6 + rnd.gauss(0, 0.1), 0.2), 3))

    def peak_allocated_gb(self):
        return max(self.allocated_gb) if self.allocated_gb else 0.0

    def peak_reserved_gb(self):
        return max(self.reserved_gb) if self.reserved_gb else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="./dashboard_preview")
    ap.add_argument("--data_dir", default="",
                    help="if given, use the real token-length histogram from it")
    a = ap.parse_args()

    install_stubs()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import finetune_ayur as FT
    print("finetune_ayur imported (heavy deps stubbed)")

    hist = synthetic_metrics()
    gpu = FakeGPUMonitor()
    print("synthetic trace: %d log entries, %d GPU samples, peak %.2fGB"
          % (len(hist), len(gpu.timestamps), gpu.peak_allocated_gb()))

    length_audit = None
    if a.data_dir:
        import ayur_data as AD
        from test_ayur_data import StubTokenizer
        rows = AD.load_split(os.path.join(a.data_dir, "train.json"))
        pairs, _, _ = AD.prepare(rows[:8000], StubTokenizer())
        length_audit = AD.token_length_audit(pairs, StubTokenizer(), 1024)
        print("real length audit: p50 %d p99 %d"
              % (length_audit["total_tokens_p50"], length_audit["total_tokens_p99"]))
    else:
        rnd = random.Random(3)
        L = sorted(int(abs(rnd.gauss(210, 90))) + 40 for _ in range(4000))
        length_audit = {"all_token_lengths": L, "max_seq_length": 1024,
                        "total_tokens_p99": L[int(0.99 * len(L))]}

    switch_history = [{"step": 600, "optimizer": "adamw_torch", "lr": 1e-4}]

    fig = FT.build_dashboard_figure(hist, gpu, batch_size=8, grad_accum_steps=4,
                                    switch_history=switch_history,
                                    length_audit=length_audit)
    n_axes = len(fig.axes)
    drawn = sum(1 for ax in fig.axes if ax.lines or ax.patches)
    print("figure built: %d axes, %d with data" % (n_axes, drawn))
    assert n_axes == 6, "expected a 3x2 dashboard, got %d axes" % n_axes
    assert drawn == 6, "only %d of 6 panels have data" % drawn

    os.makedirs(a.out, exist_ok=True)
    FT.plot_training_dashboards(hist, gpu, 8, 4, a.out,
                                switch_history=switch_history,
                                length_audit=length_audit)

    plots = os.path.join(a.out, "training_plots")
    made = sorted(os.listdir(plots))
    print("wrote %d PNGs -> %s" % (len(made), plots))
    for f in made:
        size = os.path.getsize(os.path.join(plots, f))
        print("   %-26s %7d bytes" % (f, size))
        assert size > 5000, "%s looks empty" % f

    print("\nPASS --- dashboards render")


if __name__ == "__main__":
    main()
