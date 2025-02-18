# tests ディレクトリ

このディレクトリには、アプリケーションのユニットテストを格納します。

## `__init__.py`

空のファイルで、`tests` ディレクトリを Python パッケージとして認識させるために必要です。

## `test_core.py`

`core` パッケージ内のモジュール（`game_state.py`, `player.py`, `global_data_store.py`）に対するユニットテストを記述したファイルです。

### テストの実行方法

1.  **リポジトリのルートディレクトリに移動:**

    ```bash
    cd wolf_project
    ```

2.  **仮想環境をアクティベート (推奨):**

    ```bash
    source venv/bin/activate  # Linux/macOS
    venv\Scripts\activate  # Windows
    ```

3.  **テストの実行:**

    ```bash
    python -m unittest tests/test_core.py -v
    ```
    または
    ```bash
    python -m unittest discover -v
    ```

    *   `python -m unittest`: Python の組み込みのユニットテストフレームワーク (`unittest`) を実行します。
    *   `tests/test_core.py`: テストファイル (`test_core.py`) を指定します。
    *   `-v`: 詳細な出力 (verbose) を有効にします。
    * `discover`: テストファイルを自動で検出してくれます。

### テストの構成

`test_core.py` には、以下のクラスが含まれています。

*   `TestGameState`: `core.game_state.GameState` クラスのテスト。
*   `TestGlobalDataStore`: `store.global_data_store.GlobalDataStore` クラスのテスト。
*   `TestPlayer`: `core.player.Player` クラスのテスト。

各テストクラスには、`test_` で始まる複数のテストメソッドが含まれています。これらのメソッドが個別のテストケースに対応します。

### モックの使用

`test_core.py` では、`unittest.mock.patch` を使用して、`GlobalDataStore` クラスの `event_manager` をモック化しています。これにより、イベントの送受信に依存するコードを、`event_manager` の実際の動作とは切り離してテストできます。

```python
@patch("store.global_data_store.event_manager")
def test_event_handling(self, mock_event_manager):
    # ...
```

```

この内容で `tests/README.md` を作成してください。

**補足:**

*   テストを実行する前に、仮想環境をアクティベートすることを推奨します。
*   テストが失敗した場合は、エラーメッセージをよく読み、原因を特定してください。
*   新しい機能を追加したり、既存の機能を変更したりした場合は、必ずテストを追加・更新してください。