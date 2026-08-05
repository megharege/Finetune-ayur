"""
QLoRA / SFT Fine-Tuning for AyurLLM
===================================
Adapted from the MedQA trainer. Same architecture --- typed config, native TRL
completion-only loss, hardware autotuning, telemetry, dashboards --- retargeted at
the Ayurvedic corpus and tuned for throughput.

WHAT CHANGED, AND WHY
---------------------
1.  DATA LAYER REPLACED. MedQA ships one flat schema from the Hub. This corpus is
    three local JSON files with `option_a..e`, `correct_answer` that may hold
    several letters, six question formats and two languages. All of that lives in
    `ayur_data.py` so it can be tested without a GPU --- run `test_ayur_data.py`
    before you burn an hour of compute on a schema bug.

2.  REAL VALIDATION SPLIT. The MedQA script carved eval out of train with
    `train_test_split`. Here `validation.json` already exists, built at fact
    granularity so no fact straddles the two. Re-splitting train would silently
    undo that, so it is not done.

3.  PRE-FLIGHT AUDITS. Composition, answer-position balance and token-length
    percentiles are computed and saved before training starts. The length audit
    matters more than it sounds: Devanagari costs several tokens per character,
    so a `max_seq_length` chosen for English can truncate the answer off a large
    share of the Hindi half --- and a truncated completion means loss over nothing.
    The script warns loudly if that is about to happen.

4.  THROUGHPUT WORK.
      - `group_by_length=True`  batches similar lengths together, which on a
        corpus whose stems run from 40 to 600 tokens removes most of the padding.
        This is the single biggest win available here.
      - TF32 matmuls enabled on Ampere+.
      - `dataloader_num_workers` / `pin_memory` / `persistent_workers` set from a
        sensible default rather than left at 0.
      - Tokenization mapped with `num_proc` and cached.
      - Optional `--auto_batch_size` probes VRAM and picks a per-device batch
        size instead of making you guess.

5.  MORE DASHBOARDS. The original four (loss, LR, batch size, GPU) plus
    throughput (samples/sec), grad-norm, and a token-length histogram with the
    truncation line drawn on it.

Usage
    python finetune_ayur.py \
        --model_name_or_path Qwen/Qwen2.5-3B-Instruct \
        --data_dir ../ayur_pipeline/final \
        --output_dir ./ayur_qlora_out \
        --num_train_epochs 2 \
        --per_device_train_batch_size 8 \
        --gradient_accumulation_steps 4 \
        --learning_rate 2e-4 \
        --max_seq_length 768

    # prove the data layer works first, no GPU needed:
    python test_ayur_data.py --data_dir ../ayur_pipeline/final
"""

import sys
import os

# Reduce CUDA allocator fragmentation across repeated in-kernel runs (e.g. via
# Jupyter %run) --- must be set before torch is imported / initializes CUDA.
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import gc
import json
import time
import logging
import threading
import dataclasses
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

import torch
from datasets import Dataset
from peft import LoraConfig, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    HfArgumentParser,
    TrainerCallback,
    PreTrainedTokenizerBase,
)
from transformers.trainer_utils import get_last_checkpoint
from trl import SFTConfig, SFTTrainer

import matplotlib
matplotlib.use("Agg")  # headless-safe backend for servers/containers
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ayur_data as AD

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("AyurLLM-Trainer")


# ============================================================================
# Dataclass Arguments
# ============================================================================

@dataclass
class ModelArguments:
    model_name_or_path: str = field(
        metadata={"help": "Pretrained model id or local path."}
    )
    use_4bit: bool = field(default=True, metadata={"help": "4-bit NF4 QLoRA."})
    lora_r: int = field(default=32, metadata={
        "help": "LoRA rank. 32 rather than MedQA's 16: this corpus asks the model "
                "to absorb domain vocabulary in two scripts, which needs more "
                "adapter capacity than picking an option letter on English text."})
    lora_alpha: int = field(default=64, metadata={"help": "LoRA scaling (2x rank)."})
    lora_dropout: float = field(default=0.05, metadata={"help": "LoRA dropout."})
    lora_target_modules: str = field(
        default="q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj",
        metadata={"help": "Comma-separated module names to adapt."})


@dataclass
class DataArguments:
    data_dir: str = field(
        default="../ayur_pipeline/final",
        metadata={"help": "Folder holding train.json / validation.json / test.json."})
    train_file: str = field(default="train.json", metadata={
        "help": "QA split, or a raw treatise .jsonl (sanskrit_text/commentary). "
                "The schema is detected, not configured."})
    eval_file: str = field(default="validation.json", metadata={
        "help": "Held-out file. Leave missing on raw-chunk data and --eval_frac "
                "carves one out by chunk_id."})
    eval_frac: float = field(default=0.02, metadata={
        "help": "Only used when eval_file is absent. Split is by chunk_id, so no "
                "verse appears in both halves."})
    max_target_chars: int = field(default=1200, metadata={
        "help": "Cap on a chunk-task target, so one long commentary cannot "
                "dominate the loss."})
    max_seq_length: int = field(default=768, metadata={
        "help": "Token cap. Check the length audit the script prints --- Devanagari "
                "items are much longer in tokens than they look in characters."})
    max_train_samples: Optional[int] = field(default=None)
    max_eval_samples: Optional[int] = field(default=None)
    completion_style: str = field(default="letter", metadata={
        "help": "'letter' (A / A,C) or 'letter_text' (letter plus the option text)."})
    use_system_prompt: bool = field(default=True)
    include_open_ended: bool = field(default=True, metadata={
        "help": "Train the ~2.5%% of rows that have no options (verse expositions, "
                "source lookups) as free-text generation instead of dropping them. "
                "They carry the richest domain content in the corpus."})
    open_answer_chars: int = field(default=600, metadata={
        "help": "Cap on free-text answer length, so a few long expositions do not "
                "dominate the loss or blow past max_seq_length."})
    filter_question_types: Optional[str] = field(default=None, metadata={
        "help": "Comma-separated question types to keep. Default keeps all six."})
    filter_language: Optional[str] = field(default=None, metadata={
        "help": "'en' or 'hi' to train on one language only. Default keeps both."})
    drop_over_length: bool = field(default=True, metadata={
        "help": "Drop rows longer than max_seq_length instead of truncating them. "
                "Truncation removes the completion, which makes the row a silent "
                "no-op that still costs compute."})


@dataclass
class PerfArguments:
    auto_batch_size: bool = field(default=False, metadata={
        "help": "Probe VRAM and choose per_device_train_batch_size."})
    tokenize_num_proc: int = field(default=4)
    dataloader_workers: int = field(default=-1, metadata={
        "help": "-1 picks min(8, cpu_count)."})
    enable_tf32: bool = field(default=True)
    group_by_length: bool = field(default=True, metadata={
        "help": "Batch similar-length sequences together. Biggest single "
                "throughput win on this corpus; disable only to debug."})


@dataclass
class OptimizerSwitchArguments:
    optimizer_switch_step: Optional[int] = field(default=None)
    secondary_optimizer: str = field(default="adamw_torch")
    secondary_learning_rate: Optional[float] = field(default=None)
    secondary_weight_decay: Optional[float] = field(default=None)


def _drop_clashing_fields(dc, taken):
    """Rebuild `dc` without any field whose CLI flag SFTConfig already owns.

    HfArgumentParser adds one argparse option per field across every dataclass
    it is handed, and argparse raises on a duplicate option string. Which names
    collide moves between library versions --- SFTConfig carried max_seq_length
    until TRL 0.20, TrainingArguments carried group_by_length until transformers
    v5 --- so a hardcoded exclusion list breaks on the next `pip install -U`.
    Dropping whatever actually collides keeps one stable CLI across versions;
    the parsed value is copied back onto the instance afterwards, so the rest of
    the script still reads data_args.max_seq_length as if nothing happened.
    """
    names = {f.name for f in dataclasses.fields(dc)}
    dropped = names & taken
    if not dropped:
        return dc, dropped
    spec = [(f.name, f.type, f) for f in dataclasses.fields(dc)
            if f.name not in dropped]
    new = dataclasses.make_dataclass(dc.__name__, spec)
    new.__module__ = dc.__module__
    return new, dropped


def parse_arguments():
    aux_types = (ModelArguments, DataArguments, PerfArguments,
                 OptimizerSwitchArguments)
    taken = {f.name for f in dataclasses.fields(SFTConfig)}

    prepared, dropped_by = [], {}
    for dc in aux_types:
        trimmed, dropped = _drop_clashing_fields(dc, taken)
        taken |= {f.name for f in dataclasses.fields(trimmed)}
        prepared.append(trimmed)
        dropped_by[trimmed] = dropped

    parser = HfArgumentParser(tuple(prepared) + (SFTConfig,))
    parsed = parser.parse_args_into_dataclasses()

    # Give every dropped field its parsed value back, taken from whichever
    # dataclass ended up owning the flag. One flag, one value, and the rest of
    # the script keeps reading data_args.max_seq_length as though nothing moved.
    for obj in parsed[:-1]:
        for name in dropped_by.get(type(obj), ()):
            for owner in parsed:
                if hasattr(owner, name):
                    setattr(obj, name, getattr(owner, name))
                    break
    return parsed


# ============================================================================
# Utilities & Engineering Assertions
# ============================================================================

def verify_masking_integrity(sample: Dict[str, Any], tokenizer) -> None:
    """Confirms a non-empty completion span exists for loss computation.

    Modern TRL masks the prompt natively when the dataset has separate 'prompt'
    and 'completion' columns and SFTConfig(completion_only_loss=True) is set. This
    tokenizes prompt vs prompt+completion independently to confirm the trainer has
    something to compute loss over.
    """
    logger.info("Running pre-flight Label Masking Integrity Check...")
    prompt_ids = tokenizer(sample["prompt"], add_special_tokens=False)["input_ids"]
    full_ids = tokenizer(sample["prompt"] + sample["completion"],
                         add_special_tokens=False)["input_ids"]
    prompt_len = len(prompt_ids)
    completion_len = len(full_ids) - prompt_len
    logger.info("Token Analysis -> Prompt: %d | Completion (loss target): %d",
                prompt_len, completion_len)
    if completion_len <= 0:
        raise RuntimeError(
            "CRITICAL: completion span is 0 tokens. The model would train on "
            "nothing. Check ayur_data.format_example() and the chat template.")
    logger.info("Masking verification passed.")


def log_gpu_footprint(tag: str = "Status"):
    if torch.cuda.is_available():
        logger.info("[%s] VRAM Allocated: %.2fGB | Reserved: %.2fGB | Peak: %.2fGB",
                    tag, torch.cuda.memory_allocated() / 1024 ** 3,
                    torch.cuda.memory_reserved() / 1024 ** 3,
                    torch.cuda.max_memory_allocated() / 1024 ** 3)


def suggest_batch_size(max_seq_length: int, use_4bit: bool) -> int:
    """Rough per-device batch size from free VRAM, sequence length and precision.

    Deliberately conservative --- an OOM three hours into a run costs far more than
    a slightly smaller batch, and gradient accumulation recovers the effective
    size anyway.
    """
    if not torch.cuda.is_available():
        return 4
    free = torch.cuda.get_device_properties(0).total_memory / 1024 ** 3
    budget = free * (0.55 if use_4bit else 0.35)
    per_sample_gb = (max_seq_length / 1024.0) * (0.35 if use_4bit else 0.9)
    bs = max(1, int(budget / max(per_sample_gb, 0.05)))
    for cap in (64, 32, 16, 8, 4, 2, 1):
        if bs >= cap:
            return cap
    return 1


# ============================================================================
# Telemetry
# ============================================================================

class GPUSpikeMonitor:
    """Background sampler recording VRAM at fixed intervals, so short-lived
    spikes (attention peak, optimizer step) are not missed --- the Trainer's own
    logging cadence is far too coarse to catch them.
    """
    def __init__(self, interval_sec: float = 1.0):
        self.interval_sec = interval_sec
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.timestamps: List[float] = []
        self.allocated_gb: List[float] = []
        self.reserved_gb: List[float] = []
        self.utilization: List[float] = []
        self._start_time = None

    def _sample_loop(self):
        while not self._stop_event.is_set():
            if torch.cuda.is_available():
                self.timestamps.append(time.time() - self._start_time)
                self.allocated_gb.append(torch.cuda.memory_allocated() / 1024 ** 3)
                self.reserved_gb.append(torch.cuda.memory_reserved() / 1024 ** 3)
                try:
                    self.utilization.append(float(torch.cuda.utilization()))
                except Exception:
                    self.utilization.append(float("nan"))
            self._stop_event.wait(self.interval_sec)

    def start(self):
        if not torch.cuda.is_available():
            logger.warning("CUDA unavailable --- GPU monitor collects nothing.")
            return
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._thread.start()
        logger.info("GPU spike monitor started (every %.1fs).", self.interval_sec)

    def stop(self):
        if self._thread is not None:
            self._stop_event.set()
            self._thread.join(timeout=5)
            logger.info("GPU monitor stopped. %d samples.", len(self.timestamps))

    def peak_allocated_gb(self) -> float:
        return max(self.allocated_gb) if self.allocated_gb else 0.0

    def peak_reserved_gb(self) -> float:
        return max(self.reserved_gb) if self.reserved_gb else 0.0


class MetricsLoggerCallback(TrainerCallback):
    """Writes step metrics to JSONL and buffers them for plotting."""
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.history: List[Dict[str, Any]] = []

    def on_log(self, args, state, control, logs=None, **kwargs):
        if logs:
            entry = dict(logs)
            entry["step"] = state.global_step
            entry["epoch"] = state.epoch
            entry["wall_time"] = time.time()
            with open(self.filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
            self.history.append(entry)


class CheckpointLossReporter(TrainerCallback):
    """Persists the latest train/eval loss beside every checkpoint."""
    def __init__(self):
        self.last_train_loss: Optional[float] = None
        self.last_eval_loss: Optional[float] = None

    def on_log(self, args, state, control, logs=None, **kwargs):
        if not logs:
            return
        if "loss" in logs:
            self.last_train_loss = logs["loss"]
        if "eval_loss" in logs:
            self.last_eval_loss = logs["eval_loss"]

    def on_save(self, args, state, control, **kwargs):
        ckpt_dir = os.path.join(args.output_dir, "checkpoint-%d" % state.global_step)
        logger.info("Checkpoint saved -> step %d | train_loss=%s | eval_loss=%s",
                    state.global_step, self.last_train_loss, self.last_eval_loss)
        try:
            os.makedirs(ckpt_dir, exist_ok=True)
            with open(os.path.join(ckpt_dir, "checkpoint_loss_summary.json"), "w") as f:
                json.dump({"global_step": state.global_step, "epoch": state.epoch,
                           "last_train_loss": self.last_train_loss,
                           "last_eval_loss": self.last_eval_loss}, f, indent=2)
        except FileNotFoundError:
            logger.warning("Checkpoint dir not ready; JSONL trace still has it.")


def build_optimizer(name: str, model_params, lr: float, weight_decay: float = 0.0):
    name = name.lower()
    params = [p for p in model_params if p.requires_grad]
    if name == "adamw_torch":
        return torch.optim.AdamW(params, lr=lr, weight_decay=weight_decay)
    if name == "sgd":
        return torch.optim.SGD(params, lr=lr, weight_decay=weight_decay, momentum=0.9)
    if name == "rmsprop":
        return torch.optim.RMSprop(params, lr=lr, weight_decay=weight_decay)
    if name == "adafactor":
        from transformers.optimization import Adafactor
        return Adafactor(params, lr=lr, weight_decay=weight_decay,
                         scale_parameter=False, relative_step=False)
    if name in ("adamw_8bit", "paged_adamw_8bit"):
        import bitsandbytes as bnb
        cls = bnb.optim.PagedAdamW8bit if name == "paged_adamw_8bit" else bnb.optim.AdamW8bit
        return cls(params, lr=lr, weight_decay=weight_decay)
    raise ValueError("Unknown secondary_optimizer '%s'." % name)


class OptimizerSwitchCallback(TrainerCallback):
    """Swaps the optimizer mid-run at a given global step."""
    def __init__(self, switch_step, optimizer_name, lr, weight_decay):
        self.switch_step = switch_step
        self.optimizer_name = optimizer_name
        self.lr_override = lr
        self.weight_decay_override = weight_decay
        self.trainer = None          # wired up after Trainer construction
        self._switched = False
        self.switch_history: List[Dict[str, Any]] = []

    def on_step_end(self, args, state, control, **kwargs):
        if not self.switch_step or self._switched or state.global_step < self.switch_step:
            return
        if self.trainer is None:
            logger.warning("OptimizerSwitchCallback fired without .trainer set.")
            self._switched = True
            return
        lr = self.lr_override if self.lr_override is not None else args.learning_rate
        wd = (self.weight_decay_override if self.weight_decay_override is not None
              else args.weight_decay)
        logger.info("Switching optimizer at step %d -> '%s' (lr=%s, wd=%s)",
                    state.global_step, self.optimizer_name, lr, wd)
        try:
            self.trainer.optimizer = build_optimizer(
                self.optimizer_name, self.trainer.model.parameters(), lr, wd)
            self.switch_history.append({"step": state.global_step,
                                        "optimizer": self.optimizer_name, "lr": lr})
            logger.info("Optimizer switch complete.")
        except Exception as e:
            logger.error("Optimizer switch failed, continuing with previous: %s", e)
        finally:
            self._switched = True


# ============================================================================
# Dashboards
# ============================================================================

def build_dashboard_figure(metrics_history, gpu_monitor, batch_size,
                           grad_accum_steps, switch_history=None,
                           length_audit=None):
    """One 3x2 figure: loss, LR, throughput, grad-norm, GPU, token lengths.

    Shared by the live in-notebook callback and the final PNG export so the two
    cannot drift apart.
    """
    steps = [m["step"] for m in metrics_history if "loss" in m]
    train_losses = [m["loss"] for m in metrics_history if "loss" in m]
    eval_steps = [m["step"] for m in metrics_history if "eval_loss" in m]
    eval_losses = [m["eval_loss"] for m in metrics_history if "eval_loss" in m]
    lr_steps = [m["step"] for m in metrics_history if "learning_rate" in m]
    lrs = [m["learning_rate"] for m in metrics_history if "learning_rate" in m]
    gn_steps = [m["step"] for m in metrics_history if "grad_norm" in m]
    gns = [m["grad_norm"] for m in metrics_history if "grad_norm" in m]
    tp_steps = [m["step"] for m in metrics_history if "train_samples_per_second" in m]
    tps = [m["train_samples_per_second"] for m in metrics_history
           if "train_samples_per_second" in m]

    fig, axes = plt.subplots(3, 2, figsize=(13, 12))
    ax_loss, ax_lr = axes[0, 0], axes[0, 1]
    ax_tp, ax_gn = axes[1, 0], axes[1, 1]
    ax_gpu, ax_len = axes[2, 0], axes[2, 1]

    if train_losses:
        ax_loss.plot(steps, train_losses, label="Train", color="tab:blue", lw=1.2)
    if eval_losses:
        ax_loss.plot(eval_steps, eval_losses, label="Eval", color="tab:orange",
                     marker="o", ms=3)
    for sw in (switch_history or []):
        ax_loss.axvline(sw["step"], color="tab:red", ls=":", alpha=0.8)
    ax_loss.set_title("Training / Eval Loss")
    ax_loss.set_xlabel("Global Step"); ax_loss.set_ylabel("Loss")
    ax_loss.grid(alpha=0.3)
    if train_losses or eval_losses:
        ax_loss.legend()

    if lrs:
        ax_lr.plot(lr_steps, lrs, color="tab:green")
    ax_lr.set_title("Learning Rate Schedule")
    ax_lr.set_xlabel("Global Step"); ax_lr.set_ylabel("LR")
    ax_lr.grid(alpha=0.3)

    if tps:
        ax_tp.plot(tp_steps, tps, color="tab:cyan")
    else:
        eff = batch_size * grad_accum_steps
        ax_tp.plot(steps, [eff] * len(steps), color="tab:red", ls="--",
                   label="Effective batch")
        ax_tp.plot(steps, [batch_size] * len(steps), color="tab:purple",
                   label="Per-device batch")
        if steps:
            ax_tp.legend()
    ax_tp.set_title("Throughput (samples/s)" if tps else "Batch Size")
    ax_tp.set_xlabel("Global Step")
    ax_tp.grid(alpha=0.3)

    if gns:
        ax_gn.plot(gn_steps, gns, color="tab:brown", lw=1.0)
    ax_gn.set_title("Gradient Norm")
    ax_gn.set_xlabel("Global Step"); ax_gn.set_ylabel("||g||")
    ax_gn.grid(alpha=0.3)

    if gpu_monitor.timestamps:
        ax_gpu.plot(gpu_monitor.timestamps, gpu_monitor.allocated_gb,
                    label="Allocated", color="tab:blue", lw=1.0)
        ax_gpu.plot(gpu_monitor.timestamps, gpu_monitor.reserved_gb,
                    label="Reserved", color="tab:gray", alpha=0.6, lw=1.0)
        peak = gpu_monitor.peak_allocated_gb()
        ax_gpu.axhline(peak, color="tab:red", ls="--",
                       label="Peak %.2fGB" % peak)
        ax_gpu.legend(fontsize=8)
    ax_gpu.set_title("GPU Memory / Spikes")
    ax_gpu.set_xlabel("Wall-clock (s)"); ax_gpu.set_ylabel("VRAM (GB)")
    ax_gpu.grid(alpha=0.3)

    if length_audit and length_audit.get("all_token_lengths"):
        L = length_audit["all_token_lengths"]
        ax_len.hist(L, bins=50, color="tab:olive", alpha=0.85)
        ax_len.axvline(length_audit["max_seq_length"], color="tab:red", ls="--",
                       label="max_seq_length=%d" % length_audit["max_seq_length"])
        ax_len.axvline(length_audit["total_tokens_p99"], color="tab:orange", ls=":",
                       label="p99=%d" % length_audit["total_tokens_p99"])
        ax_len.legend(fontsize=8)
    ax_len.set_title("Token Length Distribution")
    ax_len.set_xlabel("Tokens (prompt + completion)"); ax_len.set_ylabel("Rows")
    ax_len.grid(alpha=0.3)

    fig.tight_layout()
    return fig


class LiveDashboardCallback(TrainerCallback):
    """Redraws the dashboard in-place in a notebook cell. No-op outside IPython."""
    def __init__(self, metrics_callback, gpu_monitor, batch_size, grad_accum_steps,
                 refresh_every_n_logs=1, optimizer_switch_callback=None,
                 length_audit=None):
        self.metrics_callback = metrics_callback
        self.gpu_monitor = gpu_monitor
        self.batch_size = batch_size
        self.grad_accum_steps = grad_accum_steps
        self.refresh_every_n_logs = max(1, refresh_every_n_logs)
        self.optimizer_switch_callback = optimizer_switch_callback
        self.length_audit = length_audit
        self._log_count = 0
        self._display = self._clear = self._Image = None
        try:
            from IPython.display import display, clear_output, Image
            self._display, self._clear, self._Image = display, clear_output, Image
        except ImportError:
            logger.info("IPython absent --- live dashboard off; PNGs still saved.")

    def on_log(self, args, state, control, logs=None, **kwargs):
        if self._display is None or not logs:
            return
        self._log_count += 1
        if self._log_count % self.refresh_every_n_logs != 0:
            return
        try:
            import io
            sw = (self.optimizer_switch_callback.switch_history
                  if self.optimizer_switch_callback else None)
            fig = build_dashboard_figure(
                self.metrics_callback.history, self.gpu_monitor, self.batch_size,
                self.grad_accum_steps, switch_history=sw,
                length_audit=self.length_audit)
            # Render to PNG bytes explicitly: matplotlib.use("Agg") strips
            # Jupyter's inline formatter, so display(fig) would print a repr.
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
            plt.close(fig)
            buf.seek(0)
            self._clear(wait=True)
            self._display(self._Image(data=buf.getvalue()))
        except Exception as e:
            logger.warning("Live dashboard redraw failed (non-fatal): %s", e)


def plot_training_dashboards(metrics_history, gpu_monitor, batch_size,
                             grad_accum_steps, output_dir, switch_history=None,
                             length_audit=None):
    """Writes the combined dashboard plus individual PNGs."""
    plots_dir = os.path.join(output_dir, "training_plots")
    os.makedirs(plots_dir, exist_ok=True)

    fig = build_dashboard_figure(metrics_history, gpu_monitor, batch_size,
                                 grad_accum_steps, switch_history, length_audit)
    fig.savefig(os.path.join(plots_dir, "dashboard.png"), dpi=150,
                bbox_inches="tight")
    plt.close(fig)

    steps = [m["step"] for m in metrics_history if "loss" in m]
    train_losses = [m["loss"] for m in metrics_history if "loss" in m]
    eval_steps = [m["step"] for m in metrics_history if "eval_loss" in m]
    eval_losses = [m["eval_loss"] for m in metrics_history if "eval_loss" in m]

    if train_losses or eval_losses:
        plt.figure(figsize=(8, 5))
        if train_losses:
            plt.plot(steps, train_losses, label="Train Loss", color="tab:blue")
        if eval_losses:
            plt.plot(eval_steps, eval_losses, label="Eval Loss",
                     color="tab:orange", marker="o")
        for sw in (switch_history or []):
            plt.axvline(sw["step"], color="tab:red", ls=":", alpha=0.8)
        plt.xlabel("Global Step"); plt.ylabel("Loss")
        plt.title("Training / Eval Loss"); plt.legend(); plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(plots_dir, "loss_curve.png"), dpi=150)
        plt.close()

    if gpu_monitor.timestamps:
        plt.figure(figsize=(8, 5))
        plt.plot(gpu_monitor.timestamps, gpu_monitor.allocated_gb,
                 label="Allocated (GB)", color="tab:blue")
        plt.plot(gpu_monitor.timestamps, gpu_monitor.reserved_gb,
                 label="Reserved (GB)", color="tab:gray", alpha=0.6)
        peak = gpu_monitor.peak_allocated_gb()
        plt.axhline(peak, color="tab:red", ls="--", label="Peak: %.2fGB" % peak)
        plt.xlabel("Wall-clock Time (s)"); plt.ylabel("VRAM (GB)")
        plt.title("GPU Memory Usage / Spikes"); plt.legend(); plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(plots_dir, "gpu_memory_spikes.png"), dpi=150)
        plt.close()

    logger.info("Training dashboards saved to: %s", plots_dir)


# ============================================================================
# Main
# ============================================================================

def main():
    model_args, data_args, perf_args, optim_switch_args, sft_config = \
        parse_arguments()

    logger.info("Initializing AyurLLM fine-tuning for: %s",
                model_args.model_name_or_path)
    log_gpu_footprint("Pre-Flight Setup")

    if perf_args.enable_tf32 and torch.cuda.is_available():
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        logger.info("TF32 matmuls enabled.")

    os.makedirs(sft_config.output_dir, exist_ok=True)

    # ---- 1. Load the pre-built splits ---------------------------------
    train_path = os.path.join(data_args.data_dir, data_args.train_file)
    eval_path = os.path.join(data_args.data_dir, data_args.eval_file)
    if not os.path.exists(train_path):
        raise SystemExit("Missing training file: %s" % train_path)

    train_rows = AD.load_split(train_path)
    schema = AD.detect_schema(train_rows)
    logger.info("Detected input schema: %s", schema)

    if os.path.exists(eval_path):
        eval_rows = AD.load_split(eval_path)
    elif schema == "chunk":
        # No held-out file, and chunk rows have no fact_id. Splitting on
        # chunk_id keeps every task derived from one verse on the same side ---
        # a random row split would put the translation of a verse in train and
        # its transliteration in eval, which is the same leak by another name.
        import random as _rnd
        ids = sorted({str(r.get("chunk_id")) for r in train_rows})
        _rnd.Random(sft_config.seed).shuffle(ids)
        n_eval = max(1, int(len(ids) * data_args.eval_frac))
        held = set(ids[:n_eval])
        eval_rows = [r for r in train_rows if str(r.get("chunk_id")) in held]
        train_rows = [r for r in train_rows if str(r.get("chunk_id")) not in held]
        logger.info("Carved eval by chunk_id: %d chunks held out (%d rows)",
                    len(held), len(eval_rows))
    else:
        raise SystemExit("Missing eval file: %s" % eval_path)
    logger.info("Loaded -> train %d | validation %d", len(train_rows), len(eval_rows))
    logger.info("Validation comes from validation.json, not a re-split of train: "
                "the splits were built at fact granularity and re-splitting would "
                "undo that guarantee.")

    if data_args.filter_question_types:
        keep = {t.strip() for t in data_args.filter_question_types.split(",")}
        train_rows = [r for r in train_rows if r.get("question_type") in keep]
        eval_rows = [r for r in eval_rows if r.get("question_type") in keep]
        logger.info("Filtered to types %s -> train %d | val %d",
                    sorted(keep), len(train_rows), len(eval_rows))
    if data_args.filter_language:
        lang = data_args.filter_language.strip().lower()
        train_rows = [r for r in train_rows if AD.infer_language(r) == lang]
        eval_rows = [r for r in eval_rows if AD.infer_language(r) == lang]
        logger.info("Filtered to language '%s' -> train %d | val %d",
                    lang, len(train_rows), len(eval_rows))
    if data_args.max_train_samples:
        train_rows = train_rows[:data_args.max_train_samples]
    if data_args.max_eval_samples:
        eval_rows = eval_rows[:data_args.max_eval_samples]

    audit = ({"train": AD.audit_rows(train_rows),
              "validation": AD.audit_rows(eval_rows)} if schema == "qa"
             else {"note": "schema=%s; QA audits do not apply" % schema})
    pos = {}
    if schema == "qa":
        logger.info("Train composition -> %s", audit["train"]["by_type"])
        logger.info("Train languages   -> %s", audit["train"]["by_language"])
        logger.info("Answer positions  -> %s", audit["train"]["answer_position"])
        pos = audit["train"]["answer_position"]
    if pos:
        top = max(pos.values()) / max(sum(pos.values()), 1)
        if top > 0.40:
            logger.warning("Answer-position skew: one letter holds %.1f%% of "
                           "answers. A model can score well by always picking it. "
                           "Consider re-running the quality gate with "
                           "--fix-position.", 100 * top)

    # ---- 2. Tokenizer --------------------------------------------------
    tokenizer = AutoTokenizer.from_pretrained(
        model_args.model_name_or_path,
        trust_remote_code=sft_config.trust_remote_code)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # ---- 3. Format to prompt/completion --------------------------------
    kw = dict(completion_style=data_args.completion_style,
              use_system=data_args.use_system_prompt,
              allow_open=data_args.include_open_ended,
              open_answer_chars=data_args.open_answer_chars,
              max_target_chars=data_args.max_target_chars)
    train_pairs, info_tr = AD.prepare_any(train_rows, tokenizer, **kw)
    eval_pairs, info_ev = AD.prepare_any(eval_rows, tokenizer, **kw)
    logger.info("Train formatting: %s", info_tr)
    logger.info("Eval  formatting: %s", info_ev)
    dropped_tr = info_tr.get("dropped", info_tr.get("chunks_skipped", 0))
    dropped_ev = info_ev.get("dropped", info_ev.get("chunks_skipped", 0))
    open_tr = info_tr.get("open_ended", 0)
    open_ev = info_ev.get("open_ended", 0)
    logger.info("Formatted -> train %d (dropped %d, open-ended %d) | "
                "val %d (dropped %d, open-ended %d)",
                len(train_pairs), dropped_tr, open_tr,
                len(eval_pairs), dropped_ev, open_ev)
    if data_args.include_open_ended and open_tr:
        logger.info("%d open-ended rows are trained as free-text generation "
                    "rather than discarded --- they carry explanation content that "
                    "letter-picking items do not.", open_tr)
    if not train_pairs:
        raise SystemExit("No usable training rows after formatting.")

    # ---- 4. Length audit, before anything expensive --------------------
    length_audit = AD.token_length_audit(train_pairs, tokenizer,
                                         data_args.max_seq_length)
    logger.info("Token lengths -> p50 %d | p90 %d | p99 %d | max %d",
                length_audit["total_tokens_p50"], length_audit["total_tokens_p90"],
                length_audit["total_tokens_p99"], length_audit["total_tokens_max"])
    if length_audit["pct_over_max_seq_length"] > 2.0:
        logger.warning(
            "%.1f%% of rows exceed max_seq_length=%d. Truncation removes the "
            "completion, so those rows train on nothing while still costing "
            "compute. Raise --max_seq_length to about %d, or keep "
            "--drop_over_length so they are removed rather than silently broken.",
            length_audit["pct_over_max_seq_length"], data_args.max_seq_length,
            length_audit["total_tokens_p99"])

    if data_args.drop_over_length:
        def fits(p):
            n = len(tokenizer(p["prompt"] + p["completion"],
                              add_special_tokens=False)["input_ids"])
            return n <= data_args.max_seq_length
        before = len(train_pairs)
        train_pairs = [p for p in train_pairs if fits(p)]
        eval_pairs = [p for p in eval_pairs if fits(p)]
        logger.info("Dropped %d over-length training rows (%d remain).",
                    before - len(train_pairs), len(train_pairs))

    train_ds = Dataset.from_list(train_pairs)
    eval_ds = Dataset.from_list(eval_pairs)
    verify_masking_integrity(train_ds[0], tokenizer)

    # ---- 5. Hardware dispatch & quantization ---------------------------
    attn_implementation = "sdpa"
    if torch.cuda.is_available() and torch.cuda.get_device_capability()[0] >= 8:
        try:
            import flash_attn  # noqa: F401
            attn_implementation = "flash_attention_2"
        except ImportError:
            pass
    logger.info("Attention backend: '%s'", attn_implementation)

    quant_config = None
    if model_args.use_4bit:
        compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        quant_config = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=compute_dtype, bnb_4bit_use_double_quant=True)

    model = AutoModelForCausalLM.from_pretrained(
        model_args.model_name_or_path,
        quantization_config=quant_config,
        device_map="auto",
        torch_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
        attn_implementation=attn_implementation,
        trust_remote_code=sft_config.trust_remote_code)

    if model_args.use_4bit:
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)

    peft_config = LoraConfig(
        r=model_args.lora_r, lora_alpha=model_args.lora_alpha,
        lora_dropout=model_args.lora_dropout, bias="none", task_type="CAUSAL_LM",
        target_modules=[m.strip() for m in model_args.lora_target_modules.split(",")])

    # ---- 6. Trainer configuration --------------------------------------
    jsonl_log_path = os.path.join(sft_config.output_dir, "training_metrics.jsonl")

    sft_config.completion_only_loss = True
    # TRL defaults to loss_type="chunked_nll", which patches lm_head.forward. On
    # some architectures lm_head.forward is already a functools.partial and the
    # patch crashes reading __func__. The unchunked path sidesteps it.
    if not getattr(sft_config, "loss_type", None) or sft_config.loss_type == "chunked_nll":
        sft_config.loss_type = "nll"
    sft_config.max_seq_length = data_args.max_seq_length
    sft_config.optim = getattr(sft_config, "optim", None) or "paged_adamw_8bit"
    sft_config.gradient_checkpointing = True
    sft_config.gradient_checkpointing_kwargs = {"use_reentrant": False}
    sft_config.bf16 = torch.cuda.is_bf16_supported()
    sft_config.fp16 = not torch.cuda.is_bf16_supported()

    if perf_args.auto_batch_size:
        bs = suggest_batch_size(data_args.max_seq_length, model_args.use_4bit)
        logger.info("Auto batch size -> %d per device", bs)
        sft_config.per_device_train_batch_size = bs
        sft_config.per_device_eval_batch_size = bs

    sft_config.group_by_length = perf_args.group_by_length
    workers = (perf_args.dataloader_workers if perf_args.dataloader_workers >= 0
               else min(8, os.cpu_count() or 2))
    sft_config.dataloader_num_workers = workers
    sft_config.dataloader_pin_memory = True
    if workers > 0:
        sft_config.dataloader_persistent_workers = True

    if getattr(sft_config, "save_strategy", None) in (None, "no"):
        sft_config.save_strategy = "steps"
    if not getattr(sft_config, "save_steps", None):
        sft_config.save_steps = 200
    if not getattr(sft_config, "logging_steps", None):
        sft_config.logging_steps = 10
    if getattr(sft_config, "save_total_limit", None) is None:
        sft_config.save_total_limit = 3
    if getattr(sft_config, "eval_strategy", "no") in (None, "no"):
        sft_config.eval_strategy = sft_config.save_strategy
    sft_config.load_best_model_at_end = True
    sft_config.metric_for_best_model = "eval_loss"
    sft_config.greater_is_better = False
    sft_config.report_to = getattr(sft_config, "report_to", None) or []

    metrics_callback = MetricsLoggerCallback(jsonl_log_path)
    checkpoint_reporter = CheckpointLossReporter()
    gpu_monitor = GPUSpikeMonitor(interval_sec=1.0)
    optimizer_switch_callback = OptimizerSwitchCallback(
        optim_switch_args.optimizer_switch_step,
        optim_switch_args.secondary_optimizer,
        optim_switch_args.secondary_learning_rate,
        optim_switch_args.secondary_weight_decay)
    live_dashboard = LiveDashboardCallback(
        metrics_callback, gpu_monitor,
        sft_config.per_device_train_batch_size,
        sft_config.gradient_accumulation_steps,
        refresh_every_n_logs=1,
        optimizer_switch_callback=optimizer_switch_callback,
        length_audit=length_audit)

    # ---- 7. Save the pre-flight report ---------------------------------
    la = {k: v for k, v in length_audit.items() if k != "all_token_lengths"}
    preflight = {
        "model": model_args.model_name_or_path,
        "data_dir": data_args.data_dir,
        "schema": schema, "audit": audit, "length_audit": la,
        "formatting": {"train": info_tr, "eval": info_ev},
        "formatted": {"train": len(train_ds), "validation": len(eval_ds),
                      "dropped_train": dropped_tr, "dropped_eval": dropped_ev,
                      "open_ended_train": open_tr, "open_ended_eval": open_ev},
        "effective_batch": (sft_config.per_device_train_batch_size
                            * sft_config.gradient_accumulation_steps
                            * max(1, getattr(sft_config, "world_size", 1) or 1)),
        "hyperparameters": {
            "learning_rate": sft_config.learning_rate,
            "num_train_epochs": sft_config.num_train_epochs,
            "per_device_train_batch_size": sft_config.per_device_train_batch_size,
            "gradient_accumulation_steps": sft_config.gradient_accumulation_steps,
            "max_seq_length": data_args.max_seq_length,
            "lora_r": model_args.lora_r, "lora_alpha": model_args.lora_alpha,
            "lora_dropout": model_args.lora_dropout,
            "optim": sft_config.optim, "bf16": sft_config.bf16,
            "group_by_length": sft_config.group_by_length,
            "attn_implementation": attn_implementation,
            "warmup_ratio": getattr(sft_config, "warmup_ratio", None),
            "lr_scheduler_type": str(getattr(sft_config, "lr_scheduler_type", "")),
            "weight_decay": sft_config.weight_decay,
        },
    }
    with open(os.path.join(sft_config.output_dir, "preflight_report.json"),
              "w", encoding="utf-8") as f:
        json.dump(preflight, f, ensure_ascii=False, indent=2)
    logger.info("Effective batch size: %d", preflight["effective_batch"])

    trainer = SFTTrainer(
        model=model, args=sft_config,
        train_dataset=train_ds, eval_dataset=eval_ds,
        peft_config=peft_config, processing_class=tokenizer,
        callbacks=[metrics_callback, checkpoint_reporter, live_dashboard,
                   optimizer_switch_callback])
    optimizer_switch_callback.trainer = trainer

    log_gpu_footprint("Post-Initialization")

    # ---- 8. Auto-resume -------------------------------------------------
    resume_checkpoint = sft_config.resume_from_checkpoint
    if not resume_checkpoint:
        detected = get_last_checkpoint(sft_config.output_dir)
        if detected:
            resume_checkpoint = detected
            logger.info("Resuming from checkpoint: %s", resume_checkpoint)
        else:
            logger.info("No checkpoint found --- training from scratch.")

    # ---- 9. Train --------------------------------------------------------
    logger.info("Starting fine-tuning...")
    gpu_monitor.start()
    try:
        trainer.train(resume_from_checkpoint=resume_checkpoint)
    except torch.cuda.OutOfMemoryError:
        logger.error(
            "CUDA OOM. Lower --per_device_train_batch_size and raise "
            "--gradient_accumulation_steps to keep the effective batch, lower "
            "--max_seq_length (check the length audit above for a safe value), "
            "or restart the kernel to clear fragmentation from a prior run.")
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        raise
    finally:
        gpu_monitor.stop()

    # ---- 10. Save --------------------------------------------------------
    logger.info("Saving adapters and tokenizer to: %s", sft_config.output_dir)
    trainer.save_model(sft_config.output_dir)
    tokenizer.save_pretrained(sft_config.output_dir)
    with open(os.path.join(sft_config.output_dir, "run_config_audit.json"), "w") as f:
        json.dump({"model_args": model_args.__dict__,
                   "data_args": data_args.__dict__,
                   "perf_args": perf_args.__dict__,
                   "optimizer_switch_args": optim_switch_args.__dict__}, f, indent=2)

    metrics = trainer.evaluate()
    logger.info("Final evaluation: %s", metrics)
    with open(os.path.join(sft_config.output_dir, "final_metrics.json"), "w") as f:
        json.dump({"eval": metrics,
                   "peak_vram_allocated_gb": gpu_monitor.peak_allocated_gb(),
                   "peak_vram_reserved_gb": gpu_monitor.peak_reserved_gb()},
                  f, indent=2)

    plot_training_dashboards(
        metrics_callback.history, gpu_monitor,
        sft_config.per_device_train_batch_size,
        sft_config.gradient_accumulation_steps,
        sft_config.output_dir,
        optimizer_switch_callback.switch_history, length_audit)

    logger.info("Peak GPU allocation: %.2fGB", gpu_monitor.peak_allocated_gb())

    # ---- 11. VRAM cleanup, for repeated %run in one kernel ---------------
    logger.info("Releasing references and clearing CUDA cache...")
    try:
        del trainer.optimizer
    except Exception:
        pass
    del trainer
    del model
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
    log_gpu_footprint("Post-Cleanup")
    logger.info("Pipeline execution complete.")


if __name__ == "__main__":
    main()
