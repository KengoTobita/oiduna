"""FastAPI dependencies for Oiduna API."""

from fastapi import Request

from oiduna_api.extensions import ExtensionPipeline


def get_pipeline(request: Request) -> ExtensionPipeline:
    """
    Dependency to get the extension pipeline.

    Usage:
        @router.post("/session")
        async def load_session(
            pipeline: ExtensionPipeline = Depends(get_pipeline)
        ):
            payload = pipeline.apply(req.model_dump())
            ...
    """
    return request.app.state.extension_pipeline
