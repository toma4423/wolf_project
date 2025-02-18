# Werewolf Game Master Support

[![Python application](https://github.com/toma4423/wolf_project/actions/workflows/python-app.yml/badge.svg)](https://github.com/toma4423/wolf_project/actions/workflows/python-app.yml)

## 概要

人狼ゲームのゲームマスター（GM）をサポートするためのツールです。Python で書かれており、ゲームの進行管理、役職の自動割り当て、イベント通知などの機能を提供します。

## 特徴

*   **ゲーム進行管理:**
    *   ゲームのフェーズ（準備、昼、夜）を管理します。
    *   ラウンド数をカウントします。
    *   プレイヤーの生死状態を管理します。
*   **役職自動割り当て:**
    *   設定ファイルに基づいて、プレイヤーに役職をランダムに割り当てます。
    *   役職の数や種類をカスタマイズできます。
*   **イベント通知:**
    *   ゲームの進行状況（フェーズ変更、プレイヤーの死亡など）をイベントとして通知します。
    *   イベントリスナーを登録することで、イベントに応じた処理を実行できます。
*   **データ永続化:**
    *   ゲームの状態をファイルに保存し、途中から再開できます。
    *   (現在は未実装)
*   **モジュール構成:**
    *   コアロジックは `core` パッケージに格納されています。
    *   設定ファイルは `config` パッケージに格納されています。
    *   データストアは `store` パッケージに格納されています (現在はモックアップ)。
    *   UI関連のモジュールは `ui` パッケージに格納されています。

## 動作環境

*   Python 3.11 以上

## 使い方

1.  **リポジトリのクローン:**

    ```bash
    git clone https://github.com/toma4423/wolf_project.git
    cd wolf_project
    ```

2.  **仮想環境の作成とアクティベート (推奨):**

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # Linux/macOS
    venv\Scripts\activate  # Windows
    ```

3.  **依存関係のインストール:**
     現状、`requirements.txt`が空なので、依存関係はありません。

4.  **設定ファイルの編集:**

    `config/regulation.py` を編集して、ゲームの設定（役職など）をカスタマイズします。

5.  **メインスクリプトの実行:**
    *   現状、`main.py`は空の状態です。

    ```bash
    python main.py
    ```

## ディレクトリ構造

wolf_project/
├── core/ # コアロジック（ゲーム状態、プレイヤー、イベント管理）
├── config/ # 設定ファイル
├── store/ # データストア（ゲーム状態の永続化、現状はモック）
├── tests/ # ユニットテスト
├── .gitignore # Git で無視するファイル/ディレクトリ
├── main.py # メインスクリプト（現状は空）
├── README.md # このファイル
└── requirements.txt # 依存関係リスト（現時点では空）

## 貢献

バグ報告、機能提案、プルリクエストなど、歓迎します！

## ライセンス

MIT License

## TODO

*   `main.py` の実装
*   GUI の実装
*   ログ機能の強化
*   より詳細なゲーム終了判定
*   非同期処理の導入
*   Web インターフェースの実装
*   現状、`requirements.txt`が空なので、必要に応じて依存関係を追加する。
*   現状、`store/`以下はモックなので、データ永続化を実装する。

