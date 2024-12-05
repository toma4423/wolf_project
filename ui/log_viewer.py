from typing import Dict, List, Optional
from dataclasses import dataclass, field
import json
from datetime import datetime
import logging
import tkinter as tk
from tkinter import ttk, messagebox

from config.settings import APP_SETTINGS, ROLE_SETTINGS
from store.global_data_store import GlobalDataStore
from core.events import EventType, GameEvent, event_manager
from core.game_state import GamePhase
from core.player import Player, PlayerRole


@dataclass
class LogEntry:
    """ログエントリーを表すデータクラス"""

    phase: GamePhase
    round: int
    action: str
    details: Dict
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class LogViewerState:
    """ログビューアの状態を管理するデータクラス"""

    current_page: int = 0
    logs: List[LogEntry] = field(default_factory=list)
    is_game_active: bool = False
    last_update: datetime = field(default_factory=datetime.now)


class LogViewerWindow:
    """ログ確認ウィンドウ"""

    def __init__(self, parent: tk.Tk, store: GlobalDataStore):
        self.logger = logging.getLogger(__name__)

        # 基本初期化
        self.parent = parent
        self.store = store
        self.window = tk.Toplevel(parent)
        self.window.title("ログ確認")
        self.window.geometry(
            f"{APP_SETTINGS['default_window_size']['log_viewer'][0]}x"
            f"{APP_SETTINGS['default_window_size']['log_viewer'][1]}"
        )

        # 状態管理
        self.state = LogViewerState()

        # UI要素の参照
        self.log_text: Optional[tk.Text] = None
        self.page_info: Optional[ttk.Label] = None
        self.prev_button: Optional[ttk.Button] = None
        self.next_button: Optional[ttk.Button] = None

        # UIの初期化
        self._init_ui()

        # 初期データの設定
        self._initialize_data()

        # イベントマネージャーへの登録
        event_manager.subscribe_all(self)
        self.logger.info("LogViewerWindow initialized")

    def _init_ui(self) -> None:
        """UIの初期化"""
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(expand=True, fill="both")

        # ログ表示エリア
        self._create_log_area(main_frame)

        # ナビゲーションエリア
        self._create_navigation_area(main_frame)

    def _create_log_area(self, parent: ttk.Frame) -> None:
        """ログ表示エリアの作成"""
        log_frame = ttk.LabelFrame(parent, text="ログ内容", padding="5")
        log_frame.pack(fill="both", expand=True, pady=5)

        # テキストウィジェットとスクロールバー
        self.log_text = tk.Text(log_frame, wrap=tk.WORD, height=20, state="disabled")
        scrollbar = ttk.Scrollbar(
            log_frame, orient="vertical", command=self.log_text.yview
        )
        self.log_text.configure(yscrollcommand=scrollbar.set)

        # パッキング
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # フォント設定
        self.log_text.configure(font=("Helvetica", 10), padx=5, pady=5)

    def _create_navigation_area(self, parent: ttk.Frame) -> None:
        """ナビゲーションエリアの作成"""
        nav_frame = ttk.Frame(parent)
        nav_frame.pack(fill="x", pady=5)

        # ページ情報
        self.page_info = ttk.Label(nav_frame, text="ログなし", anchor="center")
        self.page_info.pack(side="top", fill="x")

        # ナビゲーションボタン
        button_frame = ttk.Frame(nav_frame)
        button_frame.pack(side="top", fill="x", pady=5)

        self.prev_button = ttk.Button(
            button_frame,
            text="前のページ",
            command=self._previous_page,
            state="disabled",
        )
        self.prev_button.pack(side="left", padx=5)

        self.next_button = ttk.Button(
            button_frame, text="次のページ", command=self._next_page, state="disabled"
        )
        self.next_button.pack(side="right", padx=5)

    def _initialize_data(self) -> None:
        """初期データの設定"""
        try:
            raw_logs = self.store.game_state.game_log
            self.state.logs = self._organize_logs(raw_logs)
            self._update_display()
            self.logger.info("Log viewer data initialized")
        except Exception as e:
            self.logger.error(f"Error initializing data: {str(e)}")
            self._show_error("データの初期化中にエラーが発生しました。")

    def _organize_logs(self, raw_logs: List[Dict]) -> List[LogEntry]:
        """ログデータを整理"""
        try:
            organized_logs = []
            current_round = None
            current_phase = None

            for log in raw_logs:
                # フェーズとラウンドの取得
                round_num = log.get("round")
                phase = GamePhase(log.get("phase"))
                action = log.get("action")

                # 新しいラウンドまたはフェーズの開始
                if round_num != current_round or phase != current_phase:
                    log_entry = LogEntry(
                        phase=phase,
                        round=round_num,
                        action=action,
                        details=self._extract_log_details(log),
                        timestamp=datetime.fromisoformat(
                            log.get("timestamp", datetime.now().isoformat())
                        ),
                    )
                    organized_logs.append(log_entry)
                    current_round = round_num
                    current_phase = phase

            return organized_logs

        except Exception as e:
            self.logger.error(f"Error organizing logs: {str(e)}")
            return []

    def _extract_log_details(self, log: Dict) -> Dict:
        """ログの詳細情報を抽出"""
        try:
            details = {}

            # アクションタイプに基づいて詳細を抽出
            action = log.get("action")
            if action == "execution":
                details = self._extract_execution_details(log)
            elif action == "night_actions":
                details = self._extract_night_action_details(log)
            elif action == "phase_start":
                details = {"message": f"{log.get('phase')} フェーズ開始"}
            elif action == "game_start":
                details = {"message": "ゲーム開始"}
            elif action == "game_end":
                details = {
                    "winning_team": log.get("winning_team"),
                    "final_round": log.get("final_round"),
                }

            return details

        except Exception as e:
            self.logger.error(f"Error extracting log details: {str(e)}")
            return {}

    def _extract_execution_details(self, log: Dict) -> Dict:
        """処刑アクションの詳細を抽出"""
        target = log.get("target")
        if target == "対象なし":
            return {"action": "処刑", "target": "対象なし"}

        role = log.get("role", "不明")
        role_name = ROLE_SETTINGS[role]["name"] if role in ROLE_SETTINGS else "不明"

        return {
            "action": "処刑",
            "target": target,
            "role": role_name,
            "original_role": role,
        }

    def _extract_night_action_details(self, log: Dict) -> Dict:
        """夜アクションの詳細を抽出"""
        details = {
            "attack": {
                "target": log.get("attack_target", "対象なし"),
                "success": log.get("attack_target") != log.get("guard_target"),
            },
            "guard": {"target": log.get("guard_target", "対象なし")},
            "fortune": {
                "target": log.get("fortune_target", "対象なし"),
                "result": None,
            },
        }

        # 占い結果の処理
        fortune_target = log.get("fortune_target")
        if fortune_target != "対象なし":
            fortune_result = log.get("fortune_result", "")
            result_name = (
                ROLE_SETTINGS[fortune_result]["name"]
                if fortune_result in ROLE_SETTINGS
                else "不明"
            )
            details["fortune"]["result"] = result_name

        return details

    def _format_display_text(self, log_entry: LogEntry) -> str:
        """ログエントリーの表示テキストを生成"""
        try:
            text_lines = []

            if log_entry.action == "execution":
                text_lines.extend(self._format_execution_text(log_entry.details))
            elif log_entry.action == "night_actions":
                text_lines.extend(self._format_night_actions_text(log_entry.details))
            elif log_entry.action == "phase_start":
                text_lines.append(log_entry.details.get("message", ""))
            elif log_entry.action == "game_start":
                text_lines.append("=== ゲーム開始 ===")
            elif log_entry.action == "game_end":
                text_lines.extend(self._format_game_end_text(log_entry.details))

            # タイムスタンプの追加
            time_str = log_entry.timestamp.strftime("%H:%M:%S")
            text_lines.append(f"[記録時刻: {time_str}]\n")

            return "\n".join(text_lines)

        except Exception as e:
            self.logger.error(f"Error formatting display text: {str(e)}")
            return "ログの表示中にエラーが発生しました。"

    def _format_execution_text(self, details: Dict) -> List[str]:
        """処刑アクションのテキストをフォーマット"""
        if details["target"] == "対象なし":
            return ["処刑: 対象なし"]

        return [f"処刑: {details['target']}", f"役職: {details['role']}"]

    def _format_night_actions_text(self, details: Dict) -> List[str]:
        """夜アクションのテキストをフォーマット"""
        text_lines = []

        # 襲撃結果
        attack = details["attack"]
        if attack["target"] == "対象なし":
            text_lines.append("襲撃: 対象なし")
        else:
            result = "成功" if attack["success"] else "失敗"
            text_lines.append(f"襲撃: {attack['target']} ({result})")

        # 護衛結果
        guard = details["guard"]
        text_lines.append(f"護衛: {guard['target']}")

        # 占い結果
        fortune = details["fortune"]
        if fortune["target"] == "対象なし":
            text_lines.append("占い: 対象なし")
        else:
            text_lines.append(
                f"占い: {fortune['target']} "
                f"(結果: {fortune['result'] if fortune['result'] else '不明'})"
            )

        return text_lines

    def _format_game_end_text(self, details: Dict) -> List[str]:
        """ゲーム終了時のテキストをフォーマット"""
        return [
            "=== ゲーム終了 ===",
            f"勝利陣営: {details['winning_team']}チーム",
            f"最終ラウンド: {details['final_round']}R",
        ]

    def _update_display(self) -> None:
        """表示の更新"""
        try:
            self.log_text.config(state="normal")
            self.log_text.delete("1.0", tk.END)

            if not self.state.logs:
                self.log_text.insert("1.0", "ログはありません")
                self.page_info.config(text="ログなし")
                self._update_navigation_buttons()
                return

            log_entry = self.state.logs[self.state.current_page]
            display_text = self._format_display_text(log_entry)

            # ページ情報の更新
            self.page_info.config(
                text=f"{log_entry.round}R {log_entry.phase.get_display_name()}"
            )

            # ログテキストの更新
            self.log_text.insert("1.0", display_text)
            self.log_text.config(state="disabled")

            # ナビゲーションボタンの更新
            self._update_navigation_buttons()

        except Exception as e:
            self.logger.error(f"Error updating display: {str(e)}")
            self._show_error("表示の更新中にエラーが発生しました。")

    def _update_navigation_buttons(self) -> None:
        """ナビゲーションボタンの状態を更新"""
        if not self.state.logs:
            self.prev_button.config(state="disabled")
            self.next_button.config(state="disabled")
            return

        self.prev_button.config(
            state="normal" if self.state.current_page > 0 else "disabled"
        )
        self.next_button.config(
            state=(
                "normal"
                if self.state.current_page < len(self.state.logs) - 1
                else "disabled"
            )
        )

    def handle_event(self, event: GameEvent) -> None:
        """イベントハンドラ"""
        try:
            handlers = {
                EventType.GAME_LOG_UPDATED: self._handle_log_update,
                EventType.GAME_STATE_RESET: self._handle_game_reset,
                EventType.ERROR: self._handle_error,
            }

            handler = handlers.get(event.type)
            if handler:
                handler(event)
                self.state.last_update = datetime.now()

        except Exception as e:
            self.logger.error(f"Error handling event {event.type}: {str(e)}")
            self._show_error("イベント処理中にエラーが発生しました。")

    def _handle_log_update(self, event: GameEvent) -> None:
        """ログ更新イベントの処理"""
        try:
            raw_logs = self.store.game_state.game_log
            self.state.logs = self._organize_logs(raw_logs)
            self.state.current_page = len(self.state.logs) - 1  # 最新のログを表示
            self._update_display()
            self.logger.info("Log viewer updated with new log entry")
        except Exception as e:
            self.logger.error(f"Error handling log update: {str(e)}")
            raise

    def _handle_game_reset(self, event: GameEvent) -> None:
        """ゲームリセットイベントの処理"""
        try:
            self.state = LogViewerState()
            self._update_display()
            self.logger.info("Log viewer reset")
        except Exception as e:
            self.logger.error(f"Error handling game reset: {str(e)}")
            raise

    def _handle_error(self, event: GameEvent) -> None:
        """エラーイベントの処理"""
        error_msg = event.data.get("message", "不明なエラー")
        self.logger.error(f"Error event received: {error_msg}")
        self._show_error(error_msg)

    def _show_error(self, message: str) -> None:
        """エラーメッセージの表示"""
        self.logger.error(message)
        messagebox.showerror("エラー", message)

    def _previous_page(self) -> None:
        """前のページに移動"""
        if self.state.current_page > 0:
            self.state.current_page -= 1
            self._update_display()

    def _next_page(self) -> None:
        """次のページに移動"""
        if self.state.current_page < len(self.state.logs) - 1:
            self.state.current_page += 1
            self._update_display()

    def destroy(self) -> None:
        """ウィンドウの破棄"""
        try:
            if hasattr(self, "window"):
                self.window.destroy()
                event_manager.unsubscribe_all(self)
                self.logger.info("Log viewer window destroyed")
        except Exception as e:
            self.logger.error(f"Error destroying window: {str(e)}")
