"""Trajectory percents and plain-English takeaways."""

from src.trajectory import build_trajectory, percent_label, project_roic


APPLE = {
    "decay_params": {
        "lambda": 0.09,
        "roic_0": 0.46,
        "roic_terminal": 0.28,
    },
    "roic_history": [(year, 0.4) for year in range(2016, 2025)],
}


def test_apple_takeaways_match_the_decay_formula():
    trajectory = build_trajectory(APPLE)
    assert trajectory is not None

    y5 = project_roic(2029 - 2016, 0.46, 0.09, 0.28)
    y10 = project_roic(2034 - 2016, 0.46, 0.09, 0.28)
    assert trajectory["year_5"] == {"year": 2029, "roic": round(y5, 4)}
    assert trajectory["year_10"] == {"year": 2034, "roic": round(y10, 4)}
    assert percent_label(y5) == "34%"
    assert percent_label(y10) == "32%"

    five = trajectory["takeaways"]["five_year"]
    ten = trajectory["takeaways"]["ten_year"]
    assert five == (
        "In 5 years, return on capital is about 34%, still above the long-run 28%. "
        "The advantage is fading slowly."
    )
    assert ten == (
        "In 10 years, return on capital is about 32%, still above the long-run 28%. "
        "The advantage is fading, but it is a wide moat that lasts."
    )
    assert trajectory["forecast"][0]["year"] == 2024
    assert trajectory["forecast"][-1]["year"] == 2034
    assert len(trajectory["historical"]) == 9


def test_missing_history_does_not_invent_a_series():
    assert build_trajectory({"decay_params": APPLE["decay_params"], "roic_history": []}) is None
    assert build_trajectory(None) is None
    assert build_trajectory({"roic_history": [(2020, 0.2)]}) is None
