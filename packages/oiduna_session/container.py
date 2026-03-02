"""SessionContainer - 軽量なマネージャーコンテナ."""

from typing import Optional
from oiduna_models import Session, IDGenerator
from .managers.base import SessionEventSink, EventSink  # EventSink is legacy alias
from .managers.client_manager import ClientManager
from .managers.destination_manager import DestinationManager
from .managers.environment_manager import EnvironmentManager
from .managers.track_manager import TrackManager
from .managers.pattern_manager import PatternManager


class SessionContainer:
    """
    軽量なマネージャーコンテナ.

    各マネージャーを直接公開し、委譲レイヤーを持たない。
    APIからは container.clients.create() のように直接アクセスする。

    Example:
        >>> container = SessionContainer()
        >>> client = container.clients.create("c1", "Alice", "mars")
        >>> track = container.tracks.create("t1", "kick", "sd", "c1")
        >>> pattern = container.patterns.create("t1", "p1", "main", "c1")
    """

    def __init__(self, event_sink: Optional[SessionEventSink] = None) -> None:
        """
        SessionContainerの初期化.

        Args:
            event_sink: Optional session event sink for SSE events.
                Accepts SessionEventSink (new) or EventSink (legacy).
        """
        self.session = Session()
        self.id_gen = IDGenerator()
        self.event_sink = event_sink

        # 各マネージャーを直接公開（委譲なし）
        self.clients = ClientManager(self.session, event_sink)
        self.destinations = DestinationManager(self.session, event_sink)
        self.tracks = TrackManager(
            self.session,
            event_sink,
            destination_manager=self.destinations,
            client_manager=self.clients,
        )
        self.patterns = PatternManager(
            self.session,
            event_sink,
            track_manager=self.tracks,
            client_manager=self.clients,
        )
        self.environment = EnvironmentManager(self.session, event_sink)

    def reset(self) -> None:
        """セッションを空の状態にリセット（admin操作）."""
        self.session = Session()
        self.id_gen.reset()

        # 全マネージャーを新しいセッションで再初期化
        self.clients.session = self.session
        self.destinations.session = self.session
        self.tracks.session = self.session
        self.patterns.session = self.session
        self.environment.session = self.session

    def get_state(self) -> Session:
        """完全なセッション状態を取得."""
        return self.session
