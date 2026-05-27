from pathlib import Path

import matplotlib.pyplot as plt

from validate_modes import (
    BENDING_MODE_ORDERS,
    DATA_DIR,
    MODE_COUNT,
    analytical_matches,
    axial_profile,
    euler_bernoulli_shape,
    load_modes,
    normalized,
)


FIGURE_PATH = DATA_DIR / "figures" / "mode_shapes_validation.png"


def main():
    data = load_modes()
    matches = analytical_matches(data)
    fig, axes = plt.subplots(2, 3, figsize=(12, 7), sharex=True, sharey=True)

    for mode, axis in zip(range(1, MODE_COUNT + 1), axes.ravel()):
        x_from_clamp, deformation = axial_profile(data, mode)
        x_mm = x_from_clamp * 1000.0
        axis.plot(x_mm, normalized(deformation), color="#1f77b4", linewidth=2, label="ANSYS")

        if mode in BENDING_MODE_ORDERS:
            order = BENDING_MODE_ORDERS[mode]
            eb_shape = euler_bernoulli_shape(order, x_from_clamp)
            axis.plot(x_mm, eb_shape, "--", color="#d62728", linewidth=1.8, label="Euler-Bernoulli")
            axis.text(
                0.04,
                0.86,
                f"corr {matches[mode]['corr']:.3f}",
                transform=axis.transAxes,
                fontsize=9,
            )
        elif mode == 4:
            axis.text(0.05, 0.82, "torsion", transform=axis.transAxes, fontsize=10)
        else:
            axis.text(0.05, 0.82, "non-bending", transform=axis.transAxes, fontsize=10)

        axis.set_title(f"Mode {mode}")
        axis.grid(True, alpha=0.3)

    for axis in axes[-1, :]:
        axis.set_xlabel("Distance from clamp, x (mm)")
    for axis in axes[:, 0]:
        axis.set_ylabel("Normalized mean |D|")

    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.suptitle("Modal Shape Validation Against Cantilever Beam Theory", y=0.98)
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.93), ncol=2, frameon=False)
    fig.tight_layout(rect=(0, 0, 1, 0.88))

    FIGURE_PATH.parent.mkdir(exist_ok=True)
    fig.savefig(FIGURE_PATH, dpi=150)
    plt.close(fig)
    print(f"Wrote {FIGURE_PATH}")


if __name__ == "__main__":
    main()
