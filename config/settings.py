# Application-wide settings
import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any


def get_base_path() -> Path:
    """アプリケーションのルートパスを取得"""
    if getattr(sys, "frozen", False):
        # PyInstallerでビルドされた場合
        return Path(sys._MEIPASS)
    else:
        # 通常の実行の場合
        return Path(__file__).parent.parent


# プロジェクトのルートディレクトリを取得
BASE_DIR = get_base_path()
LOGS_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"

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


def setup_logging():
    """ロギングの初期設定を行う"""
    try:
        # logsディレクトリを作成
        os.makedirs(LOGS_DIR, exist_ok=True)

        log_path = LOGS_DIR / "app.log"

        # ファイルハンドラの設定
        file_handler = logging.FileHandler(str(log_path), encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(APP_SETTINGS["log_format"])
        file_handler.setFormatter(file_formatter)

        # コンソールハンドラの設定
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(APP_SETTINGS["log_format"])
        console_handler.setFormatter(console_formatter)

        # ルートロガーの設定
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

        logging.info("Logging setup completed successfully")

    except Exception as e:
        print(f"Error setting up logging: {str(e)}")
        # 最低限のコンソール出力は確保
        logging.basicConfig(level=logging.INFO, format=APP_SETTINGS["log_format"])
