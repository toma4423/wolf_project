from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import logging

from config.settings import APP_SETTINGS
from store.global_data_store import GlobalDataStore
from core.events import EventType, GameEvent, event_manager
from core.game_state import GamePhase
from core.player import Player


@dataclass
class VoteStatus:
    """投票状態を管理するデータクラス"""

    player: Player
    has_voted: bool = False
    vote_time: Optional[datetime] = None
    vote_target: Optional[str] = None


@dataclass
class VoteManagerState:
    """投票管理の状態を管理するデータクラス"""

    vote_statuses: Dict[str, VoteStatus] = field(default_factory=dict)
    phase: GamePhase = GamePhase.SETUP
    round: int = 0
    is_voting_complete: bool = False
    last_update: datetime = field(default_factory=datetime.now)


class VoteManagerWindow:
    """投票管理ウィンドウ"""

    def __init__(self, parent: tk.Tk, store: GlobalDataStore):
        self.logger = logging.getLogger(__name__)

        # 基本初期化
        self.parent = parent
        self.store = store
        self.window = tk.Toplevel(parent)
        self.window.title("投票管理")
        self.window.geometry(
            f"{APP_SETTINGS['default_window_size']['vote_manager'][0]}x"
            f"{APP_SETTINGS['default_window_size']['vote_manager'][1]}"
        )

        # 状態管理
        self.state = VoteManagerState()

        # UI要素の参照
        self.remaining_votes_label: Optional[ttk.Label] = None
        self.scrollable_frame: Optional[ttk.Frame] = None
        self.vote_vars: Dict[str, tk.BooleanVar] = {}

        # UIの初期化
        self._init_ui()

        # 初期データの設定
        self._initialize_data()

        # イベントマネージャーへの登録
        event_manager.subscribe_all(self)
        self.logger.info("VoteManagerWindow initialized")

    def _init_ui(self) -> None:
        """UIの初期化"""
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(expand=True, fill="both")

        # 未投票者数表示
        self.remaining_votes_label = ttk.Label(
            main_frame, text="未投票プレイヤー: 0人", font=("Helvetica", 12, "bold")
        )
        self.remaining_votes_label.pack(fill="x", pady=(0, 10))

        # 生存者リスト表示用フレーム
        self._create_player_list_frame(main_frame)

    def _create_player_list_frame(self, parent: ttk.Frame) -> None:
        """プレイヤーリスト表示フレームの作成"""
        list_frame = ttk.LabelFrame(parent, text="生存者リスト", padding="5")
        list_frame.pack(fill="both", expand=True)

        # スクロール可能なキャンバスの作成
        canvas = tk.Canvas(list_frame)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # パッキング
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # マウスホイールでのスクロール設定
        canvas.bind_all(
            "<MouseWheel>",
            lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"),
        )

    def _initialize_data(self) -> None:
        """初期データの取得と表示"""
        try:
            game_state = self.store.game_state
            alive_players = [
                player for player in game_state.players.values() if player.is_alive
            ]

            # 番号でソート
            alive_players.sort(key=lambda x: x.number)

            # 投票状態の初期化
            self.state.vote_statuses = {
                player.name: VoteStatus(player=player) for player in alive_players
            }

            # UI更新
            self._update_player_list()
            self.logger.info(
                f"Vote manager initialized with {len(alive_players)} players"
            )

        except Exception as e:
            self.logger.error(f"Error initializing vote data: {str(e)}")
            self._show_error("データの初期化中にエラーが発生しました。")

    def _update_player_list(self) -> None:
        """プレイヤーリストの表示更新"""
        try:
            # 既存の項目をクリア
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()

            self.vote_vars.clear()

            # プレイヤーごとの表示項目作成
            for player_name, status in self.state.vote_statuses.items():
                self._create_player_row(status)

            self._update_remaining_votes()
            self.logger.debug("Player list updated in vote manager")

        except Exception as e:
            self.logger.error(f"Error updating player list: {str(e)}")
            self._show_error("プレイヤーリストの更新中にエラーが発生しました。")

    def _create_player_row(self, status: VoteStatus) -> None:
        """プレイヤー行の作成"""
        frame = ttk.Frame(self.scrollable_frame)
        frame.pack(fill="x", pady=2)

        # 番号とプレイヤー名
        ttk.Label(frame, text=f"[{status.player.number:>3}]", width=6).pack(
            side="left", padx=5
        )

        ttk.Label(frame, text=status.player.name, width=20).pack(side="left", padx=5)

        # 投票チェックボックス
        var = tk.BooleanVar(value=status.has_voted)
        self.vote_vars[status.player.name] = var

        ttk.Checkbutton(
            frame,
            variable=var,
            command=lambda p=status.player: self._handle_vote_change(p),
        ).pack(side="right", padx=5)

    def _handle_vote_change(self, player: Player) -> None:
        """投票状態変更の処理"""
        try:
            var = self.vote_vars[player.name]
            status = self.state.vote_statuses[player.name]

            # 状態の更新
            status.has_voted = var.get()
            status.vote_time = datetime.now() if var.get() else None

            self._update_remaining_votes()

            # イベント通知
            event_manager.notify(
                GameEvent(
                    type=EventType.VOTE_RECORDED,
                    data={
                        "player_name": player.name,
                        "has_voted": var.get(),
                        "phase": self.state.phase.value,
                        "round": self.state.round,
                    },
                    source="vote_manager",
                )
            )

            self.logger.info(f"Vote status updated for {player.name}: {var.get()}")

        except Exception as e:
            self.logger.error(f"Error handling vote change: {str(e)}")
            self._show_error("投票状態の更新中にエラーが発生しました。")

    def _update_remaining_votes(self) -> None:
        """未投票者数の更新"""
        try:
            # 未投票者数の計算
            remaining = sum(
                1
                for status in self.state.vote_statuses.values()
                if not status.has_voted
            )

            # ラベルの更新
            self.remaining_votes_label.config(text=f"未投票プレイヤー: {remaining}人")

            # 投票完了時の処理
            if remaining == 0 and not self.state.is_voting_complete:
                self._handle_voting_complete()

            # 色の更新
            self.remaining_votes_label.config(
                foreground="green" if remaining == 0 else "black"
            )

        except Exception as e:
            self.logger.error(f"Error updating remaining votes: {str(e)}")
            self._show_error("未投票者数の更新中にエラーが発生しました。")

    def _handle_voting_complete(self) -> None:
        """投票完了時の処理"""
        try:
            self.state.is_voting_complete = True

            event_manager.notify(
                GameEvent(
                    type=EventType.VOTING_COMPLETED,
                    data={
                        "phase": self.state.phase.value,
                        "round": self.state.round,
                        "vote_results": self._get_vote_summary(),
                    },
                    source="vote_manager",
                )
            )

            self.logger.info("Voting completed")

        except Exception as e:
            self.logger.error(f"Error handling voting completion: {str(e)}")
            self._show_error("投票完了処理中にエラーが発生しました。")

    def _get_vote_summary(self) -> Dict:
        """投票結果のサマリーを取得"""
        return {
            player_name: {
                "vote_time": status.vote_time.isoformat() if status.vote_time else None,
                "vote_target": status.vote_target,
            }
            for player_name, status in self.state.vote_statuses.items()
        }

    def handle_event(self, event: GameEvent) -> None:
        """イベントハンドラ"""
        try:
            handlers = {
                EventType.PLAYER_DIED: self._handle_player_death,
                EventType.PHASE_CHANGED: self._handle_phase_change,
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

    def _handle_player_death(self, event: GameEvent) -> None:
        """プレイヤー死亡イベントの処理"""
        try:
            player_name = event.data.get("player_name")
            if player_name in self.state.vote_statuses:
                self._initialize_data()  # 生存者リストの再構築
            self.logger.info(f"Updated vote manager for player death: {player_name}")
        except Exception as e:
            self.logger.error(f"Error handling player death: {str(e)}")
            raise

    def _handle_phase_change(self, event: GameEvent) -> None:
        """フェーズ変更イベントの処理"""
        try:
            new_phase = GamePhase(event.data.get("new_phase"))
            if new_phase == GamePhase.DAY_DISCUSSION:
                self._reset_votes()
            self.state.phase = new_phase
            self.logger.info(f"Phase changed to: {new_phase.value}")
        except Exception as e:
            self.logger.error(f"Error handling phase change: {str(e)}")
            raise

    def _handle_game_state_update(self, event: GameEvent) -> None:
        """ゲーム状態更新イベントの処理"""
        try:
            self._initialize_data()
            self.logger.info("Vote manager updated from game state")
        except Exception as e:
            self.logger.error(f"Error handling game state update: {str(e)}")
            raise

    def _handle_error(self, event: GameEvent) -> None:
        """エラーイベントの処理"""
        error_msg = event.data.get("message", "不明なエラー")
        self.logger.error(f"Error event received: {error_msg}")
        self._show_error(error_msg)

    def _reset_votes(self) -> None:
        """投票状態のリセット"""
        try:
            # 状態のリセット
            for status in self.state.vote_statuses.values():
                status.has_voted = False
                status.vote_time = None
                status.vote_target = None

            # UI変数のリセット
            for var in self.vote_vars.values():
                var.set(False)

            self.state.is_voting_complete = False
            self._update_remaining_votes()

            event_manager.notify(
                GameEvent(
                    type=EventType.VOTE_RESET,
                    data={"phase": self.state.phase.value, "round": self.state.round},
                    source="vote_manager",
                )
            )

            self.logger.info("Vote status reset")

        except Exception as e:
            self.logger.error(f"Error resetting votes: {str(e)}")
            self._show_error("投票状態のリセット中にエラーが発生しました。")

    def _sync_with_game_state(self) -> None:
        """ゲーム状態との同期"""
        try:
            game_state = self.store.game_state
            self.state.phase = game_state.current_phase
            self.state.round = game_state.current_round

            # 生存プレイヤーリストの更新
            current_players = {
                name: player
                for name, player in game_state.players.items()
                if player.is_alive
            }

            # 投票状態の更新
            updated_statuses = {}
            for name, player in current_players.items():
                if name in self.state.vote_statuses:
                    # 既存の投票状態を保持
                    updated_statuses[name] = self.state.vote_statuses[name]
                else:
                    # 新規プレイヤーの状態を作成
                    updated_statuses[name] = VoteStatus(player=player)

            self.state.vote_statuses = updated_statuses
            self._update_player_list()

            self.logger.info("Synchronized with game state")

        except Exception as e:
            self.logger.error(f"Error syncing with game state: {str(e)}")
            raise

    def _show_error(self, message: str) -> None:
        """エラーメッセージの表示"""
        self.logger.error(message)
        messagebox.showerror("エラー", message)

    def show(self) -> None:
        """ウィンドウを表示"""
        self.window.deiconify()
        self._reset_votes()
        self.logger.info("Vote manager window shown")

    def hide(self) -> None:
        """ウィンドウを非表示"""
        self.window.withdraw()
        self.logger.info("Vote manager window hidden")

    def destroy(self) -> None:
        """ウィンドウの破棄"""
        try:
            if hasattr(self, "window"):
                self.window.destroy()
                event_manager.unsubscribe_all(self)
                self.logger.info("Vote manager window destroyed")
        except Exception as e:
            self.logger.error(f"Error destroying window: {str(e)}")

    def get_vote_status_summary(self) -> Dict:
        """投票状態のサマリーを取得（デバッグ用）"""
        return {
            player_name: {
                "has_voted": status.has_voted,
                "vote_time": status.vote_time.isoformat() if status.vote_time else None,
                "vote_target": status.vote_target,
            }
            for player_name, status in self.state.vote_statuses.items()
        }
