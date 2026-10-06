"""Bounded cleanup of this runner's live Popen handle, never a shared server."""

import subprocess

_FAILURE = "owned_server_cleanup_failed"
TREE_TIMEOUT_SECONDS = 10
HANDLE_TIMEOUT_SECONDS = 5


def cleanup_owned_server(process: subprocess.Popen[bytes]) -> None:
    """Stop an owned tree; an exact-handle fallback cannot certify child cleanup.

    The caller must supply the Popen returned by its own server spawn. A PID alone
    is deliberately insufficient. If tree termination fails, always stop/reap the
    original process handle, then report the unconfirmed child outcome safely.
    """
    # A parent that has already exited may have left runner children behind. Its
    # handle can be reaped, but its potentially reused PID must never be targeted.
    tree_failed = process.poll() is not None
    try:
        if not tree_failed:
            try:
                killed = subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    capture_output=True,
                    timeout=TREE_TIMEOUT_SECONDS,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                tree_failed = killed.returncode != 0
            except (OSError, subprocess.TimeoutExpired):
                tree_failed = True
            finally:
                # kill() operates on the existing Popen handle, not a reconstructed
                # PID. It runs even when taskkill raises or times out.
                if process.poll() is None:
                    process.kill()
        process.wait(timeout=HANDLE_TIMEOUT_SECONDS)
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError(_FAILURE) from None
    if tree_failed:
        raise RuntimeError(_FAILURE)
