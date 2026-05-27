from pathlib import Path

from validate_modes import analytical_matches, classify_modes, load_modes


ROOT = Path(__file__).resolve().parents[1]


def test_classifies_bending_and_non_bending_modes():
    data = load_modes(ROOT)
    classifications = classify_modes(data)

    assert classifications[1]["type"] == "1st bending (axis A)"
    assert classifications[2]["type"] == "1st bending (axis B)"
    assert classifications[3]["type"] == "2nd bending (axis A)"
    assert classifications[5]["type"] == "2nd bending (axis B)"
    assert classifications[4]["type"] == "torsion"
    assert classifications[6]["type"] == "non-bending"


def test_bending_modes_match_euler_bernoulli_shapes():
    data = load_modes(ROOT)
    matches = analytical_matches(data)

    assert matches[1]["bending_order"] == 1
    assert matches[2]["bending_order"] == 1
    assert matches[3]["bending_order"] == 2
    assert matches[5]["bending_order"] == 2

    for mode in (1, 2, 3, 5):
        assert matches[mode]["corr"] >= 0.989
        assert matches[mode]["rms"] <= 0.08
