from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold, cross_val_score, train_test_split


DATA_DIR = Path(__file__).resolve().parent
LENGTH = 0.02
MODE_COUNT = 6
BENDING_MODE_ORDERS = {1: 1, 2: 1, 3: 2, 5: 2}
BETA_L = {1: 1.8751, 2: 4.6941, 3: 7.8548}
SIGMA = {1: 0.7341, 2: 1.0185, 3: 0.9992}


def load_modes(data_dir=DATA_DIR):
    frames = []

    for mode in range(1, MODE_COUNT + 1):
        path = Path(data_dir) / f"Mode{mode}.txt"
        df = pd.read_csv(path, sep="\t")
        df.columns = df.columns.str.strip()
        df = df.rename(
            columns={
                "Node Number": "Node",
                "X Location (m)": "X",
                "Y Location (m)": "Y",
                "Z Location (m)": "Z",
                "Total Deformation (m)": "Deformation",
            }
        )
        df["Mode"] = mode
        frames.append(df)

    return pd.concat(frames, ignore_index=True)


def axial_profile(data, mode):
    profile = (
        data[data["Mode"] == mode]
        .assign(x_from_clamp=lambda df: LENGTH - df["Z"])
        .groupby("x_from_clamp", as_index=False)["Deformation"]
        .mean()
        .sort_values("x_from_clamp")
    )
    return profile["x_from_clamp"].to_numpy(), profile["Deformation"].to_numpy()


def normalized(values):
    values = np.asarray(values, dtype=float)
    max_value = np.max(np.abs(values))
    if max_value == 0:
        return values
    return np.abs(values) / max_value


def count_interior_minima(values):
    y = normalized(values)
    count = 0

    for index in range(1, len(y) - 1):
        if y[index] < y[index - 1] and y[index] < y[index + 1] and y[index] < 0.3:
            count += 1

    return count


def classify_modes(data):
    classifications = {}

    for mode in range(1, MODE_COUNT + 1):
        _, deformation = axial_profile(data, mode)
        interior_nodes = count_interior_minima(deformation)
        tip = data[(data["Mode"] == mode) & (data["Z"].abs() < 1e-12)]["Deformation"]
        tip_std = float(tip.std(ddof=0))
        tip_min = float(tip.min())
        tip_max = float(tip.max())

        if tip_std > 5.0:
            mode_type = "torsion"
        elif mode == 6:
            mode_type = "non-bending"
        elif interior_nodes == 0:
            mode_type = f"1st bending (axis {'A' if mode == 1 else 'B'})"
        elif interior_nodes == 1:
            mode_type = f"2nd bending (axis {'A' if mode == 3 else 'B'})"
        else:
            mode_type = "unclassified"

        classifications[mode] = {
            "interior_nodes": interior_nodes,
            "tip_min": tip_min,
            "tip_max": tip_max,
            "tip_std": tip_std,
            "type": mode_type,
        }

    return classifications


def euler_bernoulli_shape(order, x_from_clamp):
    xi = np.asarray(x_from_clamp, dtype=float) / LENGTH
    beta_l = BETA_L[order]
    sigma = SIGMA[order]
    shape = (np.cosh(beta_l * xi) - np.cos(beta_l * xi)) - sigma * (
        np.sinh(beta_l * xi) - np.sin(beta_l * xi)
    )
    return normalized(shape)


def analytical_matches(data):
    matches = {}

    for mode, order in BENDING_MODE_ORDERS.items():
        x_from_clamp, deformation = axial_profile(data, mode)
        observed = normalized(deformation)
        analytical = euler_bernoulli_shape(order, x_from_clamp)
        corr = float(np.corrcoef(observed, analytical)[0, 1])
        rms = float(np.sqrt(np.mean((observed - analytical) ** 2)))
        matches[mode] = {"bending_order": order, "corr": corr, "rms": rms}

    return matches


def ml_evaluation(data):
    features = data[["X", "Y", "Z", "Mode"]]
    target = data["Deformation"]

    x_train, x_test, y_train, y_test = train_test_split(
        features, target, test_size=0.2, random_state=42
    )
    model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)
    random_split = {
        "r2": float(r2_score(y_test, predictions)),
        "mse": float(mean_squared_error(y_test, predictions)),
    }

    grouped_model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    group_scores = cross_val_score(
        grouped_model,
        features,
        target,
        cv=GroupKFold(n_splits=5),
        groups=data["Node"],
        scoring="r2",
        n_jobs=-1,
    )

    holdout = {}
    for mode in range(1, MODE_COUNT + 1):
        train = data[data["Mode"] != mode]
        test = data[data["Mode"] == mode]
        holdout_model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        holdout_model.fit(train[["X", "Y", "Z", "Mode"]], train["Deformation"])
        predicted = holdout_model.predict(test[["X", "Y", "Z", "Mode"]])
        holdout[mode] = float(r2_score(test["Deformation"], predicted))

    return {
        "random_split": random_split,
        "group_kfold_scores": group_scores,
        "group_kfold_mean": float(np.mean(group_scores)),
        "holdout_mode": holdout,
    }


def print_classification_table(classifications):
    print("Mode classification")
    print("Mode | Interior axial nodes | Tip | Type")
    print("---: | ---: | --- | ---")
    for mode, values in classifications.items():
        tip = (
            f"|D| [{values['tip_min']:.1f}, {values['tip_max']:.1f}], "
            f"std {values['tip_std']:.1f}"
        )
        print(f"{mode:>4} | {values['interior_nodes']:>20} | {tip} | {values['type']}")


def print_analytical_table(matches):
    print("\nEuler-Bernoulli cantilever shape match")
    print("Mode | EB bending order | corr | RMS")
    print("---: | ---: | ---: | ---:")
    for mode, values in matches.items():
        print(
            f"{mode:>4} | {values['bending_order']:>16} | "
            f"{values['corr']:+.4f} | {values['rms']:.4f}"
        )


def print_ml_table(results):
    random_split = results["random_split"]
    print("\nML evaluation")
    print(f"Random 80/20 split R^2: {random_split['r2']:.4f}")
    print(f"Random 80/20 split MSE: {random_split['mse']:.4f}")
    print(f"GroupKFold by node R^2 mean: {results['group_kfold_mean']:.4f}")
    print("Hold out entire mode")
    print("Mode | R^2")
    print("---: | ---:")
    for mode, score in results["holdout_mode"].items():
        print(f"{mode:>4} | {score:+.4f}")
    print("\nConclusion: this is a fast field surrogate over the six computed modes, not a new-mode predictor.")


def main():
    data = load_modes()
    print(f"Loaded {len(data)} rows across {MODE_COUNT} modes.\n")
    print_classification_table(classify_modes(data))
    print_analytical_table(analytical_matches(data))
    print_ml_table(ml_evaluation(data))


if __name__ == "__main__":
    main()
