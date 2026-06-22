"""workflow package — 16-step process split by step module."""
from app.api.workflow.core import router
from app.api.workflow import step2  # noqa: F401
from app.api.workflow import step3  # noqa: F401
from app.api.workflow import step4  # noqa: F401
from app.api.workflow import step5  # noqa: F401
from app.api.workflow import step6  # noqa: F401
from app.api.workflow import step7  # noqa: F401
from app.api.workflow import step8  # noqa: F401
from app.api.workflow import step9  # noqa: F401
from app.api.workflow import step10  # noqa: F401
from app.api.workflow import step11  # noqa: F401
from app.api.workflow import step12  # noqa: F401
from app.api.workflow import step13  # noqa: F401
from app.api.workflow import step14  # noqa: F401
from app.api.workflow import step15  # noqa: F401
from app.api.workflow import step16  # noqa: F401
__all__ = ["router"]
