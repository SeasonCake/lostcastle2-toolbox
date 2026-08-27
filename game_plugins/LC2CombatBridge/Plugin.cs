using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Reflection;
using System.Threading;
using BepInEx;
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
    public const string PluginVersion = "0.1.0";
    internal const int MaxHpSnapshots = 8192;

    private static readonly object HpSnapshotLock = new();
    private static readonly Dictionary<int, HitHpSnapshot> HpSnapshots = new();
    [ThreadStatic]
    private static Stack<int> HpStack;
    [ThreadStatic]
    private static Stack<long> PlayerHpObservationStack;
    private static long _nextPlayerHpOperationId;

    private Harmony _harmony;
    private static CombatPipeServer Bridge;

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
    }

    public override void Load()
    {
        Bridge = new CombatPipeServer(Log);
        Bridge.Start();
        _harmony = new Harmony(PluginGuid);
        _harmony.PatchAll(Assembly.GetExecutingAssembly());
        Log.LogInfo($"{PluginName} {PluginVersion} loaded; read-only local bridge active");
    }

    public override bool Unload()
    {
        _harmony?.UnpatchSelf();
        Bridge?.Dispose();
        Bridge = null;
        return true;
    }

    internal static void BeginRound()
    {
        Bridge?.BeginGameSession();
    }

    internal static void EndRound()
    {
        Bridge?.EndGameSession();
    }

    internal static void BeginRoom()
    {
        var room = CaptureRoomLocation();
        if (room is null)
        {
            Bridge?.FailSession("location_unavailable");
            return;
        }
        Bridge?.PublishRoomStarted(room);
    }

    internal static void EndRoom(SettlementDataMgr settlement)
    {
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
        if (snapshot?.Before is null)
        {
            Bridge?.FailSession("damage_snapshot_missing");
            return;
        }
        try
        {
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
            var defender = hit.mBeAtker;
            var isBoss = BossFlag(defender);
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
                ["source_token"] = direction == "taken"
                    ? "enemy.damage"
                    : DamageSourceToken(hit.mAtker, attributes),
                ["parent_operation_id"] = snapshot.ParentHitId,
                ["nesting_depth"] = snapshot.Depth,
            };
            Bridge?.Emit("damage_resolution", aggregate: true, hookPath, fields);
        }
        catch
        {
            Bridge?.FailSession("damage_conversion_failed");
        }
    }

    internal static PlayerHpChangeState BeginPlayerHpObservation(CreatureRuntimeData runtime)
    {
        var owner = runtime?.OwnerCreature;
        if (!IsPlayerRootCreature(owner))
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
            if (requested <= 0 || effective < 0)
            {
                return;
            }
            var atCapacity = after.Value >= maxAfter.Value - 0.0001f;
            var blocked = effective <= 0.0001 && !atCapacity;
            var overflow = atCapacity ? Math.Max(0.0, requested - Math.Max(0.0, effective)) : 0.0;
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
                    ["value_before"] = Finite(state.Before),
                    ["value_after"] = Finite(after.Value),
                    ["max_before"] = Finite(state.MaxBefore),
                    ["max_after"] = Finite(maxAfter.Value),
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

    private static string EntityToken(Entity entity) =>
        entity is null ? null : $"entity:{entity.EntityID.ToString(CultureInfo.InvariantCulture)}";

    private static string NullableToken(string value)
    {
        var bounded = CombatPipeServer.Bound(value, 256);
        return string.IsNullOrWhiteSpace(bounded) ? null : bounded;
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

    private static (float? Current, float? Max) ReadHp(Creature creature)
    {
        var runtime = creature?.RuntimeData;
        if (runtime is null)
        {
            return (null, null);
        }
        return (runtime.CurHP.GetDecrypted(), runtime.MaxHP.GetDecrypted());
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

[HarmonyPatch(typeof(SettlementDataMgr), nameof(SettlementDataMgr.OnGameRoundStart))]
internal static class RoundStartPatch
{
    [HarmonyPostfix]
    private static void Postfix() => Plugin.BeginRound();
}

[HarmonyPatch(typeof(SettlementDataMgr), nameof(SettlementDataMgr.OnGameRoundEnd))]
internal static class RoundEndPatch
{
    [HarmonyPostfix]
    private static void Postfix() => Plugin.EndRound();
}

[HarmonyPatch(typeof(SettlementDataMgr), nameof(SettlementDataMgr.RoomBattleData_RoomStart))]
internal static class RoomStartPatch
{
    [HarmonyPostfix]
    private static void Postfix() => Plugin.BeginRoom();
}

[HarmonyPatch(typeof(SettlementDataMgr), nameof(SettlementDataMgr.RoomBattleData_RoomEnd))]
internal static class RoomEndPatch
{
    [HarmonyPrefix]
    private static void Prefix(SettlementDataMgr __instance) => Plugin.EndRoom(__instance);
}
