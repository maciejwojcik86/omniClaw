from omniclaw.runtime.schemas import RuntimeActionRequest

__all__ = ["RuntimeActionRequest", "RuntimeService"]


def __getattr__(name: str):
    if name == "RuntimeService":
        from omniclaw.runtime.service import RuntimeService

        return RuntimeService
    raise AttributeError(name)
