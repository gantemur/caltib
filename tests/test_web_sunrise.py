import json
import math

import pytest

from caltib.core.types import SunriseState
from caltib.web_diag import api


def reject_constant(token):
    raise ValueError(f"Non-JSON constant: {token}")


def test_polar_transition_is_a_gap_in_strict_sunrise_json():
    raw = api.handle_request("sunrise", "l5", "2000-06-29", "2000-07-02", 66, 90)
    result = json.loads(raw, parse_constant=reject_constant)
    trace, = result["traces"]
    assert trace["x"] == ["2000-06-29", "2000-06-30", "2000-07-02"]
    assert len(trace["x"]) == len(trace["y"])
    assert trace["y"][:2] == [None, None]
    assert trace["y"][2] == pytest.approx(5.742234793622885, abs=1e-6)
    shading = [shape for shape in result["layout_extras"]["shapes"] if shape.get("yref") == "paper"]
    assert [(s["x0"], s["x1"], s["fillcolor"]) for s in shading] == [
        ("2000-06-29", "2000-06-29", "#fef08a"),
    ]


def test_missing_model_values_keep_alignment(monkeypatch):
    class Engine:
        values = iter((math.inf, math.nan, 0.25))

        def eval_sunrise_lmt(self, t2000_tt):
            return next(self.values), SunriseState.NORMAL

    monkeypatch.setattr(api, "get_calendar", lambda *args, **kwargs: Engine())
    raw = api.handle_request("sunrise", "l5", "2000-03-20", "2000-03-23", 35, 0)
    trace, = json.loads(raw, parse_constant=reject_constant)["traces"]
    assert len(trace["x"]) == len(trace["y"]) == 3
    assert trace["y"][:2] == [None, None]
    assert math.isfinite(trace["y"][2])


def test_sunrise_route_rejects_unsanitized_payload(monkeypatch):
    monkeypatch.setattr(api, "get_sunrise_payload", lambda *args: {"unexpected": math.nan})
    with pytest.raises(ValueError):
        api.handle_request("sunrise", "l5", "2000-03-20", "2000-03-23", 35, 0)
