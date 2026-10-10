import pytest

from actual.workflows.backoff import delay, maximum


def test_retry_jitter_is_stable_bounded_and_varies_between_intents():
    values = {delay(100, 1, f"run_{i}") for i in range(40)}
    assert len(values) > 1 and min(values) >= 200 and max(values) <= 250
    assert delay(100, 1, "same") == delay(100, 1, "same")
    assert delay(300, 4, "same") == maximum(300, 4) == 300
    with pytest.raises(ValueError):
        delay(1, 200, "invalid")
