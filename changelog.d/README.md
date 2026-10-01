# changelog.d

PR ごとに 1 ファイル。`<name>.<type>.md` で、`<type>` は
`added` / `changed` / `deprecated` / `removed` / `fixed` / `security`。

```
changelog.d/oracle-fidelity-gate.added.md
```

中身は Keep a Changelog の箇条書き 1 つ：

```markdown
- 書き出しの忠実性検査を CI の門にした
```

リリース時に `python tools/ops/changelog.py collect` が `CHANGELOG.md` の
`[Unreleased]` に畳んで断片を消す。

**`CHANGELOG.md` を直接編集しないこと。** 断片方式にしているのは、
同時に開いている PR が同じ行を編集して必ず衝突したから（[07](../docs/07-ops.md)）。
