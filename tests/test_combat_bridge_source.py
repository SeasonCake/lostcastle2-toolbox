from __future__ import annotations

from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class CombatBridgeSourceTests(unittest.TestCase):
    def test_non_battle_damage_remains_observable_but_is_not_aggregated(self) -> None:
        source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "Plugin.cs"
        ).read_text(encoding="utf-8")

        self.assertIn('public const string PluginVersion = "1.7.0";', source)
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
        self.assertIn("private static void Prefix() => Plugin.CaptureRoomExit();", source)
        self.assertIn('CaptureSettlementCacheProbe("room_exit", force: true);', source)
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
        pipe_source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "CombatPipeServer.cs"
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
        self.assertIn("private static bool _closingActiveMapTransition;", source)
        self.assertIn(
            "_closingRoomFingerprint = _activeRoomFingerprint;",
            source,
        )
        self.assertIn(
            'public string Fingerprint => $"{RoomId}:{MapFileName}";',
            pipe_source,
        )
        self.assertIn("private static string _activeRoomFingerprint;", source)
        self.assertIn("private static string _closingRoomFingerprint;", source)
        self.assertIn("var changedRoom = _closingRoomFingerprint is not null", source)
        self.assertIn("if (!combatEvidence && !changedRoom)", source)
        self.assertIn("EnsureActiveMapSession(combatEvidence: true)", source)
        self.assertIn("_closingActiveMapTransition = false;", source)

    def test_transient_duplicate_slot_is_not_published_to_the_desktop(self) -> None:
        source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "Plugin.cs"
        ).read_text(encoding="utf-8")

        self.assertIn("var seenSlots = new HashSet<int>();", source)
        self.assertIn("!seenSlots.Add(playerIndex)", source)
        self.assertIn('ReportRecoverableIssue("party_duplicate_slot")', source)
        self.assertIn("return new List<PartyMemberSnapshot>();", source)

    def test_zero_real_damage_uses_final_damage_without_changing_positive_real_hits(self) -> None:
        source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "Plugin.cs"
        ).read_text(encoding="utf-8")

        self.assertIn("Positive(damage.mFinalDamage)", source)
        self.assertIn("ReconcileDealtSettlementDamage(", source)
        self.assertIn(
            "realDamage > 0.0\n"
            "            ? Math.Max(0.0, appliedHpDamage)\n"
            "            : Math.Max(0.0, fallbackFinalDamage)",
            source,
        )
        self.assertIn("realDamage <= 0.0 && finalDamage > 0.0", source)
        self.assertIn("RecordFinalDamageFallback(attackerPlayer, settlementDamage);", source)
        self.assertIn("final_fallback_slots=", source)
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
        self.assertNotIn(
            'ReportRecoverableIssue("damage_stack_mismatch")',
            plugin_source,
        )
        self.assertIn("damage_event_skipped=False", plugin_source)
        self.assertIn("stack_mismatches=", plugin_source)

    def test_official_party_damage_and_boss_totals_are_published_by_slot(self) -> None:
        plugin_source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "Plugin.cs"
        ).read_text(encoding="utf-8")
        pipe_source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "CombatPipeServer.cs"
        ).read_text(encoding="utf-8")

        self.assertIn("CaptureOfficialDamageTotals()", plugin_source)
        self.assertIn("GlobalManager.StageNetworkCtrl?._multiRoundDataDic", plugin_source)
        self.assertIn("_diagnosticOfficialNetworkRecords += 1;", plugin_source)
        self.assertIn("GlobalManager.StatisticsMgr?", plugin_source)
        self.assertIn(".mCurAdventureRecordSaveData?", plugin_source)
        self.assertIn(".mAdventureRecordPlayerDataList", plugin_source)
        self.assertIn("var rawSlot = record.mIndex;", plugin_source)
        self.assertIn("player?.PlatformUniqueID", plugin_source)
        self.assertIn("record?.mPlatformUniqueID", plugin_source)
        self.assertIn("new HMACSHA256(OfficialIdentityHmacKey)", plugin_source)
        self.assertIn("identityToSlot.TryGetValue(fingerprint, out var slot)", plugin_source)
        self.assertNotIn("record.mID", plugin_source)
        self.assertIn("record.mDamageValue", plugin_source)
        self.assertIn("record.mBossDamageValue", plugin_source)
        self.assertIn("SyncAdventureRecordDataEnd", plugin_source)
        self.assertIn("Plugin.FinalizeOfficialDamageSync();", plugin_source)
        self.assertNotIn("LiveDamage = settlement", plugin_source)
        self.assertNotIn("NormalizeOfficialPlayerSlot", plugin_source)
        self.assertNotIn("PlayerSlotForIdentity", plugin_source)
        self.assertNotIn("PlayerSlotAtOrdinal", plugin_source)
        self.assertIn("slot_basis=platform_identity_hmac", plugin_source)
        self.assertIn("[LC2CB-OFFICIAL] kind=summary", plugin_source)
        self.assertIn("network_records=", plugin_source)
        self.assertIn("final_ready=", plugin_source)
        self.assertIn("final_records=", plugin_source)
        self.assertIn("final_duplicate_slots=", plugin_source)
        self.assertIn("final_identity_matches=", plugin_source)
        self.assertIn("final_identity_unmatched=", plugin_source)
        self.assertIn("final_identity_collisions=", plugin_source)
        self.assertIn("final_index_mismatches=", plugin_source)
        self.assertIn("final_expected_slots=", plugin_source)
        self.assertIn("final_published_slots=", plugin_source)
        self.assertIn("final_accepted=", plugin_source)
        self.assertIn("SetEquals(expectedSlots)", plugin_source)
        self.assertIn("_diagnosticFinalOfficialRecords != expectedSlots.Count", plugin_source)
        self.assertIn("_diagnosticFinalOfficialIdentityMatches != expectedSlots.Count", plugin_source)
        self.assertIn("FinalPartyBySlot", plugin_source)
        self.assertIn("FinalOfficialBySlot", plugin_source)
        self.assertIn("CaptureFinalPartyMembers(officialBySlot)", plugin_source)
        self.assertIn("_finalOfficialAccepted && FinalOfficialBySlot.Count > 0", plugin_source)
        self.assertIn("result.Clear();", plugin_source)
        self.assertIn("raw_indices=", plugin_source)
        self.assertIn(
            "RefreshPartyRoster(force: true);\n"
            '        CaptureSettlementCacheProbe("round_end_preload", force: true);\n'
            "        PrepareRoundTransition();",
            plugin_source,
        )
        self.assertIn("public long? OfficialDamage", pipe_source)
        self.assertIn("public long? OfficialBossDamage", pipe_source)
        self.assertIn('["official_damage"] = OfficialDamage.Value', pipe_source)
        self.assertIn(
            '["official_boss_damage"] = OfficialBossDamage.Value',
            pipe_source,
        )

    def test_live_official_cache_is_identity_mapped_and_separate_from_final(self) -> None:
        plugin_source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "Plugin.cs"
        ).read_text(encoding="utf-8")

        self.assertIn("CaptureLiveOfficialDiagnostics();", plugin_source)
        self.assertIn("_adventureRecordCacheDataList", plugin_source)
        self.assertIn("mAdventureRecordDataList", plugin_source)
        self.assertIn("OfficialIdentityFingerprint(record)", plugin_source)
        self.assertIn("live_identity_matches=", plugin_source)
        self.assertIn("live_identity_unmatched=", plugin_source)
        self.assertIn("live_identity_collisions=", plugin_source)
        self.assertIn("live_read_failures=", plugin_source)
        self.assertIn("private static void CaptureLiveOfficialDiagnostics()", plugin_source)
        self.assertIn("CaptureLiveOfficialDamageTotals()", plugin_source)
        self.assertIn("CaptureLiveOfficialListByIdentity(", plugin_source)
        self.assertIn("statistics?._adventureRecordCacheDataList", plugin_source)
        self.assertIn("activeValue.Damage + cacheValue.Damage", plugin_source)
        self.assertIn("activeValue.BossDamage + cacheValue.BossDamage", plugin_source)
        self.assertIn("LastLiveOfficialBySlot", plugin_source)
        self.assertIn("_liveOfficialBaselineReady", plugin_source)
        self.assertIn("records.Count < expectedSlots.Count", plugin_source)
        self.assertIn("Game-owned NPCs can have official records", plugin_source)
        self.assertIn("acceptedSlots.SetEquals(expectedSlots)", plugin_source)
        self.assertIn("value.Damage < previous.Damage", plugin_source)
        self.assertIn("StablePartyToken(", plugin_source)
        self.assertIn("var playerSlot = PlayerSlot(player);", plugin_source)
        self.assertIn("var identitySlot = historicalSlot ?? playerIndex;", plugin_source)
        self.assertIn("liveBySlot.TryGetValue(identitySlot, out var live);", plugin_source)
        self.assertIn("PlayerSlot = playerIndex,", plugin_source)
        self.assertIn("pair.Value.OfficialIdentityFingerprint", plugin_source)
        self.assertIn("identitySlots.Length > 1", plugin_source)
        self.assertIn("tokenSlots.Length == 0 && KnownPartyBySlot.Count == 0", plugin_source)
        self.assertIn("sameOfficialIdentity", plugin_source)
        self.assertIn("candidateToken,\n                previous.PlayerId", plugin_source)
        self.assertIn("KnownPartyBySlot.Clear();", plugin_source)
        self.assertIn('ReportRecoverableIssue("party_identity_unresolved")', plugin_source)
        self.assertNotIn("var playerIndex = player.Index;", plugin_source)
        pipe_source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "CombatPipeServer.cs"
        ).read_text(encoding="utf-8")
        self.assertIn("public long? LiveDamage", pipe_source)
        self.assertIn('["live_damage"] = LiveDamage.Value', pipe_source)
        self.assertIn('["live_boss_damage"] = LiveBossDamage.Value', pipe_source)
        self.assertIn("LiveDamage = member.LiveDamage is >= 0", pipe_source)
        self.assertIn("LiveBossDamage = member.LiveBossDamage is >= 0", pipe_source)

    def test_settlement_final_network_probe_targets_are_exact_and_fail_open(self) -> None:
        source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "Plugin.cs"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "internal static readonly bool ReleaseDiagnosticsEnabled = false;",
            source,
        )
        self.assertIn(
            "if (ReleaseDiagnosticsEnabled)\n"
            "        {\n"
            "            InstallOptionalSettlementNetworkProbeHooks();\n"
            "        }",
            source,
        )
        self.assertIn('"SyncSettlementData_ClientResult"', source)
        self.assertIn('"SyncSettlementData2_Rpc"', source)
        self.assertIn('"SyncSettlementData"', source)
        self.assertIn(
            "new[] { typeof(ulong), recordType, averageType }",
            source,
        )
        self.assertIn(
            "typeof(Il2CppSystem.Collections.Generic.List<ulong>)",
            source,
        )
        self.assertIn(
            "var target = AccessTools.Method(\n"
            "                typeof(StageNetworkCtrl),\n"
            "                methodName,\n"
            "                parameterTypes);",
            source,
        )
        self.assertIn("if (target is null || prefix is null)", source)
        self.assertIn("_harmony.Patch(target, prefix: new HarmonyMethod(prefix));", source)
        self.assertIn("installed=false fail_open=true", source)
        self.assertIn("catch (Exception exception)", source)
        self.assertNotIn(
            "[HarmonyPatch(typeof(StageNetworkCtrl), "
            "nameof(StageNetworkCtrl.SyncSettlementData_ClientResult))]",
            source,
        )
        self.assertNotIn(
            "[HarmonyPatch(typeof(StageNetworkCtrl), "
            "nameof(StageNetworkCtrl.SyncSettlementData2_Rpc))]",
            source,
        )

    def test_release_disables_high_volume_diagnostics_but_keeps_support_signals(self) -> None:
        plugin_source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "Plugin.cs"
        ).read_text(encoding="utf-8")
        pipe_source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "CombatPipeServer.cs"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "if (!ReleaseDiagnosticsEnabled || !_inActiveMap || RuntimeLog is null)",
            plugin_source,
        )
        self.assertIn("if (!ReleaseDiagnosticsEnabled)", plugin_source)
        self.assertIn("loaded; read-only local bridge active", plugin_source)
        self.assertIn("Combat bridge client connected; local stream active", pipe_source)
        self.assertIn("Combat bridge transport reset:", pipe_source)
        self.assertIn("Combat bridge session failed: queue_overflow", pipe_source)

    def test_settlement_final_probe_is_anonymous_bounded_and_log_only(self) -> None:
        source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "Plugin.cs"
        ).read_text(encoding="utf-8")
        pipe_source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "CombatPipeServer.cs"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "[HarmonyPatch(typeof(StageNetworkCtrl), "
            "nameof(StageNetworkCtrl.SyncAdventureRecordDataEnd))]",
            source,
        )
        self.assertIn("Plugin.BeginOfficialDamageSync();", source)
        self.assertIn('CaptureSettlementFinalProbeSnapshot("prefix");', source)
        self.assertIn('CaptureSettlementFinalProbeSnapshot("postfix");', source)
        self.assertIn("mAdventureRecordDataList", source)
        self.assertIn("_adventureRecordCacheDataList", source)
        self.assertIn("mCurAdventureRecordSaveData?", source)
        self.assertIn("_multiRoundDataDic", source)
        self.assertIn("[LC2CB-SETTLEMENT-FINAL-PROBE] kind=boundary", source)
        self.assertIn("[LC2CB-SETTLEMENT-FINAL-PROBE] kind=record", source)
        self.assertIn("identity={identity} damage={damage} boss={bossDamage}", source)
        self.assertIn("AnonymousSettlementIdentity(record)", source)
        self.assertIn("OfficialIdentityFingerprint(record)", source)
        self.assertIn('return $"slot-{matches[0].Key}";', source)
        self.assertNotIn("matches[0].Value.PlayerId", source)
        self.assertIn('return "opaque-" + fingerprint[..tokenLength]', source)
        self.assertIn(
            "internal const int MaxSettlementFinalProbeNetworkSamples = 128;",
            source,
        )
        self.assertIn(
            "internal const int MaxSettlementFinalProbeRecordsPerSurface = 32;",
            source,
        )
        self.assertIn("SettlementFinalProbeNetworkVectors.Contains(vector)", source)
        self.assertIn("sync_end_boundaries_preserved=true", source)

        probe_start = source.index("internal static void CaptureSettlementNetworkRecord(")
        probe_end = source.index("private static void CaptureSettlementCacheProbe(")
        probe_source = source[probe_start:probe_end]
        self.assertNotIn("mPlatformUniqueID", probe_source)
        self.assertNotIn("pair.Key", probe_source)
        self.assertNotIn("Bridge", probe_source)
        self.assertNotIn("Publish", probe_source)
        self.assertNotIn("Emit", probe_source)
        self.assertNotIn("LC2CB-SETTLEMENT-FINAL-PROBE", pipe_source)

    def test_settlement_round_cache_probe_is_read_only_anonymous_and_post_hit(self) -> None:
        plugin_source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "Plugin.cs"
        ).read_text(encoding="utf-8")
        pipe_source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "CombatPipeServer.cs"
        ).read_text(encoding="utf-8")

        self.assertIn("CaptureSettlementCacheProbe(", plugin_source)
        self.assertIn('"attacker_post"', plugin_source)
        self.assertIn("settlement?.mCacheRoundDataDict", plugin_source)
        self.assertIn("pair.Value?.mDamageCollector", plugin_source)
        self.assertIn("collector.mAtkDmg", plugin_source)
        self.assertIn("collector.mAtkDmg_Boss", plugin_source)
        self.assertIn("player.ID", plugin_source)
        self.assertIn("player.ClientID", plugin_source)
        self.assertIn("player.TransportID", plugin_source)
        self.assertIn("if (key == 0)", plugin_source)
        self.assertIn("internal const long SettlementCacheProbeIntervalMs = 200;", plugin_source)
        self.assertIn("&& _settlementCacheProbeDamageCallsInRoom == 1;", plugin_source)
        self.assertIn("now < _nextSettlementCacheProbeReadMs", plugin_source)
        self.assertLess(
            plugin_source.index("now < _nextSettlementCacheProbeReadMs"),
            plugin_source.index("var dictAvailable = false;"),
        )
        self.assertIn("if (!force\n            && _settlementCacheProbeOrdinarySamples", plugin_source)
        self.assertIn("force_boundaries_preserved=true", plugin_source)
        self.assertIn("ordinary_suppressed=", plugin_source)
        self.assertIn("dict_duplicate_slots=", plugin_source)
        self.assertIn("dict_collisions=", plugin_source)
        self.assertIn("dict_read_failures=", plugin_source)
        self.assertIn("dict_invalid=", plugin_source)
        self.assertIn("cache_list_slots=", plugin_source)
        self.assertIn("active_slots=", plugin_source)
        self.assertIn("singleton=", plugin_source)
        self.assertIn("OpaqueSettlementCacheKey(key)", plugin_source)
        self.assertIn(
            "BitConverter.GetBytes(_settlementCacheProbeRunEpoch).CopyTo(input, 0);",
            plugin_source,
        )
        self.assertIn("dict_opaque=", plugin_source)
        self.assertIn("damage.ToString(\"R\", CultureInfo.InvariantCulture)", plugin_source)
        self.assertNotIn("pair.Key.ToString", plugin_source)
        self.assertNotIn("LiveDamage = collector", plugin_source)
        self.assertNotIn("SettlementCache", pipe_source)

    def test_registered_player_attacker_path_is_diagnostic_until_short_control(self) -> None:
        source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "Plugin.cs"
        ).read_text(encoding="utf-8")

        self.assertIn("RefreshRegisteredAttackerCallbacks();", source)
        self.assertIn(
            "registeredPlayer.RegisterCreatureEventCallback<\n"
            "                    CreatureEvent.OnAfterHit_All_Damage_Atker>(callback, 100000);",
            source,
        )
        self.assertIn("ObserveRegisteredAttacker", source)
        self.assertIn("ObserveSettlementAttacker(argument);", source)
        self.assertIn("[LC2CB-OWNER-CHECK]", source)
        self.assertIn("[LC2CB-SLOT-CONFLICT]", source)
        self.assertIn("duplicate_callback_conflicts=", source)
        self.assertIn("registered_unique=", source)
        self.assertIn("matched_unique=", source)
        self.assertIn("forwarded=", source)
        self.assertNotIn("EmitDamageWithRegisteredSlot", source)

    def test_pipe_reconnect_keeps_the_run_session_identity(self) -> None:
        source = (
            PROJECT_ROOT / "game_plugins" / "LC2CombatBridge" / "CombatPipeServer.cs"
        ).read_text(encoding="utf-8")

        self.assertIn("StartNewSessionLocked(enqueueStart: _connected);", source)
        self.assertIn("ResumeSessionLocked();", source)
        self.assertIn('"bridge.session_resume"', source)
        self.assertIn('"degraded:transport_reconnected"', source)
        self.assertNotIn("StartSessionLocked();", source)

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
