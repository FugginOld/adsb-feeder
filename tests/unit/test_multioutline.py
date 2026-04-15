"""Tests for utils.multioutline module."""

import json
from unittest.mock import mock_open, patch

from shapely.geometry import Polygon
from utils.multioutline import MultiOutline, check_valid


def test_check_valid_rejects_empty_polygon_input():
    valid, reason = check_valid(None)
    assert valid is False
    assert "no polygon" in reason


def test_check_valid_accepts_valid_polygon():
    polygon = Polygon([(0, 0), (1, 0), (0, 1)])
    valid, reason = check_valid(polygon)
    assert valid is True
    assert reason == ""


def test_tar1090port_uses_default_when_missing(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("OTHER_KEY=value\n")

    with patch("utils.multioutline.ENV_FILE", str(env_file)):
        assert MultiOutline()._tar1090port() == "8080"


def test_tar1090port_reads_configured_port(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("AF_TAR1090_PORT=38080\n")

    with patch("utils.multioutline.ENV_FILE", str(env_file)):
        assert MultiOutline()._tar1090port() == "38080"


def test_get_outlines_ignores_missing_files_and_collects_present():
    outline_data = {"actualRange": {"last24h": {"points": [[0, 0], [1, 0], [0, 1]]}}}
    handles = {
        "/run/adsb-feeder-uf_1/readsb/outline.json": mock_open(read_data="{}").return_value,
    }

    def open_side_effect(path, *_args, **_kwargs):
        if path in handles:
            return handles[path]
        raise FileNotFoundError(path)

    with patch("builtins.open", side_effect=open_side_effect), patch("utils.multioutline.json.load", return_value=outline_data):
        outlines = MultiOutline()._get_outlines(2)

    assert outlines == [outline_data]


def test_create_returns_empty_when_no_valid_polygons():
    data = [{"actualRange": {"last24h": {"points": [[0, 0], [1, 0]]}}}]  # only two points
    result = MultiOutline().create(data)
    assert result == {"multiRange": []}


def test_create_merges_overlapping_polygons_into_single_outline():
    data = [
        {"actualRange": {"last24h": {"points": [[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]}}},
        {"actualRange": {"last24h": {"points": [[1, 1], [3, 1], [3, 3], [1, 3], [1, 1]]}}},
    ]

    result = MultiOutline().create(data)

    assert "multiRange" in result
    assert len(result["multiRange"]) == 1
    assert len(result["multiRange"][0]) >= 4


def test_create_heywhatsthat_returns_none_when_hash_is_current(monkeypatch):
    mo = MultiOutline()
    responses = [json.dumps({"lat": 1, "lon": 2, "rings": [{"alt": 1000, "points": [[0, 0], [1, 0], [0, 1]]}]})]

    monkeypatch.setattr(mo, "_get_heywhatsthat", lambda _num: responses)
    monkeypatch.setattr(mo, "_tar1090port", lambda: "8080")

    import hashlib

    current_hash = hashlib.md5("".join(responses).encode()).hexdigest()

    with patch("utils.multioutline.get_plain_url", return_value=(json.dumps({"multioutline_hash": current_hash}), 200)):
        assert mo.create_heywhatsthat(1) is None


def test_create_heywhatsthat_builds_combined_result_when_hash_changes(monkeypatch):
    mo = MultiOutline()
    responses = [
        json.dumps({"lat": 1, "lon": 2, "rings": [{"alt": 1000, "points": [[0, 0], [2, 0], [0, 2], [0, 0]]}]}),
        json.dumps({"lat": 1, "lon": 2, "rings": [{"alt": 1000, "points": [[0, 0], [1, 0], [0, 1], [0, 0]]}]}),
    ]

    monkeypatch.setattr(mo, "_get_heywhatsthat", lambda _num: responses)
    monkeypatch.setattr(mo, "_tar1090port", lambda: "8080")

    with patch("utils.multioutline.get_plain_url", return_value=(None, 404)):
        result = mo.create_heywhatsthat(2)

    assert result is not None
    assert result["id"] == "combined"
    assert result["lat"] == 1
    assert result["lon"] == 2
    assert "multioutline_hash" in result
    assert len(result["rings"]) >= 1
