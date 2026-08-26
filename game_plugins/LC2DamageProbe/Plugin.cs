using System.Globalization;
using System.Reflection;
using System.Threading;
using BepInEx;
using BepInEx.Logging;
using BepInEx.Unity.IL2CPP;
using HarmonyLib;
using Il2CppInterop.Runtime;
using LC2;

namespace LC2DamageProbe;

[BepInPlugin(PluginGuid, PluginName, PluginVersion)]
public sealed class Plugin : BasePlugin
{
    public const string PluginGuid = "io.github.seasoncake.lc2.damageprobe";
    public const string PluginName = "LC2 Damage Probe";
    public const string PluginVersion = "0.12.0";
    internal const int MaxLoggedEvents = 5000;
    internal const int MaxHpSnapshots = 8192;

    internal static ManualLogSource ProbeLog { get; private set; } = null!;
    private static int _loggedEvents;
    private static int _limitWarningLogged;
    private static readonly object HpSnapshotLock = new();
    private static readonly Dictionary<int, HitHpSnapshot> HpSnapshots = new();
    [ThreadStatic]
    private static Stack<int> HpStack;
    [ThreadStatic]
    private static Stack<long> PlayerHpObservationStack;
    private static long _nextPlayerHpOperationId;

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
        ProbeLog = Log;
        ProbeLog.LogInfo($"{PluginName} {PluginVersion} loading; observation-only probe");

        var harmony = new Harmony(PluginGuid);
        harmony.PatchAll(Assembly.GetExecutingAssembly());

        var patched = harmony.GetPatchedMethods()
            .Where(method => method.DeclaringType?.Assembly == typeof(SettlementDataMgr).Assembly)
            .Select(method => $"{method.DeclaringType?.FullName}.{method.Name}")
            .OrderBy(name => name, StringComparer.Ordinal)
            .ToArray();
        foreach (var method in patched)
        {
            ProbeLog.LogInfo($"Patched observer: {method}");
        }

        ProbeLog.LogInfo($"{PluginName} loaded; observer patches applied = {patched.Length}");
    }

    internal static void LogBoundary(string boundary, SettlementDataMgr instance)
    {
        if (!TryReserveEvent())
        {
            return;
        }

        try
        {
            var room = instance.RoomBattleDataDto;
            if (room is null)
            {
                ProbeLog.LogInfo($"[LC2DAMAGE] kind=boundary state={boundary} room_data=null");
                return;
            }

            ProbeLog.LogInfo(
                $"[LC2DAMAGE] kind=boundary state={boundary}" +
                $" normal={Number(room.normalAttackDamage)}" +
                $" skill={Number(room.skillAttackDamage)}" +
                $" throw={Number(room.throwAttackDamage)}");
        }
        catch (Exception exception)
        {
            ProbeLog.LogWarning($"[LC2DAMAGE] boundary_probe_error type={exception.GetType().Name}");
        }
    }

    internal static void LogAttackerEvent(CreatureEvent.OnAfterHit_All_Damage_Atker argument)
    {
        LogHit("official_attacker", argument.creatureID, argument.isPL, argument.GetDisposeHitInfo());
    }

    internal static void LogDefenderEvent(CreatureEvent.OnAfterHit_All_Damage_BeAtker argument)
    {
        LogHit("official_defender", argument.creatureID, null, argument.GetDisposeHitInfo());
    }

    internal static void LogMonsterEvent(DisposeHitInfo hit)
    {
        LogHit("monster_record", null, null, hit);
    }

    internal static PlayerHpChangeState BeginPlayerHpChange(CreatureRuntimeData runtime)
        => BeginPlayerHpObservation(runtime);

    internal static PlayerHpChangeState BeginPlayerHpSet(CreatureRuntimeData runtime)
        => BeginPlayerHpObservation(runtime);

    internal static PlayerHpChangeState BeginPlayerFoodRecover(CreatureRuntimeData runtime)
        => BeginPlayerHpObservation(runtime);

    private static PlayerHpChangeState BeginPlayerHpObservation(CreatureRuntimeData runtime)
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
        CreatureRuntimeData runtime,
        float deltaValue,
        DoInjuryType doInjuryType,
        bool showFloating,
        bool isRedBlood,
        string changeSourceStr,
        PlayerHpChangeState state,
        string hook)
    {
        EndPlayerHpObservation(
            "hp_change",
            state,
            $" hook={hook}" +
            $" requested={Number(deltaValue)}" +
            $" injury_type={doInjuryType}" +
            $" show_floating={showFloating.ToString().ToLowerInvariant()}" +
            $" red_blood={isRedBlood.ToString().ToLowerInvariant()}" +
            $" source={LogToken(changeSourceStr)}");
    }

    internal static void EndPlayerHpSet(float value, PlayerHpChangeState state)
    {
        EndPlayerHpObservation(
            "hp_set",
            state,
            $" target={Number(value)} source=set_cur_hp");
    }

    internal static void EndPlayerFoodRecover(
        float foodEnergy,
        bool result,
        PlayerHpChangeState state)
    {
        EndPlayerHpObservation(
            "hp_food_recover",
            state,
            $" food_energy={Number(foodEnergy)}" +
            $" result={result.ToString().ToLowerInvariant()}" +
            $" source=full_food_energy_or_recover_hp");
    }

    private static void EndPlayerHpObservation(
        string kind,
        PlayerHpChangeState state,
        string details)
    {
        if (state is null)
        {
            return;
        }
        try
        {
            if (!TryReserveEvent())
            {
                return;
            }
            var (after, maxAfter) = ReadHp(state.Owner);
            if (after is null || maxAfter is null)
            {
                return;
            }
            var effectiveDelta = after.Value - state.Before;
            ProbeLog.LogInfo(
                $"[LC2DAMAGE] kind={kind}" +
                $" operation_id={state.OperationId}" +
                $" parent_operation_id={Optional(state.ParentOperationId)}" +
                $" depth={state.Depth}" +
                $" outermost={(state.Depth == 0).ToString().ToLowerInvariant()}" +
                $" entity={EntityId(state.Owner)}" +
                $" hp_before={Number(state.Before)}" +
                $" hp_after={Number(after)}" +
                $" hp_max_before={Number(state.MaxBefore)}" +
                $" hp_max_after={Number(maxAfter)}" +
                $" effective_delta={Number(effectiveDelta)}" +
                $" effective_heal={Number(Math.Max(0f, effectiveDelta))}" +
                details);
        }
        catch (Exception exception)
        {
            ProbeLog.LogWarning($"[LC2DAMAGE] hp_observation_error kind={kind} type={exception.GetType().Name}");
        }
        finally
        {
            EndPlayerHpObservationScope(state);
        }
    }

    private static void EndPlayerHpObservationScope(PlayerHpChangeState state)
    {
        var stack = PlayerHpObservationStack;
        if (stack is null || stack.Count == 0)
        {
            ProbeLog.LogWarning($"[LC2DAMAGE] hp_observation_stack_empty actual={state.OperationId}");
            return;
        }
        if (stack.Peek() == state.OperationId)
        {
            stack.Pop();
            return;
        }
        ProbeLog.LogWarning(
            $"[LC2DAMAGE] hp_observation_stack_mismatch expected={stack.Peek()} actual={state.OperationId}");
        stack.Clear();
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

    internal static void EndHpSnapshot(bool couldDamage, Creature instance, DisposeHitInfo hit)
    {
        try
        {
            CaptureHp(instance, hit, before: false);
            LogHpSnapshot(couldDamage, instance, hit);
        }
        finally
        {
            var stack = HpStack;
            if (stack is not null && stack.Count > 0)
            {
                if (stack.Peek() == hit.ID)
                {
                    stack.Pop();
                }
                else
                {
                    ProbeLog.LogWarning($"[LC2DAMAGE] hp_stack_mismatch expected={stack.Peek()} actual={hit.ID}");
                    stack.Clear();
                }
            }
        }
    }

    internal static void LogHpSnapshot(bool couldDamage, Creature instance, DisposeHitInfo hit)
    {
        if (instance is null || hit is null || !TryReserveEvent())
        {
            return;
        }
        try
        {
            var snapshot = GetHpSnapshot(hit.ID, instance);
            ProbeLog.LogInfo(
                $"[LC2DAMAGE] kind=hp_snapshot" +
                $" hit_id={hit.ID}" +
                $" parent_hit_id={Optional(snapshot.ParentHitId)}" +
                $" depth={snapshot.Depth}" +
                $" could_damage={couldDamage.ToString().ToLowerInvariant()}" +
                $" defender_entity={EntityId(instance)}" +
                $" hp_before={Number(snapshot.Before)}" +
                $" hp_after={Number(snapshot.After)}" +
                $" hp_max={Number(snapshot.Max)}" +
                $" applied={Number(hit.mBeHitDisposeDamageInfo.mRealHPDamage)}" +
                $" lethal={hit.mBeHitDisposeDamageInfo.mDead}");
        }
        catch (Exception exception)
        {
            ProbeLog.LogWarning($"[LC2DAMAGE] hp_snapshot_log_error type={exception.GetType().Name}");
        }
    }

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
        catch (Exception exception)
        {
            ProbeLog.LogWarning($"[LC2DAMAGE] hp_probe_error phase={(before ? "before" : "after")} type={exception.GetType().Name}");
        }
    }

    private static void LogHit(string path, int? eventCreatureId, bool? isPlayerEvent, DisposeHitInfo hit)
    {
        if (!TryReserveEvent())
        {
            return;
        }

        try
        {
            if (hit is null)
            {
                ProbeLog.LogInfo(
                    $"[LC2DAMAGE] kind=hit path={path}" +
                    $" event_creature={Optional(eventCreatureId)} hit=null");
                return;
            }

            var attacker = hit.mAtker;
            var defender = hit.mBeAtker;
            var damage = hit.mDamageInfo;
            var applied = hit.mBeHitDisposeDamageInfo;
            var hp = GetHpSnapshot(hit.ID, defender);

            ProbeLog.LogInfo(
                $"[LC2DAMAGE] kind=hit path={path}" +
                $" event_creature={Optional(eventCreatureId)}" +
                $" is_player_event={Optional(isPlayerEvent)}" +
                $" hit_id={hit.ID}" +
                $" attacker_entity={EntityId(attacker)}" +
                $" attacker_owner_entity={OwnerEntityId(attacker)}" +
                $" attacker_owner_player={OwnerPlayerEntityId(attacker)}" +
                $" attacker_master_entity={MasterEntityId(attacker)}" +
                $" attacker_is_summon={SummonFlag(attacker)}" +
                $" attacker_is_pl_summon={PlayerSummonFlag(attacker)}" +
                $" attacker_type={TypeName(attacker)}" +
                $" defender_entity={EntityId(defender)}" +
                $" defender_type={TypeName(defender)}" +
                $" defender_is_boss={BossFlag(defender)}" +
                $" defender_is_elite={EliteFlag(defender)}" +
                $" hp_before={Number(hp.Before)}" +
                $" hp_after={Number(hp.After)}" +
                $" hp_max={Number(hp.Max)}" +
                $" applied={Number(applied.mRealHPDamage)}" +
                $" pending={applied.mIsPendingHPDamage}" +
                $" lethal={applied.mDead}" +
                $" ori_final={Number(damage?.mOriFinalDamage)}" +
                $" final={Number(damage?.mFinalDamage)}" +
                $" final_clamp={Number(damage?.mFinalDamage_Clamp)}" +
                $" final_normal={Number(damage?.mFinalNormalDamage)}" +
                $" final_real={Number(damage?.mFinalRealDamage)}" +
                $" critical={Optional(damage?.mBeCrit)}" +
                $" attack_type={EnumName(damage?.mAttackType)}" +
                $" special_type={EnumName(damage?.mSpecialAttackType)}" +
                $" main_attrs={DamageAttrs(hit, mainOnly: true)}" +
                $" attrs={DamageAttrs(hit, mainOnly: false)}" +
                $" injury_type={hit.mInjuryType}");
        }
        catch (Exception exception)
        {
            ProbeLog.LogWarning(
                $"[LC2DAMAGE] hit_probe_error path={path} type={exception.GetType().Name}");
        }
    }

    private static bool TryReserveEvent()
    {
        var count = Interlocked.Increment(ref _loggedEvents);
        if (count <= MaxLoggedEvents)
        {
            return true;
        }

        if (Interlocked.Exchange(ref _limitWarningLogged, 1) == 0)
        {
            ProbeLog.LogWarning($"[LC2DAMAGE] event_limit_reached max={MaxLoggedEvents}");
        }
        return false;
    }

    private static string EntityId(Entity entity) => entity is null ? "null" : entity.EntityID.ToString(CultureInfo.InvariantCulture);

    private static string OwnerEntityId(Entity entity)
    {
        var owner = entity?.OwnerEntityInHierarchy;
        return owner is null ? "null" : owner.EntityID.ToString(CultureInfo.InvariantCulture);
    }

    private static string OwnerPlayerEntityId(Entity entity)
    {
        var creature = TryCreature(entity);
        var owner = creature?.OwnerPlayerIncludeMaster;
        var ownerCreature = owner?.OwnerCreature;
        return ownerCreature is null ? "null" : ownerCreature.EntityID.ToString(CultureInfo.InvariantCulture);
    }

    private static string MasterEntityId(Entity entity)
    {
        var master = TryCreature(entity)?.Master;
        return master is null ? "null" : master.EntityID.ToString(CultureInfo.InvariantCulture);
    }

    private static string SummonFlag(Entity entity)
    {
        var creature = TryCreature(entity);
        return creature is null ? "null" : creature.mIsSummonCreature.ToString().ToLowerInvariant();
    }

    private static string PlayerSummonFlag(Entity entity)
    {
        var creature = TryCreature(entity);
        return creature is null ? "null" : creature.IsPLSummonCreature.ToString().ToLowerInvariant();
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

    private static string BossFlag(Entity entity)
    {
        var runtime = TryMonster(entity)?.RuntimeData;
        return runtime is null ? "null" : runtime.IsBoss.ToString().ToLowerInvariant();
    }

    private static string EliteFlag(Entity entity)
    {
        var runtime = TryMonster(entity)?.RuntimeData;
        return runtime is null ? "null" : runtime.IsElite.ToString().ToLowerInvariant();
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

    private static HitHpSnapshot GetHpSnapshot(int hitId, Entity defender)
    {
        lock (HpSnapshotLock)
        {
            if (HpSnapshots.TryGetValue(hitId, out var snapshot))
            {
                return snapshot;
            }
        }
        var creature = TryCreature(defender);
        var (currentHp, maxHp) = ReadHp(creature);
        return new HitHpSnapshot { After = currentHp, Max = maxHp };
    }

    private static string TypeName(Entity entity) => entity?.GetType().Name ?? "null";

    private static string Number(float? value) => value?.ToString("R", CultureInfo.InvariantCulture) ?? "null";

    private static string Optional(int? value) => value?.ToString(CultureInfo.InvariantCulture) ?? "null";

    private static string Optional(long? value) => value?.ToString(CultureInfo.InvariantCulture) ?? "null";

    private static string Optional(bool? value) => value?.ToString().ToLowerInvariant() ?? "null";

    private static string EnumName<T>(T? value) where T : struct => value?.ToString() ?? "null";

    private static string DamageAttrs(DisposeHitInfo hit, bool mainOnly)
    {
        if (hit is null)
        {
            return "null";
        }
        try
        {
            var matches = new[]
                {
                    AttrType.Fire,
                    AttrType.Ice,
                    AttrType.Poison,
                    AttrType.Electric,
                    AttrType.Evil,
                    AttrType.Blood,
                }
                .Where(attr => mainOnly
                    ? DisposeHitInfoExtend.CheckDamageMainAttrType(hit, attr)
                    : DisposeHitInfoExtend.CheckDamageAttrType(hit, attr))
                .Select(attr => attr.ToString())
                .ToArray();
            return matches.Length == 0 ? "None" : string.Join(",", matches);
        }
        catch
        {
            return "error";
        }
    }

    private static string LogToken(string value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return "null";
        }
        return new string(value
            .Take(96)
            .Select(character => char.IsWhiteSpace(character) || character == '=' ? '_' : character)
            .ToArray());
    }
}

[HarmonyPatch(typeof(CreatureRuntimeData), nameof(CreatureRuntimeData.ChangeCurrentHp))]
internal static class PlayerHpChangePatch
{
    [HarmonyPrefix]
    private static void Prefix(CreatureRuntimeData __instance, out Plugin.PlayerHpChangeState __state)
        => __state = Plugin.BeginPlayerHpChange(__instance);

    [HarmonyPostfix]
    private static void Postfix(
        CreatureRuntimeData __instance,
        float deltaValue,
        DoInjuryType doInjuryType,
        bool showFloating,
        bool isRedBlood,
        string changeSourceStr,
        Plugin.PlayerHpChangeState __state)
        => Plugin.EndPlayerHpChange(
            __instance,
            deltaValue,
            doInjuryType,
            showFloating,
            isRedBlood,
            changeSourceStr,
            __state,
            "creature_runtime");
}

[HarmonyPatch(typeof(HeroRuntimeData), nameof(HeroRuntimeData.ChangeCurrentHp))]
internal static class PlayerHeroHpChangePatch
{
    [HarmonyPrefix]
    private static void Prefix(HeroRuntimeData __instance, out Plugin.PlayerHpChangeState __state)
        => __state = Plugin.BeginPlayerHpChange(__instance);

    [HarmonyPostfix]
    private static void Postfix(
        HeroRuntimeData __instance,
        float deltaValue,
        DoInjuryType doInjuryType,
        bool showFloating,
        bool isRedBlood,
        string changeSourceStr,
        Plugin.PlayerHpChangeState __state)
        => Plugin.EndPlayerHpChange(
            __instance,
            deltaValue,
            doInjuryType,
            showFloating,
            isRedBlood,
            changeSourceStr,
            __state,
            "hero_runtime");
}

[HarmonyPatch(typeof(CreatureRuntimeData), nameof(CreatureRuntimeData.SetCurHP))]
internal static class PlayerHpSetPatch
{
    [HarmonyPrefix]
    private static void Prefix(CreatureRuntimeData __instance, out Plugin.PlayerHpChangeState __state)
        => __state = Plugin.BeginPlayerHpSet(__instance);

    [HarmonyPostfix]
    private static void Postfix(float value, Plugin.PlayerHpChangeState __state)
        => Plugin.EndPlayerHpSet(value, __state);
}

[HarmonyPatch(typeof(CreatureRuntimeData), nameof(CreatureRuntimeData.FullFoodEnergyOrRecoverHp))]
internal static class PlayerFoodRecoverPatch
{
    [HarmonyPrefix]
    private static void Prefix(CreatureRuntimeData __instance, out Plugin.PlayerHpChangeState __state)
        => __state = Plugin.BeginPlayerFoodRecover(__instance);

    [HarmonyPostfix]
    private static void Postfix(float foodEnergy, bool __result, Plugin.PlayerHpChangeState __state)
        => Plugin.EndPlayerFoodRecover(foodEnergy, __result, __state);
}

[HarmonyPatch(typeof(SettlementDataMgr), nameof(SettlementDataMgr.OnDamageAndBossDamage))]
internal static class OfficialAttackerDamagePatch
{
    [HarmonyPostfix]
    private static void Postfix(CreatureEvent.OnAfterHit_All_Damage_Atker arg) => Plugin.LogAttackerEvent(arg);
}

[HarmonyPatch(typeof(SettlementDataMgr), nameof(SettlementDataMgr.OnTakeDamage))]
internal static class OfficialDefenderDamagePatch
{
    [HarmonyPostfix]
    private static void Postfix(CreatureEvent.OnAfterHit_All_Damage_BeAtker arg) => Plugin.LogDefenderEvent(arg);
}

[HarmonyPatch(typeof(SettlementDataMgr), nameof(SettlementDataMgr.RecordMonsterBattleData))]
internal static class MonsterDamageRecordPatch
{
    [HarmonyPostfix]
    private static void Postfix(DisposeHitInfo h) => Plugin.LogMonsterEvent(h);
}

[HarmonyPatch(typeof(BeHitExecutor_Creature), "DamageProcess")]
internal static class CreatureDamageHpPatch
{
    [HarmonyPrefix]
    private static void Prefix(DisposeHitInfo disposeHitInfo, Creature beAtker) =>
        Plugin.BeginHpSnapshot(beAtker, disposeHitInfo);

    [HarmonyPostfix]
    private static void Postfix(bool couldDamage, DisposeHitInfo disposeHitInfo, Creature beAtker)
        => Plugin.EndHpSnapshot(couldDamage, beAtker, disposeHitInfo);
}

[HarmonyPatch(typeof(SettlementDataMgr), nameof(SettlementDataMgr.OnGameRoundStart))]
internal static class RoundStartPatch
{
    [HarmonyPostfix]
    private static void Postfix(SettlementDataMgr __instance) => Plugin.LogBoundary("round_start", __instance);
}

[HarmonyPatch(typeof(SettlementDataMgr), nameof(SettlementDataMgr.RoomBattleData_RoomStart))]
internal static class RoomStartPatch
{
    [HarmonyPostfix]
    private static void Postfix(SettlementDataMgr __instance) => Plugin.LogBoundary("room_start", __instance);
}

[HarmonyPatch(typeof(SettlementDataMgr), nameof(SettlementDataMgr.RoomBattleData_RoomEnd))]
internal static class RoomEndPatch
{
    [HarmonyPostfix]
    private static void Postfix(SettlementDataMgr __instance) => Plugin.LogBoundary("room_end", __instance);
}
