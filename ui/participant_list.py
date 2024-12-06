from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
import re
import logging
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from config.settings import APP_SETTINGS, ROLE_SETTINGS
from store.global_data_store import GlobalDataStore
from core.player import Player, PlayerRole
from core.events import EventType, GameEvent, event_manager


@dataclass
class ParticipantListState:
    """参加者リストの状態を管理するデータクラス"""

    participants: List[Player] = field(default_factory=list)
    non_participants: List[Player] = field(default_factory=list)
    is_confirmed: bool = False
    last_update: datetime = field(default_factory=datetime.now)


class ParticipantListWindow:
    """参加者一覧ウィンドウ"""

    def __init__(self, parent: tk.Tk, store: GlobalDataStore):
        self.logger = logging.getLogger(__name__)

        # 基本初期化
        self.parent = parent
        self.store = store
        self.window = tk.Toplevel(parent)
        self.window.title("参加者一覧")
        self.window.geometry(
            f"{APP_SETTINGS['default_window_size']['participant'][0]}x"
            f"{APP_SETTINGS['default_window_size']['participant'][1]}"
        )

        # 状態管理
        self.state = ParticipantListState()

        # UIコンポーネント参照の初期化
        self.participant_tree: Optional[ttk.Treeview] = None
        self.non_participant_tree: Optional[ttk.Treeview] = None
        self.confirm_button: Optional[ttk.Button] = None
        self.context_menus: Dict[str, tk.Menu] = {}

        # UIの初期化
        self._init_ui()
        self._create_context_menus()

        # イベントマネージャーへの登録
        event_manager.subscribe_all(self)
        self.logger.info("ParticipantListWindow initialized")

    def _init_ui(self):
        """UIの初期化"""
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(expand=True, fill="both")

        # 参加者リスト
        participants_frame = ttk.LabelFrame(
            main_frame, text="ゲーム参加者", padding="5"
        )
        participants_frame.pack(fill="both", expand=True, pady=5)

        self.participant_tree = self._create_tree(participants_frame)
        self.participant_tree.pack(fill="both", expand=True)

        # 不参加者リスト
        non_participants_frame = ttk.LabelFrame(
            main_frame, text="不参加者", padding="5"
        )
        non_participants_frame.pack(fill="both", expand=True, pady=5)

        self.non_participant_tree = self._create_tree(non_participants_frame)
        self.non_participant_tree.pack(fill="both", expand=True)

        # ボタンエリア
        self._create_button_area(main_frame)

    def _create_tree(self, parent: ttk.Frame) -> ttk.Treeview:
        """Treeviewの作成"""
        columns = ("number", "name", "role", "status")
        tree = ttk.Treeview(parent, columns=columns, show="headings")

        # スクロールバーの追加
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # 列の設定
        tree.heading("number", text="番号")
        tree.heading("name", text="名前")
        tree.heading("role", text="役職")
        tree.heading("status", text="ステータス")

        # 列幅の動的設定用関数
        def configure_column_widths(event=None):
            if not tree.winfo_exists():
                return

            tree_width = tree.winfo_width()
            if tree_width > 1:  # 有効な幅の場合のみ処理
                scrollbar_width = 20
                available_width = max(tree_width - scrollbar_width, 380)  # 最小幅を確保

                # 列幅の比率配分
                widths = {
                    "number": 0.15,  # 15%
                    "name": 0.35,  # 35%
                    "role": 0.25,  # 25%
                    "status": 0.25,  # 25%
                }

                # 各列の幅を設定
                for column, ratio in widths.items():
                    width = int(available_width * ratio)
                    tree.column(column, width=width, minwidth=int(width * 0.8))

        # ウィンドウサイズ変更時のイベントバインド
        tree.bind("<Configure>", configure_column_widths)

        # 初期サイズの設定
        tree.update_idletasks()
        configure_column_widths()

        # イベントバインド
        tree.bind("<Button-3>", self._show_context_menu)
        tree.bind("<Button-1>", self._on_tree_click)

        return tree

    def _create_button_area(self, parent: ttk.Frame):
        """ボタンエリアの作成"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill="x", pady=5)

        # 左側のボタン
        left_button_frame = ttk.Frame(button_frame)
        left_button_frame.pack(side="left", fill="x", expand=True)

        ttk.Button(
            left_button_frame,
            text="プレイヤーリスト読み込み",
            command=self._show_player_input_dialog,
        ).pack(side="left", padx=5)

        self.confirm_button = ttk.Button(
            left_button_frame,
            text="参加者リストを確定",
            command=self._confirm_participants,
            state="normal",
        )
        self.confirm_button.pack(side="left", padx=5)

        # 右側のボタン
        right_button_frame = ttk.Frame(button_frame)
        right_button_frame.pack(side="right")

        ttk.Button(right_button_frame, text="ヘルプ", command=self._show_help).pack(
            side="right", padx=5
        )

    def _create_context_menus(self):
        """右クリックメニューの作成"""
        # 参加者リスト用メニュー
        self.context_menus["participant"] = tk.Menu(self.window, tearoff=0)
        self.context_menus["participant"].add_command(
            label="不参加リストへ移動",
            command=lambda: self._move_player("to_non_participant"),
        )
        self.context_menus["participant"].add_command(
            label="番号/名前を編集", command=self._edit_player
        )

        # 不参加者リスト用メニュー
        self.context_menus["non_participant"] = tk.Menu(self.window, tearoff=0)
        self.context_menus["non_participant"].add_command(
            label="参加リストへ移動",
            command=lambda: self._move_player("to_participant"),
        )
        self.context_menus["non_participant"].add_command(
            label="番号/名前を編集", command=self._edit_player
        )

    def _show_context_menu(self, event: tk.Event):
        """右クリックメニューの表示"""
        if self.state.is_confirmed:
            return

        tree = event.widget
        item = tree.identify_row(event.y)
        if not item:
            return

        tree.selection_set(item)
        menu_type = (
            "participant" if tree == self.participant_tree else "non_participant"
        )
        self.context_menus[menu_type].post(event.x_root, event.y_root)

    def _move_player(self, direction: str) -> None:
        """プレイヤーのリスト間移動"""
        if self.state.is_confirmed:
            self._show_error("参加者リストは確定済みのため変更できません。")
            return

        try:
            source_tree, dest_tree = self._get_move_trees(direction)
            selection = source_tree.selection()
            if not selection:
                return

            moved_players = []
            for item in selection:
                values = source_tree.item(item)["values"]
                player = self._find_player_by_values(values, direction)
                if player:
                    self._perform_player_move(player, direction)
                    moved_players.append(player.name)

            self._update_trees()
            self._notify_player_movement(direction, moved_players)

        except Exception as e:
            self.logger.error(f"Error moving players: {str(e)}")
            self._show_error("プレイヤーの移動中にエラーが発生しました。")

    def _get_move_trees(self, direction: str) -> tuple[ttk.Treeview, ttk.Treeview]:
        """移動元と移動先のツリーを取得"""
        if direction == "to_non_participant":
            return self.participant_tree, self.non_participant_tree
        return self.non_participant_tree, self.participant_tree

    def _find_player_by_values(self, values: list, direction: str) -> Optional[Player]:
        """ツリーの値からプレイヤーを検索"""
        source_list = (
            self.state.participants
            if direction == "to_non_participant"
            else self.state.non_participants
        )
        return next(
            (
                p
                for p in source_list
                if str(p.number) == str(values[0]) and p.name == values[1]
            ),
            None,
        )

    def _perform_player_move(self, player: Player, direction: str) -> None:
        """プレイヤーの移動を実行"""
        if direction == "to_non_participant":
            self.state.participants.remove(player)
            self.state.non_participants.append(player)
        else:
            self.state.non_participants.remove(player)
            self.state.participants.append(player)

    def _notify_player_movement(self, direction: str, moved_players: List[str]) -> None:
        """プレイヤー移動のイベント通知"""
        if not self.state.is_confirmed:
            event_manager.notify(
                GameEvent(
                    type=EventType.PLAYERS_MOVED,
                    data={"direction": direction, "players": moved_players},
                    source="participant_list",
                )
            )
            self.logger.info(f"Players moved {direction}: {moved_players}")

    def _show_player_input_dialog(self) -> None:
        """プレイヤーリスト入力ダイアログの表示"""
        if self.state.is_confirmed:
            self._show_error("参加者リストは確定済みのため追加できません。")
            return

        dialog = tk.Toplevel(self.window)
        dialog.title("プレイヤーリスト入力")
        dialog.geometry("400x300")

        ttk.Label(
            dialog, text="プレイヤーリストを入力してください。\n形式: 番号.名前[/別名]"
        ).pack(pady=5)

        text = tk.Text(dialog, height=10)
        text.pack(fill="both", expand=True, padx=5, pady=5)

        ttk.Button(
            dialog,
            text="登録",
            command=lambda: self._process_player_input(text.get("1.0", tk.END).strip()),
        ).pack(pady=5)

    def _process_player_input(self, content: str) -> None:
        """プレイヤーリストの処理"""
        if not content:
            return

        try:
            new_participants = []
            new_non_participants = []

            for line in content.split("\n"):
                if not line.strip():
                    continue

                match = re.match(r"(\d+)\.(.+)", line.strip())
                if not match:
                    continue

                number, names = match.groups()
                name_list = [n.strip() for n in names.split("/")]

                # メインプレイヤーの作成
                main_player = Player(number=int(number), name=name_list[0])
                new_participants.append(main_player)

                # 別名プレイヤーの作成
                for alt_name in name_list[1:]:
                    non_participant = Player(number=int(number), name=alt_name)
                    new_non_participants.append(non_participant)

            self._update_player_lists(new_participants, new_non_participants)

        except Exception as e:
            self.logger.error(f"Error processing player input: {str(e)}")
            self._show_error("プレイヤーリストの処理中にエラーが発生しました。")

    def _update_player_lists(
        self, new_participants: List[Player], new_non_participants: List[Player]
    ) -> None:
        """プレイヤーリストの更新"""
        try:
            # 状態の更新
            self.state.participants = new_participants
            self.state.non_participants = new_non_participants
            self.state.last_update = datetime.now()

            # UIの更新
            self._update_trees()

            # データストアの更新（確定前のみ）
            if not self.state.is_confirmed:
                self.store.set_state("players", self.state.participants)

            # イベント通知
            event_manager.notify(
                GameEvent(
                    type=EventType.PLAYERS_UPDATED,
                    data={
                        "participant_count": len(self.state.participants),
                        "non_participant_count": len(self.state.non_participants),
                    },
                    source="participant_list",
                )
            )

            self.logger.info(
                f"Players updated: {len(self.state.participants)} participants, "
                f"{len(self.state.non_participants)} non-participants"
            )

        except Exception as e:
            self.logger.error(f"Error updating player lists: {str(e)}")
            raise

    def _confirm_participants(self) -> None:
        """参加者リストの確定処理"""
        if not self.state.participants:
            self._show_error("参加者が登録されていません。")
            return

        if not messagebox.askyesno(
            "確認",
            "参加者リストを確定しますか？\n確定後は参加者の追加・削除・移動ができなくなります。",
        ):
            return

        try:
            self.state.is_confirmed = True
            self.confirm_button.config(state="disabled")

            # メニュー項目の無効化
            self._disable_context_menus()

            # データストアの更新
            self.store.set_state("players", self.state.participants)
            self.store.set_state("players_status", True)

            event_manager.notify(
                GameEvent(
                    type=EventType.PLAYERS_CONFIRMED,
                    data={"player_count": len(self.state.participants)},
                    source="participant_list",
                )
            )

            messagebox.showinfo("通知", "参加者リストを確定しました。")
            self.logger.info(
                f"Player list confirmed with {len(self.state.participants)} players"
            )

        except Exception as e:
            self.logger.error(f"Error confirming participants: {str(e)}")
            self._show_error("参加者リストの確定中にエラーが発生しました。")

    def _update_trees(self) -> None:
        """Treeviewの表示更新"""
        try:
            if not self.window.winfo_exists():
                return

            self._update_participant_tree()
            self._update_non_participant_tree()

        except tk.TclError as e:
            self.logger.warning(f"UI component already destroyed: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error updating trees: {str(e)}")

    def _update_participant_tree(self) -> None:
        """参加者ツリーの更新"""
        if (
            not hasattr(self, "participant_tree")
            or not self.participant_tree.winfo_exists()
        ):
            return

        self.participant_tree.delete(*self.participant_tree.get_children())
        for player in sorted(self.state.participants, key=lambda x: x.number):
            role_display = ""
            if player.role and hasattr(player.role, "get_display_name"):
                role_display = player.role.get_display_name()

            self.participant_tree.insert(
                "",
                tk.END,
                values=(
                    player.number,
                    player.name,
                    role_display,
                    "生存" if player.is_alive else "死亡",
                ),
            )

    def _update_non_participant_tree(self) -> None:
        """不参加者ツリーの更新"""
        if (
            not hasattr(self, "non_participant_tree")
            or not self.non_participant_tree.winfo_exists()
        ):
            return

        self.non_participant_tree.delete(*self.non_participant_tree.get_children())
        for player in sorted(self.state.non_participants, key=lambda x: x.number):
            self.non_participant_tree.insert(
                "", tk.END, values=(player.number, player.name, "", "")
            )

    def handle_event(self, event: GameEvent) -> None:
        """イベントハンドラ"""
        try:
            handlers = {
                EventType.GAME_STATE_RESET: self._handle_game_reset,
                EventType.PLAYER_ROLE_ASSIGNED: self._handle_role_assigned,
                EventType.PLAYER_DIED: self._handle_player_death,
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

    def _handle_game_reset(self, event: GameEvent) -> None:
        """ゲームリセットの処理"""
        try:
            if not hasattr(self, "window") or not self.window.winfo_exists():
                return

            # プレイヤーリストは保持したまま、確定状態のみリセット
            self.state.is_confirmed = False

            # UIの更新
            if hasattr(self, "confirm_button") and self.confirm_button.winfo_exists():
                self.confirm_button.config(state="normal")

            self._enable_context_menus()
            self._update_trees()
            self.logger.info("Reset participant list view")

        except Exception as e:
            self.logger.error(f"Error handling game reset: {str(e)}")

    def _handle_role_assigned(self, event: GameEvent) -> None:
        """役職割り当ての処理"""
        player_name = event.data.get("player_name")
        role = event.data.get("role")

        for player in self.state.participants:
            if player.name == player_name:
                player.role = PlayerRole(role)
                break

        self._update_trees()
        self.logger.info(f"Updated view for role assignment: {player_name}")

    def _handle_player_death(self, event: GameEvent) -> None:
        """プレイヤー死亡の処理"""
        player_name = event.data.get("player_name")
        for player in self.state.participants:
            if player.name == player_name:
                player.is_alive = False
                break

        self._update_trees()
        self.logger.info(f"Updated view for player death: {player_name}")

    def _handle_game_state_update(self, event: GameEvent) -> None:
        """ゲーム状態更新の処理"""
        self._sync_with_game_state()
        self._update_trees()
        self.logger.info("Updated view from game state")

    def _handle_error(self, event: GameEvent) -> None:
        """エラーイベントの処理"""
        error_msg = event.data.get("message", "不明なエラー")
        self.logger.error(f"Error event received: {error_msg}")
        self._show_error(error_msg)

    def _sync_with_game_state(self) -> None:
        """ゲーム状態との同期"""
        try:
            game_state = self.store.game_state

            # プレイヤー情報の同期
            for player in self.state.participants:
                if player.name in game_state.players:
                    game_player = game_state.players[player.name]
                    player.role = game_player.role
                    player.is_alive = game_player.is_alive

            # 確定状態の同期
            if game_state.game_active:
                self.state.is_confirmed = True
                self.confirm_button.config(state="disabled")
                self._disable_context_menus()

        except Exception as e:
            self.logger.error(f"Error syncing with game state: {str(e)}")
            raise

    def _show_error(self, message: str) -> None:
        """エラーメッセージの表示"""
        self.logger.error(message)
        messagebox.showerror("エラー", message)

    def _disable_context_menus(self) -> None:
        """コンテキストメニューの無効化"""
        for menu in self.context_menus.values():
            for index in range(menu.index("end") + 1):
                menu.entryconfigure(index, state="disabled")

    def _enable_context_menus(self) -> None:
        """コンテキストメニューの有効化"""
        for menu in self.context_menus.values():
            for index in range(menu.index("end") + 1):
                menu.entryconfigure(index, state="normal")

    def show(self) -> None:
        """ウィンドウを表示"""
        self.window.deiconify()
        self._update_trees()

    def hide(self) -> None:
        """ウィンドウを非表示"""
        self.window.withdraw()

    def destroy(self) -> None:
        """ウィンドウの破棄"""
        try:
            if hasattr(self, "window"):
                self.window.destroy()
                event_manager.unsubscribe_all(self)
        except Exception as e:
            self.logger.error(f"Error destroying window: {str(e)}")

    def _on_tree_click(self, event: tk.Event) -> None:
        """ツリーのクリックイベントハンドラ"""
        try:
            tree = event.widget
            item = tree.identify_row(event.y)
            if item:
                tree.selection_set(item)
        except Exception as e:
            self.logger.error(f"Error handling tree click: {str(e)}")

    def _show_help(self) -> None:
        """ヘルプダイアログの表示"""
        try:
            help_text = """参加者一覧の使い方：

    1. プレイヤーの追加
    - 「プレイヤーリスト読み込み」ボタンからプレイヤーを追加できます
    - 形式：番号.名前[/別名]

    2. プレイヤーの管理
    - 右クリックで参加/不参加の切り替えができます
    - プレイヤーの編集も右クリックメニューから可能です

    3. リストの確定
    - 「参加者リストを確定」ボタンで参加者を確定します
    - 確定後は変更できなくなりますのでご注意ください"""

            messagebox.showinfo("ヘルプ", help_text)

        except Exception as e:
            self.logger.error(f"Error showing help: {str(e)}")
            self._show_error("ヘルプの表示中にエラーが発生しました。")

    def _edit_player(self) -> None:
        """プレイヤーの編集ダイアログを表示"""
        try:
            if self.state.is_confirmed:
                self._show_error("参加者リストは確定済みのため編集できません。")
                return

            # 選択されているツリーとアイテムの取得
            tree = None
            if self.participant_tree.selection():
                tree = self.participant_tree
            elif self.non_participant_tree.selection():
                tree = self.non_participant_tree

            if not tree or not tree.selection():
                self._show_error("編集するプレイヤーを選択してください。")
                return

            # 現在の値を取得
            item = tree.selection()[0]
            current_values = tree.item(item)["values"]
            if not current_values:
                return

            # 編集ダイアログの作成
            dialog = tk.Toplevel(self.window)
            dialog.title("プレイヤー編集")
            dialog.geometry("300x150")
            dialog.transient(self.window)
            dialog.grab_set()

            ttk.Label(dialog, text="番号:").grid(row=0, column=0, padx=5, pady=5)
            number_var = tk.StringVar(value=str(current_values[0]))
            number_entry = ttk.Entry(dialog, textvariable=number_var)
            number_entry.grid(row=0, column=1, padx=5, pady=5)

            ttk.Label(dialog, text="名前:").grid(row=1, column=0, padx=5, pady=5)
            name_var = tk.StringVar(value=current_values[1])
            name_entry = ttk.Entry(dialog, textvariable=name_var)
            name_entry.grid(row=1, column=1, padx=5, pady=5)

            def validate_and_update():
                try:
                    new_number = int(number_var.get())
                    new_name = name_var.get().strip()

                    if not new_name:
                        raise ValueError("名前を入力してください。")

                    # プレイヤーの更新
                    players = (
                        self.state.participants
                        if tree == self.participant_tree
                        else self.state.non_participants
                    )
                    player = self._find_player_by_values(
                        current_values,
                        (
                            "to_non_participant"
                            if tree == self.participant_tree
                            else "to_participant"
                        ),
                    )

                    if player:
                        player.number = new_number
                        player.name = new_name
                        self._update_trees()

                        # イベント通知
                        event_manager.notify(
                            GameEvent(
                                type=EventType.PLAYER_UPDATED,
                                data={
                                    "old_number": current_values[0],
                                    "old_name": current_values[1],
                                    "new_number": new_number,
                                    "new_name": new_name,
                                },
                                source="participant_list",
                            )
                        )

                    dialog.destroy()

                except ValueError as e:
                    self._show_error(str(e))
                except Exception as e:
                    self.logger.error(f"Error updating player: {str(e)}")
                    self._show_error("プレイヤーの更新中にエラーが発生しました。")

            ttk.Button(dialog, text="更新", command=validate_and_update).grid(
                row=2, column=0, columnspan=2, pady=20
            )

        except Exception as e:
            self.logger.error(f"Error showing edit dialog: {str(e)}")
            self._show_error("編集ダイアログの表示中にエラーが発生しました。")
