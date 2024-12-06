from typing import Dict, Any, Optional, Set, List, Callable
import json
import logging
from pathlib import Path
from config.settings import DATA_DIR
from core.game_state import GameState, GamePhase
from core.player import Player, PlayerRole
from core.events import event_manager, GameEvent, EventType
from datetime import datetime


class GlobalDataStore:
    """グローバルデータストア - シングルトンパターンで実装"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GlobalDataStore, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """データストアの初期化"""
        self.logger = logging.getLogger(__name__)

        # ゲーム状態の管理
        self.game_state = GameState()

        # セッション管理
        self.session_data = {
            "all_players": {},  # 全登録プレイヤー
            "session_players": set(),  # 現在のセッション参加者
        }

        # ゲームログ
        self.game_log = []

        # オブザーバー管理
        self._observers: List[Callable[[str], None]] = []

        # イベントマネージャーへの登録
        event_manager.subscribe_all(self)
        self.logger.info("GlobalDataStore initialized")

    def handle_event(self, event: GameEvent) -> None:
        """イベントの処理"""
        try:
            self.logger.info(f"Handling event: {event.type.value}")
            self.logger.debug(f"Event data: {event.data}")

            handlers = {
                EventType.REGULATION_CONFIRMED: self._handle_regulation_confirmed,
                EventType.PLAYERS_CONFIRMED: self._handle_players_confirmed,
                EventType.PLAYER_DIED: self._handle_player_death,
                EventType.PHASE_CHANGED: self._handle_phase_change,
                EventType.ROUND_CHANGED: self._handle_round_change,
                EventType.GAME_STARTED: self._handle_game_start,
                EventType.GAME_ENDED: self._handle_game_end,
                EventType.GAME_STATE_RESET: self._handle_game_reset,
                EventType.ERROR: self._handle_error,
            }

            handler = handlers.get(event.type)
            if handler:
                handler(event)
            else:
                self.logger.debug(
                    f"No specific handler for event type: {event.type.value}"
                )

        except Exception as e:
            self.logger.error(f"Error handling event {event.type.value}: {str(e)}")
            self._notify_error(str(e), event)

    def _notify_error(self, error_message: str, original_event: GameEvent) -> None:
        """エラーイベントの通知"""
        error_event = GameEvent(
            type=EventType.ERROR,
            data={"message": error_message, "original_event": original_event.to_dict()},
            source="global_data_store",
        )
        event_manager.notify(error_event)

    def get_state(self, key: str) -> Any:
        """状態の取得"""
        try:
            state_getters = {
                "players": lambda: [
                    player.to_dict() for player in self.game_state.players.values()
                ],
                "players_status": lambda: self.game_state.is_players_confirmed,
                "regulation_status": lambda: self.game_state.is_regulation_confirmed,
                "alive_players": lambda: self.game_state.alive_players,
                "current_phase": lambda: self.game_state.current_phase.value,
                "current_round": lambda: self.game_state.current_round,
                "regulation": lambda: self.game_state.regulation,
                "role_distribution": lambda: {
                    name: player.role.value
                    for name, player in self.game_state.players.items()
                    if player.role
                },
                "game_log": lambda: self.game_log,
                "session_players": lambda: list(self.session_data["session_players"]),
            }

            getter = state_getters.get(key)
            if getter:
                return getter()

            self.logger.warning(f"Unknown state key requested: {key}")
            return None

        except Exception as e:
            self.logger.error(f"Error getting state {key}: {str(e)}")
            return None

    def set_state(self, key: str, value: Any) -> None:
        """状態の設定"""
        try:
            state_setters = {
                "regulation": self._set_regulation,
                "players": self._set_players,
                "regulation_status": self._set_regulation_status,
                "players_status": self._set_players_status,
            }

            setter = state_setters.get(key)
            if setter:
                setter(value)
                self._notify_observers(key)
            else:
                self.logger.warning(f"Unknown state key for setting: {key}")

        except Exception as e:
            self.logger.error(f"Error setting state {key}: {str(e)}")
            raise

    def _set_regulation(self, regulation: Dict) -> None:
        """レギュレーションの設定"""
        if self._validate_regulation(regulation):
            self.game_state.set_regulation(regulation)
            event_manager.notify(
                GameEvent(
                    type=EventType.REGULATION_UPDATED,
                    data={"regulation": regulation},
                    source="global_data_store",
                )
            )

    def _set_players(self, players: List[Player]) -> None:
        """プレイヤー情報の設定"""
        self.game_state.players.clear()
        self.game_state.alive_players.clear()

        for player in players:
            self.game_state.add_player(player)
            self.register_session_player(player)

        event_manager.notify(
            GameEvent(
                type=EventType.PLAYERS_UPDATED,
                data={"players": [p.name for p in players]},
                source="global_data_store",
            )
        )

    def add_game_log(self, log_entry: Dict) -> None:
        """ゲームログの追加"""
        try:
            log_entry["timestamp"] = datetime.now().isoformat()
            self.game_log.append(log_entry)

            event_manager.notify(
                GameEvent(
                    type=EventType.GAME_LOG_UPDATED,
                    data={"log_entry": log_entry},
                    source="global_data_store",
                )
            )

        except Exception as e:
            self.logger.error(f"Error adding game log: {str(e)}")

    def register_observer(self, observer: Callable[[str], None]) -> None:
        """オブザーバーの登録"""
        if observer not in self._observers:
            self._observers.append(observer)
            self.logger.info(f"Observer registered: {observer.__class__.__name__}")

    def unregister_observer(self, observer: Callable[[str], None]) -> None:
        """オブザーバーの登録解除"""
        if observer in self._observers:
            self._observers.remove(observer)
            self.logger.info(f"Observer unregistered: {observer.__class__.__name__}")

    def _notify_observers(self, key: str) -> None:
        """オブザーバーに更新を通知"""
        self.logger.info(f"Notifying observers for key: {key}")
        for observer in self._observers:
            try:
                observer(key)
            except Exception as e:
                self.logger.error(f"Error notifying observer: {str(e)}")

    def save_regulation(self, name: str, regulation_data: Dict) -> bool:
        """レギュレーション設定の保存"""
        try:
            if not self._validate_regulation(regulation_data):
                return False

            file_path = DATA_DIR / "sample_regulations.json"
            regulations = {}

            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    regulations = json.load(f)

            regulations[name] = regulation_data

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(regulations, f, ensure_ascii=False, indent=2)

            event_manager.notify(
                GameEvent(
                    type=EventType.REGULATION_SAVED,
                    data={"name": name},
                    source="global_data_store",
                )
            )

            return True

        except Exception as e:
            self.logger.error(f"Error saving regulation: {str(e)}")
            return False

    def load_regulations(self) -> Dict:
        """保存済みレギュレーションの読み込み"""
        try:
            file_path = DATA_DIR / "sample_regulations.json"
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.logger.error(f"Error loading regulations: {str(e)}")
            return {}

    def _validate_regulation(self, regulation: Dict) -> bool:
        """レギュレーションデータの検証"""
        try:
            if not isinstance(regulation, dict):
                return False

            required_keys = {"roles", "round_times"}
            if not all(key in regulation for key in required_keys):
                return False

            for role in regulation["roles"]:
                try:
                    PlayerRole(role)
                except ValueError:
                    return False

            for round_time in regulation["round_times"]:
                if not isinstance(round_time.get("time"), int):
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Error validating regulation: {str(e)}")
            return False

    # Event handlers
    def _handle_regulation_confirmed(self, event: GameEvent) -> None:
        """レギュレーション確定イベントの処理"""
        self.game_state.is_regulation_confirmed = True
        self._notify_observers("regulation_status")

    def _handle_players_confirmed(self, event: GameEvent) -> None:
        """プレイヤー確定イベントの処理"""
        self.game_state.is_players_confirmed = True
        self._notify_observers("players_status")

    def _handle_player_death(self, event: GameEvent) -> None:
        """プレイヤー死亡イベントの処理"""
        player_name = event.data.get("player_name")
        if player_name in self.game_state.alive_players:
            self.game_state.kill_player(player_name)
            self._notify_observers("alive_players")
            self._notify_observers("game_state")

    def _handle_phase_change(self, event: GameEvent) -> None:
        """フェーズ変更イベントの処理"""
        self._notify_observers("current_phase")

    def _handle_round_change(self, event: GameEvent) -> None:
        """ラウンド変更イベントの処理"""
        new_round = event.data.get("round")
        if new_round:
            self.game_state.current_round = new_round
            self._notify_observers("current_round")

    def _handle_game_start(self, event: GameEvent) -> None:
        """ゲーム開始イベントの処理"""
        self.game_state.game_active = True
        self._notify_observers("game_state")

    def _handle_game_end(self, event: GameEvent) -> None:
        """ゲーム終了イベントの処理"""
        self.game_state.game_active = False
        self._notify_observers("game_state")

    def _handle_game_reset(self, event: GameEvent) -> None:
        """ゲームリセットイベントの処理"""
        try:
            # ゲーム状態をリセット
            self.game_state.reset()

            # ゲームログをクリア
            self.game_log.clear()

            # オブザーバーに通知
            self._notify_observers("game_state")
            self._notify_observers("game_log")

            self.logger.info("Game state reset completed")

        except Exception as e:
            self.logger.error(f"Error handling game reset: {str(e)}")
            raise

    def _handle_error(self, event: GameEvent) -> None:
        """エラーイベントの処理"""
        self.logger.error(
            f"Error event received: {event.data.get('message', 'Unknown error')}"
        )

    def _set_regulation_status(self, status: bool) -> None:
        """レギュレーション確定状態の設定"""
        self.game_state.is_regulation_confirmed = status
        event_manager.notify(
            GameEvent(
                type=EventType.REGULATION_STATUS_UPDATED,
                data={"status": status},
                source="global_data_store",
            )
        )

    def _set_players_status(self, status: bool) -> None:
        """プレイヤー確定状態の設定"""
        self.game_state.is_players_confirmed = status
        # PLAYERS_STATUS_UPDATEDイベントを使用
        event_manager.notify(
            GameEvent(
                type=EventType.PLAYERS_STATUS_UPDATED,
                data={"status": status},
                source="global_data_store",
            )
        )

    def register_session_player(self, player: Player) -> None:
        """セッションプレイヤーの登録"""
        try:
            self.session_data["all_players"][player.name] = player
            self.session_data["session_players"].add(player.name)

            # SESSION_PLAYER_REGISTEREDの代わりにPLAYER_ADDEDを使用
            event_manager.notify(
                GameEvent(
                    type=EventType.PLAYER_ADDED,
                    data={"player_name": player.name, "player_number": player.number},
                    source="global_data_store",
                )
            )
            self.logger.info(f"Registered session player: {player.name}")

        except Exception as e:
            self.logger.error(f"Error registering session player: {str(e)}")
            raise
