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
*   **テスト:**
    *   ユニットテストにより、コードの品質を保証します。

## 動作環境

*   Python 3.11 以上

## 使い方

1.  **リポジトリのクローン:**

    ```bash
    git clone https://github.com/toma4423/wolf_project.git
    cd wolf_project
    ```

2.  **仮想環境の作成 (推奨):**

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # Linux/macOS
    venv\Scripts\activate  # Windows
    ```

3.  **依存関係のインストール:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **設定ファイルの編集:**

    `config/settings.py` と `config/regulation.py` を編集して、ゲームの設定（役職、ラウンド時間など）をカスタマイズします。

5.  **メインスクリプトの実行:**

    ```bash
    python main.py
    ```

## ディレクトリ構造 