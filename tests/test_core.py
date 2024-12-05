import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest.mock import Mock, patch
from core.game_state import GameState, GamePhase, Team
from core.player import Player, PlayerRole
from core.events import EventType, GameEvent, event_manager
from store.global_data_store import GlobalDataStore


class TestGameState(unittest.TestCase):
    def setUp(self):
        """各テストの前に実行される"""
        self.game_state = GameState()

    def tearDown(self):
        """各テストの後に実行される"""
        self.game_state.players.clear()
        self.game_state.alive_players.clear()
        self.game_state.current_phase = GamePhase.SETUP
        self.game_state.current_round = 0
        self.game_state.regulation = None
        self.game_state.game_active = False

    def test_initial_state(self):
        """初期状態のテスト"""
        self.assertEqual(self.game_state.current_phase, GamePhase.SETUP)
        self.assertEqual(self.game_state.current_round, 0)
        self.assertFalse(self.game_state.game_active)

    def test_add_player(self):
        """プレイヤー追加のテスト"""
        player = Player(number=1, name="test_player")
        self.game_state.add_player(player)
        self.assertIn("test_player", self.game_state.players)
        self.assertIn("test_player", self.game_state.alive_players)

    def test_remove_player(self):
        """プレイヤー削除のテスト"""
        player = Player(number=1, name="test_player")
        self.game_state.add_player(player)
        self.game_state.remove_player("test_player")
        self.assertNotIn("test_player", self.game_state.players)
        self.assertNotIn("test_player", self.game_state.alive_players)

    def test_phase_transition(self):
        """フェーズ遷移のテスト"""
        player = Player(number=1, name="test_player")
        player.assign_role("villager")
        self.game_state.add_player(player)

        # 初期設定
        self.game_state.regulation = {
            "roles": {"villager": 1},
            "round_times": [{"time": 5}],
        }

        # ゲーム開始
        self.game_state.start_game()
        self.assertEqual(self.game_state.current_phase, GamePhase.DAY_DISCUSSION)
        self.assertTrue(self.game_state.game_active)

        # フェーズ変更
        self.game_state.change_phase(GamePhase.NIGHT)
        self.assertEqual(self.game_state.current_phase, GamePhase.NIGHT)

    def test_player_kill(self):
        """プレイヤー死亡処理のテスト"""
        player = Player(number=1, name="test_player")
        player.assign_role("villager")
        self.game_state.add_player(player)
        self.game_state.regulation = {
            "roles": {"villager": 1},
            "round_times": [{"time": 5}],
        }
        self.game_state.start_game()

        self.assertIn("test_player", self.game_state.alive_players)
        self.game_state.kill_player("test_player")
        self.assertNotIn("test_player", self.game_state.alive_players)

    def test_team_counts(self):
        """チーム別人数カウントのテスト"""
        # インスタンスをリセット
        self.game_state = GameState()
        self.game_state.players.clear()
        self.game_state.alive_players.clear()

        # 村人を追加
        villager = Player(number=1, name="villager1")
        villager.assign_role("villager")

        # 人狼を追加
        werewolf = Player(number=2, name="werewolf1")
        werewolf.assign_role("werewolf")

        # プレイヤーを追加して生存者として設定
        self.game_state.add_player(villager)
        self.game_state.add_player(werewolf)

        # ゲームを開始状態にする
        self.game_state.regulation = {
            "roles": {"villager": 1, "werewolf": 1},
            "round_times": [{"time": 5}],
        }
        self.game_state.start_game()

        # チーム数を確認
        counts = self.game_state.get_team_counts()
        self.assertEqual(
            counts[Team.VILLAGE.value], 1, "Village team count should be 1"
        )
        self.assertEqual(
            counts[Team.WEREWOLF.value], 1, "Werewolf team count should be 1"
        )


class TestGlobalDataStore(unittest.TestCase):
    def setUp(self):
        """各テストの前に実行される"""
        self.store = GlobalDataStore()
        self.store.game_log = []

    def tearDown(self):
        """各テストの後に実行される"""
        self.store.game_log = []
        self.store.game_state = GameState()

    def test_singleton(self):
        """シングルトンパターンのテスト"""
        store2 = GlobalDataStore()
        self.assertEqual(id(self.store), id(store2))

    def test_initial_state(self):
        """初期状態のテスト"""
        self.assertIsNotNone(self.store.game_state)
        self.assertEqual(len(self.store.game_log), 0)

    def test_regulation_validation(self):
        """レギュレーションバリデーションのテスト"""
        valid_regulation = {
            "roles": {"villager": 3, "werewolf": 1},
            "round_times": [{"round": 1, "time": 5}],
        }
        self.assertTrue(self.store._validate_regulation(valid_regulation))

        invalid_regulation = {"roles": {"invalid_role": 1}}
        self.assertFalse(self.store._validate_regulation(invalid_regulation))

    def test_game_log(self):
        """ゲームログのテスト"""
        log_entry = {
            "phase": GamePhase.DAY_DISCUSSION.value,
            "round": 1,
            "action": "phase_start",
        }
        self.store.add_game_log(log_entry)
        self.assertEqual(len(self.store.game_log), 1)
        self.assertEqual(self.store.game_log[0], log_entry)

    @patch("store.global_data_store.event_manager")
    def test_event_handling(self, mock_event_manager):
        """イベントハンドリングのテスト"""
        try:
            # プレイヤーを準備
            player = Player(number=1, name="test_player")
            player.assign_role("villager")
            self.store.game_state.add_player(player)

            # ゲームを開始状態にする
            self.store.game_state.regulation = {
                "roles": {"villager": 1},
                "round_times": [{"time": 5}],
            }
            self.store.game_state.start_game()

            # プレイヤー死亡イベントを発行
            event = GameEvent(
                type=EventType.PLAYER_DIED,
                data={"player": "test_player", "cause": "test"},
            )

            # イベントを処理
            self.store.handle_event(event)

            # イベントが発行されたことを確認
            mock_event_manager.notify.assert_called()

        except Exception as e:
            self.fail(f"Test failed with error: {str(e)}")


class TestPlayer(unittest.TestCase):
    def setUp(self):
        self.player = Player(number=1, name="test_player")

    def test_initial_state(self):
        """初期状態のテスト"""
        self.assertEqual(self.player.number, 1)
        self.assertEqual(self.player.name, "test_player")
        self.assertTrue(self.player.is_alive)
        self.assertIsNone(self.player.role)

    def test_kill(self):
        """死亡処理のテスト"""
        self.player.kill()
        self.assertFalse(self.player.is_alive)

    def test_role_assignment(self):
        """役職割り当てのテスト"""
        self.player.assign_role("werewolf")
        self.assertEqual(self.player.role.value, "werewolf")

        # 無効な役職の割り当て
        with self.assertRaises(ValueError):
            self.player.assign_role("invalid_role")


if __name__ == "__main__":
    unittest.main()
