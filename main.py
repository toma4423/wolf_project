# Entry point for the application
import tkinter as tk
from pathlib import Path
from config.settings import setup_logging
from store.global_data_store import GlobalDataStore
from ui.entry_point import EntryPointWindow
import logging


def main():
    """アプリケーションのメインエントリーポイント"""
    # ロギングの設定（ここでのみ設定）
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
