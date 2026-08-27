# Lost Castle 2 Toolbox agent entry

This project is a compact Windows/Tk toolbox. Keep product work small, reversible,
and centered on the author's visible and functional request. The workspace-level
`C:\xiangmuyunxing\biancheng\2026\AGENTS.md` also applies.

## Startup and scope

- Recheck `git status --short --branch`, HEAD, the current request, and the affected
  source/tests before editing. Historical plans and other task summaries are context,
  not current product state or authority.
- Investigation, local source changes, packaging, push, publication, redistribution,
  and game/runtime deployment are separate stages. Do not cross them implicitly.
- Use the smallest coherent change. A request about one label, field, control, or MOD
  must not redesign neighboring UI or add unrelated safety, licensing, cloud, account,
  activation, telemetry, protection, or release work.

## UI and product copy

- This is an Operate surface. Prefer familiar controls and compact task information.
- Freeze the visible order before a UI change. For a managed MOD the default order is:
  name/version -> author -> one-sentence purpose -> operational status -> actions.
- Internal implementation, provenance, and policy metadata are not routine UI copy.
  Frida/injection details, signature state, hashes, permission source, redistribution
  status, threat analysis, and legal prose belong in internal catalog policy or
  `THIRD_PARTY_NOTICES.md`, unless a dedicated diagnostic/details surface or an
  immediate irreversible decision requires them.
- Do not add claims such as “authorized”, “bundled”, “no account”, or “no telemetry”
  merely because they are true. Show information only when it helps the user complete
  the current action.
- Preserve the current layout and neighboring labels unless the author explicitly
  changes them. Verify actual Tk output for clipping/layout work; source tests alone
  are not visual acceptance.

## External tools and MODs

- Treat read-only identification, local integration, actual launch, public
  redistribution, and product protection as five separate stages.
- A user-provided tool may be identified, hash-bound, locally adapted, and reversibly
  tested within the requested stage. Unknown public redistribution permission is a
  packaging question, not a blocker for local integration.
- Actual launch requires the normal explicit user action and preserves the existing
  confirmation for game-data modification. Do not add repeated warnings elsewhere.
- Do not add encryption, signing, attestation, anti-debugging, trust chains, or other
  protection work without an explicit author decision covering protected object,
  threat, target release, time/token budget, rollback, and acceptance.

## Catalog boundary

- `assets/mod_catalog.json` separates `display`, `operation`, and `integrity_policy`.
- UI code may consume only `display` plus computed operational status/actions.
- File identity, implementation capabilities, attribution evidence, and redistribution
  evidence remain available to the manager/build/docs but must not leak into normal UI.
- New catalog entries need a positive parse case, an invalid/path traversal case,
  integrity known-good/known-red coverage, and a visible-copy boundary test.

## Native checks

Use focused checks first, then the adjacent suite:

```powershell
py -3 -m unittest tests.test_mod_manager -v
py -3 -m unittest tests.test_app_shell -v
py -3 -m unittest discover -s tests -p "test_*.py" -v
py -3 keyview.py --self-test
```

Packaging is a separate stage. A source/test change does not authorize `build.ps1`,
desktop replacement, push, publication, or runtime deployment.
