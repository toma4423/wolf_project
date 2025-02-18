from typing import Dict, Set, Optional, List
import logging
import random
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from .events import GameEvent, EventType, event_manager
from .player import Player, PlayerRole


class GamePhase(Enum):
    """ゲームフェーズの定義"""

    SETUP = "setup"
    DAY_DISCUSSION = "day_discussion"
    DAY_VOTE = "day_vote"
    NIGHT = "night"

    def get_display_name(self) -> str:
        """表示用のフェーズ名を取得"""
        phase_names = {
            self.SETUP: "準備中",
            self.DAY_DISCUSSION: "昼フェーズ（議論）",
            self.DAY_VOTE: "昼フェーズ（投票）",
            self.NIGHT: "夜フェーズ",
        }
        return phase_names.get(self, self.value)


class Team(Enum):
    """チームの定義"""

    VILLAGE = "village"
    WEREWOLF = "werewolf"

    @classmethod
    def get_team_for_role(cls, role: PlayerRole) -> "Team":
        """役職からチームを判定"""
        werewolf_roles = {PlayerRole.WEREWOLF, PlayerRole.MADMAN}
        return cls.WEREWOLF if role in werewolf_roles else cls.VILLAGE


@dataclass
class GameStateSnapshot:
    """ゲーム状態のスナップショット"""

    phase: GamePhase
    round: int
    alive_players: Set[str]
    players: Dict[str, Player]
    timestamp: datetime = field(default_factory=datetime.now)


class GameState:
    """ゲームの状態を管理するクラス"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # 基本状態
        self.players: Dict[str, Player] = {}
        self.alive_players: Set[str] = set()
        self.current_phase: GamePhase = GamePhase.SETUP
        self.current_round: int = 0
        self.regulation: Optional[Dict] = None
        self.game_active: bool = False

        # 確定状態
        self.is_regulation_confirmed: bool = False
        self.is_players_confirmed: bool = False

        # 状態履歴
        self._state_history: List[GameStateSnapshot] = []

        self.logger.info("GameState initialized")

    def add_player(self, player: Player) -> None:
        """プレイヤーの追加"""
        try:
            if player.name in self.players:
                self.logger.warning(f"Player {player.name} already exists")
                return

            self.players[player.name] = player
            if player.is_alive:
                self.alive_players.add(player.name)

            self.is_players_confirmed = False

            event_manager.notify(
                GameEvent(
                    type=EventType.PLAYER_ADDED,
                    data={"player": player.to_dict()},
                    source="game_state",
                )
            )

            self._save_snapshot("player_added")
            self.logger.info(f"Added player: {player.name}")

        except Exception as e:
            self.logger.error(f"Error adding player: {str(e)}")
            raise

    def remove_player(self, player_name: str) -> None:
        """プレイヤーの削除"""
        try:
            if player_name not in self.players:
                self.logger.warning(f"Player {player_name} does not exist")
                return

            player = self.players[player_name]
            del self.players[player_name]
            self.alive_players.discard(player_name)

            event_manager.notify(
                GameEvent(
                    type=EventType.PLAYER_REMOVED,
                    data={"player_name": player_name},
                    source="game_state",
                )
            )

            self._save_snapshot("player_removed")
            self.logger.info(f"Removed player: {player_name}")

        except Exception as e:
            self.logger.error(f"Error removing player: {str(e)}")
            raise

    def kill_player(self, player_name: str) -> bool:
        """プレイヤーを死亡状態にする"""
        try:
            if not self.game_active:
                self.logger.warning("Cannot kill player: Game is not active")
                return False

            if player_name not in self.players:
                return False

            player = self.players[player_name]
            if not player.is_alive:  # 追加：既に死亡している場合は早期リターン
                self.logger.debug(f"Player {player_name} is already dead")
                return False

            player.kill()
            self.alive_players.remove(player_name)

            event_manager.notify(
                GameEvent(
                    type=EventType.PLAYER_DIED,
                    data={
                        "player_name": player_name,
                        "role": player.role.value if player.role else None,
                        "phase": self.current_phase.value,
                        "round": self.current_round,
                    },
                    source="game_state",
                )
            )

            self._save_snapshot("player_killed")
            self._check_game_end_condition()
            return True

        except Exception as e:
            self.logger.error(f"Error killing player: {str(e)}")
            raise

    def change_phase(self, new_phase: GamePhase) -> None:
        """フェーズの変更"""
        try:
            if not self.game_active:
                self.logger.warning("Cannot change phase: Game is not active")
                return

            old_phase = self.current_phase
            self.current_phase = new_phase

            event_manager.notify(
                GameEvent(
                    type=EventType.PHASE_CHANGED,
                    data={
                        "old_phase": old_phase.value,
                        "new_phase": new_phase.value,
                        "round": self.current_round,
                    },
                    source="game_state",
                )
            )

            self._save_snapshot("phase_changed")
            self.logger.info(f"Phase changed to: {new_phase.value}")

        except Exception as e:
            self.logger.error(f"Error changing phase: {str(e)}")
            raise

    def set_regulation(self, regulation: Dict) -> None:
        """レギュレーションの設定"""
        try:
            self.regulation = regulation
            self.is_regulation_confirmed = False

            event_manager.notify(
                GameEvent(
                    type=EventType.REGULATION_UPDATED,
                    data={"regulation": regulation},
                    source="game_state",
                )
            )

            self._save_snapshot("regulation_set")
            self.logger.info("Regulation set")

        except Exception as e:
            self.logger.error(f"Error setting regulation: {str(e)}")
            raise

    def confirm_regulation(self) -> None:
        """レギュレーションの確定"""
        try:
            if not self.regulation:
                raise ValueError("Cannot confirm: No regulation set")

            self.is_regulation_confirmed = True

            event_manager.notify(
                GameEvent(
                    type=EventType.REGULATION_CONFIRMED,
                    data={"regulation": self.regulation},
                    source="game_state",
                )
            )

            self._save_snapshot("regulation_confirmed")
            self.logger.info("Regulation confirmed")

        except Exception as e:
            self.logger.error(f"Error confirming regulation: {str(e)}")
            raise

    def confirm_players(self) -> None:
        """プレイヤー一覧の確定"""
        try:
            if not self.players:
                raise ValueError("Cannot confirm: No players set")

            self.is_players_confirmed = True

            event_manager.notify(
                GameEvent(
                    type=EventType.PLAYERS_CONFIRMED,
                    data={"players": list(self.players.keys())},
                    source="game_state",
                )
            )

            self._save_snapshot("players_confirmed")
            self.logger.info("Players confirmed")

        except Exception as e:
            self.logger.error(f"Error confirming players: {str(e)}")
            raise

    def start_game(self) -> None:
        """ゲーム開始"""
        try:
            if not self.is_regulation_confirmed:
                raise ValueError("Cannot start: Regulation not confirmed")
            if not self.is_players_confirmed:
                raise ValueError("Cannot start: Players not confirmed")
            if len(self.players) != self.regulation.num_players:
                raise ValueError("Cannot start: Player count does not match regulation")

            self.alive_players = set(self.players.keys())
            self.current_round = 1
            self.current_phase = GamePhase.DAY_DISCUSSION
            self.game_active = True

            # 役職の割り当て処理を追加
            self._assign_roles()

            event_manager.notify(
                GameEvent(
                    type=EventType.GAME_STARTED,
                    data={
                        "round": self.current_round,
                        "phase": self.current_phase.value,
                        "player_count": len(self.players),
                    },
                    source="game_state",
                )
            )

            self._save_snapshot("game_started")
            self.logger.info("Game started")

        except Exception as e:
            self.logger.error(f"Error starting game: {str(e)}")
            raise

    def _assign_roles(self) -> None:
        """役職をランダムに割り当てる"""
        try:
            # レギュレーションから役職リストを作成
            roles_to_assign = []
            for role, count in self.regulation.roles.items():
                roles_to_assign.extend([PlayerRole(role)] * count)

            # 役職をシャッフル
            random.shuffle(roles_to_assign)

            # プレイヤーに役職を割り当て
            players_list = list(self.players.values())
            for player, role in zip(players_list, roles_to_assign):
                player.role = role
                # 役職割り当てイベントを発行
                event_manager.notify(
                    GameEvent(
                        type=EventType.PLAYER_ROLE_ASSIGNED,
                        data={"player_name": player.name, "role": role.value},
                        source="game_state",
                    )
                )
                self.logger.info(f"Assigned role {role.value} to player {player.name}")

        except Exception as e:
            self.logger.error(f"Error assigning roles: {str(e)}")
            raise

    def reset(self) -> None:
        """ゲーム状態のリセット"""
        try:
            # 確定状態のみリセット
            self.game_active = False
            self.is_regulation_confirmed = False
            self.is_players_confirmed = False

            # フェーズとラウンドをリセット
            self.current_phase = GamePhase.SETUP
            self.current_round = 0

            # プレイヤー状態のリセット（役職と生存状態のみ）
            for player in self.players.values():
                player.role = None
                player.is_alive = True

            # 生存プレイヤーリストをクリア
            self.alive_players.clear()

            # レギュレーションをクリア
            self.regulation = None

            # 履歴をクリア
            self._state_history.clear()

            self._save_snapshot("game_reset")
            self.logger.info("Game state reset")

        except Exception as e:
            self.logger.error(f"Error resetting game state: {str(e)}")
            raise

    def _validate_player_count(self) -> bool:
        """プレイヤー数のバリデーション"""
        try:
            if not self.regulation or "roles" not in self.regulation:
                return False
            total_roles = sum(self.regulation["roles"].values())
            return total_roles == len(self.players)
        except Exception as e:
            self.logger.error(f"Error validating player count: {str(e)}")
            return False

    def _check_game_end_condition(self) -> None:
        """ゲーム終了条件のチェック"""
        if not self.alive_players:
            return

        try:
            werewolf_count = sum(
                1
                for name in self.alive_players
                if self.players[name].role == PlayerRole.WEREWOLF
            )
            villager_count = len(self.alive_players) - werewolf_count

            # 人狼陣営または村人陣営が全滅した場合
            if werewolf_count >= villager_count or werewolf_count == 0:
                # 終了イベントを通知するが、ゲームは終了させない
                event_manager.notify(
                    GameEvent(
                        type=EventType.GAME_ENDED,
                        data={
                            "winning_team": (
                                Team.WEREWOLF.value
                                if werewolf_count >= villager_count
                                else Team.VILLAGE.value
                            ),
                            "final_round": self.current_round,
                            "werewolf_count": werewolf_count,
                            "villager_count": villager_count,
                        },
                        source="game_state",
                    )
                )
                self.logger.info(
                    f"Game end condition met: {'Werewolf' if werewolf_count >= villager_count else 'Village'} team wins"
                )

        except Exception as e:
            self.logger.error(f"Error checking game end condition: {str(e)}")
            raise

    def _end_game(self, winning_team: Team) -> None:
        """ゲームの終了"""
        try:
            event_manager.notify(
                GameEvent(
                    type=EventType.GAME_ENDED,
                    data={
                        "winning_team": winning_team.value,
                        "final_round": self.current_round,
                    },
                    source="game_state",
                )
            )

            self.game_active = False
            self._save_snapshot("game_ended")
            self.logger.info(f"Game ended. Winner: {winning_team.value}")

        except Exception as e:
            self.logger.error(f"Error ending game: {str(e)}")
            raise

    def _save_snapshot(self, reason: str) -> None:
        """現在の状態のスナップショットを保存"""
        try:
            snapshot = GameStateSnapshot(
                phase=self.current_phase,
                round=self.current_round,
                alive_players=self.alive_players.copy(),
                players={
                    name: player.to_dict() for name, player in self.players.items()
                },
            )
            self._state_history.append(snapshot)
            self.logger.debug(f"State snapshot saved: {reason}")
        except Exception as e:
            self.logger.error(f"Error saving state snapshot: {str(e)}")

    def get_team_counts(self) -> Dict[str, int]:
        """各陣営の生存者数を取得"""
        try:
            werewolf_count = sum(
                1
                for name in self.alive_players
                if self.players[name].role == PlayerRole.WEREWOLF
            )
            return {
                Team.VILLAGE.value: len(self.alive_players) - werewolf_count,
                Team.WEREWOLF.value: werewolf_count,
            }
        except Exception as e:
            self.logger.error(f"Error getting team counts: {str(e)}")
            raise

    def get_alive_players_list(self) -> List[str]:
        """生存プレイヤーのリストを取得"""
        return sorted(list(self.alive_players))

    def next_round(self) -> None:
        """次のラウンドへ進む"""
        try:
            self.current_round += 1
            self.current_phase = GamePhase.DAY_DISCUSSION

            event_manager.notify(
                GameEvent(
                    type=EventType.ROUND_CHANGED,
                    data={
                        "round": self.current_round,
                        "phase": self.current_phase.value,
                    },
                    source="game_state",
                )
            )

            self._save_snapshot("round_changed")
            self.logger.info(f"Advanced to round {self.current_round}")

        except Exception as e:
            self.logger.error(f"Error advancing round: {str(e)}")
            raise

    def get_player_by_name(self, player_name: str) -> Optional[Player]:
        """プレイヤー名からプレイヤーを取得"""
        try:
            return self.players.get(player_name)
        except Exception as e:
            self.logger.error(f"Error getting player by name: {str(e)}")
            raise
