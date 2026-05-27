from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_COLUMNS = {
    "Node Number",
    "X Location (m)",
    "Y Location (m)",
    "Z Location (m)",
    "Total Deformation (m)",
}


def load_mode_file(mode):
    path = ROOT / f"Mode{mode}.txt"
    df = pd.read_csv(path, sep="\t")
    df.columns = df.columns.str.strip()
    return df


def test_all_mode_files_load_with_expected_shape_and_columns():
    frames = []

    for mode in range(1, 7):
        df = load_mode_file(mode)
        assert REQUIRED_COLUMNS.issubset(df.columns)
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)
    assert len(combined) == 6462


def test_deformation_is_nonnegative_and_zero_at_clamp():
    combined = pd.concat([load_mode_file(mode) for mode in range(1, 7)], ignore_index=True)

    deformation = combined["Total Deformation (m)"]
    assert (deformation >= 0).all()

    clamp = combined[combined["Z Location (m)"].sub(0.02).abs() < 1e-12]
    assert not clamp.empty
    assert clamp["Total Deformation (m)"].abs().max() < 1e-9


def test_coordinates_match_expected_beam_bounds():
    combined = pd.concat([load_mode_file(mode) for mode in range(1, 7)], ignore_index=True)

    assert combined["X Location (m)"].between(-0.002, 0.002).all()
    assert combined["Y Location (m)"].between(-0.001, 0.001).all()
    assert combined["Z Location (m)"].between(0.0, 0.02).all()

