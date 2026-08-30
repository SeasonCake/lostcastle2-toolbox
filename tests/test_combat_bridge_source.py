from __future__ import annotations

from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class CombatBridgeSourceTests(unittest.TestCase):
    def test_non_battle_damage_remains_observable_but_is_not_aggregated(self) -> None:
        source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "Plugin.cs"
        ).read_text(encoding="utf-8")

        self.assertIn('public const string PluginVersion = "0.4.12";', source)
        self.assertIn("var aggregate = ShouldAggregateDamage(direction);", source)
        self.assertIn('Bridge?.Emit(\n                "damage_resolution",\n                aggregate,', source)
        self.assertIn('StageMgr.Instance?.IsNonBattleRoom() is not true', source)
        self.assertNotIn('IndexOf("_Shop_", StringComparison.OrdinalIgnoreCase)', source)
        self.assertIn('["is_boss"] = isBoss', source)

    def test_room_location_is_captured_after_room_change_finishes(self) -> None:
        source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "Plugin.cs"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "[HarmonyPatch(typeof(SettlementDataMgr), nameof(SettlementDataMgr.OnChangeRoomEnd))]",
            source,
        )
        self.assertNotIn(
            "[HarmonyPatch(typeof(SettlementDataMgr), nameof(SettlementDataMgr.OnChangeRoomStart))]",
            source,
        )
        self.assertIn('LogRoomDiagnostic("change_room_end", room);', source)

    def test_mana_diagnostics_record_raw_display_and_summary_values(self) -> None:
        source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "Plugin.cs"
        ).read_text(encoding="utf-8")

        self.assertIn("[LC2CB-MP] kind=spend", source)
        self.assertIn("[LC2CB-MP] kind=recovery", source)
        self.assertIn("[LC2CB-MP] kind=summary", source)
        self.assertIn("var spentRaw = Positive(arg.useMana);", source)
        self.assertIn('["effective_delta"] = -spentRaw', source)
        self.assertIn("ReconcileOfficialManaRecovery(", source)
        self.assertIn("same_operation_spend_raw=", source)
        self.assertIn('["effective_delta"] = effectiveRaw', source)

    def test_same_operation_spend_does_not_hide_recovery(self) -> None:
        source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "Plugin.cs"
        ).read_text(encoding="utf-8")

        self.assertIn("TrackOfficialManaSpend(spentRaw);", source)
        self.assertIn("TakeOfficialManaSpendCoverage()", source)
        self.assertIn("afterRaw - beforeRaw + pairedSpend", source)
        self.assertIn("ResetOfficialManaSpendCoverage();", source)

    def test_low_level_mana_gain_fills_callback_gaps_without_double_counting(self) -> None:
        source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "Plugin.cs"
        ).read_text(encoding="utf-8")

        self.assertIn("TakeOfficialManaRecoveryCoverage(state.OperationId)", source)
        self.assertIn("var sameOperationSpendRaw = state.Depth == 0", source)
        self.assertIn("ReconcileFallbackManaRecovery(", source)
        self.assertIn("sameOperationSpendRaw,", source)
        self.assertIn("var observedBeforeRaw = _lastObservedPlayerMp;", source)
        self.assertIn("observedBeforeRaw ?? state.Before", source)
        self.assertIn("Math.Max(rootedRecoveryRaw, sequentialRecoveryRaw)", source)
        self.assertIn("Math.Max(0.0, recoveredRaw - coveredRaw)", source)
        self.assertIn('var operation = aggregateFallback\n                ? "gain"', source)
        self.assertIn('var sourceToken = aggregateFallback\n                ? "resource.mana_recovery"', source)
        self.assertIn("var blocked = !aggregateFallback", source)
        self.assertIn("same_operation_spend_raw=", source)
        self.assertIn("observed_before_raw=", source)
        self.assertIn("_lastObservedPlayerMp = currentRaw.Value;", source)
        self.assertIn("aggregate: aggregateFallback", source)
        self.assertIn("TrackOfficialManaRecovery(effectiveRaw);", source)
        self.assertIn("var rootOperationId = stack.Last();", source)
        self.assertIn("[LC2CB-MP] kind=runtime_gain", source)
        self.assertIn("ShouldEmitMpObservation(requested, effective, fallbackGain)", source)
        self.assertIn('["source_token"] = sourceToken', source)
        self.assertNotIn('["observed_requested_delta"]', source)
        self.assertNotIn('["observed_effective_delta"]', source)
        self.assertNotIn('["official_covered_delta"]', source)

    def test_direct_negative_hp_is_separate_from_official_damage(self) -> None:
        source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "Plugin.cs"
        ).read_text(encoding="utf-8")

        self.assertIn("public bool InsideDamageResolution { get; init; }", source)
        self.assertIn("if (state.InsideDamageResolution)", source)
        self.assertIn('["resource_operation"] = "loss"', source)
        self.assertIn('["effective_delta"] = effective', source)
        self.assertIn('?? "resource.self_damage"', source)

    def test_hp_diagnostics_preserve_existing_effective_recovery_semantics(self) -> None:
        source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "Plugin.cs"
        ).read_text(encoding="utf-8")

        self.assertIn("[LC2CB-HP] kind=observation", source)
        self.assertIn("effective_raw=", source)
        self.assertIn('["effective_delta"] = effective', source)
        self.assertNotIn("ReconcileHpRecovery(", source)
        self.assertNotIn("NormalizeHpGain(", source)

    def test_round_transition_excludes_camp_refill_before_preload(self) -> None:
        source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "Plugin.cs"
        ).read_text(encoding="utf-8")

        self.assertIn("internal static void PrepareRoundTransition()", source)
        self.assertIn("internal static void BeginCampPreload()", source)
        self.assertIn(
            "[HarmonyPatch(typeof(PlayerManager), "
            "nameof(PlayerManager.OnGameRoundEndPreLoadCamp))]",
            source,
        )
        self.assertIn("private static void Prefix() => Plugin.BeginCampPreload();", source)
        self.assertIn('LogRoomDiagnostic("round_end_preload_camp");', source)
        self.assertIn("private static void Prefix() => Plugin.PrepareRoundTransition();", source)
        self.assertIn("private static void Postfix() => Plugin.BeginRound();", source)
        self.assertIn("var inActiveMap = _inActiveMap;", source)
        self.assertIn("if (!inActiveMap)", source)
        self.assertIn("in_map={inActiveMap}", source)

    def test_hp_diagnostics_include_bounded_source_token(self) -> None:
        source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "Plugin.cs"
        ).read_text(encoding="utf-8")

        self.assertIn("source_token={DiagnosticToken(sourceToken)}", source)
        self.assertIn("CombatPipeServer.Bound(value, 128)", source)
        self.assertIn('.Replace("\\r", "\\\\r", StringComparison.Ordinal)', source)

    def test_taken_diagnostics_expose_official_and_actual_damage_stages(self) -> None:
        source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "Plugin.cs"
        ).read_text(encoding="utf-8")

        self.assertIn("[LC2CB-TAKEN] kind=damage", source)
        self.assertIn("original_raw=", source)
        self.assertIn("real_raw=", source)
        self.assertIn("hp_before_raw=", source)
        self.assertIn("applied_raw=", source)
        self.assertIn("settlement_display=", source)
        self.assertIn("Math.Abs(effective) > 0.0001", source)

    def test_local_resource_and_taken_paths_ignore_remote_player_state(self) -> None:
        source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "Plugin.cs"
        ).read_text(encoding="utf-8")

        self.assertIn("private static bool IsLocalPlayerRootCreature", source)
        self.assertIn("PlayerManager.Instance?.LocalPlayer?.OwnerCreature", source)
        self.assertIn(
            'direction == "taken" && !IsLocalPlayerRootCreature(TryCreature(defender))',
            source,
        )
        self.assertGreaterEqual(source.count("!IsLocalPlayerRootCreature("), 5)
        self.assertIn('["resource_operation"] = "loss"', source)
        self.assertGreaterEqual(source.count('["value_before"] = Positive('), 4)
        self.assertGreaterEqual(source.count('["max_after"] = Positive('), 4)

    def test_multiplayer_uses_opaque_roster_and_owner_tokens(self) -> None:
        plugin_source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "Plugin.cs"
        ).read_text(encoding="utf-8")
        pipe_source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "CombatPipeServer.cs"
        ).read_text(encoding="utf-8")

        self.assertIn("RefreshPartyRoster(force: true);", plugin_source)
        self.assertIn("result.Count < 16", plugin_source)
        self.assertIn("bounded.Count < 16", pipe_source)
        self.assertIn("member.PlayerSlot is >= 0 and <= 15", pipe_source)
        self.assertIn("OwnerPlayerIncludeMaster", plugin_source)
        self.assertIn("OwnerPlayer(hit)", plugin_source)
        self.assertIn("hit.mAtkerInHierarchy", plugin_source)
        self.assertIn("OwnerEntityInHierarchy(candidate)", plugin_source)
        self.assertIn("OwnerEntity(candidate)", plugin_source)
        self.assertIn("CreatureMaster(candidate)", plugin_source)
        self.assertIn("PlayerForRootCreature", plugin_source)
        self.assertNotIn("StandMaster(candidate)", plugin_source)
        self.assertNotIn("root.EntityID == entity.EntityID", plugin_source)
        self.assertLess(
            plugin_source.index("OwnerPlayer(hit.mAtkerInHierarchy)"),
            plugin_source.index("OwnerPlayer(hit.mAtker);"),
        )
        self.assertIn('["owner_player_id"] = PlayerToken(attackerPlayer)', plugin_source)
        self.assertIn('["player_id"] = PlayerToken(defenderPlayer)', plugin_source)
        self.assertIn("local.Pointer == player.Pointer", plugin_source)
        self.assertNotIn("player.Index == 0", plugin_source)
        self.assertIn('var identity = player.Pointer != IntPtr.Zero', plugin_source)
        self.assertIn("[LC2CB-OWNER] kind=summary", plugin_source)
        self.assertIn('var token = $"player-{++_nextPlayerToken}";', pipe_source)
        self.assertIn('["status"] = "party_updated"', pipe_source)
        self.assertIn('["party_members"] = payload', pipe_source)
        self.assertNotIn("NickName", plugin_source)
        self.assertNotIn("PlatformUniqueID", plugin_source)

    def test_single_event_failures_degrade_without_freezing_the_session(self) -> None:
        plugin_source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "Plugin.cs"
        ).read_text(encoding="utf-8")
        pipe_source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "CombatPipeServer.cs"
        ).read_text(encoding="utf-8")

        self.assertNotIn("Bridge?.FailSession(", plugin_source)
        self.assertGreaterEqual(plugin_source.count("ReportRecoverableIssue("), 10)
        self.assertIn('"bridge.recoverable_issue"', pipe_source)
        self.assertIn('["status"] = "live"', pipe_source)
        self.assertIn('$"degraded:{detail}"', pipe_source)
        self.assertIn("Combat bridge event skipped:", pipe_source)
        self.assertIn("Combat bridge session failed: queue_overflow", pipe_source)

    def test_damage_snapshots_evict_oldest_without_clearing_the_live_set(self) -> None:
        source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "Plugin.cs"
        ).read_text(encoding="utf-8")

        self.assertIn("Dictionary<int, LinkedListNode<int>> HpSnapshotNodes", source)
        self.assertIn("LinkedList<int> HpSnapshotOrder", source)
        self.assertIn(
            "while (HpSnapshots.Count >= MaxHpSnapshots && "
            "HpSnapshotOrder.First is not null)",
            source,
        )
        self.assertIn("TryTakeHitSnapshotLocked(hit.ID, out snapshot);", source)
        self.assertIn("ResetHitSnapshots();", source)
        self.assertNotIn('ReportRecoverableIssue("damage_snapshot_overflow")', source)


if __name__ == "__main__":
    unittest.main()
