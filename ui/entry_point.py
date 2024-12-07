from typing import Optional, Dict
from dataclasses import dataclass, field
import logging
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox

from config.settings import APP_SETTINGS
from store.global_data_store import GlobalDataStore
from core.events import EventType, GameEvent, event_manager
from core.game_state import GameState
from ui.gm_mode_main import GMMainWindow


@dataclass
class AppState:
    """アプリケーションの状態を管理するデータクラス"""

    current_mode: Optional[str] = None
    is_game_active: bool = False
    windows: Dict[str, Optional[tk.Toplevel]] = field(default_factory=dict)
    last_update: datetime = field(default_factory=datetime.now)


class EntryPointWindow:
    """エントリーポイントウィンドウ"""

    def __init__(self, parent: tk.Tk, store: GlobalDataStore):
        self.logger = logging.getLogger(__name__)

        # 基本初期化
        self.parent = parent
        self.store = store
        self.window = tk.Toplevel(parent)
        self.window.title(APP_SETTINGS["app_name"])

        # ウィンドウサイズの設定
        window_width = APP_SETTINGS["default_window_size"]["entry_point"][0]
        window_height = APP_SETTINGS["default_window_size"]["entry_point"][1]
        self.window.geometry(f"{window_width}x{window_height}")
        self.window.resizable(False, False)

        # 状態管理
        self.state = AppState()

        # UI要素の参照
        self.main_frame: Optional[ttk.Frame] = None
        self.gm_button: Optional[ttk.Button] = None
        self.player_button: Optional[ttk.Button] = None
        self.exit_button: Optional[ttk.Button] = None

        # UIの初期化
        self._init_ui()

        # ウィンドウの中央配置
        self._center_window()

        # イベントマネージャーへの登録
        event_manager.subscribe_all(self)

        # ウィンドウクローズ時のハンドラ設定
        self.window.protocol("WM_DELETE_WINDOW", self._on_closing)

        self.logger.info("EntryPointWindow initialized")

    def _init_ui(self) -> None:
        """UIの初期化"""
        # メインフレーム
        self.main_frame = ttk.Frame(self.window, padding="20")
        self.main_frame.place(relx=0.5, rely=0.5, anchor="center")

        # タイトル
        title_label = ttk.Label(
            self.main_frame,
            text=APP_SETTINGS["app_name"],
            font=("Helvetica", 14, "bold"),
        )
        title_label.pack(pady=20)

        # ボタンスタイルの設定
        self._setup_button_style()

        # ボタンの作成
        self._create_buttons()

    def _setup_button_style(self) -> None:
        """ボタンスタイルの設定"""
        style = ttk.Style()
        style.configure("Action.TButton", padding=10, width=20, font=("Helvetica", 10))

    def _create_buttons(self) -> None:
        """ボタンの作成"""
        # GMモード開始ボタン
        self.gm_button = ttk.Button(
            self.main_frame,
            text="GMモードを開始",
            style="Action.TButton",
            command=self._start_gm_mode,
        )
        self.gm_button.pack(pady=10)

        # プレイヤーモード開始ボタン
        self.player_button = ttk.Button(
            self.main_frame,
            text="プレイヤーモードを開始",
            style="Action.TButton",
            command=self._start_player_mode,
        )
        self.player_button.pack(pady=10)

        # アプリ終了ボタン
        self.exit_button = ttk.Button(
            self.main_frame,
            text="アプリを終了",
            style="Action.TButton",
            command=self._confirm_exit,
        )
        self.exit_button.pack(pady=10)

    def _center_window(self) -> None:
        """ウィンドウを画面中央に配置"""
        window_width = APP_SETTINGS["default_window_size"]["entry_point"][0]
        window_height = APP_SETTINGS["default_window_size"]["entry_point"][1]

        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()

        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2

        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")

    def _start_gm_mode(self) -> None:
        """GMモードの開始"""
        try:
            if self.state.is_game_active:
                if (
                    "gm_window" in self.state.windows
                    and self.state.windows["gm_window"]
                ):
                    self.state.windows["gm_window"].lift()
                return

            # エントリーポイントウィンドウを非表示
            self.window.withdraw()

            # GMモードメインウィンドウを作成
            gm_window = GMMainWindow(self.window, self.store)
            self.state.windows["gm_window"] = gm_window.window

            # GMウィンドウが閉じられた時の処理を設定
            gm_window.window.protocol("WM_DELETE_WINDOW", self._on_gm_window_closing)

            # 状態の更新
            self.state.current_mode = "gm"
            self.state.is_game_active = True

            # イベント通知
            event_manager.notify(
                GameEvent(
                    type=EventType.GM_MODE_STARTED,
                    data={"timestamp": datetime.now().isoformat()},
                    source="entry_point",
                )
            )

            self.logger.info("GM mode started")

        except Exception as e:
            self.logger.error(f"Error starting GM mode: {str(e)}")
            self._show_error("GMモードの開始時にエラーが発生しました。")
            self.window.deiconify()

    def _start_player_mode(self) -> None:
        """プレイヤーモードの開始"""
        # 開発中の機能として通知
        messagebox.showinfo(
            "お知らせ",
            "プレイヤーモードは現在開発中です。\n今後のアップデートをお待ちください。",
        )

    def _on_gm_window_closing(self) -> None:
        """GMウィンドウが閉じられた時の処理"""
        if not messagebox.askokcancel("確認", "GMモードを終了しますか？"):
            return

        try:
            # GMウィンドウの破棄
            if "gm_window" in self.state.windows and self.state.windows["gm_window"]:
                self.state.windows["gm_window"].destroy()
                self.state.windows["gm_window"] = None

            # ゲーム状態のリセット
            self.store.game_state.reset()

            # 状態の更新
            self.state.current_mode = None
            self.state.is_game_active = False

            # イベント通知
            event_manager.notify(
                GameEvent(
                    type=EventType.GM_MODE_ENDED,
                    data={"cause": "user_close"},
                    source="entry_point",
                )
            )

            # エントリーポイントウィンドウを再表示
            self.window.deiconify()

            self.logger.info("GM mode ended")

        except Exception as e:
            self.logger.error(f"Error closing GM mode: {str(e)}")
            self._show_error("GMモードの終了時にエラーが発生しました。")

    def handle_event(self, event: GameEvent) -> None:
        """イベントハンドラ"""
        try:
            handlers = {
                EventType.GAME_STATE_RESET: self._handle_game_reset,
                EventType.GAME_STARTED: self._handle_game_started,
                EventType.GAME_ENDED: self._handle_game_ended,
                EventType.ERROR: self._handle_error,
            }

            handler = handlers.get(event.type)
            if handler:
                handler(event)
                self.state.last_update = datetime.now()

        except Exception as e:
            self.logger.error(f"Error handling event {event.type}: {str(e)}")
            self._show_error("イベント処理中にエラーが発生しました。")

    def _handle_game_reset(self, event: GameEvent) -> None:
        """ゲームリセットイベントの処理"""
        try:
            self.logger.info("Game state reset")
            if not self.state.windows.get("gm_window"):
                self.window.deiconify()
                self.state.is_game_active = False
                self.state.current_mode = None
        except Exception as e:
            self.logger.error(f"Error handling game reset: {str(e)}")
            raise

    def _handle_game_started(self, event: GameEvent) -> None:
        """ゲーム開始イベントの処理"""
        try:
            self.logger.info("Game started")
            self.window.withdraw()
            self.state.is_game_active = True
        except Exception as e:
            self.logger.error(f"Error handling game start: {str(e)}")
            raise

    def _handle_game_ended(self, event: GameEvent) -> None:
        """ゲーム終了イベントの処理"""
        try:
            self.logger.info("Game ended")
            # メインメニューに戻る処理を削除し、ログ記録のみ行う
        except Exception as e:
            self.logger.error(f"Error handling game end: {str(e)}")
            raise

    def _handle_error(self, event: GameEvent) -> None:
        """エラーイベントの処理"""
        error_msg = event.data.get("message", "不明なエラー")
        self.logger.error(f"Error event received: {error_msg}")
        self._show_error(error_msg)

    def _return_to_main_menu(self) -> None:
        """メインメニューに戻る"""
        try:
            # 開いているウィンドウをすべて閉じる
            for window_key, window in self.state.windows.items():
                if window and window.winfo_exists():
                    window.destroy()
                self.state.windows[window_key] = None

            # ゲーム状態のリセット
            self.store.game_state.reset()

            # 状態のリセット
            self.state.current_mode = None
            self.state.is_game_active = False

            # イベント通知
            event_manager.notify(
                GameEvent(
                    type=EventType.GAME_STATE_RESET,
                    data={"cause": "return_to_menu"},
                    source="entry_point",
                )
            )

            # エントリーポイントウィンドウを再表示
            self.window.deiconify()
            self.logger.info("Returned to main menu")

        except Exception as e:
            self.logger.error(f"Error returning to main menu: {str(e)}")
            self._show_error("メインメニューへの移動時にエラーが発生しました。")

    def _confirm_exit(self) -> None:
        """アプリケーション終了の確認"""
        if not messagebox.askokcancel("確認", "アプリケーションを終了しますか？"):
            return

        try:
            # 開いているウィンドウをすべて閉じる
            for window_key, window in self.state.windows.items():
                if window and window.winfo_exists():
                    window.destroy()
                self.state.windows[window_key] = None

            # イベント通知
            event_manager.notify(
                GameEvent(
                    type=EventType.APPLICATION_CLOSING,
                    data={
                        "cause": "user_request",
                        "timestamp": datetime.now().isoformat(),
                    },
                    source="entry_point",
                )
            )

            # メインウィンドウを閉じる
            self.logger.info("Application terminated by user")
            self.parent.quit()

        except Exception as e:
            self.logger.error(f"Error during application shutdown: {str(e)}")
            self._show_error("アプリケーションの終了時にエラーが発生しました。")

    def _on_closing(self) -> None:
        """ウィンドウを閉じる際の処理"""
        self._confirm_exit()

    def _show_error(self, message: str) -> None:
        """エラーメッセージの表示"""
        self.logger.error(message)
        messagebox.showerror("エラー", message)

    def _clean_up_resources(self) -> None:
        """リソースのクリーンアップ"""
        try:
            # イベントマネージャーからの登録解除
            event_manager.unsubscribe_all(self)

            # 開いているウィンドウの破棄
            for window_key, window in self.state.windows.items():
                if window and window.winfo_exists():
                    window.destroy()
                self.state.windows[window_key] = None

            self.logger.info("Resources cleaned up successfully")

        except Exception as e:
            self.logger.error(f"Error during resource cleanup: {str(e)}")

    def show(self) -> None:
        """ウィンドウを表示"""
        self.window.deiconify()
        self.window.lift()

    def hide(self) -> None:
        """ウィンドウを非表示"""
        self.window.withdraw()

    def destroy(self) -> None:
        """ウィンドウの破棄"""
        try:
            self._clean_up_resources()
            if hasattr(self, "window"):
                self.window.destroy()
            self.logger.info("Entry point window destroyed")
        except Exception as e:
            self.logger.error(f"Error destroying window: {str(e)}")

    def get_app_status(self) -> Dict:
        """アプリケーションの状態を取得（デバッグ用）"""
        return {
            "current_mode": self.state.current_mode,
            "is_game_active": self.state.is_game_active,
            "active_windows": {
                key: bool(window and window.winfo_exists())
                for key, window in self.state.windows.items()
            },
            "last_update": self.state.last_update.isoformat(),
        }
