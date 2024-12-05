from enum import Enum
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
import logging
import json


class EventType(Enum):
    """イベントタイプの列挙型定義"""

    # プレイヤー関連
    PLAYER_ADDED = "player_added"
    PLAYER_REMOVED = "player_removed"
    PLAYER_ROLE_ASSIGNED = "player_role_assigned"
    PLAYER_DIED = "player_died"
    PLAYER_STATUS_UPDATED = "player_status_updated"
    PLAYERS_CONFIRMED = "players_confirmed"
    PLAYERS_UPDATED = "players_updated"
    PLAYERS_MOVED = "players_moved"
    PLAYER_UPDATED = "player_updated"

    # ゲーム進行関連
    GAME_STARTED = "game_started"
    GAME_ENDED = "game_ended"
    GAME_STATE_RESET = "game_state_reset"
    PHASE_CHANGED = "phase_changed"
    ROUND_CHANGED = "round_changed"

    # 設定関連
    REGULATION_CONFIRMED = "regulation_confirmed"
    REGULATION_UPDATED = "regulation_updated"
    REGULATION_SAVED = "regulation_saved"

    # アクション関連
    VOTE_RECORDED = "vote_recorded"
    VOTE_COMPLETED = "vote_completed"
    NIGHT_ACTION_RECORDED = "night_action_recorded"
    NIGHT_ACTION_COMPLETED = "night_action_completed"
    VOTING_COMPLETED = "voting_completed"

    # アプリケーション管理
    GM_MODE_STARTED = "gm_mode_started"
    GM_MODE_ENDED = "gm_mode_ended"
    APPLICATION_CLOSING = "application_closing"
    GAME_STATE_UPDATED = "game_state_updated"
    GAME_LOG_UPDATED = "game_log_updated"

    # ステータス関連のイベントを追加
    REGULATION_STATUS_UPDATED = "regulation_status_updated"
    PLAYERS_STATUS_UPDATED = "players_status_updated"

    # エラー関連
    ERROR = "error"


@dataclass
class GameEvent:
    """ゲームイベントを表すデータクラス"""

    type: EventType
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = field(default="system")
    event_id: str = field(
        default_factory=lambda: f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    )

    def __post_init__(self):
        """イベントの検証を行う"""
        if not isinstance(self.type, EventType):
            try:
                self.type = EventType(self.type)
            except ValueError as e:
                raise ValueError(f"Invalid event type: {self.type}") from e

    def to_dict(self) -> Dict[str, Any]:
        """イベントを辞書形式に変換"""
        return {
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "event_id": self.event_id,
        }

    def __str__(self) -> str:
        return f"GameEvent(type={self.type.value}, source={self.source}, timestamp={self.timestamp.isoformat()})"


class EventManager:
    """イベントの管理と配信を行うクラス"""

    def __init__(self):
        self._observers: Dict[EventType, List[Callable[[GameEvent], None]]] = {
            event_type: [] for event_type in EventType
        }
        self._event_history: List[GameEvent] = []
        self._max_history_size: int = 1000
        self.logger = logging.getLogger(__name__)

    def subscribe(
        self, event_type: EventType, callback: Callable[[GameEvent], None]
    ) -> None:
        """特定のイベントタイプに対するコールバックを登録"""
        if not callable(callback):
            raise ValueError("Callback must be callable")

        self._observers[event_type].append(callback)
        self.logger.debug(f"Subscribed to {event_type.value}: {callback.__name__}")

    def subscribe_all(self, observer: object) -> None:
        """すべてのイベントタイプに対してオブザーバーを登録"""
        if hasattr(observer, "handle_event"):
            for event_type in EventType:
                self.subscribe(event_type, observer.handle_event)
            self.logger.info(
                f"Observer {observer.__class__.__name__} subscribed to all events"
            )
        else:
            raise ValueError("Observer must have handle_event method")

    def unsubscribe(
        self, event_type: EventType, callback: Callable[[GameEvent], None]
    ) -> None:
        """イベントタイプに対するコールバックの登録を解除"""
        if callback in self._observers[event_type]:
            self._observers[event_type].remove(callback)
            self.logger.debug(
                f"Unsubscribed from {event_type.value}: {callback.__name__}"
            )

    def unsubscribe_all(self, observer: object) -> None:
        """すべてのイベントタイプからオブザーバーの登録を解除"""
        if hasattr(observer, "handle_event"):
            for event_type in EventType:
                self.unsubscribe(event_type, observer.handle_event)
            self.logger.info(
                f"Observer {observer.__class__.__name__} unsubscribed from all events"
            )

    def notify(self, event: GameEvent) -> None:
        """イベントを発行し、登録されたコールバックを実行"""
        try:
            self._add_to_history(event)
            self.logger.info(f"Event notified: {event}")

            # DEBUGレベルで詳細なイベントデータをログ出力
            self.logger.debug(
                f"Event details: {json.dumps(event.to_dict(), ensure_ascii=False)}"
            )

            for callback in self._observers[event.type]:
                try:
                    callback(event)
                except Exception as e:
                    error_event = self._create_error_event(e, event, callback.__name__)
                    self.logger.error(
                        f"Error in callback {callback.__name__}: {str(e)}"
                    )
                    self._handle_error_event(error_event)

        except Exception as e:
            self.logger.error(f"Critical error in event notification: {str(e)}")
            raise

    def _create_error_event(
        self, error: Exception, original_event: GameEvent, callback_name: str
    ) -> GameEvent:
        """エラーイベントの作成"""
        return GameEvent(
            type=EventType.ERROR,
            data={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "original_event_type": original_event.type.value,
                "callback_name": callback_name,
                "original_event_data": original_event.data,
            },
            source="event_manager",
        )

    def _handle_error_event(self, error_event: GameEvent) -> None:
        """エラーイベントの処理"""
        try:
            for callback in self._observers[EventType.ERROR]:
                try:
                    callback(error_event)
                except Exception as e:
                    self.logger.critical(f"Error in error handling callback: {str(e)}")
        except Exception as e:
            self.logger.critical(f"Critical error in error event handling: {str(e)}")

    def _add_to_history(self, event: GameEvent) -> None:
        """イベント履歴への追加"""
        self._event_history.append(event)
        if len(self._event_history) > self._max_history_size:
            self._event_history.pop(0)

    def get_recent_events(
        self, count: Optional[int] = None, event_type: Optional[EventType] = None
    ) -> List[GameEvent]:
        """最近のイベントを取得"""
        events = self._event_history
        if event_type:
            events = [e for e in events if e.type == event_type]
        if count:
            events = events[-count:]
        return events

    def clear_history(self) -> None:
        """イベント履歴のクリア"""
        self._event_history.clear()
        self.logger.info("Event history cleared")

    def get_event_counts(self) -> Dict[EventType, int]:
        """イベントタイプごとの発生回数を取得"""
        counts = {event_type: 0 for event_type in EventType}
        for event in self._event_history:
            counts[event.type] += 1
        return counts


# グローバルなイベントマネージャーのインスタンス
event_manager = EventManager()
