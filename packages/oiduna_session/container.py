"""SessionContainer - 軽量なマネージャーコンテナ."""

from typing import Optional
from oiduna_models import Session
from .managers.base import SessionEventSink
from .managers.client_manager import ClientManager
from .managers.destination_manager import DestinationManager
from .managers.environment_manager import EnvironmentManager
from .managers.track_manager import TrackManager
from .managers.pattern_manager import PatternManager
from .managers.timeline_manager import TimelineManager


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
        self.event_sink = event_sink

        # 各マネージャーを直接公開（委譲なし）
        # Session単位のIDGeneratorを使用
        self.clients = ClientManager(self.session, event_sink)
        self.destinations = DestinationManager(self.session, event_sink)
        self.tracks = TrackManager(
            self.session,
            event_sink,
            id_generator=self.session._id_generator,
            destination_manager=self.destinations,
            client_manager=self.clients,
        )
        self.patterns = PatternManager(
            self.session,
            event_sink,
            id_generator=self.session._id_generator,
            track_manager=self.tracks,
            client_manager=self.clients,
        )
        self.environment = EnvironmentManager(self.session, event_sink)
        self.timeline = TimelineManager(self.session, event_sink)

    def reset(self) -> None:
        """セッションを空の状態にリセット（admin操作）."""
        self.session = Session()
        # Session作成時に新しい _id_generator が自動作成される

        # 全マネージャーを新しいセッションで再初期化
        self.clients.session = self.session
        self.destinations.session = self.session
        self.tracks.session = self.session
        self.tracks.id_generator = self.session._id_generator
        self.patterns.session = self.session
        self.patterns.id_generator = self.session._id_generator
        self.environment.session = self.session
        self.timeline = TimelineManager(self.session, self.event_sink)

    def get_state(self) -> Session:
        """完全なセッション状態を取得."""
        return self.session
