# reimpl-playbook

既存のプログラムを**別のフレームワークで作り直す**案件のための、
方法・雛形・動くツール一式。

`chummer-web`（C# / WinForms のデスクトップアプリ → Python + TypeScript の Web アプリ、
実セーブ 34 件・テスト 1830 件）で実際に効いたものだけを抽象化してある。
事例は [`docs/case-study.md`](docs/case-study.md)。

## 読む順

まず [`docs/00-method.md`](docs/00-method.md)。着手順と、
「赤いままでよい検査」と「緑でなければならない検査」の区別が書いてある。
ここを間違えると数か月戻る。

| | |
|---|---|
| [00 方法](docs/00-method.md) | 前提・順序・例外の置き場所 |
| [01 本家を正解として測る](docs/01-oracle.md) | balance / roundtrip / fidelity |
| [02 上流データのピン留め](docs/02-upstream-pin.md) | vendoring しない、ref を固定する |
| [03 ドキュメントと計画](docs/03-docs-and-plans.md) | 4 点セットと plans の作法 |
| [04 境界をまたぐ型](docs/04-boundary-types.md) | 片側から生成、CI で stale を落とす |
| [05 外部仕様の漂流監視](docs/05-spec-drift.md) | テストでは捕まらない変化 |
| [06 カバレッジ](docs/06-coverage.md) | ハンドラ表から導出する |
| [07 運用](docs/07-ops.md) | changelog 断片・順次マージ・doctor・retry |

## 動かす

```sh
make setup      # 依存（pytest だけ）
make example    # 突き合わせハーネスを例題で回す
make test       # ツール自身のテスト
```

`make example` の出力：

```
artefact     total: ref / ours
a-1.xml      3300 / 3300 (+0)
a-2.xml      540 / 540 (+0)
draft-7.xml  (not comparable)

comparable: 2  not comparable: 1  failed to load: 0
  total agrees: 2 of 2
```

## 中身

```
docs/        方法（散文）。これが本体
templates/   自分のリポジトリにコピーして埋める雛形
tools/
  oracle/    本家を正解として測るハーネス（★ 中核）
  pin/       上流データをピンした ref で取得
  coverage/  ハンドラ表からカバレッジを導出
  drift/     版管理されていない外部仕様の監視
  generated/ 生成ファイルの stale 検出
  ops/       changelog 断片・順次マージ・doctor・retry
example/     oracle の配線例（請求書という極小の題材）
tests/       tools 自身のテスト
```

## 自分の案件への持ち込み方

1. `tools/` をコピーする
2. `tools/pin/fetch_upstream.py` の `UPSTREAM` / `DEFAULT_REF` / `FILES` / `CORPUS_DIR` を埋める
3. `example/adapter.py` を見ながら、自分の `Oracle` と `Subject` を書く（各 1 クラス）
4. `python -m tools.oracle.cli --adapter your.adapter` が表を出したら、そこからが本番
5. `templates/docs/` をコピーして埋める

3 が一番短い。`example/adapter.py` は全部入りで 160 行で、
実案件でもこの桁から大きくは外れない。
