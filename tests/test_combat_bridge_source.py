from __future__ import annotations

from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class CombatBridgeSourceTests(unittest.TestCase):
    def test_non_battle_damage_remains_observable_but_is_not_aggregated(self) -> None:
        source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "Plugin.cs"
        ).read_text(encoding="utf-8")

        self.assertIn('public const string PluginVersion = "0.4.5";', source)
        self.assertIn('aggregate: ShouldAggregateDamage(direction)', source)
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
        self.assertIn("OwnerPlayerIncludeMaster", plugin_source)
        self.assertIn('["owner_player_id"] = PlayerToken(attackerPlayer)', plugin_source)
        self.assertIn('["player_id"] = PlayerToken(defenderPlayer)', plugin_source)
        self.assertIn('var token = $"player-{++_nextPlayerToken}";', pipe_source)
        self.assertIn('["status"] = "party_updated"', pipe_source)
        self.assertIn('["party_members"] = payload', pipe_source)
        self.assertNotIn("NickName", plugin_source)
        self.assertNotIn("PlatformUniqueID", plugin_source)


if __name__ == "__main__":
    unittest.main()
