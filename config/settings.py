# Application-wide settings

from pathlib import Path
import logging
from typing import Dict, Any

# プロジェクトのルートディレクトリを取得
ROOT_DIR = Path(__file__).parent.parent

# 各種ディレクトリパスの設定
LOGS_DIR = ROOT_DIR / "logs"
DATA_DIR = ROOT_DIR / "data"

# アプリケーション設定
APP_SETTINGS: Dict[str, Any] = {
    "app_name": "人狼ゲームサポート",
    "version": "1.0.0",
    "default_window_size": {
        "entry_point": (300, 300),
        "gm_main": (400, 500),
        "regulation": (300, 500),
        "participant": (400, 800),
        "game_progress": (400, 400),
        "vote_manager": (500, 400),
        "log_viewer": (600, 400),
    },
    "max_players": 20,
    "min_players": 3,
    "default_discussion_time": 180,  # 秒
    "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
}

# 役職設定
ROLE_SETTINGS = {
    "villager": {
        "name": "村人",
        "team": "village",
        "description": "特別な能力を持たない村の住人",
    },
    "werewolf": {"name": "人狼", "team": "werewolf", "description": "夜に人を襲う人狼"},
    "seer": {
        "name": "占い師",
        "team": "village",
        "description": "夜に誰か一人が人狼かどうかを知ることができる",
    },
    "medium": {
        "name": "霊能者",
        "team": "village",
        "description": "処刑された人が人狼だったかどうかを知ることができる",
    },
    "guard": {
        "name": "狩人",
        "team": "village",
        "description": "夜に誰か一人を人狼の襲撃から守ることができる",
    },
    "madman": {
        "name": "狂人",
        "team": "werewolf",
        "description": "人狼陣営の人間。人狼を勝利に導く",
    },
}

# ゲームフェーズ設定
# GAME_PHASES = {
#    "setup": "設定",
#    "day_discussion": "昼の議論",
#    "day_vote": "処刑投票",
#    "night": "夜の行動",
#    "game_end": "ゲーム終了",
# }


# ロギング設定
def setup_logging():
    """ロギングの初期設定を行う"""
    LOGS_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        filename=LOGS_DIR / "app.log",
        level=logging.INFO,
        format=APP_SETTINGS["log_format"],
    )

    # コンソールへのハンドラも追加
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(APP_SETTINGS["log_format"])
    console_handler.setFormatter(formatter)
    logging.getLogger().addHandler(console_handler)
