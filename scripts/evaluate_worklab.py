"""Isolated synthetic development replay; no live or held-out accuracy claim."""

import json

from actual.worklab.evaluator import answers, evaluate
from actual.worklab.fixtures import observations
from actual.worklab.replay import replay

if __name__ == "__main__":
    print(
        json.dumps(
            evaluate(tuple(replay(case) for case in observations()), answers()), sort_keys=True
        )
    )
