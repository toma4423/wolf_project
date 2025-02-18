# config ディレクトリ

このディレクトリには、アプリケーションの設定ファイルが含まれています。

## `settings.py`

アプリケーション全体の設定を定義します。

### 設定項目

*   `BASE_DIR`: アプリケーションのルートディレクトリのパス。
*   `LOGS_DIR`: ログファイルを保存するディレクトリのパス。
*   `DATA_DIR`: データファイルを保存するディレクトリのパス (現在は未使用)。
*   `APP_SETTINGS`: アプリケーションに関する設定。
    *   `app_name`: アプリケーションの名前。
    *   `version`: アプリケーションのバージョン。
    *   `default_window_size`: 各ウィンドウのデフォルトサイズ (今後 GUI を実装する際に使用)。
    *   `max_players`: 参加可能な最大プレイヤー数。
    *   `min_players`: ゲーム開始に必要な最小プレイヤー数。
    *   `default_discussion_time`: デフォルトの議論時間 (秒)。
    *   `log_format`: ログのフォーマット。
*   `ROLE_SETTINGS`: 各役職の詳細設定。
    *   `name`: 役職名。
    *   `team`: 所属する陣営 (`village` または `werewolf`)。
    *   `description`: 役職の説明。
* `setup_logging()`:ロギング設定を行う関数。

## `regulation.py`

ゲームのレギュレーション（役職の構成など）を定義します。

### 設定項目

*   `num_players`: プレイヤーの総数。
*   `num_wolves`: 人狼の数。
*   `num_fortunetellers`: 占い師の数。
*   `num_knights`: 騎士の数。
*   `num_mediums`: 霊媒師の数。
*   `num_hunters`: 狩人の数。
*   `num_freemasons`: 共有者の数 (現状未使用)。
*   `has_audience`: 観戦者の有無 (現状未使用)。
*  `roles`: 各役職の人数を辞書形式で定義します。

## 注意点
* `config/__init__.py` は空のファイルで、`config` ディレクトリを Python パッケージとして認識させるために必要です。

```

この内容で `config/README.md` を作成してください。

**補足:**

*   各設定項目の説明は、`settings.py` と `regulation.py` のコード内のコメントや変数名から推測される内容に基づいています。
*   `settings.py` の `ROLE_SETTINGS` は、役職の基本情報を定義していますが、`regulation.py` で実際にゲームに使用する役職の構成を決定します。
*   今後、設定項目が追加・変更された場合は、この README.md も更新してください。