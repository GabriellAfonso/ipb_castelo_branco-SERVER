"""Settings loader.

Selects the active settings module based on environment.

- Default: dev
- Production: set DJANGO_ENV=prod

You can also explicitly set DJANGO_SETTINGS_MODULE to core.settings.dev/prod.
"""

from __future__ import annotations

import os


_env = (os.environ.get("DJANGO_ENV") or "dev").strip().lower()

if _env in {"prod", "production"}:
    from .prod import *  # noqa: F401,F403
else:
    from .dev import *  # noqa: F401,F403
