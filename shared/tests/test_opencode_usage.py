from coreview_shared.agent.opencode import OpenCodeAgent


def test_parse_step_finish_usage_extracts_tokens() -> None:
    event = {
        "type": "step_finish",
        "part": {
            "type": "step-finish",
            "reason": "tool-calls",
            "tokens": {
                "input": 1200,
                "output": 340,
                "total": 1540,
            },
        },
    }
    usage = OpenCodeAgent._parse_step_finish_usage(event, 0)
    assert usage is not None
    assert usage.call_index == 0
    assert usage.input_tokens == 1200
    assert usage.output_tokens == 340
    assert usage.total_tokens == 1540
    assert usage.reason == "tool-calls"


def test_parse_step_finish_usage_computes_total_when_missing() -> None:
    event = {
        "type": "step_finish",
        "part": {
            "type": "step-finish",
            "tokens": {
                "input_tokens": 100,
                "output_tokens": 25,
            },
        },
    }
    usage = OpenCodeAgent._parse_step_finish_usage(event, 2)
    assert usage is not None
    assert usage.total_tokens == 125


def test_parse_step_finish_usage_records_zero_when_tokens_missing() -> None:
    event = {
        "type": "step_finish",
        "part": {"type": "step-finish", "reason": "stop"},
    }
    usage = OpenCodeAgent._parse_step_finish_usage(event, 1)
    assert usage is not None
    assert usage.input_tokens == 0
    assert usage.output_tokens == 0
    assert usage.total_tokens == 0


def test_parse_step_finish_usage_ignores_non_finish_events() -> None:
    assert OpenCodeAgent._parse_step_finish_usage({"type": "text"}, 0) is None
