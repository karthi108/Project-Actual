"""Explicit non-sensitive diagnostic, with metadata output only and no HTTP route."""

import asyncio
import logging
import sys

from actual.capabilities.probe import PROBE, ProbeInput

from .codec import encode_object
from .config import OllamaSettings
from .errors import ModelFailure
from .gateway import MODEL_LOG, ModelGateway, metadata_json
from .ollama import OllamaQwenProvider


async def probe(settings: OllamaSettings) -> str:
    gateway = ModelGateway(OllamaQwenProvider(settings), capabilities=(PROBE,))
    result = await gateway.run(PROBE, ProbeInput(synthetic=True, tokens=("red", "blue", "green")))
    return metadata_json(result.metadata)


def main() -> None:
    if len(sys.argv) != 1:
        raise SystemExit("The synthetic model probe accepts no prompt or input arguments.")
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    MODEL_LOG.handlers = [handler]
    MODEL_LOG.setLevel(logging.INFO)
    MODEL_LOG.propagate = False
    try:
        result = asyncio.run(probe(OllamaSettings.from_environment()))
    except ModelFailure as error:
        print(encode_object({"status": "failure", "error_code": error.code.value}).decode())
        raise SystemExit(1) from None
    print(result)


if __name__ == "__main__":
    main()
