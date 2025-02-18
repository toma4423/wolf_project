# core ディレクトリ

このディレクトリには、アプリケーションのコアとなるロジックが含まれています。

## `__init__.py`

空のファイルで、`core` ディレクトリを Python パッケージとして認識させるために必要です。

## `events.py`

ゲーム内で発生するイベントを定義し、イベントの送受信を管理するモジュールです。

### 主要なクラス

*   `GameEvent`: ゲームイベントを表すクラス。イベントの種類 (`type`)、イベントに関連するデータ (`data`)、イベントの発生源 (`source`) などの属性を持ちます。
*   `EventType`: イベントの種類を定義する列挙型 (`Enum`)。
    *   例: `PLAYER_ADDED`, `PLAYER_REMOVED`, `GAME_STARTED`, `PHASE_CHANGED`, `PLAYER_DIED` など。
*   `EventManager`: イベントの送受信を管理するクラス。シングルトンパターンで実装されています。
    *   `subscribe(listener)`: イベントリスナーを登録します。
    *   `unsubscribe(listener)`: イベントリスナーの登録を解除します。
    *   `notify(event)`: イベントを発生させ、登録されているすべてのリスナーに通知します。

### イベントリスナー

イベントリスナーは、`GameEvent` オブジェクトを引数に取り、何らかの処理を行う関数です。

```python
def my_listener(event: GameEvent):
    if event.type == EventType.PLAYER_DIED:
        print(f"Player {event.data['player_name']} died!")

event_manager.subscribe(my_listener)
```

## `game_state.py`

ゲームの状態（プレイヤー、フェーズ、ラウンド数など）を管理するモジュールです。

### 主要なクラス

*   `GameState`: ゲームの状態を管理するクラス。
    *   `players`: 参加しているプレイヤーのリスト。
    *   `alive_players`: 生存しているプレイヤーのリスト。
    *   `current_phase`: 現在のゲームフェーズ (`GamePhase` 列挙型)。
    *   `current_round`: 現在のラウンド数。
    *   `regulation`: ゲームのレギュレーション（役職構成など）。
    *   `add_player(player)`: プレイヤーを追加します。
    *   `remove_player(player_name)`: プレイヤーを削除します。
    *   `start_game()`: ゲームを開始します。
    *   `change_phase(new_phase)`: ゲームフェーズを変更します。
    *   `kill_player(player_name)`: プレイヤーを死亡状態にします。
    *   `get_team_counts()`: 各チームの生存者数を取得します。
    *   `next_round()`: 次のラウンドに進めます。
*   `GamePhase`: ゲームフェーズを定義する列挙型 (`Enum`)。
    *   `SETUP`: 準備中
    *   `DAY_DISCUSSION`: 昼フェーズ（議論）
    *   `DAY_VOTE`: 昼フェーズ（投票）
    *   `NIGHT`: 夜フェーズ
*   `Team`: チームを定義する列挙型 (`Enum`)。
    *   `VILLAGE`: 村人陣営
    *   `WEREWOLF`: 人狼陣営
* `GameStateSnapshot`: ゲーム状態のスナップショットを保存するクラス

## `player.py`

プレイヤーに関する情報を管理するモジュールです。

### 主要なクラス

*   `Player`: プレイヤーを表すクラス。
    *   `number`: プレイヤー番号。
    *   `name`: プレイヤー名。
    *   `role`: 役職 (`PlayerRole` 列挙型)。
    *   `is_alive`: 生死状態。
    *   `assign_role(role)`: 役職を割り当てます。
    *   `kill()`: プレイヤーを死亡状態にします。
    *   `resurrect()`: プレイヤーを生存状態に戻します（主にテスト用）。
*   `PlayerRole`: プレイヤーの役職を定義する列挙型 (`Enum`)。
    *   `VILLAGER`: 村人
    *   `WEREWOLF`: 人狼
    *   `GUARD`: 狩人
    *   `SEER`: 占い師
    *   `MEDIUM`: 霊媒師
    *   `MADMAN`: 狂人
* `PlayerStatus`: プレイヤーの状態変更履歴を管理するクラス

```

この内容で `core/README.md` を作成してください。

**補足:**

*   各ファイルの説明は、コード内のコメントやクラス/メソッドの定義から推測される内容に基づいています。
*   今後、クラスやメソッドが追加・変更された場合は、この README.md も更新してください。
* イベントリスナーのコード例は、`events.py`の説明に含めました。