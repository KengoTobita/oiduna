"""Configuration for Oiduna client"""


class Config:
    """Oiduna client configuration"""

    def __init__(
        self,
        base_url: str = "http://localhost:57122",
        timeout: float = 30.0,
    ):
        """Initialize configuration

        Args:
            base_url: Oiduna API base URL
            timeout: Default request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout


# Default configuration instance
default_config = Config()
