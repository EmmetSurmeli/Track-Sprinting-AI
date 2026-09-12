"""The optional live evaluation must not exceed its own local spending allowance."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

from track_sprint.schemas import CoachingReport


@pytest.fixture
def evaluation(tmp_path):
    spec = importlib.util.spec_from_file_location("evaluation", Path(__file__).parents[1] / "scripts/evaluate_coaching.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OUT = tmp_path
    return module


def arguments():
    return dict(model="gpt-5.4-mini", instructions="test", input="test", text_format=CoachingReport, max_output_tokens=2500)


def test_budget_refuses_request_before_network(evaluation):
    calls = []
    meter = evaluation.BudgetedResponses(SimpleNamespace(responses=SimpleNamespace(parse=lambda **kw: calls.append(kw))))
    meter.entries = [{"budget_charge_usd": evaluation.CAP_USD - .001}]
    with pytest.raises(RuntimeError, match="budget reached"):
        meter.parse(**arguments())
    assert not calls


def test_unknown_network_outcome_keeps_reserve_across_runs(evaluation):
    def timeout(**kw):
        raise TimeoutError()
    client = SimpleNamespace(responses=SimpleNamespace(parse=timeout))
    meter = evaluation.BudgetedResponses(client)
    with pytest.raises(TimeoutError):
        meter.parse(**arguments())
    reloaded = evaluation.BudgetedResponses(client)
    assert reloaded.entries[0]["budget_charge_usd"] > 0
    assert reloaded.entries[0]["outcome"] == "TimeoutError"


def test_usage_replaces_reserve_and_counts_cached_tokens_conservatively(evaluation):
    response = SimpleNamespace(status="completed", usage=SimpleNamespace(model_dump=lambda: {"input_tokens":1000,"output_tokens":100}),
                               model_dump_json=lambda **kw: '{}')
    meter = evaluation.BudgetedResponses(SimpleNamespace(responses=SimpleNamespace(parse=lambda **kw: response)))
    meter.parse(**arguments())
    assert meter.entries[0]["estimated_usd"] == pytest.approx(.0012)
    assert meter.entries[0]["budget_charge_usd"] < meter.entries[0]["reserved_usd"]
