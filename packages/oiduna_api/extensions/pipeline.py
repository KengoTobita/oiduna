"""Extension pipeline - discovery, registration, and execution."""

import logging
from importlib.metadata import entry_points
from typing import Callable

from .base import BaseExtension

logger = logging.getLogger(__name__)

ENTRY_POINT_GROUP = "oiduna.extensions"


class ExtensionPipeline:
    """
    Manages the lifecycle and execution of extensions.

    Responsibilities:
    - Register extensions
    - Apply session transformations in order
    - Collect runtime hooks for loop_engine
    - Manage startup/shutdown

    Usage:
        >>> pipeline = ExtensionPipeline()
        >>> pipeline.register("superdirt", SuperDirtExtension())
        >>> payload = pipeline.apply({"messages": [], "bpm": 120})
        >>> hooks = pipeline.get_send_hooks()
    """

    def __init__(self):
        self._extensions: list[tuple[str, BaseExtension]] = []

    def register(self, name: str, ext: BaseExtension) -> None:
        """
        Register an extension.

        Args:
            name: Extension name (e.g., "superdirt")
            ext: Extension instance
        """
        self._extensions.append((name, ext))
        logger.info(f"Extension registered: {name}")

    @property
    def extensions(self) -> list[tuple[str, BaseExtension]]:
        """Get list of (name, extension) tuples."""
        return self._extensions

    def apply(self, payload: dict) -> dict:
        """
        Apply all extension transformations in order.

        Args:
            payload: Session payload dict

        Returns:
            Transformed payload

        Raises:
            ExtensionError: If any extension fails
        """
        for name, ext in self._extensions:
            try:
                payload = ext.transform(payload)
            except Exception as e:
                logger.exception(f"Extension '{name}' failed during transform")
                raise ExtensionError(name, str(e)) from e

        return payload

    def get_send_hooks(self) -> list[Callable]:
        """
        Collect before_send_messages hooks from all extensions.

        Returns:
            List of callables with signature:
            (messages, current_bpm, current_step) -> messages

        Used by loop_engine to apply runtime transformations.
        """
        hooks = []
        for name, ext in self._extensions:
            # Only include if extension overrides the default implementation
            if ext.before_send_messages.__func__ is not BaseExtension.before_send_messages:
                hooks.append(ext.before_send_messages)
                logger.debug(f"Registered send hook from extension: {name}")

        return hooks

    async def startup_all(self) -> None:
        """Call startup() on all extensions."""
        for name, ext in self._extensions:
            try:
                logger.info(f"Starting extension: {name}")
                ext.startup()
            except Exception:
                logger.exception(f"Extension '{name}' failed during startup")
                raise

    async def shutdown_all(self) -> None:
        """Call shutdown() on all extensions (reverse order)."""
        for name, ext in reversed(self._extensions):
            try:
                logger.info(f"Shutting down extension: {name}")
                ext.shutdown()
            except Exception:
                logger.exception(f"Extension '{name}' failed during shutdown")


class ExtensionError(Exception):
    """Raised when an extension transformation fails."""

    def __init__(self, extension_name: str, message: str):
        self.extension_name = extension_name
        super().__init__(f"Extension '{extension_name}' failed: {message}")


def discover_extensions() -> ExtensionPipeline:
    """
    Auto-discover extensions via entry_points and build pipeline.

    Looks for entry_points in the "oiduna.extensions" group.
    Extensions are registered in the order they are discovered.

    Returns:
        ExtensionPipeline with discovered extensions

    Example pyproject.toml:
        [project.entry-points."oiduna.extensions"]
        superdirt = "oiduna_extension_superdirt:SuperDirtExtension"
    """
    pipeline = ExtensionPipeline()

    try:
        discovered = entry_points(group=ENTRY_POINT_GROUP)
    except TypeError:
        # Python 3.9 compatibility
        discovered = entry_points().get(ENTRY_POINT_GROUP, [])

    if not discovered:
        logger.info("No extensions found")
        return pipeline

    for ep in discovered:
        try:
            # Load extension class
            cls = ep.load()

            # Validate it's a BaseExtension subclass
            if not issubclass(cls, BaseExtension):
                logger.warning(
                    f"Entry point '{ep.name}' does not extend BaseExtension, skipping"
                )
                continue

            # Instantiate with default config
            # TODO: Load config from extensions.yaml if it exists
            instance = cls()
            pipeline.register(ep.name, instance)

        except Exception as e:
            logger.error(f"Failed to load extension '{ep.name}': {e}")
            raise

    return pipeline
