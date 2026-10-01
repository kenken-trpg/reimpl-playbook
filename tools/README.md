# tools/

自分のリポジトリにそのままコピーして使う部分。各ディレクトリの
docstring が説明で、対応する散文が `docs/` にある。

| | 何をするか | 散文 |
|---|---|---|
| `oracle/` | 本家が書いたファイルを正解として subject を測る | [01](../docs/01-oracle.md) |
| `pin/` | 上流のファイルを固定した commit で取得 | [02](../docs/02-upstream-pin.md) |
| `generated/` | 生成ファイルが stale なら CI で落とす | [04](../docs/04-boundary-types.md) |
| `drift/` | 版管理されていない外部仕様の変化を作業リストにする | [05](../docs/05-spec-drift.md) |
| `coverage/` | ハンドラ表からカバレッジを導出 | [06](../docs/06-coverage.md) |
| `ops/` | changelog 断片 / 順次マージ / doctor / retry | [07](../docs/07-ops.md) |

`oracle/` 以外は**穴埋めが要る**：`pin/fetch_upstream.py` の上流 3 定数、
`drift/watch.py` の `fetch_spec()` と `PROBES`、
`ops/merge_chain.conf.sh` の検査コマンド。
埋めずに動くのは `oracle/`（adapter を書けば動く）と `ops/` の
`retry.sh` / `keep_both_sides.py` だけ。
