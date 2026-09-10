import numpy as np
import pytest

from track_sprint.metrics import angle, side_metrics, smooth, cycles_from_thigh


def skeleton():
    p = np.ones((33, 4))
    # An upright body, horizontal forward thigh, vertical shin in a 2:1 image.
    p[11, :2], p[23, :2], p[25, :2], p[27, :2] = (.4, .2), (.4, .5), (.55, .5), (.55, .8)
    return p


def test_known_right_angle_and_pixel_aspect():
    p = skeleton()
    out = side_metrics(p, "left", 1000, 500, "right")
    assert out == pytest.approx({"knee": 90, "hip": 90, "trunk": 0, "thigh": 90})
    p[25, :2] = (.5, .7)  # 100 px forward and 100 px down, despite unequal normalized steps
    assert side_metrics(p, "left", 1000, 500, "right")["thigh"] == pytest.approx(45)


def test_mirroring_and_direction_preserve_angles():
    p = skeleton()
    mirror = p.copy()
    mirror[:, 0] = 1 - p[:, 0]
    assert side_metrics(p, "left", 1000, 500, "right") == pytest.approx(
        side_metrics(mirror, "left", 1000, 500, "left"))


def test_low_visibility_affects_only_dependent_angles():
    p = skeleton()
    p[27, 2] = .2
    result = side_metrics(p, "left", 1000, 500, "right")
    assert np.isnan(result["knee"])
    assert result["hip"] == pytest.approx(90)
    p[23, :2] = p[25, :2]
    assert np.isnan(side_metrics(p, "left", 1000, 500, "right")["hip"])


def test_straight_leg_and_degenerate_geometry():
    assert angle(np.array([0., 1.]), np.array([0., 0.]), np.array([0., -1.])) == pytest.approx(180)
    assert np.isnan(angle(np.zeros(2), np.zeros(2), np.ones(2)))


def test_smoothing_never_bridges_a_visibility_gap():
    values = np.array([0., 1., 3., 2., 5., np.nan, 20., 21., 22., 23., 24.])
    filtered = smooth(values, np.arange(len(values)) / 60)
    assert np.isnan(filtered[5])
    assert filtered[6:] == pytest.approx([20, 21, 22, 23, 24])
    assert np.isfinite(filtered[:5]).all()


def test_cycles_require_repeated_peaks_and_valid_span():
    values = 60 * np.sin(np.linspace(0, 6 * np.pi, 180))
    assert len(cycles_from_thigh(values)) == 2
    values[45:135] = np.nan
    assert cycles_from_thigh(values) == []
