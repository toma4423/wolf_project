# Entry point for the application

import tkinter as tk

# import logging
from pathlib import Path
from config.settings import setup_logging
from store.global_data_store import GlobalDataStore
from ui.entry_point import EntryPointWindow

# main.pyまたはエントリーポイントで
import logging

logging.basicConfig(
    filename="logs/app.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    encoding="utf-8",  # エンコーディングを明示的に指定
)


def main():
    """アプリケーションのメインエントリーポイント"""
    # ロギングの設定
    setup_logging()
    logging.info("Application starting...")

    try:
        # グローバルデータストアの初期化
        store = GlobalDataStore()

        # メインウィンドウの作成
        root = tk.Tk()
        root.withdraw()  # ルートウィンドウを非表示

        # エントリーポイントウィンドウの表示
        entry_window = EntryPointWindow(root, store)

        # メインループの開始
        root.mainloop()

    except Exception as e:
        logging.error(f"Application error: {str(e)}")
        raise
    finally:
        logging.info("Application shutting down...")


if __name__ == "__main__":
    main()
