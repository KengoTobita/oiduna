"""Output formatting utilities"""

import json
import sys
from typing import Any, Dict
from rich.console import Console


class OutputFormatter:
    """Handles output formatting for JSON and human-readable modes"""

    def __init__(self, json_mode: bool = False, console: Console = None):
        """Initialize output formatter

        Args:
            json_mode: Enable JSON output mode
            console: Rich console instance (for human mode)
        """
        self.json_mode = json_mode
        self.console = console or Console()

    def success(self, message: str, data: Any = None) -> None:
        """Output success message

        Args:
            message: Success message
            data: Optional data to include
        """
        if self.json_mode:
            output = {
                "status": "success",
                "message": message,
                "data": data
            }
            print(json.dumps(output, indent=2))
        else:
            self.console.print(f"[green]✓[/green] {message}")
            if data and isinstance(data, dict):
                for key, value in data.items():
                    self.console.print(f"  {key}: {value}")

    def error(self, message: str, details: str = None) -> None:
        """Output error message

        Args:
            message: Error message
            details: Optional error details
        """
        if self.json_mode:
            output = {
                "status": "error",
                "message": message,
                "details": details
            }
            print(json.dumps(output, indent=2), file=sys.stderr)
        else:
            self.console.print(f"[red]✗[/red] {message}", file=sys.stderr)
            if details:
                self.console.print(f"  {details}", file=sys.stderr)

    def info(self, message: str) -> None:
        """Output info message (human mode only)

        Args:
            message: Info message
        """
        if not self.json_mode:
            self.console.print(f"[blue]ℹ[/blue] {message}")
