from pathlib import Path
import logging
import sys

import uvicorn


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from omniclaw.app import create_app
from omniclaw.config import load_settings
from omniclaw.litellm_runtime import ensure_local_litellm_proxy


settings = load_settings()
app = create_app(settings)


def main() -> None:
    logger = logging.getLogger(__name__)
    with ensure_local_litellm_proxy(settings, logger=logger):
        uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
