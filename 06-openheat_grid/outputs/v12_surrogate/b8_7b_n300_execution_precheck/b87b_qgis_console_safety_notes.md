# B8.7b QGIS Console Safety Notes

These notes are for a future B8.7c execution package only. B8.7b does not create a runner and does not authorize QGIS or SOLWEIG execution.

- Read any future local runner with `encoding="utf-8-sig"` to avoid BOM-related console failures.
- Inject an explicit `__file__` for the future local-only runner path.
- Set `sys.argv` to the future local-only runner path before execution.
- Set `cwd` to the future runner parent directory.
- Keep any future real execution outside the Git worktree and under a local-only output root.
- Keep repo-side runners dry-run or absent unless a future lane explicitly authorizes otherwise.
- Do not copy, open, or commit rasters or `svfs.zip`.
