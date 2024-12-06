from typing import Dict, Set, Optional, List
from dataclasses import dataclass, field
import logging
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from config.settings import APP_SETTINGS, ROLE_SETTINGS
from store.global_data_store import GlobalDataStore
from core.events import EventType, GameEvent, event_manager
from core.game_state import GamePhase, Team
from core.player import Player, PlayerRole


@dataclass
class GameAction:
    """ゲームアクション（投票や夜アクション）を表すデータクラス"""

    phase: GamePhase
    round: int
    actor: str
    target: str
    action_type: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class GameProgressState:
    """ゲーム進行の状態を管理するデータクラス"""

    current_phase: GamePhase = GamePhase.SETUP
    current_round: int = 0
    selected_actions: Dict[str, str] = field(default_factory=dict)
    action_history: List[GameAction] = field(default_factory=list)
    last_update: datetime = field(default_factory=datetime.now)


class GameProgressWindow:
    """ゲーム進行管理ウィンドウ"""

    def __init__(self, parent: tk.Tk, store: GlobalDataStore):
        self.logger = logging.getLogger(__name__)

        # 基本初期化
        self.parent = parent
        self.store = store
        self.window = tk.Toplevel(parent)
        self.window.title("ゲーム進行管理")
        self.window.geometry(
            f"{APP_SETTINGS['default_window_size']['game_progress'][0]}x"
            f"{APP_SETTINGS['default_window_size']['game_progress'][1]}"
        )

        # 状態管理
        self.state = GameProgressState(
            current_phase=store.game_state.current_phase,  # 追加
            current_round=store.game_state.current_round,  # 追加
        )

        # UI要素の参照
        self.phase_label: Optional[ttk.Label] = None
        self.round_label: Optional[ttk.Label] = None
        self.time_label: Optional[ttk.Label] = None
        self.action_combos: Dict[str, ttk.Combobox] = {}
        self.day_frame: Optional[ttk.LabelFrame] = None
        self.night_frame: Optional[ttk.LabelFrame] = None

        # UIの初期化
        self._init_ui()

        # フェーズ表示の更新を追加
        self._sync_with_game_state()  # 追加
        self._update_phase_display()  # 追加

        # イベントマネージャーへの登録
        event_manager.subscribe_all(self)
        self.logger.info("GameProgressWindow initialized")

    def _init_ui(self) -> None:
        """UIの初期化"""
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(expand=True, fill="both")

        # フェーズ情報表示部分
        self._create_phase_info(main_frame)

        # アクション選択部分（昼/夜で切り替え）
        self.day_frame = self._create_day_frame(main_frame)
        self.night_frame = self._create_night_frame(main_frame)

        # 現在のフェーズに応じて表示を切り替え
        self._update_phase_display()

    def _create_phase_info(self, parent: ttk.Frame) -> None:
        """フェーズ情報表示部分の作成"""
        info_frame = ttk.LabelFrame(parent, text="現在の状態", padding="5")
        info_frame.pack(fill="x", pady=5)

        # フェーズとラウンド表示
        phase_frame = ttk.Frame(info_frame)
        phase_frame.pack(fill="x", pady=2)

        self.phase_label = ttk.Label(
            phase_frame,
            text=f"現在のフェーズ: {self.state.current_phase.get_display_name()}",
        )
        self.phase_label.pack(side="left", padx=5)

        self.round_label = ttk.Label(
            phase_frame, text=f"ラウンド: {self.state.current_round}"
        )
        self.round_label.pack(side="right", padx=5)

        # 制限時間表示
        time_frame = ttk.Frame(info_frame)
        time_frame.pack(fill="x", pady=2)
        self.time_label = ttk.Label(
            time_frame, text=f"残り時間: {self._format_time(self._get_round_time())}"
        )
        self.time_label.pack(side="right", padx=5)

    def _create_day_frame(self, parent: ttk.Frame) -> ttk.LabelFrame:
        """昼フェーズのUI作成"""
        frame = ttk.LabelFrame(parent, text="昼フェーズ - 処刑投票", padding="5")

        # 処刑対象選択
        ttk.Label(frame, text="処刑対象:").pack(fill="x", pady=2)

        selection_frame = ttk.Frame(frame)
        selection_frame.pack(fill="x", pady=5)

        self.action_combos["execution"] = ttk.Combobox(
            selection_frame, state="readonly"
        )
        self.action_combos["execution"].pack(fill="x", pady=2)

        # 処刑確定ボタン
        ttk.Button(frame, text="処刑確定", command=self._confirm_execution).pack(
            fill="x", pady=10
        )

        return frame

    def _create_night_frame(self, parent: ttk.Frame) -> ttk.LabelFrame:
        """夜フェーズのUI作成"""
        frame = ttk.LabelFrame(
            parent, text="夜フェーズ - 各役職のアクション", padding="5"
        )

        # 人狼の襲撃対象選択
        ttk.Label(frame, text="人狼の襲撃対象:").pack(fill="x", pady=2)
        self.action_combos["attack"] = ttk.Combobox(frame, state="readonly")
        self.action_combos["attack"].pack(fill="x", pady=2)

        # 護衛対象選択
        ttk.Label(frame, text="ボディーガードの護衛対象:").pack(fill="x", pady=2)
        self.action_combos["guard"] = ttk.Combobox(frame, state="readonly")
        self.action_combos["guard"].pack(fill="x", pady=2)

        # 占い対象選択
        ttk.Label(frame, text="占い師の占い対象:").pack(fill="x", pady=2)
        self.action_combos["fortune"] = ttk.Combobox(frame, state="readonly")
        self.action_combos["fortune"].pack(fill="x", pady=2)

        # 夜アクション確定ボタン
        ttk.Button(
            frame, text="夜アクション確定", command=self._confirm_night_actions
        ).pack(fill="x", pady=10)

        return frame

    def _update_phase_display(self) -> None:
        """フェーズに応じた表示の切り替え"""
        is_day = self.state.current_phase in [
            GamePhase.DAY_DISCUSSION,
            GamePhase.DAY_VOTE,
        ]

        if is_day:
            self.night_frame.pack_forget()
            self.day_frame.pack(fill="both", expand=True, pady=5)
        else:
            self.day_frame.pack_forget()
            self.night_frame.pack(fill="both", expand=True, pady=5)

        self._update_player_lists()
        self._clear_selections()

    def _update_player_lists(self) -> None:
        """プレイヤーリストの更新"""
        try:
            if not hasattr(self, "window") or not self.window.winfo_exists():
                return

            # 生存プレイヤーのリストを取得
            alive_players = self.store.game_state.get_alive_players_list()
            choices = ["対象なし"] + alive_players

            # 各コンボボックスの更新
            for combo_name, combo in self.action_combos.items():
                if not hasattr(combo, "winfo_exists") or not combo.winfo_exists():
                    continue

                try:
                    current_value = combo.get()
                    combo["values"] = choices
                    # 既存の選択を保持（有効な場合のみ）
                    if current_value in choices:
                        combo.set(current_value)
                    else:
                        combo.set("対象なし")
                except tk.TclError:
                    continue

            self.logger.debug(
                f"Updated player lists with {len(alive_players)} alive players"
            )

        except Exception as e:
            self.logger.error(f"Error updating player lists: {str(e)}")

    def _clear_selections(self) -> None:
        """選択状態のクリア"""
        try:
            for combo in self.action_combos.values():
                combo.set("対象なし")
            self.state.selected_actions.clear()

        except Exception as e:
            self.logger.error(f"Error clearing selections: {str(e)}")

    def _get_round_time(self) -> int:
        """現在のラウンドの制限時間を取得"""
        try:
            regulation = self.store.game_state.regulation
            if not regulation or "round_times" not in regulation:
                return APP_SETTINGS["default_discussion_time"]

            round_times = regulation["round_times"]
            if not round_times:
                return APP_SETTINGS["default_discussion_time"]

            if self.state.current_round <= len(round_times):
                return round_times[self.state.current_round - 1]["time"]
            return round_times[-1]["time"]

        except Exception as e:
            self.logger.error(f"Error getting round time: {str(e)}")
            return APP_SETTINGS["default_discussion_time"]

    def _format_time(self, minutes: int) -> str:
        """時間を "MM:00" 形式にフォーマット"""
        return f"{minutes:02d}:00"

    def _confirm_execution(self) -> None:
        """処刑の確定処理"""
        try:
            target = self.action_combos["execution"].get()
            if not target:
                self._show_error("処刑対象を選択してください。")
                return

            if not messagebox.askyesno(
                "確認", f"{target}を処刑します。よろしいですか？"
            ):
                return

            self._record_action("execution", target)

            if target != "対象なし":
                player = self.store.game_state.get_player_by_name(target)
                if player:
                    self._execute_player(player)

            # ログの記録
            self._log_execution(target)

            # フェーズ変更
            self._change_to_night_phase()

            self.logger.info(f"Execution confirmed: {target}")

        except Exception as e:
            self.logger.error(f"Error in execution confirmation: {str(e)}")
            self._show_error("処刑処理中にエラーが発生しました。")
            self._handle_action_error()

    def _confirm_night_actions(self) -> None:
        """夜アクションの確定処理"""
        try:
            actions = {
                key: combo.get()
                for key, combo in self.action_combos.items()
                if key in ["attack", "guard", "fortune"]
            }

            if not self._validate_night_actions(actions):
                return

            if not messagebox.askyesno(
                "確認", "夜のアクションを確定します。よろしいですか？"
            ):
                return

            # 各アクションの記録
            for action_type, target in actions.items():
                self._record_action(action_type, target)

            # 襲撃と護衛の処理
            self._process_night_actions(actions)

            # ログの記録
            self._log_night_actions(actions)

            # 次のラウンドへ
            self._proceed_to_next_round()

            self.logger.info("Night actions confirmed")

        except Exception as e:
            self.logger.error(f"Error in night actions confirmation: {str(e)}")
            self._show_error("夜アクション処理中にエラーが発生しました。")
            self._handle_action_error()

    def _validate_night_actions(self, actions: Dict[str, str]) -> bool:
        """夜アクションのバリデーション"""
        if not all(actions.values()):
            self._show_error("全ての役職のアクションを選択してください。")
            return False
        return True

    def _record_action(self, action_type: str, target: str) -> None:
        """アクションの記録"""
        action = GameAction(
            phase=self.state.current_phase,
            round=self.state.current_round,
            action_type=action_type,
            actor="system",
            target=target,
        )
        self.state.action_history.append(action)
        self.state.selected_actions[action_type] = target

    def _execute_player(self, player: Player) -> None:
        """プレイヤーの処刑実行"""
        if not player.is_alive:  # 追加：既に死亡している場合はスキップ
            return

        event_manager.notify(
            GameEvent(
                type=EventType.PLAYER_DIED,
                data={
                    "player_name": player.name,
                    "role": player.role.value if player.role else None,
                    "phase": self.state.current_phase.value,
                    "round": self.state.current_round,
                    "cause": "execution",
                },
                source="game_progress",
            )
        )

    def _process_night_actions(self, actions: Dict[str, str]) -> None:
        """夜アクションの処理"""
        try:
            attack_target = actions["attack"]
            guard_target = actions["guard"]

            # 襲撃対象が「対象なし」の場合は何もしない
            if attack_target == "対象なし":
                return

            # 襲撃対象が守護されている場合は死亡しない
            if attack_target == guard_target and guard_target != "対象なし":
                return

            # 守護されていない場合は襲撃対象を死亡させる
            target_player = self.store.game_state.get_player_by_name(attack_target)
            if target_player:
                event_manager.notify(
                    GameEvent(
                        type=EventType.PLAYER_DIED,
                        data={
                            "player_name": target_player.name,
                            "role": (
                                target_player.role.value if target_player.role else None
                            ),
                            "phase": self.state.current_phase.value,
                            "round": self.state.current_round,
                            "cause": "werewolf_attack",
                        },
                        source="game_progress",
                    )
                )

        except Exception as e:
            self.logger.error(f"Error processing night actions: {str(e)}")
            raise

    def _log_execution(self, target: str) -> None:
        """処刑のログ記録"""
        self.store.add_game_log(
            {
                "phase": self.state.current_phase.value,
                "round": self.state.current_round,
                "action": "execution",
                "target": target,
                "role": (
                    self.store.game_state.get_player_by_name(target).role.value
                    if target != "対象なし"
                    and self.store.game_state.get_player_by_name(target)
                    else ""
                ),
            }
        )

        # 夜フェーズのログを事前に追加
        self.store.add_game_log(
            {
                "phase": GamePhase.NIGHT.value,
                "round": self.state.current_round,
                "action": "phase_start",
            }
        )

    def _log_night_actions(self, actions: Dict[str, str]) -> None:
        """夜アクションのログ記録"""
        try:
            # 占い結果の取得
            fortune_result = ""
            if actions["fortune"] != "対象なし":
                target_player = self.store.game_state.get_player_by_name(
                    actions["fortune"]
                )
                if target_player and target_player.role:
                    fortune_result = target_player.role.value

            # 襲撃結果の判定
            attack_success = actions["attack"] != "対象なし" and (
                actions["guard"] == "対象なし" or actions["attack"] != actions["guard"]
            )

            # アクションログの記録
            self.store.add_game_log(
                {
                    "phase": self.state.current_phase.value,
                    "round": self.state.current_round,
                    "action": "night_actions",
                    "attack_target": actions["attack"],
                    "guard_target": actions["guard"],
                    "fortune_target": actions["fortune"],
                    "fortune_result": fortune_result,
                    "attack_success": attack_success,
                }
            )

            # 次のラウンドの昼フェーズログを事前に追加
            next_round = self.state.current_round + 1
            message_type = "kill" if attack_success else "no_kill"
            self.store.add_game_log(
                {
                    "phase": GamePhase.DAY_DISCUSSION.value,
                    "round": next_round,
                    "action": "phase_start",
                    "message_type": message_type,
                    "victim": actions["attack"] if attack_success else None,
                }
            )

        except Exception as e:
            self.logger.error(f"Error logging night actions: {str(e)}")
            raise

    def _change_to_night_phase(self) -> None:
        """夜フェーズへの移行"""
        self.store.game_state.change_phase(GamePhase.NIGHT)
        self.state.current_phase = GamePhase.NIGHT
        self._update_phase_display()

    def _proceed_to_next_round(self) -> None:
        """次のラウンドへの移行"""
        try:
            if not hasattr(self, "window") or not self.window.winfo_exists():
                return

            # GameStateの更新を先に行う
            self.store.game_state.next_round()

            # 内部状態の更新は後で
            self.state.current_round = self.store.game_state.current_round
            self.state.current_phase = self.store.game_state.current_phase

            # UI更新前の存在確認
            if all(
                hasattr(self, frame) and getattr(self, frame).winfo_exists()
                for frame in ["day_frame", "night_frame"]
            ):
                self._update_phase_display()

            self.logger.info(f"Proceeded to next round: {self.state.current_round}")
        except tk.TclError:
            # ウィンドウが既に破棄されている場合
            return
        except Exception as e:
            self.logger.error(f"Error proceeding to next round: {str(e)}")

    def handle_event(self, event: GameEvent) -> None:
        """イベントハンドラ"""
        try:
            handlers = {
                EventType.PHASE_CHANGED: self._handle_phase_change,
                EventType.PLAYER_DIED: self._handle_player_death,
                EventType.ROUND_CHANGED: self._handle_round_change,
                EventType.GAME_STATE_UPDATED: self._handle_game_state_update,
                EventType.ERROR: self._handle_error,
            }

            handler = handlers.get(event.type)
            if handler:
                handler(event)
                self.state.last_update = datetime.now()

        except Exception as e:
            self.logger.error(f"Error handling event {event.type}: {str(e)}")
            self._show_error("イベント処理中にエラーが発生しました。")

    def _handle_phase_change(self, event: GameEvent) -> None:
        """フェーズ変更イベントの処理"""
        try:
            if not hasattr(self, "window") or not self.window.winfo_exists():
                return

            self.state.current_phase = GamePhase(event.data.get("new_phase"))

            # UI更新前にウィンドウとフレームの存在確認
            if (
                hasattr(self, "day_frame")
                and hasattr(self, "night_frame")
                and self.day_frame.winfo_exists()
                and self.night_frame.winfo_exists()
            ):
                self._update_phase_display()

            self.logger.info(f"Phase changed to: {self.state.current_phase.value}")
        except tk.TclError:
            # ウィンドウが既に破棄されている場合
            return
        except Exception as e:
            self.logger.error(f"Error handling phase change: {str(e)}")

    def _handle_player_death(self, event: GameEvent) -> None:
        """プレイヤー死亡イベントの処理"""
        self._update_player_lists()
        self.logger.info(
            f"Updated lists after player death: {event.data.get('player_name')}"
        )

    def _handle_round_change(self, event: GameEvent) -> None:
        """ラウンド変更イベントの処理"""
        try:
            if not hasattr(self, "window") or not self.window.winfo_exists():
                return

            self.state.current_round = event.data.get("round", 0)

            # time_labelの存在確認を追加
            if hasattr(self, "time_label") and self.time_label.winfo_exists():
                time_limit = self._get_round_time()
                self.time_label.config(
                    text=f"残り時間: {self._format_time(time_limit)}"
                )

            self.logger.info(f"Round changed to: {self.state.current_round}")
        except tk.TclError:
            # ウィンドウが既に破棄されている場合
            return
        except Exception as e:
            self.logger.error(f"Error handling round change: {str(e)}")

    def _handle_game_state_update(self, event: GameEvent) -> None:
        """ゲーム状態更新イベントの処理"""
        self._sync_with_game_state()
        self._update_phase_display()
        self.logger.info("Game state sync completed")

    def _handle_error(self, event: GameEvent) -> None:
        """エラーイベントの処理"""
        error_msg = event.data.get("message", "不明なエラー")
        self.logger.error(f"Error event received: {error_msg}")
        self._show_error(error_msg)

    def _sync_with_game_state(self) -> None:
        """ゲーム状態との同期"""
        try:
            game_state = self.store.game_state
            self.state.current_phase = game_state.current_phase
            self.state.current_round = game_state.current_round
            self._update_player_lists()
        except Exception as e:
            self.logger.error(f"Error syncing with game state: {str(e)}")
            raise

    def _handle_action_error(self) -> None:
        """アクションエラーの処理"""
        self._clear_selections()
        self._sync_with_game_state()
        self._update_phase_display()

    def _show_error(self, message: str) -> None:
        """エラーメッセージの表示"""
        self.logger.error(message)
        messagebox.showerror("エラー", message)

    def destroy(self) -> None:
        """ウィンドウの破棄"""
        try:
            if hasattr(self, "window"):
                self.window.destroy()
                event_manager.unsubscribe_all(self)
                self.logger.info("Game progress window destroyed")
        except Exception as e:
            self.logger.error(f"Error destroying window: {str(e)}")
