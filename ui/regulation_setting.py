from typing import Dict, List, Optional
from dataclasses import dataclass, field
import json
import logging
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime
from pathlib import Path

from config.settings import APP_SETTINGS, ROLE_SETTINGS, DATA_DIR
from store.global_data_store import GlobalDataStore
from core.events import EventType, GameEvent, event_manager
from core.game_state import GamePhase
from core.player import PlayerRole


@dataclass
class RegulationState:
    """レギュレーション設定の状態を管理するデータクラス"""

    role_counts: Dict[str, int] = field(default_factory=dict)
    round_times: List[Dict[str, int]] = field(default_factory=list)
    is_confirmed: bool = False
    last_update: datetime = field(default_factory=datetime.now)
    total_players: int = 0


@dataclass
class RoundTimeConfig:
    """ラウンド時間設定を管理するデータクラス"""

    round_number: int
    time: int
    frame: ttk.Frame
    time_var: tk.StringVar


class RegulationSettingWindow:
    """レギュレーション設定ウィンドウ"""

    def __init__(self, parent: tk.Tk, store: GlobalDataStore):
        self.logger = logging.getLogger(__name__)

        # 基本初期化
        self.parent = parent
        self.store = store
        self.window = tk.Toplevel(parent)
        self.window.title("レギュレーション設定")
        self.window.geometry(
            f"{APP_SETTINGS['default_window_size']['regulation'][0]}x"
            f"{APP_SETTINGS['default_window_size']['regulation'][1]}"
        )

        # 状態管理
        self.state = RegulationState()
        self.state.role_counts = {role_id: 0 for role_id in ROLE_SETTINGS.keys()}

        # UI要素の参照
        self.role_spinboxes: Dict[str, ttk.Spinbox] = {}
        self.total_label: Optional[ttk.Label] = None
        self.round_frame: Optional[ttk.Frame] = None
        self.round_configs: List[RoundTimeConfig] = []

        # UIの初期化
        self._init_ui()

        # イベントマネージャーへの登録
        event_manager.subscribe_all(self)
        self.logger.info("RegulationSettingWindow initialized")

    def _init_ui(self) -> None:
        """UIの初期化"""
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(expand=True, fill="both")

        # 役職設定セクション
        self._create_role_section(main_frame)

        # タイマー設定セクション
        self._create_timer_section(main_frame)

        # 保存・呼び出しセクション
        self._create_save_section(main_frame)

        # レギュレーション決定ボタン
        self._create_confirm_button(main_frame)

    def _create_role_section(self, parent: ttk.Frame) -> None:
        """役職設定セクションの作成"""
        role_frame = ttk.LabelFrame(parent, text="役職設定", padding="5")
        role_frame.pack(fill="x", pady=5)

        # 合計人数表示
        self.total_label = ttk.Label(role_frame, text="合計人数: 0")
        self.total_label.pack(side="bottom", pady=5)

        # 役職ごとの設定行を作成
        for role_id in ROLE_SETTINGS:
            frame = ttk.Frame(role_frame)
            frame.pack(fill="x", pady=2)

            ttk.Label(frame, text=f"{ROLE_SETTINGS[role_id]['name']}:").pack(
                side="left", padx=5
            )

            spinbox = ttk.Spinbox(
                frame,
                from_=0,
                to=APP_SETTINGS["max_players"],
                width=5,
                command=self._update_total_count,
            )
            spinbox.set("0")
            spinbox.pack(side="right", padx=5)

            self.role_spinboxes[role_id] = spinbox

    def _create_timer_section(self, parent: ttk.Frame) -> None:
        """タイマー設定セクションの作成"""
        timer_frame = ttk.LabelFrame(parent, text="話し合い時間設定", padding="5")
        timer_frame.pack(fill="x", pady=5)

        self.round_frame = ttk.Frame(timer_frame)
        self.round_frame.pack(fill="x")

        ttk.Button(timer_frame, text="ラウンド追加", command=self._add_round).pack(
            fill="x", pady=5
        )

        # 初期ラウンドの追加
        self._add_round()

    def _create_save_section(self, parent: ttk.Frame) -> None:
        """保存・呼び出しセクションの作成"""
        save_frame = ttk.Frame(parent)
        save_frame.pack(fill="x", pady=5)

        ttk.Button(save_frame, text="設定を保存", command=self._save_regulation).pack(
            side="left", padx=5
        )

        ttk.Button(
            save_frame, text="保存済み設定を開く", command=self._show_saved_regulations
        ).pack(side="right", padx=5)

    def _create_confirm_button(self, parent: ttk.Frame) -> None:
        """レギュレーション決定ボタンの作成"""
        ttk.Button(
            parent, text="レギュレーション決定", command=self._confirm_regulation
        ).pack(fill="x", pady=10)

    def _add_round(self) -> None:
        """ラウンドの追加"""
        round_num = len(self.round_configs) + 1

        # デフォルト時間の設定
        default_time = "3"
        if self.round_configs:
            default_time = self.round_configs[-1].time_var.get()

        frame = ttk.Frame(self.round_frame)
        frame.pack(fill="x", pady=2)

        ttk.Label(frame, text=f"{round_num}R:").pack(side="left", padx=5)

        time_var = tk.StringVar(value=default_time)
        spinbox = ttk.Spinbox(frame, from_=1, to=60, width=5, textvariable=time_var)
        spinbox.pack(side="left", padx=5)

        ttk.Label(frame, text="分").pack(side="left")

        # 削除ボタン（最初のラウンド以外）
        if round_num > 1:
            ttk.Button(
                frame,
                text="削除",
                command=lambda f=frame, r=round_num: self._remove_round(f, r),
            ).pack(side="right", padx=5)

        # 設定の保存
        config = RoundTimeConfig(
            round_number=round_num,
            time=int(default_time),
            frame=frame,
            time_var=time_var,
        )
        self.round_configs.append(config)

    def _remove_round(self, frame: ttk.Frame, round_num: int) -> None:
        """ラウンドの削除"""
        try:
            frame.destroy()
            self.round_configs = [
                config
                for config in self.round_configs
                if config.round_number != round_num
            ]

            # ラウンド番号の振り直し
            for i, config in enumerate(self.round_configs, 1):
                config.round_number = i
                for widget in config.frame.winfo_children():
                    if isinstance(widget, ttk.Label) and "R:" in widget.cget("text"):
                        widget.config(text=f"{i}R:")

            self.logger.info(f"Removed round {round_num}")

        except Exception as e:
            self.logger.error(f"Error removing round: {str(e)}")
            self._show_error("ラウンドの削除中にエラーが発生しました。")

    def _update_total_count(self) -> None:
        """合計人数の更新"""
        try:
            total = sum(int(spinbox.get()) for spinbox in self.role_spinboxes.values())
            self.state.total_players = total

            if hasattr(self, "total_label"):
                self.total_label.config(text=f"合計人数: {total}")

            self._validate_total_players(total)

        except ValueError:
            self.logger.warning("Invalid number input detected")
            self.total_label.config(text="合計人数: 無効な入力")
        except Exception as e:
            self.logger.error(f"Error updating total count: {str(e)}")

    def _validate_total_players(self, total: int) -> None:
        """プレイヤー数の検証"""
        if total < APP_SETTINGS["min_players"]:
            self.total_label.config(
                text=f"合計人数: {total} (最低{APP_SETTINGS['min_players']}人必要)"
            )
        elif total > APP_SETTINGS["max_players"]:
            self.total_label.config(
                text=f"合計人数: {total} (最大{APP_SETTINGS['max_players']}人まで)"
            )

    def _create_regulation_data(self) -> Dict:
        """レギュレーションデータの作成"""
        return {
            "roles": {
                role_id: int(spinbox.get())
                for role_id, spinbox in self.role_spinboxes.items()
            },
            "round_times": [
                {"round": config.round_number, "time": int(config.time_var.get())}
                for config in self.round_configs
            ],
            "total_players": self.state.total_players,
        }

    def _save_regulation(self) -> None:
        """レギュレーションの保存"""
        try:
            name = simpledialog.askstring(
                "保存", "レギュレーション名を入力してください:", parent=self.window
            )

            if not name:
                return

            regulation_data = self._create_regulation_data()
            if not self._validate_regulation_data(regulation_data):
                self._show_error("無効なレギュレーションデータです。")
                return

            if self.store.save_regulation(name, regulation_data):
                event_manager.notify(
                    GameEvent(
                        type=EventType.REGULATION_SAVED,
                        data={"name": name, "regulation": regulation_data},
                        source="regulation_setting",
                    )
                )
                messagebox.showinfo("保存完了", "レギュレーションを保存しました。")
                self.logger.info(f"Regulation '{name}' saved successfully")
            else:
                raise ValueError("レギュレーションの保存に失敗しました。")

        except Exception as e:
            self.logger.error(f"Error saving regulation: {str(e)}")
            self._show_error(f"レギュレーションの保存中にエラーが発生しました。")

    def _show_saved_regulations(self) -> None:
        """保存済みレギュレーションの表示"""
        try:
            regulations = self.store.load_regulations()
            if not regulations:
                messagebox.showinfo("通知", "保存済みのレギュレーションはありません。")
                return

            dialog = tk.Toplevel(self.window)
            dialog.title("保存済みレギュレーション")
            dialog.geometry("300x400")

            list_box = tk.Listbox(dialog)
            list_box.pack(fill="both", expand=True, padx=5, pady=5)

            for name in sorted(regulations.keys()):
                list_box.insert(tk.END, name)

            button_frame = ttk.Frame(dialog)
            button_frame.pack(fill="x", padx=5, pady=5)

            ttk.Button(
                button_frame,
                text="読み込み",
                command=lambda: self._load_selected_regulation(
                    list_box, dialog, regulations
                ),
            ).pack(side="left", padx=5)

            ttk.Button(button_frame, text="閉じる", command=dialog.destroy).pack(
                side="right", padx=5
            )

        except Exception as e:
            self.logger.error(f"Error showing saved regulations: {str(e)}")
            self._show_error("保存済みレギュレーションの表示中にエラーが発生しました。")

    def _load_selected_regulation(
        self, list_box: tk.Listbox, dialog: tk.Toplevel, regulations: Dict
    ) -> None:
        """選択されたレギュレーションの読み込み"""
        try:
            selection = list_box.curselection()
            if not selection:
                return

            name = list_box.get(selection[0])
            regulation_data = regulations[name]

            if self._validate_regulation_data(regulation_data):
                self._load_regulation(regulation_data)
                dialog.destroy()
                self.logger.info(f"Loaded regulation: {name}")
            else:
                raise ValueError("無効なレギュレーションデータです。")

        except Exception as e:
            self.logger.error(f"Error loading regulation: {str(e)}")
            self._show_error("レギュレーションの読み込み中にエラーが発生しました。")

    def _load_regulation(self, regulation_data: Dict) -> None:
        """レギュレーションの読み込み"""
        try:
            # 役職人数の設定
            for role_id, count in regulation_data["roles"].items():
                if role_id in self.role_spinboxes:
                    self.role_spinboxes[role_id].set(str(count))

            self._update_total_count()

            # ラウンド時間の設定
            self._clear_rounds()
            for round_time in regulation_data["round_times"]:
                self._add_round()
                self.round_configs[-1].time_var.set(str(round_time["time"]))

            event_manager.notify(
                GameEvent(
                    type=EventType.REGULATION_UPDATED,
                    data={"regulation": regulation_data},
                    source="regulation_setting",
                )
            )

        except Exception as e:
            self.logger.error(f"Error loading regulation data: {str(e)}")
            raise

    def _clear_rounds(self) -> None:
        """ラウンド設定のクリア"""
        for config in self.round_configs:
            config.frame.destroy()
        self.round_configs.clear()

    def _confirm_regulation(self) -> None:
        """レギュレーションの確定"""
        try:
            regulation_data = self._create_regulation_data()

            if not self._validate_regulation_data(regulation_data):
                return

            if not messagebox.askyesno(
                "確認",
                "レギュレーションを確定しますか？\n確定後は変更できなくなります。",
            ):
                return

            # データストアの更新
            self.store.set_state("regulation", regulation_data)
            self.store.set_state("regulation_status", True)

            # 状態の更新
            self.state.is_confirmed = True
            self._disable_inputs()

            event_manager.notify(
                GameEvent(
                    type=EventType.REGULATION_CONFIRMED,
                    data={"regulation": regulation_data},
                    source="regulation_setting",
                )
            )

            messagebox.showinfo("確定", "レギュレーションを確定しました。")
            self.logger.info("Regulation confirmed")

        except Exception as e:
            self.logger.error(f"Error confirming regulation: {str(e)}")
            self._show_error("レギュレーションの確定中にエラーが発生しました。")

    def _validate_regulation_data(self, regulation: Dict) -> bool:
        """レギュレーションデータの検証"""
        try:
            total_players = regulation["total_players"]

            if total_players < APP_SETTINGS["min_players"]:
                self._show_error(
                    f"最低{APP_SETTINGS['min_players']}人のプレイヤーが必要です。"
                )
                return False

            if total_players > APP_SETTINGS["max_players"]:
                self._show_error(
                    f"最大{APP_SETTINGS['max_players']}人までしか設定できません。"
                )
                return False

            # 役職の検証
            if not self._validate_roles(regulation["roles"]):
                return False

            # ラウンド時間の検証
            if not self._validate_round_times(regulation["round_times"]):
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error validating regulation: {str(e)}")
            return False

    def _validate_roles(self, roles: Dict[str, int]) -> bool:
        """役職設定の検証"""
        try:
            # 必須役職のチェック
            if roles.get("werewolf", 0) == 0:
                self._show_error("人狼は最低1人必要です。")
                return False

            if roles.get("villager", 0) == 0:
                self._show_error("村人は最低1人必要です。")
                return False

            # 役職バランスのチェック
            werewolf_count = roles.get("werewolf", 0)
            total_count = sum(roles.values())

            if werewolf_count >= total_count / 2:
                self._show_error("人狼の数が多すぎます。")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error validating roles: {str(e)}")
            return False

    def _validate_round_times(self, round_times: List[Dict]) -> bool:
        """ラウンド時間設定の検証"""
        try:
            if not round_times:
                self._show_error("最低1ラウンドの設定が必要です。")
                return False

            for round_time in round_times:
                if not isinstance(round_time.get("time"), int):
                    self._show_error("無効なラウンド時間設定です。")
                    return False

                if round_time["time"] < 1 or round_time["time"] > 60:
                    self._show_error("ラウンド時間は1〜60分の間で設定してください。")
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Error validating round times: {str(e)}")
            return False

    def _disable_inputs(self) -> None:
        """入力要素の無効化"""
        try:
            for spinbox in self.role_spinboxes.values():
                spinbox.config(state="disabled")

            for config in self.round_configs:
                for child in config.frame.winfo_children():
                    if isinstance(child, (ttk.Spinbox, ttk.Button)):
                        child.config(state="disabled")

        except Exception as e:
            self.logger.error(f"Error disabling inputs: {str(e)}")

    def handle_event(self, event: GameEvent) -> None:
        """イベントハンドラ"""
        try:
            # ウィンドウが存在しない場合は処理をスキップ
            if not hasattr(self, "window") or not self.window.winfo_exists():
                return

            handlers = {
                EventType.GAME_STATE_RESET: self._handle_game_reset,
                EventType.ERROR: self._handle_error,
            }

            handler = handlers.get(event.type)
            if handler:
                handler(event)

        except Exception as e:
            self.logger.error(f"Error handling event {event.type}: {str(e)}")
            self._show_error("イベント処理中にエラーが発生しました。")

    def _handle_game_reset(self, event: GameEvent) -> None:
        """ゲームリセットの処理"""
        try:
            # ウィンドウが存在しない場合は処理をスキップ
            if not hasattr(self, "window") or not self.window.winfo_exists():
                return

            # UIコンポーネントの存在確認をしてから処理
            self._reset_ui_state()
            self.logger.info("Reset regulation setting view")

        except Exception as e:
            self.logger.error(f"Error handling game reset: {str(e)}")

    def _handle_error(self, event: GameEvent) -> None:
        """エラーイベントの処理"""
        error_msg = event.data.get("message", "不明なエラー")
        self.logger.error(f"Error event received: {error_msg}")
        self._show_error(error_msg)

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
        except Exception as e:
            self.logger.error(f"Error destroying window: {str(e)}")
