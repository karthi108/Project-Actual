"""The rejected v1 runner is archived; it must not silently run a changed pipeline."""

import sys

if __name__ == "__main__":
    if len(sys.argv) != 1:
        print('{"evaluation":"failed","error_code":"unsupported_arguments"}')
        raise SystemExit(2)
    print('{"evaluation":"failed","error_code":"rejected_phase6_runner"}')
    raise SystemExit(1)
