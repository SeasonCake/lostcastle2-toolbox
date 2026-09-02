# Lost Castle 2 Toolbox agent entry

This project is a compact Windows/Tk toolbox. Keep product work small, reversible,
and centered on the author's visible and functional request. The workspace-level
If a parent workspace `AGENTS.md` exists, it also applies.

## Startup and scope

- Recheck `git status --short --branch`, HEAD, the current request, and the affected
  source/tests before editing. Historical plans and other task summaries are context,
  not current product state or authority.
- Investigation, local source changes, packaging, push, publication, redistribution,
  and game/runtime deployment are separate stages. Do not cross them implicitly.
- Use the smallest coherent change. A request about one label, field, control, or MOD
  must not redesign neighboring UI or add unrelated safety, licensing, cloud, account,
  activation, telemetry, protection, or release work.

## End-to-end continuity and runtime conditions

- If the author selects an endpoint such as “build the next desktop candidate” or
  “deploy this frozen Bridge candidate and smoke-test it”, continue through the local
  reversible source, focused tests, build, receipt, rollback, deployment and smoke
  steps needed for that endpoint. Do not ask again at each boundary. Push, public
  release, third-party redistribution, destructive cleanup and a different product
  scope remain separate.
- A required game exit, real key press, combat action or screenshot is an author input
  or runtime condition, not a new authorization gate. State it once with the exact
  resume condition while continuing other safe work.
- After a restart or stale PID, recover from the current handoff and durable receipts;
  recreate local collectors/jobs when equivalent. Never claim a reminder or scheduled
  continuation without an automation ID/status receipt.
- Repeated reconnects or image-heavy slowdown trigger a fresh successor after current
  source, installed DLL, package and open-issue identities are recorded. The successor
  reads the canonical handoff and live files, not the full screenshot history.

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
desktop replacement, push, publication, or runtime deployment unless the author's
selected endpoint already includes that exact stage.

Before replacing a game DLL, query process state as structured data using exact process
name and executable path. An absent result must be observed twice; missing fields,
formatted blank rows, stale handles, collector state or room/session state mean
`unknown/hold`, not “game exited”. Freeze an exact rollback and candidate hash before
the copy, then read back the installed identity. Do not infer process state from
`Format-Table` output.
