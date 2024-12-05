from typing import Dict, Optional, Set
import random
import logging
from dataclasses import dataclass, field
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox

from config.settings import APP_SETTINGS, ROLE_SETTINGS
from store.global_data_store import GlobalDataStore
from ui.regulation_setting import RegulationSettingWindow
from ui.participant_list import ParticipantListWindow
from ui.game_progress import GameProgressWindow

from core.player import Player, PlayerRole
from core.events import EventType, GameEvent, event_manager
from core.game_state import GamePhase, Team


@dataclass
class GMWindowState:
    """GMウィンドウの状態を管理するデータクラス"""

    regulation_confirmed: bool = False
    participants_confirmed: bool = False
    game_active: bool = False
    last_update: datetime = field(default_factory=datetime.now)


class GMMainWindow:
    """GMモードのメインウィンドウ"""

    def __init__(self, root: tk.Tk, store: GlobalDataStore):
        self.logger = logging.getLogger(__name__)

        # 基本初期化
        self.root = root
        self.store = store
        self.window = tk.Toplevel(root)
        self.window.title(f"{APP_SETTINGS['app_name']} - GMモード")
        self.window.geometry(
            f"{APP_SETTINGS['default_window_size']['gm_main'][0]}x{APP_SETTINGS['default_window_size']['gm_main'][1]}"
        )

        # GMセリフテンプレート
        self._init_speech_templates()

        # ウィンドウの参照を保持
        self.sub_windows: Dict[str, Optional[tk.Toplevel]] = {
            "regulation": None,
            "participant": None,
            "game_progress": None,
        }

        # 状態管理
        self.state = GMWindowState()

        # UIの初期化
        self._init_ui()

        # イベントマネージャーへの登録
        event_manager.subscribe_all(self)

        self.logger.info("GMMainWindow initialized")

    def _init_speech_templates(self):
        """GMセリフテンプレートの初期化"""
        self.speech_templates = {
            "game_start": "ゲームを開始します。全員、目を閉じてください。",
            "morning": {
                "kill": "朝になりました。昨晩、{}が無残な姿で発見されました。",
                "no_kill": "朝になりました。昨晩は誰も犠牲になりませんでした。",
            },
            "execution": "投票の結果、{}が処刑されることになりました。",
            "night": "夜になりました。全員、目を閉じてください。",
        }

    def handle_event(self, event: GameEvent) -> None:
        """イベントハンドラ"""
        try:
            self.logger.info(f"Handling event: {event.type.value}")

            # ウィンドウが既に破棄されている場合は処理をスキップ
            if not hasattr(self, "window") or not self.window.winfo_exists():
                return

            handlers = {
                EventType.REGULATION_CONFIRMED: self._handle_regulation_confirmed,
                EventType.PLAYERS_CONFIRMED: self._handle_players_confirmed,
                EventType.GAME_STARTED: self._handle_game_started,
                EventType.GAME_ENDED: self._handle_game_ended,
                EventType.PLAYER_DIED: self._handle_player_death,
                EventType.PHASE_CHANGED: self._handle_phase_change,
                EventType.ERROR: self._handle_error,
                EventType.GAME_LOG_UPDATED: self._handle_log_update,
            }

            handler = handlers.get(event.type)
            if handler:
                handler(event)

            # ウィンドウが存在する場合のみUI更新
            if self.window.winfo_exists():
                self._update_ui_state()

        except Exception as e:
            self.logger.error(f"Error handling event {event.type.value}: {str(e)}")

    def _handle_error(self, event: GameEvent) -> None:
        """エラーイベントの処理"""
        error_msg = event.data.get("message", "不明なエラー")
        self.logger.error(f"Error event received: {error_msg}")
        self._show_error(error_msg)

    def _show_error(self, message: str) -> None:
        """エラーメッセージの表示"""
        try:
            messagebox.showerror("エラー", message)
        except Exception as e:
            self.logger.error(f"Error showing error message: {str(e)}")

    def _update_ui_state(self) -> None:
        """UI状態の更新"""
        try:
            # ウィンドウが破棄されている場合は処理をスキップ
            if not hasattr(self, "window") or not self.window.winfo_exists():
                return

            # 基本情報の更新
            game_state = self.store.game_state

            # フェーズとラウンドの更新
            if hasattr(self, "phase_label") and self.phase_label.winfo_exists():
                self.phase_label.config(
                    text=f"フェーズ: {game_state.current_phase.get_display_name()}"
                )
            if hasattr(self, "round_label") and self.round_label.winfo_exists():
                self.round_label.config(
                    text=f"ラウンド: {game_state.current_round or '-'}"
                )

            # チーム情報の更新
            team_counts = game_state.get_team_counts()
            if hasattr(self, "village_count") and self.village_count.winfo_exists():
                self.village_count.config(
                    text=f"村人チーム 残り人数: {team_counts[Team.VILLAGE.value]}"
                )
            if hasattr(self, "wolf_count") and self.wolf_count.winfo_exists():
                self.wolf_count.config(
                    text=f"人狼チーム 残り人数: {team_counts[Team.WEREWOLF.value]}"
                )

            # スタートボタンの状態更新
            if hasattr(self, "start_button") and self.start_button.winfo_exists():
                self._update_start_button()

            self.state.last_update = datetime.now()

        except Exception as e:
            self.logger.error(f"Error updating UI state: {str(e)}")

    def _init_ui(self) -> None:
        """UIの初期化"""
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(expand=True, fill="both")

        # UIコンポーネントの作成
        self._create_gm_speech_area(main_frame)
        self._create_game_info_area(main_frame)
        self._create_button_area(main_frame)
        self._create_status_area(main_frame)
        self._create_debug_area(main_frame)

    def _create_gm_speech_area(self, parent: ttk.Frame) -> None:
        """GMセリフ表示エリアの作成"""
        speech_frame = ttk.LabelFrame(parent, text="GMセリフ表示", padding="5")
        speech_frame.pack(fill="x", pady=5)

        self.speech_text = tk.Text(speech_frame, height=4, wrap="word")
        self.speech_text.pack(fill="x")
        self.speech_text.insert(
            "1.0", "ゲーム開始前です。準備が整ったらゲームを開始してください。"
        )
        self.speech_text.config(state="disabled")

    def _create_game_info_area(self, parent: ttk.Frame) -> None:
        """ゲーム情報表示エリアの作成"""
        info_frame = ttk.LabelFrame(parent, text="ゲーム情報", padding="5")
        info_frame.pack(fill="x", pady=5)

        # チーム情報
        team_frame = ttk.Frame(info_frame)
        team_frame.pack(fill="x")

        self.village_count = ttk.Label(team_frame, text="村人チーム 残り人数: -")
        self.village_count.pack(side="left", padx=5)

        self.wolf_count = ttk.Label(team_frame, text="人狼チーム 残り人数: -")
        self.wolf_count.pack(side="right", padx=5)

        # フェーズ情報
        phase_frame = ttk.Frame(info_frame)
        phase_frame.pack(fill="x")

        self.phase_label = ttk.Label(phase_frame, text="フェーズ: 準備中")
        self.phase_label.pack(side="left", padx=5)

        self.round_label = ttk.Label(phase_frame, text="ラウンド: -")
        self.round_label.pack(side="right", padx=5)

    def _create_button_area(self, parent: ttk.Frame) -> None:
        """ボタンエリアの作成"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(pady=10)

        # サブウィンドウを開くボタン群
        self.window_buttons = {
            "participant": ttk.Button(
                button_frame,
                text="参加者一覧ウィンドウを開く",
                command=lambda: self._open_sub_window("participant"),
            ),
            "regulation": ttk.Button(
                button_frame,
                text="レギュレーション設定ウィンドウを開く",
                command=lambda: self._open_sub_window("regulation"),
            ),
            "game_progress": ttk.Button(
                button_frame,
                text="ゲーム進行ウィンドウを開く",
                command=lambda: self._open_sub_window("game_progress"),
            ),
        }

        for button in self.window_buttons.values():
            button.pack(fill="x", pady=2)

        # ゲーム制御ボタン
        self.start_button = ttk.Button(
            button_frame,
            text="ゲームスタート",
            command=self._start_game,
            state="disabled",
        )
        self.start_button.pack(fill="x", pady=10)

    def _create_status_area(self, parent: ttk.Frame) -> None:
        """ステータス表示エリアの作成"""
        status_frame = ttk.LabelFrame(parent, text="準備状況", padding="5")
        status_frame.pack(fill="x", pady=5)

        self.status_labels = {
            "regulation": ttk.Label(status_frame, text="レギュレーション設定: 未確定"),
            "participant": ttk.Label(status_frame, text="参加者一覧: 未確定"),
        }

        for label in self.status_labels.values():
            label.pack(fill="x")

    def _create_debug_area(self, parent: ttk.Frame) -> None:
        """デバッグエリアの作成"""
        debug_frame = ttk.Frame(parent)
        debug_frame.pack(pady=5)

        ttk.Button(
            debug_frame, text="デバッグ情報表示", command=self._show_debug_info
        ).pack(fill="x")

    def _open_sub_window(self, window_type: str) -> None:
        """サブウィンドウを開く"""
        try:
            window_classes = {
                "regulation": RegulationSettingWindow,
                "participant": ParticipantListWindow,
                "game_progress": GameProgressWindow,
            }

            # 既存のウィンドウが存在するか確認
            current_window = self.sub_windows.get(window_type)
            if current_window and current_window.winfo_exists():
                current_window.lift()
                return

            # 新しいウィンドウを作成
            window_class = window_classes.get(window_type)
            if window_class:
                new_window = window_class(self.window, self.store)
                new_window.window.transient(self.window)
                self.sub_windows[window_type] = new_window.window

                self.logger.info(f"Opened {window_type} window")
            else:
                raise ValueError(f"Unknown window type: {window_type}")

        except Exception as e:
            self.logger.error(f"Error opening {window_type} window: {str(e)}")
            self._show_error(f"ウィンドウを開く際にエラーが発生しました: {str(e)}")

    def _start_game(self) -> None:
        """ゲームを開始する"""
        try:
            if not (
                self.state.regulation_confirmed and self.state.participants_confirmed
            ):
                self._show_error("レギュレーション設定と参加者一覧の確定が必要です。")
                return

            if not messagebox.askyesno("確認", "ゲームを開始しますか？"):
                return

            # ゲーム状態の初期化と開始
            self.store.game_state.start_game()

            # ゲームログに開始記録を追加
            self.store.add_game_log(
                {
                    "phase": GamePhase.DAY_DISCUSSION.value,
                    "round": 1,
                    "action": "game_start",
                    "timestamp": datetime.now().isoformat(),
                }
            )

            # UI状態の更新
            self.state.game_active = True
            self._update_gm_speech(self.speech_templates["game_start"])
            self._update_start_button()

            # ゲーム進行ウィンドウを開く
            self._open_sub_window("game_progress")

            # イベント通知
            event_manager.notify(
                GameEvent(
                    type=EventType.GAME_STARTED,
                    data={
                        "player_count": len(self.store.game_state.players),
                        "regulation": self.store.game_state.regulation,
                    },
                    source="gm_window",
                )
            )

            self.logger.info("Game started successfully")

        except Exception as e:
            self.logger.error(f"Error starting game: {str(e)}")
            self._show_error(f"ゲーム開始時にエラーが発生しました: {str(e)}")
            self._handle_game_error()

    def _end_game(self) -> None:
        """ゲームを終了する"""
        try:
            if not messagebox.askyesno("確認", "ゲームを終了しますか？"):
                return

            # 全てのウィンドウをリセット
            self._reset_windows()

            # 状態のリセット
            self.state = GMWindowState()

            # UIの更新
            self._reset_ui_state()
            self._update_gm_speech(
                "ゲームを終了しました。参加者とレギュレーションを確定してください。"
            )

            # イベント通知
            event_manager.notify(
                GameEvent(
                    type=EventType.GAME_STATE_RESET,
                    data={"reason": "manual_end"},
                    source="gm_window",
                )
            )

            self.logger.info("Game ended and reset successfully")

        except Exception as e:
            self.logger.error(f"Error ending game: {str(e)}")
            self._show_error("ゲーム終了時にエラーが発生しました。")

    def _reset_windows(self) -> None:
        """すべてのサブウィンドウをリセット"""
        for window_type, window in self.sub_windows.items():
            try:
                if window and window.winfo_exists():
                    window.destroy()
                self.sub_windows[window_type] = None
            except Exception as e:
                self.logger.error(f"Error closing {window_type} window: {str(e)}")

    def _reset_ui_state(self) -> None:
        """UI状態のリセット"""
        try:
            # ラベルのリセット
            status_texts = {
                "regulation": "レギュレーション設定: 未確定",
                "participant": "参加者一覧: 未確定",
            }
            for key, text in status_texts.items():
                self.status_labels[key].config(text=text)

            self.phase_label.config(text="フェーズ: 準備中")
            self.round_label.config(text="ラウンド: -")
            self.village_count.config(text="村人チーム 残り人数: -")
            self.wolf_count.config(text="人狼チーム 残り人数: -")

            # ボタンのリセット
            self.start_button.config(
                text="ゲームスタート", command=self._start_game, state="disabled"
            )

        except Exception as e:
            self.logger.error(f"Error resetting UI state: {str(e)}")
            raise

    def _update_start_button(self) -> None:
        """スタートボタンの状態を更新"""
        try:
            if self.state.game_active:
                self.start_button.config(
                    text="ゲーム終了", command=self._end_game, state="normal"
                )
            else:
                enabled = (
                    self.state.regulation_confirmed
                    and self.state.participants_confirmed
                )
                self.start_button.config(
                    text="ゲームスタート",
                    command=self._start_game,
                    state="normal" if enabled else "disabled",
                )

        except Exception as e:
            self.logger.error(f"Error updating start button: {str(e)}")

    def _update_gm_speech(self, text: str) -> None:
        """GMセリフを更新"""
        try:
            self.speech_text.config(state="normal")
            self.speech_text.delete("1.0", tk.END)
            self.speech_text.insert("1.0", text)
            self.speech_text.config(state="disabled")

        except Exception as e:
            self.logger.error(f"Error updating GM speech: {str(e)}")

    # イベントハンドラーのメソッド
    def _handle_regulation_confirmed(self, event: GameEvent) -> None:
        """レギュレーション確定イベントの処理"""
        try:
            self.state.regulation_confirmed = True
            self.status_labels["regulation"].config(text="レギュレーション設定: 確定")
            self._update_start_button()
            self.logger.info("Regulation confirmed")
        except Exception as e:
            self.logger.error(f"Error handling regulation confirmation: {str(e)}")

    def _handle_players_confirmed(self, event: GameEvent) -> None:
        """プレイヤー確定イベントの処理"""
        try:
            self.state.participants_confirmed = True
            self.status_labels["participant"].config(text="参加者一覧: 確定")
            self._update_start_button()
            self.logger.info("Players confirmed")
        except Exception as e:
            self.logger.error(f"Error handling player confirmation: {str(e)}")

    def _handle_game_started(self, event: GameEvent) -> None:
        """ゲーム開始イベントの処理"""
        try:
            self.state.game_active = True
            self._update_ui_state()
            self.logger.info("Game start handled")
        except Exception as e:
            self.logger.error(f"Error handling game start: {str(e)}")

    def _handle_game_ended(self, event: GameEvent) -> None:
        """ゲーム終了イベントの処理"""
        try:
            winning_team = event.data.get("winning_team")
            if messagebox.askyesno(
                "ゲーム終了",
                f"{winning_team}チームの勝利です。\nメインメニューに戻りますか？",
            ):
                self._end_game()
        except Exception as e:
            self.logger.error(f"Error handling game end: {str(e)}")

    def _handle_phase_change(self, event: GameEvent) -> None:
        """フェーズ変更イベントの処理"""
        try:
            phase = event.data.get("new_phase")
            if phase == GamePhase.NIGHT.value:
                self._update_gm_speech(self.speech_templates["night"])
            self._update_ui_state()
        except Exception as e:
            self.logger.error(f"Error handling phase change: {str(e)}")

    def _handle_player_death(self, event: GameEvent) -> None:
        """プレイヤー死亡イベントの処理"""
        try:
            player_name = event.data.get("player_name")
            if event.data.get("phase") == GamePhase.NIGHT.value:
                self._update_gm_speech(
                    self.speech_templates["morning"]["kill"].format(player_name)
                )
            self._update_ui_state()
        except Exception as e:
            self.logger.error(f"Error handling player death: {str(e)}")

    def _handle_log_update(self, event: GameEvent) -> None:
        """ログ更新イベントの処理"""
        try:
            log_entry = event.data.get("log_entry", {})
            action = log_entry.get("action")

            if (
                action == "phase_start"
                and log_entry.get("phase") == GamePhase.DAY_DISCUSSION.value
            ):
                # 朝のメッセージ処理
                message_type = log_entry.get("message_type")
                if message_type == "kill":
                    victim = log_entry.get("victim")
                    self._update_gm_speech(
                        self.speech_templates["morning"]["kill"].format(victim)
                    )
                elif message_type == "no_kill":
                    self._update_gm_speech(self.speech_templates["morning"]["no_kill"])

            elif action == "execution":
                # 処刑メッセージ処理
                target = log_entry.get("target")
                if target and target != "対象なし":
                    self._update_gm_speech(
                        self.speech_templates["execution"].format(target)
                    )

            elif (
                action == "phase_start"
                and log_entry.get("phase") == GamePhase.NIGHT.value
            ):
                # 夜のメッセージ処理
                self._update_gm_speech(self.speech_templates["night"])

        except Exception as e:
            self.logger.error(f"Error handling log update: {str(e)}")

    def _show_debug_info(self) -> None:
        """デバッグ情報の表示"""
        try:
            debug_info = [
                "=== GMMainWindow Debug Info ===",
                f"Regulation confirmed: {self.state.regulation_confirmed}",
                f"Players confirmed: {self.state.participants_confirmed}",
                f"Game active: {self.state.game_active}",
                f"Last update: {self.state.last_update}",
                "\nWindow states:",
                *[
                    f"{k}: {bool(v and v.winfo_exists())}"
                    for k, v in self.sub_windows.items()
                ],
                "\nGameState info:",
                f"Phase: {self.store.game_state.current_phase}",
                f"Round: {self.store.game_state.current_round}",
                f"Player count: {len(self.store.game_state.players)}",
            ]

            # ログ出力
            for line in debug_info:
                self.logger.debug(line)

            # UI表示
            messagebox.showinfo("Debug Info", "\n".join(debug_info))

        except Exception as e:
            self.logger.error(f"Error showing debug info: {str(e)}")
            self._show_error("デバッグ情報の表示中にエラーが発生しました。")

    def _handle_game_error(self) -> None:
        """ゲームエラーの処理"""
        try:
            self.state.game_active = False
            self._reset_windows()
            self._reset_ui_state()

            event_manager.notify(
                GameEvent(
                    type=EventType.GAME_STATE_RESET,
                    data={"reason": "error_recovery"},
                    source="gm_window",
                )
            )
        except Exception as e:
            self.logger.critical(f"Error in error recovery: {str(e)}")
