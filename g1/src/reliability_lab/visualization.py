"""Non-interactive, source-derived figures; no estimated detector masks."""
from __future__ import annotations
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import BoundaryNorm, ListedColormap


def plot_signals(x_ref: np.ndarray, x_obs: np.ndarray, time_s: np.ndarray,
                 config: dict, path: str | Path) -> None:
    p = config["corruption"]
    alpha = p["alpha"]
    fig, axes = plt.subplots(2, 3, figsize=(16, 7), sharex=True, constrained_layout=True)
    for row, record_id in enumerate(config["experiment"]["record_ids"]):
        for axis, axis_name in enumerate(config["experiment"]["axis_names"]):
            ax = axes[row, axis]
            ax.plot(time_s, x_ref[row, axis], linewidth=1.3, color="#2B6CB0", label="X_ref")
            ax.plot(time_s, x_obs[row, axis], linewidth=1.1, color="#D1495B",
                    linestyle="--", label="X_obs")
            if axis == p["axis"]:
                ax.axvspan(p["start_s"], p["end_s"], color="#FACF73",
                           alpha=0.28, label="[3,6) injection window")
                ax.axvline(p["start_s"], color="#C48A23", linewidth=0.8)
                ax.axvline(p["end_s"], color="#C48A23", linewidth=0.8)
            ax.set_title(f"{record_id} / {axis_name}")
            ax.set_ylabel("dynamic acceleration (m/s²)")
            ax.grid(alpha=0.2)
            ax.set_xlim(0, config["generator"]["duration_s"])
            if row == 1:
                ax.set_xlabel("time (s)")
            if row == 0 and axis == 0:
                ax.legend(loc="upper right", fontsize=8)
    fig.suptitle(f"G1 | reference vs axis freeze | alpha={alpha:g} | window shown only on x")
    fig.savefig(path, dpi=155)
    plt.close(fig)


def plot_mask(mask: np.ndarray, config: dict, path: str | Path) -> None:
    p = config["corruption"]
    edges = np.arange(config["generator"]["samples"] + 1) / config["generator"]["fs_hz"]
    fig, axes = plt.subplots(2, 1, figsize=(13, 5.1), sharex=True, constrained_layout=True)
    cmap = ListedColormap(["#F1F5F9", "#E17942"])
    norm = BoundaryNorm([-0.5, 0.5, 1.5], cmap.N)
    for i, name in enumerate(config["experiment"]["record_ids"]):
        m = axes[i].pcolormesh(edges, np.arange(4), mask[i], shading="flat", cmap=cmap,
                               norm=norm)
        axes[i].set_yticks([0.5, 1.5, 2.5], ["x", "y", "z"])
        axes[i].set_ylim(3, 0)
        axes[i].set_xlim(0, config["generator"]["duration_s"])
        axes[i].set_ylabel(name)
        axes[i].set_title(f"{name} | injected mask entries = {int(mask[i].sum())}")
    axes[-1].set_xlabel("time (s); each cell spans [i/fs,(i+1)/fs)")
    cbar = fig.colorbar(m, ax=axes, ticks=[0, 1], fraction=0.018, pad=0.01)
    cbar.ax.set_yticklabels(["0: no injection", "1: injection"])
    fig.suptitle(f"G1 true injection mask Z (alpha={p['alpha']:g}); NOT a detector output")
    fig.savefig(path, dpi=155)
    plt.close(fig)
