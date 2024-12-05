from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import logging
from enum import Enum
from datetime import datetime

from .events import GameEvent, EventType, event_manager


class PlayerRole(Enum):
    """プレイヤーの役職を定義"""

    VILLAGER = "villager"
    WEREWOLF = "werewolf"
    GUARD = "guard"
    SEER = "seer"
    MEDIUM = "medium"
    MADMAN = "madman"

    def get_display_name(self) -> str:
        """表示用の役職名を取得"""
        display_names = {
            self.VILLAGER: "村人",
            self.WEREWOLF: "人狼",
            self.GUARD: "狩人",
            self.SEER: "占い師",
            self.MEDIUM: "霊能者",
            self.MADMAN: "狂人",
        }
        return display_names.get(self, self.value)


@dataclass
class PlayerStatus:
    """プレイヤーの状態変更履歴を管理"""

    is_alive: bool
    role: Optional[PlayerRole]
    timestamp: datetime = field(default_factory=datetime.now)
    reason: str = ""


@dataclass
class Player:
    """プレイヤーを表すクラス"""

    number: int
    name: str
    role: Optional[PlayerRole] = None
    is_alive: bool = True
    _status_history: list = field(default_factory=list)
    _logger: logging.Logger = field(init=False)

    def __post_init__(self):
        """初期化後の処理"""
        self._logger = logging.getLogger(__name__)
        self._add_status_record("初期化")

    def assign_role(self, role: str) -> None:
        """役職の割り当て"""
        try:
            new_role = PlayerRole(role)
            old_role = self.role
            self.role = new_role

            event_manager.notify(
                GameEvent(
                    type=EventType.PLAYER_ROLE_ASSIGNED,
                    data={
                        "player_name": self.name,
                        "role": new_role.value,
                        "old_role": old_role.value if old_role else None,
                        "number": self.number,
                    },
                    source="player",
                )
            )

            self._add_status_record(f"役職割り当て: {new_role.get_display_name()}")
            self._logger.info(f"Role assigned to player {self.name}: {new_role.value}")

        except ValueError as e:
            self._logger.error(
                f"Invalid role assignment for player {self.name}: {role}"
            )
            raise ValueError(f"Invalid role: {role}") from e
        except Exception as e:
            self._logger.error(f"Error assigning role to player {self.name}: {str(e)}")
            raise

    def kill(self) -> None:
        """プレイヤーを死亡状態にする"""
        try:
            if not self.is_alive:
                self._logger.warning(f"Player {self.name} is already dead")
                return

            self.is_alive = False

            event_manager.notify(
                GameEvent(
                    type=EventType.PLAYER_DIED,
                    data={
                        "player_name": self.name,
                        "role": self.role.value if self.role else None,
                        "number": self.number,
                    },
                    source="player",
                )
            )

            self._add_status_record("死亡")
            self._logger.info(f"Player {self.name} died")

        except Exception as e:
            self._logger.error(f"Error killing player {self.name}: {str(e)}")
            raise

    def resurrect(self) -> None:
        """プレイヤーを生存状態に戻す（主にテスト用）"""
        try:
            if self.is_alive:
                self._logger.warning(f"Player {self.name} is already alive")
                return

            self.is_alive = True

            event_manager.notify(
                GameEvent(
                    type=EventType.PLAYER_STATUS_UPDATED,
                    data={
                        "player_name": self.name,
                        "status": "alive",
                        "number": self.number,
                        "role": self.role.value if self.role else None,
                    },
                    source="player",
                )
            )

            self._add_status_record("復活")
            self._logger.info(f"Player {self.name} resurrected")

        except Exception as e:
            self._logger.error(f"Error resurrecting player {self.name}: {str(e)}")
            raise

    def update_status(self, is_alive: bool) -> None:
        """プレイヤーの状態を更新"""
        if is_alive:
            self.resurrect()
        else:
            self.kill()

    def _add_status_record(self, reason: str) -> None:
        """状態変更の記録を追加"""
        try:
            status = PlayerStatus(is_alive=self.is_alive, role=self.role, reason=reason)
            self._status_history.append(status)
        except Exception as e:
            self._logger.error(f"Error adding status record: {str(e)}")

    def get_status_history(self) -> list:
        """状態変更履歴の取得"""
        return self._status_history

    def to_dict(self) -> Dict[str, Any]:
        """プレイヤー情報を辞書形式で返す"""
        return {
            "number": self.number,
            "name": self.name,
            "role": self.role.value if self.role else None,
            "is_alive": self.is_alive,
            "status_history": [
                {
                    "is_alive": status.is_alive,
                    "role": status.role.value if status.role else None,
                    "timestamp": status.timestamp.isoformat(),
                    "reason": status.reason,
                }
                for status in self._status_history
            ],
        }

    def __str__(self) -> str:
        """文字列表現"""
        role_str = self.role.get_display_name() if self.role else "未割当"
        status_str = "生存" if self.is_alive else "死亡"
        return f"Player(番号={self.number}, 名前={self.name}, 役職={role_str}, 状態={status_str})"

    def __eq__(self, other) -> bool:
        """等価性の比較"""
        if not isinstance(other, Player):
            return False
        return self.number == other.number and self.name == other.name

    def __hash__(self) -> int:
        """ハッシュ値の計算"""
        return hash((self.number, self.name))
