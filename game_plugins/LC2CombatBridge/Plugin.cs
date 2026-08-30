using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Reflection;
using System.Threading;
using BepInEx;
using BepInEx.Logging;
using BepInEx.Unity.IL2CPP;
using HarmonyLib;
using Il2CppInterop.Runtime;
using LC2;

namespace LC2CombatBridge;

[BepInPlugin(PluginGuid, PluginName, PluginVersion)]
public sealed class Plugin : BasePlugin
{
    public const string PluginGuid = "io.github.seasoncake.lc2.combatbridge";
    public const string PluginName = "LC2 Combat Bridge";
    public const string PluginVersion = "0.4.8";
    internal const int MaxHpSnapshots = 8192;

    private static readonly object HpSnapshotLock = new();
    private static readonly Dictionary<int, HitHpSnapshot> HpSnapshots = new();
    [ThreadStatic]
    private static Stack<int> HpStack;
    [ThreadStatic]
    private static Stack<long> PlayerHpObservationStack;
    [ThreadStatic]
    private static Stack<long> PlayerMpObservationStack;
    [ThreadStatic]
    private static long? OfficialManaRecoveryRootOperationId;
    [ThreadStatic]
    private static double OfficialManaRecoveryCovered;
    [ThreadStatic]
    private static long? OfficialManaSpendRootOperationId;
    [ThreadStatic]
    private static double OfficialManaSpendCovered;
    private static long _nextPlayerHpOperationId;
    private static long _nextPlayerMpOperationId;
    private static bool _awaitingMapEntry = true;
    private static bool _inActiveMap;
    private static bool _manaRecoveryArmed;
    private static float? _lastObservedPlayerMp;
    private static double _diagnosticManaSpent;
    private static double _diagnosticManaGained;
    private static int _diagnosticManaSpendEvents;
    private static int _diagnosticManaGainEvents;
    private static long _nextPartyRosterProbeMs;

    private Harmony _harmony;
    private static CombatPipeServer Bridge;
    private static ManualLogSource RuntimeLog;
    private static Player RegisteredRecoveryPlayer;
    private static Il2CppSystem.Action<CreatureEvent.OnRecoverMana> RecoverManaCallback;

    private sealed class HitHpSnapshot
    {
        public float? Before { get; set; }
        public float? After { get; set; }
        public float? Max { get; set; }
        public int? ParentHitId { get; set; }
        public int Depth { get; set; }
    }

    internal sealed class PlayerHpChangeState
    {
        public Creature Owner { get; init; }
        public float Before { get; init; }
        public float MaxBefore { get; init; }
        public long OperationId { get; init; }
        public long? ParentOperationId { get; init; }
        public int Depth { get; init; }
        public bool InsideDamageResolution { get; init; }
    }

    internal sealed class PlayerMpChangeState
    {
        public Creature Owner { get; init; }
        public float Before { get; init; }
        public float MaxBefore { get; init; }
        public long OperationId { get; init; }
        public long? ParentOperationId { get; init; }
        public int Depth { get; init; }
    }

    public override void Load()
    {
        RuntimeLog = Log;
        Bridge = new CombatPipeServer(Log);
        Bridge.Start();
        _harmony = new Harmony(PluginGuid);
        _harmony.PatchAll(Assembly.GetExecutingAssembly());
        Log.LogInfo($"{PluginName} {PluginVersion} loaded; read-only local bridge active");
    }

    public override bool Unload()
    {
        UnregisterRecoverManaCallback();
        _harmony?.UnpatchSelf();
        Bridge?.Dispose();
        Bridge = null;
        RuntimeLog = null;
        return true;
    }

    internal static void BeginRound()
    {
        EnsureRecoverManaCallback();
        // This hook also fires while returning to camp. Defer the reset until a
        // validated non-camp room start proves that the next map has begun.
        _awaitingMapEntry = true;
        _inActiveMap = false;
        _manaRecoveryArmed = false;
        _nextPartyRosterProbeMs = 0;
        ResetOfficialManaRecoveryCoverage();
        ResetOfficialManaSpendCoverage();
        SyncPlayerMpObservation();
        LogRoomDiagnostic("round_start");
    }

    internal static void PrepareRoundTransition()
    {
        // StageMgr.OnGameRoundStart is a final fallback for round transitions.
        // The explicit camp-preload callback closes successful/failed runs before
        // the game refills the player while returning to camp.
        _awaitingMapEntry = true;
        _inActiveMap = false;
        _manaRecoveryArmed = false;
    }

    internal static void BeginCampPreload()
    {
        PrepareRoundTransition();
        LogRoomDiagnostic("round_end_preload_camp");
    }

    internal static void EndRound()
    {
        LogManaSummary("round_end");
        LogRoomDiagnostic("round_end");
        _awaitingMapEntry = true;
        _inActiveMap = false;
        _manaRecoveryArmed = false;
        _nextPartyRosterProbeMs = 0;
        ResetOfficialManaRecoveryCoverage();
        ResetOfficialManaSpendCoverage();
        _lastObservedPlayerMp = null;
        Bridge?.EndGameSession();
    }

    internal static void BeginRoom()
    {
        EnsureRecoverManaCallback();
        var room = CaptureActiveMapLocation();
        LogRoomDiagnostic("change_room_end", room);
        if (room is null)
        {
            return;
        }
        ActivateMapSession(room);
    }

    private static bool EnsureActiveMapSession()
    {
        if (_inActiveMap)
        {
            return true;
        }
        var room = CaptureActiveMapLocation();
        if (room is null)
        {
            return false;
        }
        ActivateMapSession(room);
        return true;
    }

    private static void ActivateMapSession(RoomLocation room)
    {
        if (_awaitingMapEntry || !_inActiveMap)
        {
            _awaitingMapEntry = false;
            _manaRecoveryArmed = false;
            ResetOfficialManaRecoveryCoverage();
            ResetOfficialManaSpendCoverage();
            SyncPlayerMpObservation();
            ResetDiagnosticManaTotals();
            LogManaSummary("session_start");
            Bridge?.BeginGameSession();
        }
        _inActiveMap = true;
        Bridge?.PublishRoomStarted(room);
        RefreshPartyRoster(force: true);
    }

    private static RoomLocation CaptureActiveMapLocation()
    {
        try
        {
            return StageMgr.Instance?.IsInCamp is false ? CaptureRoomLocation() : null;
        }
        catch
        {
            return null;
        }
    }

    private static void EnsureRecoverManaCallback()
    {
        try
        {
            var player = PlayerManager.Instance?.LocalPlayer;
            if (player is null || RegisteredRecoveryPlayer?.Pointer == player.Pointer)
            {
                return;
            }
            UnregisterRecoverManaCallback();
            RecoverManaCallback ??=
                (Il2CppSystem.Action<CreatureEvent.OnRecoverMana>)
                (Action<CreatureEvent.OnRecoverMana>)EmitOfficialManaRecovery;
            player.RegisterCreatureEventCallback<CreatureEvent.OnRecoverMana>(
                RecoverManaCallback,
                0);
            RegisteredRecoveryPlayer = player;
        }
        catch (Exception exception)
        {
            RuntimeLog?.LogWarning(
                $"Mana recovery callback unavailable: {exception.GetType().Name}");
        }
    }

    private static void UnregisterRecoverManaCallback()
    {
        if (RegisteredRecoveryPlayer is null || RecoverManaCallback is null)
        {
            RegisteredRecoveryPlayer = null;
            return;
        }
        try
        {
            RegisteredRecoveryPlayer
                .UnRegisterCreatureEventCallback<CreatureEvent.OnRecoverMana>(
                    RecoverManaCallback,
                    0);
        }
        catch
        {
            // The player may already be disposed during room or plugin teardown.
        }
        RegisteredRecoveryPlayer = null;
    }

    internal static void EndRoom(SettlementDataMgr settlement)
    {
        LogManaSummary("room_end");
        LogRoomDiagnostic("room_end");
        try
        {
            var room = settlement?.RoomBattleDataDto;
            if (room is not null)
            {
                Bridge?.EmitCheckpoint(new Dictionary<string, object>
                {
                    ["normal_attack_damage"] = Finite(room.normalAttackDamage),
                    ["skill_attack_damage"] = Finite(room.skillAttackDamage),
                    ["throw_attack_damage"] = Finite(room.throwAttackDamage),
                });
            }
        }
        catch
        {
            Bridge?.FailSession("checkpoint_unavailable");
            return;
        }
        Bridge?.PublishRoomEnded();
    }

    internal static void BeginHpSnapshot(Creature instance, DisposeHitInfo hit)
    {
        CaptureHp(instance, hit, before: true);
        if (instance is null || hit is null)
        {
            return;
        }
        var stack = HpStack ??= new Stack<int>();
        lock (HpSnapshotLock)
        {
            if (!HpSnapshots.TryGetValue(hit.ID, out var snapshot))
            {
                snapshot = new HitHpSnapshot();
                HpSnapshots[hit.ID] = snapshot;
            }
            snapshot.ParentHitId = stack.Count > 0 ? stack.Peek() : null;
            snapshot.Depth = stack.Count;
        }
        stack.Push(hit.ID);
    }

    internal static void EndHpSnapshot(Creature instance, DisposeHitInfo hit)
    {
        try
        {
            CaptureHp(instance, hit, before: false);
        }
        finally
        {
            var stack = HpStack;
            if (stack is not null && stack.Count > 0)
            {
                if (hit is not null && stack.Peek() == hit.ID)
                {
                    stack.Pop();
                }
                else
                {
                    stack.Clear();
                    Bridge?.FailSession("damage_stack_mismatch");
                }
            }
        }
    }

    internal static void EmitDamage(string direction, DisposeHitInfo hit, string hookPath)
    {
        if (hit is null)
        {
            Bridge?.FailSession("damage_event_missing");
            return;
        }
        HitHpSnapshot snapshot;
        lock (HpSnapshotLock)
        {
            HpSnapshots.TryGetValue(hit.ID, out snapshot);
            HpSnapshots.Remove(hit.ID);
        }
        var defender = hit.mBeAtker;
        if (direction == "taken" && !IsLocalPlayerRootCreature(TryCreature(defender)))
        {
            return;
        }
        if (snapshot?.Before is null)
        {
            Bridge?.FailSession("damage_snapshot_missing");
            return;
        }
        try
        {
            RefreshPartyRoster(force: false);
            var damage = hit.mDamageInfo;
            var appliedInfo = hit.mBeHitDisposeDamageInfo;
            var realDamage = Positive(appliedInfo.mRealHPDamage);
            var hpBefore = Positive(snapshot.Before.Value);
            var appliedHpDamage = Math.Min(realDamage, hpBefore);
            var originalDamage = damage is null
                ? realDamage
                : Positive(damage.mOriFinalDamage);
            var settlementDamage = direction == "taken"
                ? CeilingToInt(originalDamage)
                : CeilingToInt(appliedHpDamage);
            var attributes = DamageAttributes(hit);
            var isBoss = BossFlag(defender);
            var attacker = hit.mAtker;
            var attackerPlayer = OwnerPlayer(attacker);
            var defenderPlayer = OwnerPlayer(defender);
            if (direction == "taken")
            {
                RuntimeLog?.LogInfo(
                    $"[LC2CB-TAKEN] kind=damage hit_id={Math.Max(0, hit.ID)} " +
                    $"original_raw={DiagnosticNumber(originalDamage)} " +
                    $"real_raw={DiagnosticNumber(realDamage)} " +
                    $"hp_before_raw={DiagnosticNumber(hpBefore)} " +
                    $"applied_raw={DiagnosticNumber(appliedHpDamage)} " +
                    $"settlement_display={settlementDamage} " +
                    $"mitigated_raw={DiagnosticNumber(Math.Max(0.0, originalDamage - realDamage))} " +
                    $"depth={snapshot.Depth}");
            }
            var fields = new Dictionary<string, object>
            {
                ["damage_direction"] = direction,
                ["hit_id"] = Math.Max(0, hit.ID),
                ["target_id"] = EntityToken(defender),
                ["target_kind"] = TargetKind(defender),
                ["pre_mitigation_damage"] = originalDamage,
                ["post_mitigation_damage"] = realDamage,
                ["applied_hp_damage"] = appliedHpDamage,
                ["settlement_damage"] = settlementDamage,
                ["mitigated_damage"] = Math.Max(0.0, originalDamage - realDamage),
                ["overkill_damage"] = Math.Max(0.0, realDamage - appliedHpDamage),
                ["damage_outcome"] = DamageOutcome(originalDamage, realDamage, appliedHpDamage),
                ["critical"] = damage?.mBeCrit,
                ["lethal"] = appliedInfo.mDead,
                ["is_boss"] = isBoss,
                ["damage_attributes"] = attributes,
                ["player_id"] = PlayerToken(defenderPlayer),
                ["actor_entity_id"] = EntityToken(attacker),
                ["owner_player_id"] = PlayerToken(attackerPlayer),
                ["source_entity_id"] = EntityToken(attacker),
                ["source_token"] = direction == "taken"
                    ? "enemy.damage"
                    : DamageSourceToken(attacker, attributes),
                ["parent_operation_id"] = snapshot.ParentHitId,
                ["nesting_depth"] = snapshot.Depth,
            };
            Bridge?.Emit(
                "damage_resolution",
                aggregate: ShouldAggregateDamage(direction),
                hookPath,
                fields);
        }
        catch
        {
            Bridge?.FailSession("damage_conversion_failed");
        }
    }

    internal static PlayerHpChangeState BeginPlayerHpObservation(CreatureRuntimeData runtime)
    {
        var owner = runtime?.OwnerCreature;
        if (!IsLocalPlayerRootCreature(owner))
        {
            return null;
        }
        var (before, maxBefore) = ReadHp(owner);
        if (before is null || maxBefore is null)
        {
            return null;
        }
        var stack = PlayerHpObservationStack ??= new Stack<long>();
        var operationId = Interlocked.Increment(ref _nextPlayerHpOperationId);
        var state = new PlayerHpChangeState
        {
            Owner = owner,
            Before = before.Value,
            MaxBefore = maxBefore.Value,
            OperationId = operationId,
            ParentOperationId = stack.Count > 0 ? stack.Peek() : null,
            Depth = stack.Count,
            InsideDamageResolution = HpStack is not null && HpStack.Count > 0,
        };
        stack.Push(operationId);
        return state;
    }

    internal static void EndPlayerHpChange(
        float requestedDelta,
        string sourceToken,
        PlayerHpChangeState state,
        string hookPath)
    {
        EndPlayerHpObservation(requestedDelta, sourceToken, "gain", state, hookPath);
    }

    internal static void EndPlayerHpSet(float targetValue, PlayerHpChangeState state)
    {
        var requestedDelta = state is null ? 0f : targetValue - state.Before;
        EndPlayerHpObservation(requestedDelta, "set_cur_hp", "set", state, "runtime.set_cur_hp");
    }

    internal static void EndPlayerFoodRecover(float foodEnergy, PlayerHpChangeState state)
    {
        EndPlayerHpObservation(
            foodEnergy,
            "full_food_energy_or_recover_hp",
            "gain",
            state,
            "runtime.full_food_energy_or_recover_hp");
    }

    private static void EndPlayerHpObservation(
        float requestedDelta,
        string sourceToken,
        string operation,
        PlayerHpChangeState state,
        string hookPath)
    {
        if (state is null)
        {
            return;
        }
        try
        {
            var (after, maxAfter) = ReadHp(state.Owner);
            if (after is null || maxAfter is null || state.Depth != 0)
            {
                return;
            }
            var requested = Finite(requestedDelta);
            var effective = Finite(after.Value - state.Before);
            var inActiveMap = _inActiveMap;
            if (requested > 0
                || Math.Abs(effective) > 0.0001
                || Math.Abs(maxAfter.Value - state.MaxBefore) > 0.0001)
            {
                RuntimeLog?.LogInfo(
                    $"[LC2CB-HP] kind=observation hook={hookPath} " +
                    $"source_token={DiagnosticToken(sourceToken)} " +
                    $"requested_raw={DiagnosticNumber(requested)} " +
                    $"before_raw={DiagnosticNumber(state.Before)} after_raw={DiagnosticNumber(after)} " +
                    $"effective_raw={DiagnosticNumber(effective)} " +
                    $"max_before_raw={DiagnosticNumber(state.MaxBefore)} " +
                    $"max_after_raw={DiagnosticNumber(maxAfter)} " +
                    $"in_map={inActiveMap} inside_damage={state.InsideDamageResolution}");
            }
            if (!inActiveMap)
            {
                return;
            }
            if (effective < -0.0001)
            {
                if (state.InsideDamageResolution)
                {
                    return;
                }
                Bridge?.Emit(
                    "resource_change",
                    aggregate: true,
                    hookPath,
                    new Dictionary<string, object>
                    {
                        ["resource"] = "hp",
                        ["resource_operation"] = "loss",
                        ["requested_delta"] = requested,
                        ["effective_delta"] = effective,
                        ["value_before"] = Positive(state.Before),
                        ["value_after"] = Positive(after.Value),
                        ["max_before"] = Positive(state.MaxBefore),
                        ["max_after"] = Positive(maxAfter.Value),
                        ["blocked"] = false,
                        ["overflow"] = 0.0,
                        ["source_token"] = NullableToken(sourceToken)
                            ?? "resource.self_damage",
                        ["parent_operation_id"] = state.ParentOperationId,
                        ["nesting_depth"] = state.Depth,
                    });
                return;
            }
            if (requested <= 0)
            {
                return;
            }
            var atCapacity = after.Value >= maxAfter.Value - 0.0001f;
            var blocked = effective <= 0.0001 && !atCapacity;
            var overflow = atCapacity
                ? Math.Max(0.0, requested - Math.Max(0.0, effective))
                : 0.0;
            Bridge?.Emit(
                "resource_change",
                aggregate: true,
                hookPath,
                new Dictionary<string, object>
                {
                    ["resource"] = "hp",
                    ["resource_operation"] = effective > 0 ? operation : "attempt",
                    ["requested_delta"] = requested,
                    ["effective_delta"] = effective,
                    ["value_before"] = Positive(state.Before),
                    ["value_after"] = Positive(after.Value),
                    ["max_before"] = Positive(state.MaxBefore),
                    ["max_after"] = Positive(maxAfter.Value),
                    ["blocked"] = blocked,
                    ["overflow"] = overflow,
                    ["source_token"] = NullableToken(sourceToken),
                    ["parent_operation_id"] = state.ParentOperationId,
                    ["nesting_depth"] = state.Depth,
                });
        }
        catch
        {
            Bridge?.FailSession("resource_conversion_failed");
        }
        finally
        {
            EndPlayerHpObservationScope(state);
        }
    }

    private static void EndPlayerHpObservationScope(PlayerHpChangeState state)
    {
        var stack = PlayerHpObservationStack;
        if (stack is null || stack.Count == 0 || stack.Peek() != state.OperationId)
        {
            stack?.Clear();
            Bridge?.FailSession("resource_stack_mismatch");
            return;
        }
        stack.Pop();
    }

    internal static PlayerMpChangeState BeginPlayerMpObservation(CreatureRuntimeData runtime)
    {
        var owner = runtime?.OwnerCreature;
        if (!IsLocalPlayerRootCreature(owner))
        {
            return null;
        }
        var (before, maxBefore) = ReadMp(owner);
        if (before is null || maxBefore is null)
        {
            return null;
        }
        var stack = PlayerMpObservationStack ??= new Stack<long>();
        var operationId = Interlocked.Increment(ref _nextPlayerMpOperationId);
        var state = new PlayerMpChangeState
        {
            Owner = owner,
            Before = before.Value,
            MaxBefore = maxBefore.Value,
            OperationId = operationId,
            ParentOperationId = stack.Count > 0 ? stack.Peek() : null,
            Depth = stack.Count,
        };
        stack.Push(operationId);
        return state;
    }

    internal static void EndPlayerMpObservation(
        float requestedDelta,
        PlayerMpChangeState state,
        string hookPath)
    {
        if (state is null)
        {
            return;
        }
        try
        {
            var (after, maxAfter) = ReadMp(state.Owner);
            if (after is null || maxAfter is null)
            {
                return;
            }
            var observedBeforeRaw = _lastObservedPlayerMp;
            var requested = Finite(requestedDelta);
            var effective = Finite(after.Value - state.Before);
            var officialCovered = state.Depth == 0
                ? TakeOfficialManaRecoveryCoverage(state.OperationId)
                : 0.0;
            var sameOperationSpendRaw = state.Depth == 0
                ? TakeOfficialManaSpendCoverage()
                : 0.0;
            var fallbackGain = state.Depth == 0
                && _inActiveMap
                && _manaRecoveryArmed
                ? ReconcileFallbackManaRecovery(
                    state.Before,
                    after.Value,
                    sameOperationSpendRaw,
                    officialCovered,
                    observedBeforeRaw ?? state.Before)
                : 0.0;
            var aggregateFallback = fallbackGain > 0.0001;
            if (state.Depth == 0)
            {
                _lastObservedPlayerMp = after.Value;
            }
            if (!ShouldEmitMpObservation(requested, effective, fallbackGain))
            {
                return;
            }
            var operation = aggregateFallback
                ? "gain"
                : effective < -0.0001
                    ? "spend"
                    : effective > 0.0001
                        ? "gain"
                        : "attempt";
            var sourceToken = aggregateFallback
                ? "resource.mana_recovery"
                : requested < 0 || effective < 0
                    ? "resource.skill_cost"
                    : "resource.mana_recovery";
            var atCapacity = after.Value >= maxAfter.Value - 0.0001f;
            var blocked = !aggregateFallback
                && Math.Abs(effective) <= 0.0001
                && Math.Abs(requested) > 0.0001;
            var overflow = !aggregateFallback && requested > 0 && atCapacity
                ? Math.Max(0.0, requested - Math.Max(0.0, effective))
                : 0.0;
            if (aggregateFallback)
            {
                _diagnosticManaGained += fallbackGain;
                _diagnosticManaGainEvents += 1;
                RuntimeLog?.LogInfo(
                    $"[LC2CB-MP] kind=runtime_gain hook={hookPath} " +
                    $"before_raw={DiagnosticNumber(state.Before)} " +
                    $"after_raw={DiagnosticNumber(after)} effective_raw={DiagnosticNumber(effective)} " +
                    $"observed_before_raw={DiagnosticNumber(observedBeforeRaw)} " +
                    $"same_operation_spend_raw={DiagnosticNumber(sameOperationSpendRaw)} " +
                    $"official_covered={DiagnosticNumber(officialCovered)} " +
                    $"fallback_raw={DiagnosticNumber(fallbackGain)} " +
                    $"armed={_manaRecoveryArmed} in_map={_inActiveMap}");
            }
            Bridge?.Emit(
                "resource_change",
                aggregate: aggregateFallback,
                hookPath,
                new Dictionary<string, object>
                {
                    ["resource"] = "mp",
                    ["resource_operation"] = operation,
                    ["requested_delta"] = aggregateFallback ? fallbackGain : requested,
                    ["effective_delta"] = aggregateFallback ? fallbackGain : effective,
                    ["value_before"] = Positive(state.Before),
                    ["value_after"] = Positive(after.Value),
                    ["max_before"] = Positive(state.MaxBefore),
                    ["max_after"] = Positive(maxAfter.Value),
                    ["blocked"] = blocked,
                    ["overflow"] = overflow,
                    ["source_token"] = sourceToken,
                    ["parent_operation_id"] = state.ParentOperationId,
                    ["nesting_depth"] = state.Depth,
                });
        }
        catch
        {
            Bridge?.FailSession("mp_resource_conversion_failed");
        }
        finally
        {
            var stack = PlayerMpObservationStack;
            if (stack is null || stack.Count == 0 || stack.Peek() != state.OperationId)
            {
                stack?.Clear();
                ResetOfficialManaRecoveryCoverage();
                ResetOfficialManaSpendCoverage();
                Bridge?.FailSession("mp_resource_stack_mismatch");
            }
            else
            {
                stack.Pop();
                if (state.Depth == 0)
                {
                    ResetOfficialManaSpendCoverage();
                }
            }
        }
    }

    internal static void EmitOfficialManaSpend(CreatureEvent.OnUseMana arg)
    {
        try
        {
            EnsureRecoverManaCallback();
            var entity = EntityMgr.Instance?.GetEntity(arg.creatureID);
            var creature = TryCreature(entity);
            if (!IsLocalPlayerRootCreature(creature))
            {
                return;
            }
            var spentRaw = Positive(arg.useMana);
            var spentDisplay = DisplayMpAmount(arg.useMana);
            if (spentRaw <= 0.0001 || !EnsureActiveMapSession())
            {
                return;
            }
            _manaRecoveryArmed = true;
            TrackOfficialManaSpend(spentRaw);
            _diagnosticManaSpent += spentRaw;
            _diagnosticManaSpendEvents += 1;
            var (currentRaw, maxRaw) = ReadMp(creature);
            RuntimeLog?.LogInfo(
                $"[LC2CB-MP] kind=spend raw={DiagnosticNumber(arg.useMana)} " +
                $"display={DiagnosticNumber(spentDisplay)} current_raw={DiagnosticNumber(currentRaw)} " +
                $"current_display={DiagnosticDisplayMp(currentRaw)} max_raw={DiagnosticNumber(maxRaw)} " +
                $"last_observed_raw={DiagnosticNumber(_lastObservedPlayerMp)} " +
                $"events={_diagnosticManaSpendEvents} total={DiagnosticNumber(_diagnosticManaSpent)}");
            if (currentRaw is not null && float.IsFinite(currentRaw.Value))
            {
                // The official callback observes the authoritative post-spend
                // value. Keep it as the sequential baseline so an enclosing
                // runtime call can reveal a refund even when its own net delta
                // remains zero or negative.
                _lastObservedPlayerMp = currentRaw.Value;
            }
            Bridge?.Emit(
                "resource_change",
                aggregate: true,
                "settlement.official_mana_spend",
                new Dictionary<string, object>
                {
                    ["resource"] = "mp",
                    ["resource_operation"] = "spend",
                    ["requested_delta"] = -spentRaw,
                    ["effective_delta"] = -spentRaw,
                    ["value_before"] = null,
                    ["value_after"] = null,
                    ["max_before"] = null,
                    ["max_after"] = null,
                    ["blocked"] = false,
                    ["overflow"] = 0.0,
                    ["source_token"] = "resource.skill_cost",
                    ["actor_entity_id"] = EntityToken(creature),
                    ["trigger_kind"] = "skill_use",
                    ["parent_operation_id"] = null,
                    ["nesting_depth"] = 0,
                });
        }
        catch
        {
            Bridge?.FailSession("mp_spend_conversion_failed");
        }
    }

    internal static void EmitOfficialManaRecovery(CreatureEvent.OnRecoverMana arg)
    {
        try
        {
            var entity = EntityMgr.Instance?.GetEntity(arg.creatureID);
            var creature = TryCreature(entity);
            if (!IsLocalPlayerRootCreature(creature))
            {
                return;
            }
            var (afterRaw, maxAfterRaw) = ReadMp(creature);
            var beforeRaw = _lastObservedPlayerMp;
            if (afterRaw is null || maxAfterRaw is null)
            {
                return;
            }
            _lastObservedPlayerMp = afterRaw.Value;
            var beforeDisplay = beforeRaw is null
                ? (double?)null
                : DisplayMpValue(beforeRaw.Value);
            var afterDisplay = DisplayMpValue(afterRaw.Value);
            var maxAfterDisplay = DisplayMpValue(maxAfterRaw.Value);
            var sameOperationSpendRaw = TakeOfficialManaSpendCoverage();
            var effectiveRaw = beforeRaw is null
                ? 0.0
                : ReconcileOfficialManaRecovery(
                    beforeRaw.Value,
                    afterRaw.Value,
                    sameOperationSpendRaw);
            var effectiveDisplay = DisplayMpAmount((float)effectiveRaw);
            RuntimeLog?.LogInfo(
                $"[LC2CB-MP] kind=recovery before_raw={DiagnosticNumber(beforeRaw)} " +
                $"after_raw={DiagnosticNumber(afterRaw)} before_display={DiagnosticNumber(beforeDisplay)} " +
                $"after_display={DiagnosticNumber(afterDisplay)} " +
                $"same_operation_spend_raw={DiagnosticNumber(sameOperationSpendRaw)} " +
                $"effective_raw={DiagnosticNumber(effectiveRaw)} " +
                $"effective_display={DiagnosticNumber(effectiveDisplay)} " +
                $"armed={_manaRecoveryArmed} in_map={_inActiveMap}");
            if (beforeRaw is null || !_inActiveMap || !_manaRecoveryArmed)
            {
                return;
            }
            // OnRecoverMana reports the post-recovery target, not the delta.
            // Accumulate the raw before/after difference and round only at the UI
            // boundary; rounding every callback can bias a long run.
            if (effectiveRaw <= 0.0001)
            {
                return;
            }
            _diagnosticManaGained += effectiveRaw;
            _diagnosticManaGainEvents += 1;
            TrackOfficialManaRecovery(effectiveRaw);
            Bridge?.Emit(
                "resource_change",
                aggregate: true,
                "player.official_mana_recovery",
                new Dictionary<string, object>
                {
                    ["resource"] = "mp",
                    ["resource_operation"] = "gain",
                    ["requested_delta"] = effectiveRaw,
                    ["effective_delta"] = effectiveRaw,
                    ["value_before"] = Positive(beforeRaw.Value),
                    ["value_after"] = Positive(afterRaw.Value),
                    ["max_before"] = Positive(maxAfterRaw.Value),
                    ["max_after"] = Positive(maxAfterRaw.Value),
                    ["blocked"] = false,
                    ["overflow"] = 0.0,
                    ["source_token"] = "resource.mana_recovery",
                    ["actor_entity_id"] = EntityToken(creature),
                    ["parent_operation_id"] = null,
                    ["nesting_depth"] = 0,
                });
        }
        catch
        {
            Bridge?.FailSession("mp_recovery_conversion_failed");
        }
    }

    private static RoomLocation CaptureRoomLocation()
    {
        try
        {
            var stage = StageMgr.Instance;
            var stageLevel = (int)stage.CurStageLevel;
            var roomIndex = stage.CurRoomIndex;
            var scenarioId = CombatPipeServer.Bound(stage.CurScenario.ToString(), 128);
            var mapFileName = CombatPipeServer.Bound(stage.CurRoomInfo?.mapFileName, 256);
            if (
                stageLevel < 0
                || stageLevel > 6
                || !ValidRoomIndex(roomIndex)
                || string.IsNullOrWhiteSpace(scenarioId)
                || string.IsNullOrWhiteSpace(mapFileName))
            {
                return null;
            }
            return new RoomLocation
            {
                StageLevel = stageLevel,
                ScenarioId = scenarioId,
                RoomIndex = roomIndex,
                MapFileName = mapFileName,
            };
        }
        catch
        {
            return null;
        }
    }

    private static bool ValidRoomIndex(int value) =>
        value is >= 0 and <= 10 or 99 or 100 or 101;

    private static void ResetDiagnosticManaTotals()
    {
        _diagnosticManaSpent = 0.0;
        _diagnosticManaGained = 0.0;
        _diagnosticManaSpendEvents = 0;
        _diagnosticManaGainEvents = 0;
    }

    internal static double ReconcileOfficialManaRecovery(
        double beforeRaw,
        double afterRaw,
        double sameOperationSpendRaw)
    {
        if (!double.IsFinite(beforeRaw) || !double.IsFinite(afterRaw))
        {
            return 0.0;
        }
        var pairedSpend = double.IsFinite(sameOperationSpendRaw)
            ? Math.Max(0.0, sameOperationSpendRaw)
            : 0.0;
        return Math.Max(0.0, afterRaw - beforeRaw + pairedSpend);
    }

    internal static bool ShouldEmitMpObservation(
        double requestedRaw,
        double effectiveRaw,
        double fallbackGainRaw) =>
        Math.Abs(requestedRaw) > 0.0001
        || Math.Abs(effectiveRaw) > 0.0001
        || fallbackGainRaw > 0.0001;

    internal static double ReconcileFallbackManaRecovery(
        double beforeRaw,
        double afterRaw,
        double sameOperationSpendRaw,
        double officialCoveredRaw,
        double observedBeforeRaw)
    {
        var rootedRecoveryRaw = ReconcileOfficialManaRecovery(
            beforeRaw,
            afterRaw,
            sameOperationSpendRaw);
        var sequentialRecoveryRaw = double.IsFinite(observedBeforeRaw)
            ? Math.Max(0.0, afterRaw - observedBeforeRaw)
            : 0.0;
        var recoveredRaw = Math.Max(rootedRecoveryRaw, sequentialRecoveryRaw);
        var coveredRaw = double.IsFinite(officialCoveredRaw)
            ? Math.Max(0.0, officialCoveredRaw)
            : 0.0;
        return Math.Max(0.0, recoveredRaw - coveredRaw);
    }

    private static void TrackOfficialManaSpend(double spentRaw)
    {
        var stack = PlayerMpObservationStack;
        if (stack is null || stack.Count == 0 || spentRaw <= 0.0001)
        {
            return;
        }
        var rootOperationId = stack.Last();
        if (OfficialManaSpendRootOperationId != rootOperationId)
        {
            OfficialManaSpendRootOperationId = rootOperationId;
            OfficialManaSpendCovered = 0.0;
        }
        OfficialManaSpendCovered += spentRaw;
    }

    private static double TakeOfficialManaSpendCoverage()
    {
        var stack = PlayerMpObservationStack;
        if (stack is null || stack.Count == 0)
        {
            return 0.0;
        }
        var rootOperationId = stack.Last();
        if (OfficialManaSpendRootOperationId != rootOperationId)
        {
            return 0.0;
        }
        var covered = OfficialManaSpendCovered;
        OfficialManaSpendCovered = 0.0;
        return covered;
    }

    private static void ResetOfficialManaSpendCoverage()
    {
        OfficialManaSpendRootOperationId = null;
        OfficialManaSpendCovered = 0.0;
    }

    private static void TrackOfficialManaRecovery(double effectiveRaw)
    {
        var stack = PlayerMpObservationStack;
        if (stack is null || stack.Count == 0)
        {
            return;
        }
        var rootOperationId = stack.Last();
        if (OfficialManaRecoveryRootOperationId != rootOperationId)
        {
            OfficialManaRecoveryRootOperationId = rootOperationId;
            OfficialManaRecoveryCovered = 0.0;
        }
        OfficialManaRecoveryCovered += effectiveRaw;
    }

    private static double TakeOfficialManaRecoveryCoverage(long rootOperationId)
    {
        var covered = OfficialManaRecoveryRootOperationId == rootOperationId
            ? OfficialManaRecoveryCovered
            : 0.0;
        ResetOfficialManaRecoveryCoverage();
        return covered;
    }

    private static void ResetOfficialManaRecoveryCoverage()
    {
        OfficialManaRecoveryRootOperationId = null;
        OfficialManaRecoveryCovered = 0.0;
    }

    private static void LogManaSummary(string point) =>
        RuntimeLog?.LogInfo(
            $"[LC2CB-MP] kind=summary point={point} " +
            $"spend_events={_diagnosticManaSpendEvents} spent={DiagnosticNumber(_diagnosticManaSpent)} " +
            $"gain_events={_diagnosticManaGainEvents} gained={DiagnosticNumber(_diagnosticManaGained)} " +
            $"net={DiagnosticNumber(_diagnosticManaGained - _diagnosticManaSpent)} " +
            $"last_observed_raw={DiagnosticNumber(_lastObservedPlayerMp)}");

    private static void LogRoomDiagnostic(string callback, RoomLocation room = null)
    {
        try
        {
            var stage = StageMgr.Instance;
            RuntimeLog?.LogInfo(
                $"[LC2CB-ROOM] callback={callback} valid={room is not null} " +
                $"is_camp={stage?.IsInCamp} non_battle={stage?.IsNonBattleRoom()} " +
                $"stage={(stage is null ? "null" : ((int)stage.CurStageLevel).ToString(CultureInfo.InvariantCulture))} " +
                $"scenario={CombatPipeServer.Bound(stage?.CurScenario.ToString(), 128)} " +
                $"room_index={(stage is null ? "null" : stage.CurRoomIndex.ToString(CultureInfo.InvariantCulture))} " +
                $"map={CombatPipeServer.Bound(stage?.CurRoomInfo?.mapFileName, 256)}");
        }
        catch (Exception exception)
        {
            RuntimeLog?.LogWarning(
                $"[LC2CB-ROOM] callback={callback} diagnostic_failed={exception.GetType().Name}");
        }
    }

    private static string DiagnosticDisplayMp(float? raw) =>
        raw is null ? "null" : DiagnosticNumber(DisplayMpValue(raw.Value));

    private static string DiagnosticNumber(float? value) =>
        value is null ? "null" : DiagnosticNumber((double)value.Value);

    private static string DiagnosticNumber(float value) =>
        DiagnosticNumber((double)value);

    private static string DiagnosticNumber(double? value) =>
        value is null ? "null" : DiagnosticNumber(value.Value);

    private static string DiagnosticNumber(double value) =>
        double.IsFinite(value)
            ? value.ToString("R", CultureInfo.InvariantCulture)
            : "non_finite";

    private static void CaptureHp(Creature instance, DisposeHitInfo hit, bool before)
    {
        if (instance is null || hit is null)
        {
            return;
        }
        try
        {
            var (currentHp, maxHp) = ReadHp(instance);
            lock (HpSnapshotLock)
            {
                if (HpSnapshots.Count >= MaxHpSnapshots && !HpSnapshots.ContainsKey(hit.ID))
                {
                    HpSnapshots.Clear();
                    Bridge?.FailSession("damage_snapshot_overflow");
                    return;
                }
                if (!HpSnapshots.TryGetValue(hit.ID, out var snapshot))
                {
                    snapshot = new HitHpSnapshot();
                    HpSnapshots[hit.ID] = snapshot;
                }
                if (before)
                {
                    snapshot.Before = currentHp;
                    snapshot.Max = maxHp;
                }
                else
                {
                    snapshot.After = currentHp;
                    snapshot.Max ??= maxHp;
                }
            }
        }
        catch
        {
            Bridge?.FailSession("damage_snapshot_failed");
        }
    }

    private static string[] DamageAttributes(DisposeHitInfo hit)
    {
        return new[]
            {
                AttrType.Fire,
                AttrType.Ice,
                AttrType.Poison,
                AttrType.Electric,
                AttrType.Evil,
                AttrType.Blood,
            }
            .Where(attr => DisposeHitInfoExtend.CheckDamageAttrType(hit, attr))
            .Select(attr => attr.ToString())
            .ToArray();
    }

    private static string DamageSourceToken(Entity attacker, string[] attributes)
    {
        var creature = TryCreature(attacker);
        if (creature?.IsPLSummonCreature is true)
        {
            return "combat.summon";
        }
        return attributes.Length > 0 ? "combat.player.element" : "combat.player.normal";
    }

    private static string DamageOutcome(double original, double resolved, double applied)
    {
        if (applied > 0)
        {
            return "applied";
        }
        if (original > 0 && resolved <= 0)
        {
            return "absorbed";
        }
        return original > 0 ? "blocked" : "unknown";
    }

    private static string TargetKind(Entity entity)
    {
        var monster = TryMonster(entity)?.RuntimeData;
        if (monster is not null)
        {
            if (monster.IsBoss)
            {
                return "boss";
            }
            return monster.IsElite ? "elite" : "normal";
        }
        return IsPlayerRootCreature(TryCreature(entity)) ? "player" : "unknown";
    }

    private static bool? BossFlag(Entity entity)
    {
        var runtime = TryMonster(entity)?.RuntimeData;
        return runtime is null ? null : runtime.IsBoss;
    }

    private static bool ShouldAggregateDamage(string direction)
    {
        if (!string.Equals(direction, "dealt", StringComparison.Ordinal))
        {
            return true;
        }
        // Non-battle rooms can contain target dummies that participate in the
        // official attacker callback and report IsBoss=true, while the game's
        // end-of-run settlement excludes them. Use the game's own room semantic
        // instead of guessing from map filenames or room indices.
        try
        {
            return StageMgr.Instance?.IsNonBattleRoom() is not true;
        }
        catch
        {
            return true;
        }
    }

    private static string EntityToken(Entity entity) =>
        entity is null ? null : $"entity:{entity.EntityID.ToString(CultureInfo.InvariantCulture)}";

    private static void RefreshPartyRoster(bool force)
    {
        var now = Environment.TickCount64;
        if (!force && now < _nextPartyRosterProbeMs)
        {
            return;
        }
        _nextPartyRosterProbeMs = now + 1000;
        var members = CapturePartyMembers();
        if (members.Count > 0)
        {
            Bridge?.PublishPartyUpdated(members);
        }
    }

    private static List<PartyMemberSnapshot> CapturePartyMembers()
    {
        var result = new List<PartyMemberSnapshot>();
        try
        {
            var manager = PlayerManager.Instance;
            var players = manager?.PlayerList;
            var local = manager?.LocalPlayer;
            if (players is not null)
            {
                var seen = new HashSet<string>(StringComparer.Ordinal);
                for (var index = 0; index < players.Count && result.Count < 8; index += 1)
                {
                    var player = players[index];
                    var token = PlayerToken(player);
                    if (player is null || token is null || !seen.Add(token))
                    {
                        continue;
                    }
                    var playerIndex = player.Index;
                    result.Add(new PartyMemberSnapshot
                    {
                        PlayerId = token,
                        PlayerSlot = playerIndex is >= 0 and <= 7 ? playerIndex : null,
                        IsLocal = local is not null && local.Pointer == player.Pointer,
                    });
                }
            }
            if (result.Count == 0 && local is not null)
            {
                var token = PlayerToken(local);
                if (token is not null)
                {
                    var playerIndex = local.Index;
                    result.Add(new PartyMemberSnapshot
                    {
                        PlayerId = token,
                        PlayerSlot = playerIndex is >= 0 and <= 7 ? playerIndex : null,
                        IsLocal = true,
                    });
                }
            }
        }
        catch (Exception exception)
        {
            RuntimeLog?.LogWarning(
                $"Party snapshot unavailable: {exception.GetType().Name}");
        }
        return result;
    }

    private static Player OwnerPlayer(Entity entity)
    {
        try
        {
            return TryCreature(entity)?.OwnerPlayerIncludeMaster;
        }
        catch
        {
            return null;
        }
    }

    private static string PlayerToken(Player player)
    {
        if (player is null)
        {
            return null;
        }
        try
        {
            var identity = player.ID != 0
                ? $"id:{player.ID.ToString(CultureInfo.InvariantCulture)}"
                : player.ClientID != 0
                    ? $"client:{player.ClientID.ToString(CultureInfo.InvariantCulture)}"
                    : player.TransportID != 0
                        ? $"transport:{player.TransportID.ToString(CultureInfo.InvariantCulture)}"
                        : $"slot:{player.Index.ToString(CultureInfo.InvariantCulture)}";
            return Bridge?.GetPlayerToken(identity);
        }
        catch
        {
            return null;
        }
    }

    private static string NullableToken(string value)
    {
        var bounded = CombatPipeServer.Bound(value, 256);
        return string.IsNullOrWhiteSpace(bounded) ? null : bounded;
    }

    private static string DiagnosticToken(string value)
    {
        var bounded = CombatPipeServer.Bound(value, 128);
        return string.IsNullOrWhiteSpace(bounded)
            ? "null"
            : bounded
                .Replace("\r", "\\r", StringComparison.Ordinal)
                .Replace("\n", "\\n", StringComparison.Ordinal)
                .Replace("\t", "\\t", StringComparison.Ordinal)
                .Replace(" ", "_", StringComparison.Ordinal);
    }

    private static Creature TryCreature(Entity entity)
    {
        if (entity is null)
        {
            return null;
        }
        try
        {
            return entity.TryCast<Creature>();
        }
        catch
        {
            return null;
        }
    }

    private static Monster TryMonster(Entity entity)
    {
        if (entity is null)
        {
            return null;
        }
        try
        {
            return entity.TryCast<Monster>();
        }
        catch
        {
            return null;
        }
    }

    private static bool IsPlayerRootCreature(Creature creature)
    {
        if (creature is null)
        {
            return false;
        }
        try
        {
            var playerCreature = creature.OwnerPlayerIncludeMaster?.OwnerCreature;
            return playerCreature is not null && playerCreature.EntityID == creature.EntityID;
        }
        catch
        {
            return false;
        }
    }

    private static bool IsLocalPlayerRootCreature(Creature creature)
    {
        if (!IsPlayerRootCreature(creature))
        {
            return false;
        }
        try
        {
            var localCreature = PlayerManager.Instance?.LocalPlayer?.OwnerCreature;
            return localCreature is not null && localCreature.EntityID == creature.EntityID;
        }
        catch
        {
            return false;
        }
    }

    private static (float? Current, float? Max) ReadHp(Creature creature)
    {
        var runtime = creature?.RuntimeData;
        if (runtime is null)
        {
            return (null, null);
        }
        return (runtime.CurHP.GetDecrypted(), runtime.MaxHP.GetDecrypted());
    }

    private static (float? Current, float? Max) ReadMp(Creature creature)
    {
        var runtime = creature?.RuntimeData;
        if (runtime is null)
        {
            return (null, null);
        }
        return (runtime.CurMP.GetDecrypted(), runtime.MaxMP.GetDecrypted());
    }

    private static void SyncPlayerMpObservation()
    {
        try
        {
            var creature = PlayerManager.Instance?.LocalPlayer?.OwnerCreature;
            var (current, _) = ReadMp(creature);
            _lastObservedPlayerMp = current is not null && float.IsFinite(current.Value)
                ? current.Value
                : null;
        }
        catch
        {
            _lastObservedPlayerMp = null;
        }
    }

    private static double DisplayMpValue(float rawValue)
    {
        if (!float.IsFinite(rawValue) || rawValue < 0f)
        {
            return 0.0;
        }
        return Math.Max(0, CreatureRuntimeData.ToCurMPInt(rawValue));
    }

    private static double DisplayMpAmount(float rawValue)
    {
        if (!float.IsFinite(rawValue) || rawValue <= 0f)
        {
            return 0.0;
        }
        // OnUseMana/OnRecoverMana use the internal float unit. Match the game's
        // own CurMP_Int conversion so the HUD reports the same visible amount.
        return Math.Max(0, CreatureRuntimeData.ToCurMPInt(rawValue));
    }

    private static double Finite(float value) =>
        float.IsFinite(value) ? value : 0.0;

    private static double Positive(float value) =>
        Math.Max(0.0, Finite(value));

    private static int CeilingToInt(double value) =>
        value >= int.MaxValue ? int.MaxValue : (int)Math.Ceiling(Math.Max(0.0, value));
}

[HarmonyPatch(typeof(CreatureRuntimeData), nameof(CreatureRuntimeData.ChangeCurrentHp))]
internal static class PlayerHpChangePatch
{
    [HarmonyPrefix]
    private static void Prefix(CreatureRuntimeData __instance, out Plugin.PlayerHpChangeState __state) =>
        __state = Plugin.BeginPlayerHpObservation(__instance);

    [HarmonyPostfix]
    private static void Postfix(
        float deltaValue,
        string changeSourceStr,
        Plugin.PlayerHpChangeState __state) =>
        Plugin.EndPlayerHpChange(deltaValue, changeSourceStr, __state, "runtime.creature_hp_change");
}

[HarmonyPatch(typeof(CreatureRuntimeData), nameof(CreatureRuntimeData.ChangeCurrentMp))]
internal static class PlayerMpChangePatch
{
    [HarmonyPrefix]
    private static void Prefix(
        CreatureRuntimeData __instance,
        out Plugin.PlayerMpChangeState __state) =>
        __state = Plugin.BeginPlayerMpObservation(__instance);

    [HarmonyPostfix]
    private static void Postfix(
        float deltaValue,
        Plugin.PlayerMpChangeState __state) =>
        Plugin.EndPlayerMpObservation(
            deltaValue,
            __state,
            "runtime.creature_mp_change");
}

[HarmonyPatch(typeof(CreatureRuntimeData), nameof(CreatureRuntimeData.UpdateMp))]
internal static class PlayerMpRecoveryPatch
{
    [HarmonyPrefix]
    private static void Prefix(
        CreatureRuntimeData __instance,
        out Plugin.PlayerMpChangeState __state) =>
        __state = Plugin.BeginPlayerMpObservation(__instance);

    [HarmonyPostfix]
    private static void Postfix(Plugin.PlayerMpChangeState __state) =>
        Plugin.EndPlayerMpObservation(0f, __state, "runtime.update_mp");
}

[HarmonyPatch(typeof(HeroRuntimeData), nameof(HeroRuntimeData.ChangeCurrentHp))]
internal static class PlayerHeroHpChangePatch
{
    [HarmonyPrefix]
    private static void Prefix(HeroRuntimeData __instance, out Plugin.PlayerHpChangeState __state) =>
        __state = Plugin.BeginPlayerHpObservation(__instance);

    [HarmonyPostfix]
    private static void Postfix(
        float deltaValue,
        string changeSourceStr,
        Plugin.PlayerHpChangeState __state) =>
        Plugin.EndPlayerHpChange(deltaValue, changeSourceStr, __state, "runtime.hero_hp_change");
}

[HarmonyPatch(typeof(CreatureRuntimeData), nameof(CreatureRuntimeData.SetCurHP))]
internal static class PlayerHpSetPatch
{
    [HarmonyPrefix]
    private static void Prefix(CreatureRuntimeData __instance, out Plugin.PlayerHpChangeState __state) =>
        __state = Plugin.BeginPlayerHpObservation(__instance);

    [HarmonyPostfix]
    private static void Postfix(float value, Plugin.PlayerHpChangeState __state) =>
        Plugin.EndPlayerHpSet(value, __state);
}

[HarmonyPatch(typeof(CreatureRuntimeData), nameof(CreatureRuntimeData.FullFoodEnergyOrRecoverHp))]
internal static class PlayerFoodRecoverPatch
{
    [HarmonyPrefix]
    private static void Prefix(CreatureRuntimeData __instance, out Plugin.PlayerHpChangeState __state) =>
        __state = Plugin.BeginPlayerHpObservation(__instance);

    [HarmonyPostfix]
    private static void Postfix(float foodEnergy, Plugin.PlayerHpChangeState __state) =>
        Plugin.EndPlayerFoodRecover(foodEnergy, __state);
}

[HarmonyPatch(typeof(BeHitExecutor_Creature), "DamageProcess")]
internal static class CreatureDamageHpPatch
{
    [HarmonyPrefix]
    private static void Prefix(DisposeHitInfo disposeHitInfo, Creature beAtker) =>
        Plugin.BeginHpSnapshot(beAtker, disposeHitInfo);

    [HarmonyPostfix]
    private static void Postfix(DisposeHitInfo disposeHitInfo, Creature beAtker) =>
        Plugin.EndHpSnapshot(beAtker, disposeHitInfo);
}

[HarmonyPatch(typeof(SettlementDataMgr), nameof(SettlementDataMgr.OnDamageAndBossDamage))]
internal static class OfficialAttackerDamagePatch
{
    [HarmonyPostfix]
    private static void Postfix(CreatureEvent.OnAfterHit_All_Damage_Atker arg) =>
        Plugin.EmitDamage("dealt", arg.GetDisposeHitInfo(), "settlement.official_attacker");
}

[HarmonyPatch(typeof(SettlementDataMgr), nameof(SettlementDataMgr.OnTakeDamage))]
internal static class OfficialDefenderDamagePatch
{
    [HarmonyPostfix]
    private static void Postfix(CreatureEvent.OnAfterHit_All_Damage_BeAtker arg) =>
        Plugin.EmitDamage("taken", arg.GetDisposeHitInfo(), "settlement.official_defender");
}

[HarmonyPatch(typeof(StageMgr), nameof(StageMgr.OnGameRoundStart))]
internal static class RoundStartPatch
{
    [HarmonyPrefix]
    private static void Prefix() => Plugin.PrepareRoundTransition();

    [HarmonyPostfix]
    private static void Postfix() => Plugin.BeginRound();
}

[HarmonyPatch(typeof(PlayerManager), nameof(PlayerManager.OnGameRoundEndPreLoadCamp))]
internal static class RoundEndPreLoadCampPatch
{
    [HarmonyPrefix]
    private static void Prefix() => Plugin.BeginCampPreload();
}

[HarmonyPatch(typeof(SettlementDataMgr), nameof(SettlementDataMgr.OnGameRoundEnd))]
internal static class RoundEndPatch
{
    [HarmonyPostfix]
    private static void Postfix() => Plugin.EndRound();
}

[HarmonyPatch(typeof(SettlementDataMgr), nameof(SettlementDataMgr.OnChangeRoomEnd))]
internal static class RoomEndLocationPatch
{
    [HarmonyPostfix]
    private static void Postfix() => Plugin.BeginRoom();
}

[HarmonyPatch(typeof(SettlementDataMgr), nameof(SettlementDataMgr.OnUseMana))]
internal static class OfficialManaSpendPatch
{
    [HarmonyPostfix]
    private static void Postfix(CreatureEvent.OnUseMana arg) =>
        Plugin.EmitOfficialManaSpend(arg);
}

[HarmonyPatch(typeof(SettlementDataMgr), nameof(SettlementDataMgr.RoomBattleData_RoomEnd))]
internal static class RoomEndPatch
{
    [HarmonyPrefix]
    private static void Prefix(SettlementDataMgr __instance) => Plugin.EndRoom(__instance);
}
