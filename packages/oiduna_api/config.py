"""Centralized configuration using Pydantic Settings

All environment variables are managed here.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # OSC Configuration
    osc_host: str = "127.0.0.1"
    osc_port: int = 57120

    # MIDI Configuration
    midi_port: str | None = None

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Testing Configuration
    run_stability_tests: bool = False

    # Asset Management Configuration
    assets_dir: Path = Path("./oiduna_data")

    @property
    def samples_dir(self) -> Path:
        """Directory for custom samples"""
        return self.assets_dir / "samples"

    @property
    def synthdefs_dir(self) -> Path:
        """Directory for custom SynthDefs"""
        return self.assets_dir / "synthdefs"

    # Upload limits
    max_sample_size_mb: int = 100
    max_total_samples_gb: int = 10

    # SuperDirt integration
    superdirt_auto_reload: bool = True


# Global settings instance
settings = Settings()
