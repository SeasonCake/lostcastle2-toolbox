# Contributing

Thank you for helping improve Lost Castle 2 Toolbox.

## Before opening a change

- Keep the overlay, macro engine, game bridge, aggregator, and UI as separate modules.
- Prefer one generic behavior over item-specific branches. New item names belong in `assets/combat_sources.json` unless they introduce genuinely new semantics.
- Do not commit game binaries, generated interop assemblies, logs, screenshots containing personal data, local configuration, or packaged builds.
- Do not add first-party behavior that modifies combat values, saves, drops, network state, or bypasses game restrictions. A third-party catalog entry must remain isolated, opt-in, hash-pinned, attributed, risk-labeled, and separately licensed.
- Do not commit or package a third-party binary without documented redistribution permission.

## Tests

Run on Windows with Python 3.13:

```powershell
py -3 -m pip install -r requirements-dev.txt
py -3 -m unittest discover -s tests -p "test_*.py" -v
py -3 keyview.py --self-test
```

Contract changes need schema validation and at least one valid and invalid example. Aggregation changes need deterministic replay tests. UI changes should include startup, disconnected/stale, empty, live and compact-layout checks.

## Combat evidence

When reporting a new source or game-version change, include the game build, whether the player was host/client, the observed path, expected result, and a minimal redacted excerpt. Treat one run as a reproduction, not proof that the behavior is universal.

By contributing, you agree that your contribution is licensed under the repository's MIT License.
