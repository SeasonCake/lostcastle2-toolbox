using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
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
    public const string PluginVersion = "1.7.0";
    internal static readonly bool ReleaseDiagnosticsEnabled = false;
    internal const int MaxHpSnapshots = 8192;
    internal const int MaxAttackerDiagnosticHits = 131072;
    internal const int MaxSettlementCacheProbeOrdinarySamples = 4096;
    internal const int MaxSettlementFinalProbeNetworkSamples = 128;
    internal const int MaxSettlementFinalProbeRecordsPerSurface = 32;
    internal const long SettlementCacheProbeIntervalMs = 200;

    private static readonly object HpSnapshotLock = new();
    private static readonly Dictionary<int, HitHpSnapshot> HpSnapshots = new();
    private static readonly Dictionary<int, LinkedListNode<int>> HpSnapshotNodes = new();
    private static readonly LinkedList<int> HpSnapshotOrder = new();
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
    private static bool _closingActiveMapTransition;
    private static string _activeRoomFingerprint;
    private static string _closingRoomFingerprint;
    private static bool _manaRecoveryArmed;
    private static float? _lastObservedPlayerMp;
    private static double _diagnosticManaSpent;
    private static double _diagnosticManaGained;
    private static int _diagnosticManaSpendEvents;
    private static int _diagnosticManaGainEvents;
    private static long _diagnosticLocalDamage;
    private static long _diagnosticRemoteDamage;
    private static long _diagnosticUnattributedDamage;
    private static long _diagnosticLocalBossDamage;
    private static long _diagnosticRemoteBossDamage;
    private static long _diagnosticUnattributedBossDamage;
    private static int _diagnosticLocalDamageEvents;
    private static int _diagnosticRemoteDamageEvents;
    private static int _diagnosticUnattributedDamageEvents;
    private static int _diagnosticDamageStackMismatches;
    private static readonly int[] DiagnosticFinalFallbackEventsBySlot = new int[16];
    private static readonly long[] DiagnosticFinalFallbackDamageBySlot = new long[16];
    private static int _diagnosticFinalFallbackUnattributedEvents;
    private static long _diagnosticFinalFallbackUnattributedDamage;
    private static long _nextPartyRosterProbeMs;
    private static int _diagnosticOfficialNetworkRecords;
    private static int _diagnosticOfficialFallbackRecords;
    private static string _diagnosticOfficialRawIndices = "";
    private static bool _diagnosticLiveOfficialCacheAvailable;
    private static bool _diagnosticLiveOfficialActiveAvailable;
    private static int _diagnosticLiveOfficialCacheRecords;
    private static int _diagnosticLiveOfficialActiveRecords;
    private static int _diagnosticLiveOfficialIdentityMatches;
    private static int _diagnosticLiveOfficialIdentityUnmatched;
    private static int _diagnosticLiveOfficialIdentityCollisions;
    private static int _diagnosticLiveOfficialReadFailures;
    private static string _diagnosticLiveOfficialCacheSlots = "none";
    private static string _diagnosticLiveOfficialActiveSlots = "none";
    private static bool _finalOfficialReady;
    private static int _diagnosticFinalOfficialRecords;
    private static int _diagnosticFinalOfficialInvalidSlots;
    private static int _diagnosticFinalOfficialDuplicateSlots;
    private static string _diagnosticFinalOfficialRawIndices = "";
    private static int _diagnosticFinalOfficialIdentityMatches;
    private static int _diagnosticFinalOfficialIdentityUnmatched;
    private static int _diagnosticFinalOfficialIdentityCollisions;
    private static int _diagnosticFinalOfficialIndexMismatches;
    private static bool _finalOfficialAccepted;
    private static int _diagnosticFinalOfficialExpectedSlots;
    private static int _diagnosticFinalOfficialPublishedSlots;
    private static readonly byte[] OfficialIdentityHmacKey =
        RandomNumberGenerator.GetBytes(32);
    private static readonly Dictionary<int, KnownPartyIdentity> KnownPartyBySlot = new();
    private static readonly Dictionary<int, KnownPartyIdentity> FinalPartyBySlot = new();
    private static readonly Dictionary<int, OfficialDamageTotals> FinalOfficialBySlot = new();
    private static readonly Dictionary<int, OfficialDamageTotals> LastLiveOfficialBySlot = new();
    private static bool _liveOfficialBaselineReady;
    private static int _settlementCacheProbeRunEpoch;
    private static int _settlementCacheProbeRoomEpoch;
    private static int _settlementCacheProbeCalls;
    private static int _settlementCacheProbeSamples;
    private static int _settlementCacheProbeOrdinarySamples;
    private static int _settlementCacheProbeDamageCallsInRoom;
    private static int _settlementCacheProbeThrottledCalls;
    private static bool _settlementCacheProbeSuppressed;
    private static long _nextSettlementCacheProbeReadMs;
    private static string _lastSettlementCacheProbeVector;
    private static string _lastSettlementCacheProbeDamageRoom;
    private static readonly object SettlementFinalProbeLock = new();
    private static readonly HashSet<string> SettlementFinalProbeNetworkVectors =
        new(StringComparer.Ordinal);
    private static int _settlementFinalProbeSequence;
    private static int _settlementFinalProbeNetworkSamples;
    private static int _settlementFinalProbeDuplicateCalls;
    private static int _settlementFinalProbeSuppressedCalls;
    private static bool _settlementFinalProbeSuppressionLogged;
    private static readonly object AttackerDiagnosticLock = new();
    private static readonly Dictionary<IntPtr, RegisteredAttackerCallback>
        RegisteredAttackerCallbacks = new();
    private static readonly HashSet<string> SettlementAttackerHits = new(StringComparer.Ordinal);
    private static readonly Dictionary<string, int> RegisteredAttackerHitSlots = new(StringComparer.Ordinal);
    private static readonly int[] RegisteredSlotEvents = new int[16];
    private static readonly int[] RegisteredSlotForwardedEvents = new int[16];
    private static readonly int[] RegisteredSlotOwnerMatches = new int[16];
    private static readonly int[] RegisteredSlotOwnerConflicts = new int[16];
    private static readonly int[] RegisteredSlotOwnerUnresolved = new int[16];
    private static int _registeredDuplicateCallbackConflicts;
    private static int _loggedRegisteredSlotConflicts;

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

    private sealed class OfficialDamageTotals
    {
        public long Damage { get; set; }
        public long BossDamage { get; set; }
    }

    private sealed class KnownPartyIdentity
    {
        public string PlayerId { get; init; }
        public bool IsLocal { get; init; }
        public string OfficialIdentityFingerprint { get; init; }
    }

    private sealed class SettlementCacheKeyMatch
    {
        public HashSet<int> Slots { get; } = new();
        public HashSet<string> Bases { get; } = new(StringComparer.Ordinal);
    }

    private sealed class SettlementCacheSlotValue
    {
        public float Damage { get; init; }
        public float BossDamage { get; init; }
    }

    private sealed class RegisteredAttackerCallback
    {
        public Player Player { get; init; }
        public int PlayerSlot { get; init; }
        public Il2CppSystem.Action<CreatureEvent.OnAfterHit_All_Damage_Atker> Callback { get; init; }
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
        if (ReleaseDiagnosticsEnabled)
        {
            InstallOptionalSettlementNetworkProbeHooks();
        }
        Log.LogInfo($"{PluginName} {PluginVersion} loaded; read-only local bridge active");
    }

    private void InstallOptionalSettlementNetworkProbeHooks()
    {
        var recordType = typeof(LC2.Statistics.AdventureRecordPlayerData);
        var averageType = typeof(LC2.Statistics.AdventureRecordPlayerAverageData);
        InstallOptionalSettlementNetworkProbeHook(
            "SyncSettlementData_ClientResult",
            new[] { typeof(ulong), recordType, averageType },
            nameof(SettlementNetworkProbePatchMethods.SyncSettlementDataClientResultPrefix));
        InstallOptionalSettlementNetworkProbeHook(
            "SyncSettlementData2_Rpc",
            new[] { typeof(ulong), recordType, averageType },
            nameof(SettlementNetworkProbePatchMethods.SyncSettlementData2RpcPrefix));
        InstallOptionalSettlementNetworkProbeHook(
            "SyncSettlementData",
            new[]
            {
                typeof(ulong),
                recordType,
                averageType,
                typeof(Il2CppSystem.Collections.Generic.List<ulong>),
            },
            nameof(SettlementNetworkProbePatchMethods.SyncSettlementDataServerPrefix));
    }

    private void InstallOptionalSettlementNetworkProbeHook(
        string methodName,
        Type[] parameterTypes,
        string prefixName)
    {
        try
        {
            var target = AccessTools.Method(
                typeof(StageNetworkCtrl),
                methodName,
                parameterTypes);
            var prefix = AccessTools.Method(
                typeof(SettlementNetworkProbePatchMethods),
                prefixName);
            if (target is null || prefix is null)
            {
                Log.LogInfo(
                    "[LC2CB-SETTLEMENT-FINAL-PROBE] kind=hook " +
                    $"target={methodName} installed=false fail_open=true");
                return;
            }
            _harmony.Patch(target, prefix: new HarmonyMethod(prefix));
            Log.LogInfo(
                "[LC2CB-SETTLEMENT-FINAL-PROBE] kind=hook " +
                $"target={methodName} installed=true fail_open=true");
        }
        catch (Exception exception)
        {
            Log.LogWarning(
                "[LC2CB-SETTLEMENT-FINAL-PROBE] kind=hook " +
                $"target={methodName} installed=false fail_open=true " +
                $"error={exception.GetType().Name}");
        }
    }

    public override bool Unload()
    {
        UnregisterRecoverManaCallback();
        UnregisterAllRegisteredAttackerCallbacks();
        _harmony?.UnpatchSelf();
        Bridge?.Dispose();
        ResetHitSnapshots();
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
        if (_inActiveMap)
        {
            _closingActiveMapTransition = true;
            _closingRoomFingerprint = _activeRoomFingerprint;
        }
        _awaitingMapEntry = true;
        _inActiveMap = false;
        _manaRecoveryArmed = false;
    }

    internal static void BeginCampPreload()
    {
        RefreshPartyRoster(force: true);
        CaptureSettlementCacheProbe("round_end_preload", force: true);
        PrepareRoundTransition();
        LogRoomDiagnostic("round_end_preload_camp");
    }

    internal static void EndRound()
    {
        RefreshPartyRoster(force: true);
        CaptureSettlementCacheProbe("round_end", force: true);
        LogManaSummary("round_end");
        LogDamageOwnerSummary("round_end");
        LogRegisteredAttackerSummary("round_end");
        LogRoomDiagnostic("round_end");
        _awaitingMapEntry = true;
        _inActiveMap = false;
        _manaRecoveryArmed = false;
        _nextPartyRosterProbeMs = 0;
        ResetOfficialManaRecoveryCoverage();
        ResetOfficialManaSpendCoverage();
        _lastObservedPlayerMp = null;
        UnregisterAllRegisteredAttackerCallbacks();
        Bridge?.EndGameSession();
        _closingActiveMapTransition = false;
        _activeRoomFingerprint = null;
        _closingRoomFingerprint = null;
    }

    internal static void BeginOfficialDamageSync()
    {
        if (!_inActiveMap)
        {
            return;
        }
        CaptureSettlementFinalProbeSnapshot("prefix");
    }

    internal static void FinalizeOfficialDamageSync()
    {
        if (!_inActiveMap)
        {
            return;
        }
        CaptureSettlementFinalProbeSnapshot("postfix");
        _finalOfficialReady = true;
        RefreshPartyRoster(force: true);
        CaptureSettlementCacheProbe("final_sync", force: true);
    }

    internal static void BeginRoom()
    {
        EnsureRecoverManaCallback();
        var room = CaptureActiveMapLocation();
        LogDamageOwnerSummary("change_room_end");
        LogRegisteredAttackerSummary("change_room_end");
        ResetRegisteredAttackerDiagnostics();
        LogRoomDiagnostic("change_room_end", room);
        if (room is null)
        {
            return;
        }
        ActivateMapSession(room);
    }

    internal static void CaptureRoomExit()
    {
        RefreshPartyRoster(force: true);
        CaptureSettlementCacheProbe("room_exit", force: true);
    }

    private static bool EnsureActiveMapSession(bool combatEvidence = false)
    {
        if (_inActiveMap)
        {
            return true;
        }
        var room = CaptureActiveMapLocation(combatEvidence);
        if (room is null)
        {
            return false;
        }
        ActivateMapSession(room);
        return true;
    }

    private static void ActivateMapSession(RoomLocation room)
    {
        var beginsNewSession = _awaitingMapEntry || !_inActiveMap;
        var beginsNewRoom = beginsNewSession
            || !string.Equals(
                _activeRoomFingerprint,
                room.Fingerprint,
                StringComparison.Ordinal);
        if (beginsNewSession)
        {
            _awaitingMapEntry = false;
            _manaRecoveryArmed = false;
            ResetOfficialManaRecoveryCoverage();
            ResetOfficialManaSpendCoverage();
            SyncPlayerMpObservation();
            ResetHitSnapshots();
            ResetDiagnosticManaTotals();
            ResetDiagnosticDamageOwnerTotals();
            ResetOfficialDamageState();
            LogManaSummary("session_start");
            LogDamageOwnerSummary("session_start");
            Bridge?.BeginGameSession();
        }
        if (beginsNewRoom)
        {
            _settlementCacheProbeRoomEpoch += 1;
            _settlementCacheProbeDamageCallsInRoom = 0;
            _nextSettlementCacheProbeReadMs = 0;
            _lastSettlementCacheProbeDamageRoom = null;
        }
        _closingActiveMapTransition = false;
        _closingRoomFingerprint = null;
        _activeRoomFingerprint = room.Fingerprint;
        _inActiveMap = true;
        Bridge?.PublishRoomStarted(room);
        RefreshPartyRoster(force: true);
        CaptureSettlementCacheProbe("room_entry", force: true);
    }

    private static RoomLocation CaptureActiveMapLocation(bool combatEvidence = false)
    {
        try
        {
            var room = StageMgr.Instance?.IsInCamp is false
                ? CaptureRoomLocation()
                : null;
            if (room is null || !_closingActiveMapTransition)
            {
                return room;
            }
            var changedRoom = _closingRoomFingerprint is not null
                && !string.Equals(
                    room.Fingerprint,
                    _closingRoomFingerprint,
                    StringComparison.Ordinal);
            if (!combatEvidence && !changedRoom)
            {
                return null;
            }
            _closingActiveMapTransition = false;
            _closingRoomFingerprint = null;
            return room;
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

    private static void RefreshRegisteredAttackerCallbacks()
    {
        if (!_inActiveMap)
        {
            return;
        }
        try
        {
            var players = PlayerManager.Instance?.PlayerList;
            if (players is null)
            {
                return;
            }
            var currentPointers = new HashSet<IntPtr>();
            for (var index = 0; index < players.Count && index < 16; index += 1)
            {
                var player = players[index];
                if (player is null || player.Pointer == IntPtr.Zero)
                {
                    continue;
                }
                var playerSlot = PlayerSlot(player);
                if (playerSlot is not >= 0 or > 15)
                {
                    continue;
                }
                currentPointers.Add(player.Pointer);
                if (RegisteredAttackerCallbacks.TryGetValue(player.Pointer, out var known))
                {
                    if (known.PlayerSlot == playerSlot.Value)
                    {
                        continue;
                    }
                    UnregisterRegisteredAttackerCallback(known);
                    RegisteredAttackerCallbacks.Remove(player.Pointer);
                }
                var registeredPlayer = player;
                var registeredSlot = playerSlot.Value;
                var callback =
                    (Il2CppSystem.Action<CreatureEvent.OnAfterHit_All_Damage_Atker>)
                    (Action<CreatureEvent.OnAfterHit_All_Damage_Atker>)(argument =>
                        ObserveRegisteredAttacker(registeredPlayer, registeredSlot, argument));
                registeredPlayer.RegisterCreatureEventCallback<
                    CreatureEvent.OnAfterHit_All_Damage_Atker>(callback, 100000);
                RegisteredAttackerCallbacks[player.Pointer] = new RegisteredAttackerCallback
                {
                    Player = registeredPlayer,
                    PlayerSlot = registeredSlot,
                    Callback = callback,
                };
            }
            foreach (var pointer in RegisteredAttackerCallbacks.Keys
                .Where(pointer => !currentPointers.Contains(pointer))
                .ToArray())
            {
                UnregisterRegisteredAttackerCallback(RegisteredAttackerCallbacks[pointer]);
                RegisteredAttackerCallbacks.Remove(pointer);
            }
        }
        catch (Exception exception)
        {
            RuntimeLog?.LogWarning(
                $"Registered attacker diagnostics unavailable: {exception.GetType().Name}");
        }
    }

    private static void UnregisterAllRegisteredAttackerCallbacks()
    {
        foreach (var registration in RegisteredAttackerCallbacks.Values.ToArray())
        {
            UnregisterRegisteredAttackerCallback(registration);
        }
        RegisteredAttackerCallbacks.Clear();
    }

    private static void UnregisterRegisteredAttackerCallback(
        RegisteredAttackerCallback registration)
    {
        if (registration?.Player is null || registration.Callback is null)
        {
            return;
        }
        try
        {
            registration.Player.UnRegisterCreatureEventCallback<
                CreatureEvent.OnAfterHit_All_Damage_Atker>(registration.Callback, 100000);
        }
        catch
        {
            // Network player objects can be disposed during roster transitions.
        }
    }

    private static void ObserveRegisteredAttacker(
        Player registeredPlayer,
        int registeredSlot,
        CreatureEvent.OnAfterHit_All_Damage_Atker argument)
    {
        try
        {
            var hit = argument.GetDisposeHitInfo();
            var key = HitDiagnosticKey(hit);
            if (key is null || registeredSlot is < 0 or > 15)
            {
                return;
            }
            var ownerSlot = PlayerSlot(OwnerPlayer(hit));
            var rawAttackerId = hit?.mAtker?.EntityID;
            var forwarded = rawAttackerId is not null && argument.creatureID != rawAttackerId.Value;
            var logConflict = false;
            lock (AttackerDiagnosticLock)
            {
                RegisteredSlotEvents[registeredSlot] += 1;
                if (forwarded)
                {
                    RegisteredSlotForwardedEvents[registeredSlot] += 1;
                }
                if (ownerSlot is null)
                {
                    RegisteredSlotOwnerUnresolved[registeredSlot] += 1;
                }
                else if (ownerSlot == registeredSlot)
                {
                    RegisteredSlotOwnerMatches[registeredSlot] += 1;
                }
                else
                {
                    RegisteredSlotOwnerConflicts[registeredSlot] += 1;
                    logConflict = _loggedRegisteredSlotConflicts++ < 32;
                }
                if (RegisteredAttackerHitSlots.Count < MaxAttackerDiagnosticHits)
                {
                    if (RegisteredAttackerHitSlots.TryGetValue(key, out var previousSlot)
                        && previousSlot != registeredSlot)
                    {
                        _registeredDuplicateCallbackConflicts += 1;
                        logConflict = _loggedRegisteredSlotConflicts++ < 32;
                    }
                    else
                    {
                        RegisteredAttackerHitSlots[key] = registeredSlot;
                    }
                }
            }
            if (logConflict)
            {
                var ownerSlotText = ownerSlot?.ToString(CultureInfo.InvariantCulture) ?? "null";
                RuntimeLog?.LogWarning(
                    $"[LC2CB-SLOT-CONFLICT] registered_slot={registeredSlot} " +
                    $"owner_slot={ownerSlotText} " +
                    $"hit_id={Math.Max(0, hit?.ID ?? 0)} sender={Math.Max(0, argument.creatureID)} " +
                    $"raw={Math.Max(0, rawAttackerId ?? 0)} " +
                    $"hierarchy={Math.Max(0, hit?.mAtkerInHierarchy?.EntityID ?? 0)}");
            }
        }
        catch (Exception exception)
        {
            RuntimeLog?.LogWarning(
                $"Registered attacker event unavailable: {exception.GetType().Name}");
        }
    }

    private static void ObserveSettlementAttacker(
        CreatureEvent.OnAfterHit_All_Damage_Atker argument)
    {
        try
        {
            var key = HitDiagnosticKey(argument.GetDisposeHitInfo());
            if (key is null)
            {
                return;
            }
            lock (AttackerDiagnosticLock)
            {
                if (SettlementAttackerHits.Count < MaxAttackerDiagnosticHits)
                {
                    SettlementAttackerHits.Add(key);
                }
            }
        }
        catch
        {
        }
    }

    private static string HitDiagnosticKey(DisposeHitInfo hit)
    {
        if (hit is null)
        {
            return null;
        }
        var pointer = hit.Pointer != IntPtr.Zero
            ? hit.Pointer.ToInt64().ToString("X", CultureInfo.InvariantCulture)
            : "0";
        return $"{pointer}:{Math.Max(0, hit.ID).ToString(CultureInfo.InvariantCulture)}";
    }

    private static int? PlayerSlot(Player player)
    {
        try
        {
            return player?.Index is >= 0 and <= 15 ? player.Index : null;
        }
        catch
        {
            return null;
        }
    }

    private static bool TryHistoricalPartySlot(
        string candidateToken,
        string officialIdentityFingerprint,
        out int? historicalSlot)
    {
        historicalSlot = null;
        if (officialIdentityFingerprint is not null)
        {
            var identitySlots = KnownPartyBySlot
                .Where(pair => string.Equals(
                    pair.Value.OfficialIdentityFingerprint,
                    officialIdentityFingerprint,
                    StringComparison.Ordinal))
                .Select(pair => pair.Key)
                .Take(2)
                .ToArray();
            if (identitySlots.Length == 1)
            {
                historicalSlot = identitySlots[0];
                return true;
            }
            if (identitySlots.Length > 1)
            {
                return false;
            }
            return true;
        }
        var tokenSlots = KnownPartyBySlot
            .Where(pair => string.Equals(
                pair.Value.PlayerId,
                candidateToken,
                StringComparison.Ordinal))
            .Select(pair => pair.Key)
            .Take(2)
            .ToArray();
        if (tokenSlots.Length == 1)
        {
            historicalSlot = tokenSlots[0];
            return true;
        }
        return tokenSlots.Length == 0 && KnownPartyBySlot.Count == 0;
    }

    private static string StablePartyToken(
        string candidateToken,
        int identitySlot,
        string officialIdentityFingerprint)
    {
        if (!KnownPartyBySlot.TryGetValue(identitySlot, out var previous))
        {
            return candidateToken;
        }
        var sameOfficialIdentity = officialIdentityFingerprint is not null
            && string.Equals(
                officialIdentityFingerprint,
                previous.OfficialIdentityFingerprint,
                StringComparison.Ordinal);
        return sameOfficialIdentity
            || string.Equals(
                candidateToken,
                previous.PlayerId,
                StringComparison.Ordinal)
            ? previous.PlayerId
            : candidateToken;
    }

    private static void LogRegisteredAttackerSummary(string point)
    {
        if (!ReleaseDiagnosticsEnabled)
        {
            return;
        }
        lock (AttackerDiagnosticLock)
        {
            var values = Enumerable.Range(0, 16)
                .Where(slot => RegisteredSlotEvents[slot] > 0)
                .Select(slot =>
                {
                    var unique = RegisteredAttackerHitSlots.Count(pair => pair.Value == slot);
                    var matched = RegisteredAttackerHitSlots.Count(pair =>
                        pair.Value == slot && SettlementAttackerHits.Contains(pair.Key));
                    return $"slot={slot}:events={RegisteredSlotEvents[slot]}:" +
                        $"unique={unique}:matched={matched}:" +
                        $"forwarded={RegisteredSlotForwardedEvents[slot]}:" +
                        $"owner_match={RegisteredSlotOwnerMatches[slot]}:" +
                        $"conflict={RegisteredSlotOwnerConflicts[slot]}:" +
                        $"unresolved={RegisteredSlotOwnerUnresolved[slot]}";
                })
                .ToArray();
            var matchedHits = RegisteredAttackerHitSlots.Count(pair =>
                SettlementAttackerHits.Contains(pair.Key));
            var localSlot = PlayerSlot(PlayerManager.Instance?.LocalPlayer);
            RuntimeLog?.LogInfo(
                $"[LC2CB-OWNER-CHECK] point={point} " +
                $"local_slot={(localSlot is null ? "null" : localSlot.Value)} " +
                $"settlement_unique={SettlementAttackerHits.Count} " +
                $"registered_unique={RegisteredAttackerHitSlots.Count} " +
                $"matched_unique={matchedHits} " +
                $"duplicate_callback_conflicts={_registeredDuplicateCallbackConflicts} " +
                string.Join(" ", values));
        }
    }

    private static void ResetRegisteredAttackerDiagnostics()
    {
        lock (AttackerDiagnosticLock)
        {
            SettlementAttackerHits.Clear();
            RegisteredAttackerHitSlots.Clear();
            Array.Clear(RegisteredSlotEvents, 0, RegisteredSlotEvents.Length);
            Array.Clear(RegisteredSlotForwardedEvents, 0, RegisteredSlotForwardedEvents.Length);
            Array.Clear(RegisteredSlotOwnerMatches, 0, RegisteredSlotOwnerMatches.Length);
            Array.Clear(RegisteredSlotOwnerConflicts, 0, RegisteredSlotOwnerConflicts.Length);
            Array.Clear(RegisteredSlotOwnerUnresolved, 0, RegisteredSlotOwnerUnresolved.Length);
            _registeredDuplicateCallbackConflicts = 0;
            _loggedRegisteredSlotConflicts = 0;
        }
    }

    internal static void EndRoom(SettlementDataMgr settlement)
    {
        CaptureSettlementCacheProbe("room_exit", force: true);
        LogManaSummary("room_end");
        LogDamageOwnerSummary("room_end");
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
            Bridge?.ReportRecoverableIssue("checkpoint_unavailable");
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
            var snapshot = GetOrCreateHitSnapshotLocked(hit.ID);
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
                    var mismatchCount = Interlocked.Increment(
                        ref _diagnosticDamageStackMismatches);
                    if (mismatchCount == 1)
                    {
                        RuntimeLog?.LogWarning(
                            "[LC2CB-DAMAGE] kind=stack_mismatch action=nesting_reset " +
                            "damage_event_skipped=False");
                    }
                }
            }
        }
    }

    internal static void EmitOfficialAttacker(
        CreatureEvent.OnAfterHit_All_Damage_Atker argument)
    {
        ObserveSettlementAttacker(argument);
        var hit = argument.GetDisposeHitInfo();
        EmitDamage(
            "dealt",
            hit,
            "settlement.official_attacker");
        _settlementCacheProbeDamageCallsInRoom += 1;
        CaptureSettlementCacheProbe(
            "attacker_post",
            triggerSlot: PlayerSlot(OwnerPlayer(hit)));
    }

    internal static void EmitDamage(string direction, DisposeHitInfo hit, string hookPath)
    {
        if (hit is null)
        {
            Bridge?.ReportRecoverableIssue("damage_event_missing");
            return;
        }
        HitHpSnapshot snapshot;
        lock (HpSnapshotLock)
        {
            TryTakeHitSnapshotLocked(hit.ID, out snapshot);
        }
        var defender = hit.mBeAtker;
        if (direction == "taken" && !IsLocalPlayerRootCreature(TryCreature(defender)))
        {
            return;
        }
        if (snapshot?.Before is null)
        {
            Bridge?.ReportRecoverableIssue("damage_snapshot_missing");
            return;
        }
        if (!EnsureActiveMapSession(combatEvidence: true))
        {
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
            var finalDamage = damage is null ? 0.0 : Positive(damage.mFinalDamage);
            var dealtSettlementDamage = ReconcileDealtSettlementDamage(
                realDamage,
                appliedHpDamage,
                finalDamage);
            var originalDamage = damage is null
                ? realDamage
                : Positive(damage.mOriFinalDamage);
            var settlementDamage = direction == "taken"
                ? CeilingToInt(originalDamage)
                : CeilingToInt(dealtSettlementDamage);
            var attributes = DamageAttributes(hit);
            var isBoss = BossFlag(defender);
            var attacker = hit.mAtker;
            var attackerPlayer = OwnerPlayer(hit);
            var defenderPlayer = OwnerPlayer(defender);
            var aggregate = ShouldAggregateDamage(direction);
            if (direction == "dealt" && aggregate)
            {
                RecordDamageOwner(attackerPlayer, settlementDamage, isBoss is true);
                if (realDamage <= 0.0 && finalDamage > 0.0)
                {
                    RecordFinalDamageFallback(attackerPlayer, settlementDamage);
                }
            }
            if (direction == "taken")
            {
                LogDiagnosticInfo(
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
                aggregate,
                hookPath,
                fields);
        }
        catch
        {
            Bridge?.ReportRecoverableIssue("damage_conversion_failed");
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
                LogDiagnosticInfo(
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
            Bridge?.ReportRecoverableIssue("resource_conversion_failed");
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
            Bridge?.ReportRecoverableIssue("resource_stack_mismatch");
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
                LogDiagnosticInfo(
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
            Bridge?.ReportRecoverableIssue("mp_resource_conversion_failed");
        }
        finally
        {
            var stack = PlayerMpObservationStack;
            if (stack is null || stack.Count == 0 || stack.Peek() != state.OperationId)
            {
                stack?.Clear();
                ResetOfficialManaRecoveryCoverage();
                ResetOfficialManaSpendCoverage();
                Bridge?.ReportRecoverableIssue("mp_resource_stack_mismatch");
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
            if (spentRaw <= 0.0001 || !EnsureActiveMapSession(combatEvidence: true))
            {
                return;
            }
            _manaRecoveryArmed = true;
            TrackOfficialManaSpend(spentRaw);
            _diagnosticManaSpent += spentRaw;
            _diagnosticManaSpendEvents += 1;
            var (currentRaw, maxRaw) = ReadMp(creature);
            LogDiagnosticInfo(
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
            Bridge?.ReportRecoverableIssue("mp_spend_conversion_failed");
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
            LogDiagnosticInfo(
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
            Bridge?.ReportRecoverableIssue("mp_recovery_conversion_failed");
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

    private static void ResetDiagnosticDamageOwnerTotals()
    {
        _diagnosticLocalDamage = 0;
        _diagnosticRemoteDamage = 0;
        _diagnosticUnattributedDamage = 0;
        _diagnosticLocalBossDamage = 0;
        _diagnosticRemoteBossDamage = 0;
        _diagnosticUnattributedBossDamage = 0;
        _diagnosticLocalDamageEvents = 0;
        _diagnosticRemoteDamageEvents = 0;
        _diagnosticUnattributedDamageEvents = 0;
        _diagnosticDamageStackMismatches = 0;
        Array.Clear(
            DiagnosticFinalFallbackEventsBySlot,
            0,
            DiagnosticFinalFallbackEventsBySlot.Length);
        Array.Clear(
            DiagnosticFinalFallbackDamageBySlot,
            0,
            DiagnosticFinalFallbackDamageBySlot.Length);
        _diagnosticFinalFallbackUnattributedEvents = 0;
        _diagnosticFinalFallbackUnattributedDamage = 0;
    }

    private static void ResetOfficialDamageState()
    {
        UnregisterAllRegisteredAttackerCallbacks();
        ResetRegisteredAttackerDiagnostics();
        _finalOfficialReady = false;
        _diagnosticFinalOfficialRecords = 0;
        _diagnosticFinalOfficialInvalidSlots = 0;
        _diagnosticFinalOfficialDuplicateSlots = 0;
        _diagnosticFinalOfficialRawIndices = "";
        _diagnosticFinalOfficialIdentityMatches = 0;
        _diagnosticFinalOfficialIdentityUnmatched = 0;
        _diagnosticFinalOfficialIdentityCollisions = 0;
        _diagnosticFinalOfficialIndexMismatches = 0;
        _finalOfficialAccepted = false;
        _diagnosticFinalOfficialExpectedSlots = 0;
        _diagnosticFinalOfficialPublishedSlots = 0;
        KnownPartyBySlot.Clear();
        FinalPartyBySlot.Clear();
        FinalOfficialBySlot.Clear();
        LastLiveOfficialBySlot.Clear();
        _liveOfficialBaselineReady = false;
        _settlementCacheProbeRunEpoch += 1;
        _settlementCacheProbeRoomEpoch = 0;
        _settlementCacheProbeCalls = 0;
        _settlementCacheProbeSamples = 0;
        _settlementCacheProbeOrdinarySamples = 0;
        _settlementCacheProbeDamageCallsInRoom = 0;
        _settlementCacheProbeThrottledCalls = 0;
        _settlementCacheProbeSuppressed = false;
        _nextSettlementCacheProbeReadMs = 0;
        _lastSettlementCacheProbeVector = null;
        _lastSettlementCacheProbeDamageRoom = null;
        lock (SettlementFinalProbeLock)
        {
            SettlementFinalProbeNetworkVectors.Clear();
            _settlementFinalProbeSequence = 0;
            _settlementFinalProbeNetworkSamples = 0;
            _settlementFinalProbeDuplicateCalls = 0;
            _settlementFinalProbeSuppressedCalls = 0;
            _settlementFinalProbeSuppressionLogged = false;
        }
    }

    private static void RecordDamageOwner(Player owner, int damage, bool isBoss)
    {
        var boundedDamage = Math.Max(0, damage);
        if (owner is null)
        {
            _diagnosticUnattributedDamage += boundedDamage;
            _diagnosticUnattributedDamageEvents += 1;
            if (isBoss)
            {
                _diagnosticUnattributedBossDamage += boundedDamage;
            }
            return;
        }
        var isLocal = false;
        try
        {
            var local = PlayerManager.Instance?.LocalPlayer;
            isLocal = local is not null && local.Pointer == owner.Pointer;
        }
        catch
        {
        }
        if (isLocal)
        {
            _diagnosticLocalDamage += boundedDamage;
            _diagnosticLocalDamageEvents += 1;
            if (isBoss)
            {
                _diagnosticLocalBossDamage += boundedDamage;
            }
        }
        else
        {
            _diagnosticRemoteDamage += boundedDamage;
            _diagnosticRemoteDamageEvents += 1;
            if (isBoss)
            {
                _diagnosticRemoteBossDamage += boundedDamage;
            }
        }
    }

    private static void RecordFinalDamageFallback(Player owner, int damage)
    {
        var slot = PlayerSlot(owner);
        if (slot is >= 0 and <= 15)
        {
            DiagnosticFinalFallbackEventsBySlot[slot.Value] += 1;
            DiagnosticFinalFallbackDamageBySlot[slot.Value] += Math.Max(0, damage);
            return;
        }
        _diagnosticFinalFallbackUnattributedEvents += 1;
        _diagnosticFinalFallbackUnattributedDamage += Math.Max(0, damage);
    }

    private static void LogDamageOwnerSummary(string point)
    {
        if (!ReleaseDiagnosticsEnabled)
        {
            return;
        }
        var fallbackSlots = string.Join(",", Enumerable.Range(0, 16)
            .Where(slot => DiagnosticFinalFallbackEventsBySlot[slot] > 0)
            .Select(slot =>
                $"{slot}:{DiagnosticFinalFallbackEventsBySlot[slot]}:" +
                DiagnosticFinalFallbackDamageBySlot[slot]));
        LogDiagnosticInfo(
            $"[LC2CB-OWNER] kind=summary point={point} " +
            $"local_events={_diagnosticLocalDamageEvents} local_damage={_diagnosticLocalDamage} " +
            $"local_boss={_diagnosticLocalBossDamage} " +
            $"remote_events={_diagnosticRemoteDamageEvents} remote_damage={_diagnosticRemoteDamage} " +
            $"remote_boss={_diagnosticRemoteBossDamage} " +
            $"unattributed_events={_diagnosticUnattributedDamageEvents} " +
            $"unattributed_damage={_diagnosticUnattributedDamage} " +
            $"unattributed_boss={_diagnosticUnattributedBossDamage} " +
            $"stack_mismatches={_diagnosticDamageStackMismatches} " +
            $"final_fallback_slots={(string.IsNullOrEmpty(fallbackSlots) ? "none" : fallbackSlots)} " +
            $"final_fallback_unattributed_events={_diagnosticFinalFallbackUnattributedEvents} " +
            $"final_fallback_unattributed_damage={_diagnosticFinalFallbackUnattributedDamage}");
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

    internal static double ReconcileDealtSettlementDamage(
        double realDamage,
        double appliedHpDamage,
        double fallbackFinalDamage) =>
        realDamage > 0.0
            ? Math.Max(0.0, appliedHpDamage)
            : Math.Max(0.0, fallbackFinalDamage);

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

    private static void LogManaSummary(string point)
    {
        if (!ReleaseDiagnosticsEnabled)
        {
            return;
        }
        LogDiagnosticInfo(
            $"[LC2CB-MP] kind=summary point={point} " +
            $"spend_events={_diagnosticManaSpendEvents} spent={DiagnosticNumber(_diagnosticManaSpent)} " +
            $"gain_events={_diagnosticManaGainEvents} gained={DiagnosticNumber(_diagnosticManaGained)} " +
            $"net={DiagnosticNumber(_diagnosticManaGained - _diagnosticManaSpent)} " +
            $"last_observed_raw={DiagnosticNumber(_lastObservedPlayerMp)}");
    }

    private static void LogRoomDiagnostic(string callback, RoomLocation room = null)
    {
        if (!ReleaseDiagnosticsEnabled)
        {
            return;
        }
        try
        {
            var stage = StageMgr.Instance;
            LogDiagnosticInfo(
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

    private static void LogDiagnosticInfo(string message)
    {
        if (ReleaseDiagnosticsEnabled)
        {
            RuntimeLog?.LogInfo(message);
        }
    }

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
                var snapshot = GetOrCreateHitSnapshotLocked(hit.ID);
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
            Bridge?.ReportRecoverableIssue("damage_snapshot_failed");
        }
    }

    private static HitHpSnapshot GetOrCreateHitSnapshotLocked(int hitId)
    {
        if (HpSnapshots.TryGetValue(hitId, out var existing))
        {
            return existing;
        }
        while (HpSnapshots.Count >= MaxHpSnapshots && HpSnapshotOrder.First is not null)
        {
            var oldest = HpSnapshotOrder.First;
            HpSnapshotOrder.RemoveFirst();
            HpSnapshotNodes.Remove(oldest.Value);
            HpSnapshots.Remove(oldest.Value);
        }
        var snapshot = new HitHpSnapshot();
        HpSnapshots[hitId] = snapshot;
        HpSnapshotNodes[hitId] = HpSnapshotOrder.AddLast(hitId);
        return snapshot;
    }

    private static bool TryTakeHitSnapshotLocked(int hitId, out HitHpSnapshot snapshot)
    {
        var found = HpSnapshots.TryGetValue(hitId, out snapshot);
        HpSnapshots.Remove(hitId);
        if (HpSnapshotNodes.Remove(hitId, out var node))
        {
            HpSnapshotOrder.Remove(node);
        }
        return found;
    }

    private static void ResetHitSnapshots()
    {
        lock (HpSnapshotLock)
        {
            HpSnapshots.Clear();
            HpSnapshotNodes.Clear();
            HpSnapshotOrder.Clear();
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
        RefreshRegisteredAttackerCallbacks();
        var members = CapturePartyMembers();
        if (members.Count > 0)
        {
            Bridge?.PublishPartyUpdated(members);
            if (force)
            {
                LogOfficialDamageSummary(members);
            }
        }
    }

    private static void LogOfficialDamageSummary(
        IReadOnlyList<PartyMemberSnapshot> members)
    {
        if (!ReleaseDiagnosticsEnabled)
        {
            return;
        }
        CaptureLiveOfficialDiagnostics();
        _ = CaptureLiveOfficialDamageTotals();
        var values = members
            .OrderBy(member => member.PlayerSlot ?? 99)
            .Select(member =>
                $"slot={(member.PlayerSlot is null ? "null" : member.PlayerSlot.Value)}:" +
                $"damage={(member.OfficialDamage is null ? "null" : member.OfficialDamage.Value)}:" +
                $"boss={(member.OfficialBossDamage is null ? "null" : member.OfficialBossDamage.Value)}")
            .ToArray();
        LogDiagnosticInfo(
            $"[LC2CB-OFFICIAL] kind=summary members={members.Count} " +
            $"network_records={_diagnosticOfficialNetworkRecords} " +
            $"fallback_records={_diagnosticOfficialFallbackRecords} " +
            $"live_cache_available={_diagnosticLiveOfficialCacheAvailable.ToString().ToLowerInvariant()} " +
            $"live_cache_records={_diagnosticLiveOfficialCacheRecords} " +
            $"live_active_available={_diagnosticLiveOfficialActiveAvailable.ToString().ToLowerInvariant()} " +
            $"live_active_records={_diagnosticLiveOfficialActiveRecords} " +
            $"live_identity_matches={_diagnosticLiveOfficialIdentityMatches} " +
            $"live_identity_unmatched={_diagnosticLiveOfficialIdentityUnmatched} " +
            $"live_identity_collisions={_diagnosticLiveOfficialIdentityCollisions} " +
            $"live_read_failures={_diagnosticLiveOfficialReadFailures} " +
            $"live_cache_slots={_diagnosticLiveOfficialCacheSlots} " +
            $"live_active_slots={_diagnosticLiveOfficialActiveSlots} " +
            $"final_ready={_finalOfficialReady.ToString().ToLowerInvariant()} " +
            $"final_records={_diagnosticFinalOfficialRecords} " +
            $"final_invalid_slots={_diagnosticFinalOfficialInvalidSlots} " +
            $"final_duplicate_slots={_diagnosticFinalOfficialDuplicateSlots} " +
            $"final_raw_indices={_diagnosticFinalOfficialRawIndices} " +
            $"final_identity_matches={_diagnosticFinalOfficialIdentityMatches} " +
            $"final_identity_unmatched={_diagnosticFinalOfficialIdentityUnmatched} " +
            $"final_identity_collisions={_diagnosticFinalOfficialIdentityCollisions} " +
            $"final_index_mismatches={_diagnosticFinalOfficialIndexMismatches} " +
            $"final_expected_slots={_diagnosticFinalOfficialExpectedSlots} " +
            $"final_published_slots={_diagnosticFinalOfficialPublishedSlots} " +
            $"final_accepted={_finalOfficialAccepted.ToString().ToLowerInvariant()} " +
            "slot_basis=platform_identity_hmac " +
            $"raw_indices={_diagnosticOfficialRawIndices} " +
            string.Join(" ", values));
    }

    internal static void CaptureSettlementNetworkRecord(
        string surface,
        LC2.Statistics.AdventureRecordPlayerData record)
    {
        if (!ReleaseDiagnosticsEnabled)
        {
            return;
        }
        var log = RuntimeLog;
        if (!_inActiveMap || log is null)
        {
            return;
        }

        var identity = "null";
        var damage = "null";
        var bossDamage = "null";
        var readFailure = false;
        try
        {
            if (record is not null)
            {
                identity = AnonymousSettlementIdentity(record);
                damage = record.mDamageValue.ToString(CultureInfo.InvariantCulture);
                bossDamage = record.mBossDamageValue.ToString(CultureInfo.InvariantCulture);
            }
        }
        catch
        {
            identity = "read-failure";
            damage = "read-failure";
            bossDamage = "read-failure";
            readFailure = true;
        }

        var vector = $"{surface}:{identity}:{damage}:{bossDamage}:{readFailure}";
        var sequence = 0;
        var networkSamples = 0;
        var duplicateCalls = 0;
        var suppressedCalls = 0;
        var logSuppression = false;
        lock (SettlementFinalProbeLock)
        {
            if (SettlementFinalProbeNetworkVectors.Contains(vector))
            {
                _settlementFinalProbeDuplicateCalls += 1;
                return;
            }
            if (_settlementFinalProbeNetworkSamples
                >= MaxSettlementFinalProbeNetworkSamples)
            {
                _settlementFinalProbeSuppressedCalls += 1;
                if (!_settlementFinalProbeSuppressionLogged)
                {
                    _settlementFinalProbeSuppressionLogged = true;
                    sequence = ++_settlementFinalProbeSequence;
                    logSuppression = true;
                }
            }
            else
            {
                SettlementFinalProbeNetworkVectors.Add(vector);
                _settlementFinalProbeNetworkSamples += 1;
                sequence = ++_settlementFinalProbeSequence;
            }
            networkSamples = _settlementFinalProbeNetworkSamples;
            duplicateCalls = _settlementFinalProbeDuplicateCalls;
            suppressedCalls = _settlementFinalProbeSuppressedCalls;
        }
        if (sequence == 0)
        {
            return;
        }
        if (logSuppression)
        {
            log.LogWarning(
                "[LC2CB-SETTLEMENT-FINAL-PROBE] kind=suppressed " +
                $"seq={sequence} max_network_samples={MaxSettlementFinalProbeNetworkSamples} " +
                "sync_end_boundaries_preserved=true");
            return;
        }
        log.LogInfo(
            "[LC2CB-SETTLEMENT-FINAL-PROBE] kind=record " +
            $"seq={sequence} phase=prefix surface={surface} " +
            $"identity={identity} damage={damage} boss={bossDamage} " +
            $"read_failure={readFailure.ToString().ToLowerInvariant()} " +
            $"network_samples={networkSamples} duplicate_calls={duplicateCalls} " +
            $"suppressed_calls={suppressedCalls}");
    }

    private static void CaptureSettlementFinalProbeSnapshot(string phase)
    {
        if (!ReleaseDiagnosticsEnabled)
        {
            return;
        }
        var log = RuntimeLog;
        if (log is null)
        {
            return;
        }

        var activeAvailable = false;
        var activeRecords = 0;
        var activeReadFailures = 0;
        var activeTruncated = false;
        var active = "unavailable";
        try
        {
            active = CaptureSettlementFinalProbeList(
                GlobalManager.StatisticsMgr?.mAdventureRecordDataList,
                out activeAvailable,
                out activeRecords,
                out activeReadFailures,
                out activeTruncated);
        }
        catch
        {
            activeReadFailures += 1;
        }

        var cacheAvailable = false;
        var cacheRecords = 0;
        var cacheReadFailures = 0;
        var cacheTruncated = false;
        var cache = "unavailable";
        try
        {
            cache = CaptureSettlementFinalProbeList(
                GlobalManager.StatisticsMgr?._adventureRecordCacheDataList,
                out cacheAvailable,
                out cacheRecords,
                out cacheReadFailures,
                out cacheTruncated);
        }
        catch
        {
            cacheReadFailures += 1;
        }

        var saveAvailable = false;
        var saveRecords = 0;
        var saveReadFailures = 0;
        var saveTruncated = false;
        var save = "unavailable";
        try
        {
            save = CaptureSettlementFinalProbeList(
                GlobalManager.StatisticsMgr?
                    .mCurAdventureRecordSaveData?
                    .mAdventureRecordPlayerDataList,
                out saveAvailable,
                out saveRecords,
                out saveReadFailures,
                out saveTruncated);
        }
        catch
        {
            saveReadFailures += 1;
        }

        var networkAvailable = false;
        var networkRecords = 0;
        var networkReadFailures = 0;
        var networkTruncated = false;
        var network = "unavailable";
        try
        {
            network = CaptureSettlementFinalProbeDictionary(
                GlobalManager.StageNetworkCtrl?._multiRoundDataDic,
                out networkAvailable,
                out networkRecords,
                out networkReadFailures,
                out networkTruncated);
        }
        catch
        {
            networkReadFailures += 1;
        }

        int sequence;
        int networkSamples;
        int duplicateCalls;
        int suppressedCalls;
        lock (SettlementFinalProbeLock)
        {
            sequence = ++_settlementFinalProbeSequence;
            networkSamples = _settlementFinalProbeNetworkSamples;
            duplicateCalls = _settlementFinalProbeDuplicateCalls;
            suppressedCalls = _settlementFinalProbeSuppressedCalls;
        }
        log.LogInfo(
            "[LC2CB-SETTLEMENT-FINAL-PROBE] kind=boundary " +
            $"seq={sequence} phase={phase} run={_settlementCacheProbeRunEpoch} " +
            $"room_epoch={_settlementCacheProbeRoomEpoch} " +
            $"active_available={activeAvailable.ToString().ToLowerInvariant()} " +
            $"active_records={activeRecords} active_read_failures={activeReadFailures} " +
            $"active_truncated={activeTruncated.ToString().ToLowerInvariant()} active={active} " +
            $"cache_available={cacheAvailable.ToString().ToLowerInvariant()} " +
            $"cache_records={cacheRecords} cache_read_failures={cacheReadFailures} " +
            $"cache_truncated={cacheTruncated.ToString().ToLowerInvariant()} cache={cache} " +
            $"save_available={saveAvailable.ToString().ToLowerInvariant()} " +
            $"save_records={saveRecords} save_read_failures={saveReadFailures} " +
            $"save_truncated={saveTruncated.ToString().ToLowerInvariant()} save={save} " +
            $"network_available={networkAvailable.ToString().ToLowerInvariant()} " +
            $"network_records={networkRecords} network_read_failures={networkReadFailures} " +
            $"network_truncated={networkTruncated.ToString().ToLowerInvariant()} network={network} " +
            $"network_samples={networkSamples} duplicate_calls={duplicateCalls} " +
            $"suppressed_calls={suppressedCalls}");
    }

    private static string CaptureSettlementFinalProbeList(
        Il2CppSystem.Collections.Generic.List<
            LC2.Statistics.AdventureRecordPlayerData> records,
        out bool available,
        out int recordCount,
        out int readFailures,
        out bool truncated)
    {
        available = records is not null;
        recordCount = 0;
        readFailures = 0;
        truncated = false;
        if (records is null)
        {
            return "none";
        }
        recordCount = records.Count;
        truncated = recordCount > MaxSettlementFinalProbeRecordsPerSurface;
        var values = new List<string>();
        var limit = Math.Min(recordCount, MaxSettlementFinalProbeRecordsPerSurface);
        for (var index = 0; index < limit; index += 1)
        {
            try
            {
                values.Add(FormatSettlementFinalProbeRecord(records[index]));
            }
            catch
            {
                readFailures += 1;
                values.Add("read-failure");
            }
        }
        return values.Count == 0 ? "empty" : string.Join(",", values);
    }

    private static string CaptureSettlementFinalProbeDictionary(
        Il2CppSystem.Collections.Generic.Dictionary<
            ulong,
            LC2.Statistics.AdventureRecordPlayerData> records,
        out bool available,
        out int recordCount,
        out int readFailures,
        out bool truncated)
    {
        available = records is not null;
        recordCount = 0;
        readFailures = 0;
        truncated = false;
        if (records is null)
        {
            return "none";
        }
        recordCount = records.Count;
        truncated = recordCount > MaxSettlementFinalProbeRecordsPerSurface;
        var values = new List<string>();
        foreach (var pair in records)
        {
            if (values.Count >= MaxSettlementFinalProbeRecordsPerSurface)
            {
                break;
            }
            try
            {
                values.Add(FormatSettlementFinalProbeRecord(pair.Value));
            }
            catch
            {
                readFailures += 1;
                values.Add("read-failure");
            }
        }
        return values.Count == 0 ? "empty" : string.Join(",", values);
    }

    private static string FormatSettlementFinalProbeRecord(
        LC2.Statistics.AdventureRecordPlayerData record)
    {
        if (record is null)
        {
            return "null";
        }
        return $"{AnonymousSettlementIdentity(record)}:" +
            $"{record.mDamageValue.ToString(CultureInfo.InvariantCulture)}:" +
            record.mBossDamageValue.ToString(CultureInfo.InvariantCulture);
    }

    private static string AnonymousSettlementIdentity(
        LC2.Statistics.AdventureRecordPlayerData record)
    {
        var fingerprint = OfficialIdentityFingerprint(record);
        if (fingerprint is null)
        {
            return "missing";
        }
        var matches = KnownPartyBySlot
            .Where(pair => string.Equals(
                pair.Value.OfficialIdentityFingerprint,
                fingerprint,
                StringComparison.Ordinal))
            .Take(2)
            .ToArray();
        if (matches.Length == 1)
        {
            // The final official summary is keyed by slot. Keep this diagnostic
            // surface on the same anonymous key so the acceptance checker never
            // has to infer player-N ordering or match by damage values.
            return $"slot-{matches[0].Key}";
        }
        if (matches.Length > 1)
        {
            return "collision";
        }
        var tokenLength = Math.Min(16, fingerprint.Length);
        return "opaque-" + fingerprint[..tokenLength].ToLowerInvariant();
    }

    private static void CaptureSettlementCacheProbe(
        string point,
        bool force = false,
        int? triggerSlot = null)
    {
        if (!ReleaseDiagnosticsEnabled || !_inActiveMap || RuntimeLog is null)
        {
            return;
        }
        _settlementCacheProbeCalls += 1;
        var firstDamageInRoom = string.Equals(
                point,
                "attacker_post",
                StringComparison.Ordinal)
            && _settlementCacheProbeDamageCallsInRoom == 1;
        var now = Environment.TickCount64;
        if (!force
            && !firstDamageInRoom
            && now < _nextSettlementCacheProbeReadMs)
        {
            _settlementCacheProbeThrottledCalls += 1;
            return;
        }
        if (!force)
        {
            _nextSettlementCacheProbeReadMs = now + SettlementCacheProbeIntervalMs;
        }

        var dictAvailable = false;
        var dictRecords = 0;
        var dictMatched = 0;
        var dictUnmatched = 0;
        var dictCollisions = 0;
        var dictReadFailures = 0;
        var dictInvalid = 0;
        var duplicateSlots = new HashSet<int>();
        var dictSlots = new Dictionary<int, SettlementCacheSlotValue>();
        var matchBasisCounts = new Dictionary<string, int>(StringComparer.Ordinal);
        var opaqueRecords = new List<string>();
        var keyMatches = new Dictionary<ulong, SettlementCacheKeyMatch>();

        try
        {
            var players = PlayerManager.Instance?.PlayerList;
            if (players is not null)
            {
                for (var index = 0; index < players.Count; index += 1)
                {
                    try
                    {
                        var player = players[index];
                        var slot = PlayerSlot(player);
                        if (slot is null)
                        {
                            continue;
                        }
                        AddSettlementCacheKeyMatch(
                            keyMatches,
                            player.ID,
                            slot.Value,
                            "player_id");
                        AddSettlementCacheKeyMatch(
                            keyMatches,
                            player.ClientID,
                            slot.Value,
                            "client_id");
                        AddSettlementCacheKeyMatch(
                            keyMatches,
                            player.TransportID,
                            slot.Value,
                            "transport_id");
                    }
                    catch
                    {
                        dictReadFailures += 1;
                    }
                }
            }

            var ambiguousIdentities = new HashSet<string>(StringComparer.Ordinal);
            var identityToSlot = new Dictionary<string, int>(StringComparer.Ordinal);
            foreach (var (slot, known) in KnownPartyBySlot)
            {
                var fingerprint = known.OfficialIdentityFingerprint;
                if (fingerprint is null || ambiguousIdentities.Contains(fingerprint))
                {
                    continue;
                }
                if (!identityToSlot.TryAdd(fingerprint, slot))
                {
                    identityToSlot.Remove(fingerprint);
                    ambiguousIdentities.Add(fingerprint);
                }
            }

            var settlement = GlobalManager.SettlementDataMgr;
            var cache = settlement?.mCacheRoundDataDict;
            dictAvailable = cache is not null;
            var network = GlobalManager.StageNetworkCtrl?._multiRoundDataDic;
            if (cache is not null)
            {
                foreach (var pair in cache)
                {
                    dictRecords += 1;
                    if (pair.Key == 0)
                    {
                        dictUnmatched += 1;
                        AddOpaqueSettlementRecord(
                            opaqueRecords,
                            pair.Key,
                            "unmatched",
                            null);
                        continue;
                    }
                    var match = new SettlementCacheKeyMatch();
                    if (keyMatches.TryGetValue(pair.Key, out var directMatch))
                    {
                        foreach (var directSlot in directMatch.Slots)
                        {
                            match.Slots.Add(directSlot);
                        }
                        foreach (var basis in directMatch.Bases)
                        {
                            match.Bases.Add(basis);
                        }
                    }
                    try
                    {
                        if (network is not null
                            && network.TryGetValue(pair.Key, out var networkRecord)
                            && networkRecord is not null)
                        {
                            var fingerprint = OfficialIdentityFingerprint(networkRecord);
                            if (fingerprint is not null
                                && !ambiguousIdentities.Contains(fingerprint)
                                && identityToSlot.TryGetValue(fingerprint, out var identitySlot))
                            {
                                match.Slots.Add(identitySlot);
                                match.Bases.Add("network_identity");
                            }
                        }
                    }
                    catch
                    {
                        dictReadFailures += 1;
                    }

                    if (match.Slots.Count == 0)
                    {
                        dictUnmatched += 1;
                        AddOpaqueSettlementRecord(
                            opaqueRecords,
                            pair.Key,
                            "unmatched",
                            match);
                        continue;
                    }
                    if (match.Slots.Count != 1)
                    {
                        dictCollisions += 1;
                        AddOpaqueSettlementRecord(
                            opaqueRecords,
                            pair.Key,
                            "collision",
                            match);
                        continue;
                    }
                    var slot = match.Slots.Single();
                    dictMatched += 1;
                    var basisName = match.Bases.Count == 1
                        ? match.Bases.Single()
                        : "multi";
                    matchBasisCounts[basisName] =
                        matchBasisCounts.GetValueOrDefault(basisName) + 1;

                    try
                    {
                        var collector = pair.Value?.mDamageCollector;
                        if (collector is null)
                        {
                            dictReadFailures += 1;
                            AddOpaqueSettlementRecord(
                                opaqueRecords,
                                pair.Key,
                                "read_failure",
                                match);
                            continue;
                        }
                        var damage = collector.mAtkDmg;
                        var bossDamage = collector.mAtkDmg_Boss;
                        if (!ValidSettlementCacheDamage(damage, bossDamage))
                        {
                            dictInvalid += 1;
                            AddOpaqueSettlementRecord(
                                opaqueRecords,
                                pair.Key,
                                "invalid",
                                match);
                        }
                        if (duplicateSlots.Contains(slot))
                        {
                            continue;
                        }
                        if (dictSlots.ContainsKey(slot))
                        {
                            dictSlots.Remove(slot);
                            duplicateSlots.Add(slot);
                            AddOpaqueSettlementRecord(
                                opaqueRecords,
                                pair.Key,
                                "duplicate_slot",
                                match);
                            continue;
                        }
                        dictSlots[slot] = new SettlementCacheSlotValue
                        {
                            Damage = damage,
                            BossDamage = bossDamage,
                        };
                    }
                    catch
                    {
                        dictReadFailures += 1;
                        AddOpaqueSettlementRecord(
                            opaqueRecords,
                            pair.Key,
                            "read_failure",
                            match);
                    }
                }
            }
        }
        catch
        {
            dictReadFailures += 1;
        }

        var singletonAvailable = false;
        var singletonInvalid = false;
        var singletonValue = "none";
        try
        {
            var collector = GlobalManager.SettlementDataMgr?
                .mCacheRoundData?
                .mDamageCollector;
            singletonAvailable = collector is not null;
            if (collector is not null)
            {
                var damage = collector.mAtkDmg;
                var bossDamage = collector.mAtkDmg_Boss;
                singletonInvalid = !ValidSettlementCacheDamage(damage, bossDamage);
                singletonValue = FormatSettlementCacheDamage(damage, bossDamage);
            }
        }
        catch
        {
            dictReadFailures += 1;
        }

        // Keep all three game-owned data faces in one main-thread sample. The
        // checker, not the plugin, decides whether a cache is a delta, a
        // cumulative value, or unavailable.
        CaptureLiveOfficialDiagnostics();
        var dictSlotValue = FormatSettlementCacheSlots(dictSlots);
        var cacheSlotValue = _diagnosticLiveOfficialCacheSlots;
        var activeSlotValue = _diagnosticLiveOfficialActiveSlots;
        var vector =
            $"{_settlementCacheProbeRunEpoch}:{_settlementCacheProbeRoomEpoch}:" +
            $"{dictAvailable}:{dictRecords}:{dictMatched}:{dictUnmatched}:" +
            $"{dictCollisions}:{dictReadFailures}:{dictInvalid}:" +
            $"{FormatIntegerSet(duplicateSlots)}:{dictSlotValue}:" +
            $"{cacheSlotValue}:{activeSlotValue}:{singletonAvailable}:" +
            $"{singletonInvalid}:{singletonValue}";
        var changed = !string.Equals(
            vector,
            _lastSettlementCacheProbeVector,
            StringComparison.Ordinal);
        _lastSettlementCacheProbeVector = vector;
        var roomToken =
            $"{_settlementCacheProbeRunEpoch}:{_settlementCacheProbeRoomEpoch}";
        var firstDamageSample = string.Equals(
                point,
                "attacker_post",
                StringComparison.Ordinal)
            && !string.Equals(
                roomToken,
                _lastSettlementCacheProbeDamageRoom,
                StringComparison.Ordinal);
        if (firstDamageSample)
        {
            _lastSettlementCacheProbeDamageRoom = roomToken;
        }
        if (!force && !changed && !firstDamageSample)
        {
            return;
        }
        if (!force
            && _settlementCacheProbeOrdinarySamples
                >= MaxSettlementCacheProbeOrdinarySamples)
        {
            if (!_settlementCacheProbeSuppressed)
            {
                _settlementCacheProbeSuppressed = true;
                RuntimeLog.LogWarning(
                    "[LC2CB-SETTLEMENT-CACHE] kind=suppressed " +
                    $"run={_settlementCacheProbeRunEpoch} " +
                    $"room_epoch={_settlementCacheProbeRoomEpoch} " +
                    $"max_ordinary_samples={MaxSettlementCacheProbeOrdinarySamples} " +
                    "force_boundaries_preserved=true");
            }
            return;
        }
        if (!force)
        {
            _settlementCacheProbeOrdinarySamples += 1;
        }
        _settlementCacheProbeSamples += 1;

        var expectedSlots = KnownPartyBySlot.Keys.ToHashSet();
        var mappedHumanSlots = dictSlots.Keys
            .Where(slot => expectedSlots.Contains(slot) && !duplicateSlots.Contains(slot))
            .ToHashSet();
        var humanComplete = expectedSlots.Count > 0
            && mappedHumanSlots.SetEquals(expectedSlots);
        var localSlot = PlayerSlot(PlayerManager.Instance?.LocalPlayer);
        var combat = true;
        try
        {
            combat = StageMgr.Instance?.IsNonBattleRoom() is not true;
        }
        catch
        {
        }
        var basisValue = matchBasisCounts.Count == 0
            ? "none"
            : string.Join(",", matchBasisCounts
                .OrderBy(pair => pair.Key, StringComparer.Ordinal)
                .Select(pair => $"{pair.Key}:{pair.Value}"));
        var triggerSlotValue = triggerSlot is null
            ? "null"
            : triggerSlot.Value.ToString(CultureInfo.InvariantCulture);
        var localSlotValue = localSlot is null
            ? "null"
            : localSlot.Value.ToString(CultureInfo.InvariantCulture);
        var opaqueRecordValue = opaqueRecords.Count == 0
            ? "none"
            : string.Join(",", opaqueRecords);
        var ordinarySuppressed =
            _settlementCacheProbeOrdinarySamples
                >= MaxSettlementCacheProbeOrdinarySamples;
        RuntimeLog.LogInfo(
            $"[LC2CB-SETTLEMENT-CACHE] kind=sample " +
            $"run={_settlementCacheProbeRunEpoch} " +
            $"room_epoch={_settlementCacheProbeRoomEpoch} " +
            $"sample={_settlementCacheProbeSamples} " +
            $"call={_settlementCacheProbeCalls} point={point} " +
            $"ordinary_samples={_settlementCacheProbeOrdinarySamples} " +
            $"ordinary_suppressed={ordinarySuppressed.ToString().ToLowerInvariant()} " +
            $"throttled_calls={_settlementCacheProbeThrottledCalls} " +
            $"combat={combat.ToString().ToLowerInvariant()} " +
            $"trigger_slot={triggerSlotValue} " +
            $"local_slot={localSlotValue} " +
            $"damage_calls={_settlementCacheProbeDamageCallsInRoom} " +
            $"humans={expectedSlots.Count} dict_available={dictAvailable.ToString().ToLowerInvariant()} " +
            $"dict_records={dictRecords} dict_matched={dictMatched} " +
            $"dict_unmatched={dictUnmatched} dict_duplicate_slots={duplicateSlots.Count} " +
            $"dict_collisions={dictCollisions} dict_read_failures={dictReadFailures} " +
            $"dict_invalid={dictInvalid} human_mapped={mappedHumanSlots.Count} " +
            $"human_complete={humanComplete.ToString().ToLowerInvariant()} " +
            $"changed={changed.ToString().ToLowerInvariant()} dict_basis={basisValue} " +
            $"dict_opaque={opaqueRecordValue} " +
            $"dict_slots={dictSlotValue} " +
            $"cache_list_available={_diagnosticLiveOfficialCacheAvailable.ToString().ToLowerInvariant()} " +
            $"cache_list_records={_diagnosticLiveOfficialCacheRecords} " +
            $"cache_list_slots={cacheSlotValue} " +
            $"active_available={_diagnosticLiveOfficialActiveAvailable.ToString().ToLowerInvariant()} " +
            $"active_records={_diagnosticLiveOfficialActiveRecords} " +
            $"active_slots={activeSlotValue} " +
            $"stat_identity_matches={_diagnosticLiveOfficialIdentityMatches} " +
            $"stat_identity_unmatched={_diagnosticLiveOfficialIdentityUnmatched} " +
            $"stat_identity_collisions={_diagnosticLiveOfficialIdentityCollisions} " +
            $"stat_read_failures={_diagnosticLiveOfficialReadFailures} " +
            $"singleton_available={singletonAvailable.ToString().ToLowerInvariant()} " +
            $"singleton_invalid={singletonInvalid.ToString().ToLowerInvariant()} " +
            $"singleton={singletonValue}");
    }

    private static void AddSettlementCacheKeyMatch(
        Dictionary<ulong, SettlementCacheKeyMatch> matches,
        ulong key,
        int slot,
        string basis)
    {
        if (key == 0)
        {
            return;
        }
        if (!matches.TryGetValue(key, out var match))
        {
            match = new SettlementCacheKeyMatch();
            matches[key] = match;
        }
        match.Slots.Add(slot);
        match.Bases.Add(basis);
    }

    private static void AddOpaqueSettlementRecord(
        List<string> records,
        ulong key,
        string status,
        SettlementCacheKeyMatch match)
    {
        if (records.Count >= 32)
        {
            return;
        }
        var basis = match is null || match.Bases.Count == 0
            ? "none"
            : string.Join("+", match.Bases.OrderBy(value => value, StringComparer.Ordinal));
        records.Add(
            $"{OpaqueSettlementCacheKey(key)}:{status}:{basis}");
    }

    private static string OpaqueSettlementCacheKey(ulong key)
    {
        using var hmac = new HMACSHA256(OfficialIdentityHmacKey);
        var input = new byte[sizeof(int) + sizeof(ulong)];
        BitConverter.GetBytes(_settlementCacheProbeRunEpoch).CopyTo(input, 0);
        BitConverter.GetBytes(key).CopyTo(input, sizeof(int));
        var digest = Convert.ToHexString(
            hmac.ComputeHash(input));
        return digest[..16];
    }

    private static bool ValidSettlementCacheDamage(float damage, float bossDamage) =>
        !float.IsNaN(damage)
        && !float.IsInfinity(damage)
        && !float.IsNaN(bossDamage)
        && !float.IsInfinity(bossDamage)
        && damage >= 0
        && bossDamage >= 0
        && bossDamage <= damage;

    private static string FormatSettlementCacheDamage(float damage, float bossDamage) =>
        $"{damage.ToString("R", CultureInfo.InvariantCulture)}:" +
        bossDamage.ToString("R", CultureInfo.InvariantCulture);

    private static string FormatSettlementCacheSlots(
        IReadOnlyDictionary<int, SettlementCacheSlotValue> values)
    {
        if (values.Count == 0)
        {
            return "none";
        }
        return string.Join(",", values
            .OrderBy(pair => pair.Key)
            .Select(pair =>
                $"{pair.Key}:" +
                FormatSettlementCacheDamage(
                    pair.Value.Damage,
                    pair.Value.BossDamage)));
    }

    private static string FormatIntegerSet(IReadOnlySet<int> values) =>
        values.Count == 0
            ? "none"
            : string.Join(",", values.OrderBy(value => value));

    private static void CaptureLiveOfficialDiagnostics()
    {
        _diagnosticLiveOfficialCacheAvailable = false;
        _diagnosticLiveOfficialActiveAvailable = false;
        _diagnosticLiveOfficialCacheRecords = 0;
        _diagnosticLiveOfficialActiveRecords = 0;
        _diagnosticLiveOfficialIdentityMatches = 0;
        _diagnosticLiveOfficialIdentityUnmatched = 0;
        _diagnosticLiveOfficialIdentityCollisions = 0;
        _diagnosticLiveOfficialReadFailures = 0;
        _diagnosticLiveOfficialCacheSlots = "none";
        _diagnosticLiveOfficialActiveSlots = "none";

        var ambiguousIdentities = new HashSet<string>(StringComparer.Ordinal);
        var identityToSlot = new Dictionary<string, int>(StringComparer.Ordinal);
        foreach (var (slot, known) in KnownPartyBySlot)
        {
            var fingerprint = known.OfficialIdentityFingerprint;
            if (fingerprint is null || ambiguousIdentities.Contains(fingerprint))
            {
                continue;
            }
            if (!identityToSlot.TryAdd(fingerprint, slot))
            {
                identityToSlot.Remove(fingerprint);
                ambiguousIdentities.Add(fingerprint);
                _diagnosticLiveOfficialIdentityCollisions += 1;
            }
        }

        var manager = GlobalManager.StatisticsMgr;
        var cacheTotals = new Dictionary<int, OfficialDamageTotals>();
        var activeTotals = new Dictionary<int, OfficialDamageTotals>();
        try
        {
            var records = manager?._adventureRecordCacheDataList;
            _diagnosticLiveOfficialCacheAvailable = records is not null;
            CaptureLiveOfficialList(
                records,
                identityToSlot,
                ambiguousIdentities,
                cacheTotals,
                ref _diagnosticLiveOfficialCacheRecords);
        }
        catch
        {
            _diagnosticLiveOfficialReadFailures += 1;
        }
        try
        {
            var records = manager?.mAdventureRecordDataList;
            _diagnosticLiveOfficialActiveAvailable = records is not null;
            CaptureLiveOfficialList(
                records,
                identityToSlot,
                ambiguousIdentities,
                activeTotals,
                ref _diagnosticLiveOfficialActiveRecords);
        }
        catch
        {
            _diagnosticLiveOfficialReadFailures += 1;
        }
        _diagnosticLiveOfficialCacheSlots = FormatOfficialDamageTotals(cacheTotals);
        _diagnosticLiveOfficialActiveSlots = FormatOfficialDamageTotals(activeTotals);
    }

    private static void CaptureLiveOfficialList(
        Il2CppSystem.Collections.Generic.List<LC2.Statistics.AdventureRecordPlayerData> records,
        IReadOnlyDictionary<string, int> identityToSlot,
        IReadOnlySet<string> ambiguousIdentities,
        Dictionary<int, OfficialDamageTotals> result,
        ref int recordCount)
    {
        if (records is null)
        {
            return;
        }
        var seenPointers = new HashSet<IntPtr>();
        for (var index = 0; index < records.Count; index += 1)
        {
            try
            {
                var record = records[index];
                if (record is null
                    || (record.Pointer != IntPtr.Zero && !seenPointers.Add(record.Pointer)))
                {
                    continue;
                }
                recordCount += 1;
                var fingerprint = OfficialIdentityFingerprint(record);
                if (fingerprint is null
                    || ambiguousIdentities.Contains(fingerprint)
                    || !identityToSlot.TryGetValue(fingerprint, out var slot))
                {
                    _diagnosticLiveOfficialIdentityUnmatched += 1;
                    continue;
                }
                _diagnosticLiveOfficialIdentityMatches += 1;
                MergeOfficialDamage(
                    result,
                    slot,
                    Math.Max(0, record.mDamageValue),
                    Math.Max(0, record.mBossDamageValue));
            }
            catch
            {
                _diagnosticLiveOfficialReadFailures += 1;
            }
        }
    }

    private static string FormatOfficialDamageTotals(
        IReadOnlyDictionary<int, OfficialDamageTotals> values)
    {
        if (values.Count == 0)
        {
            return "none";
        }
        return string.Join(",", values
            .OrderBy(pair => pair.Key)
            .Select(pair =>
                $"{pair.Key}:{pair.Value.Damage}:{pair.Value.BossDamage}"));
    }

    private static Dictionary<int, OfficialDamageTotals> CaptureLiveOfficialDamageTotals()
    {
        var empty = new Dictionary<int, OfficialDamageTotals>();
        if (_finalOfficialReady || KnownPartyBySlot.Count == 0)
        {
            return empty;
        }
        try
        {
            var identityToSlot = new Dictionary<string, int>(StringComparer.Ordinal);
            foreach (var (slot, known) in KnownPartyBySlot)
            {
                var fingerprint = known.OfficialIdentityFingerprint;
                if (fingerprint is null || !identityToSlot.TryAdd(fingerprint, slot))
                {
                    return empty;
                }
            }
            if (identityToSlot.Count != KnownPartyBySlot.Count)
            {
                return empty;
            }
            var expectedSlots = KnownPartyBySlot.Keys.ToHashSet();
            var statistics = GlobalManager.StatisticsMgr;
            var active = CaptureLiveOfficialListByIdentity(
                statistics?.mAdventureRecordDataList,
                identityToSlot,
                expectedSlots);
            var roomCache = CaptureLiveOfficialListByIdentity(
                statistics?._adventureRecordCacheDataList,
                identityToSlot,
                expectedSlots);
            if (active.Count != expectedSlots.Count
                || roomCache.Count != expectedSlots.Count)
            {
                return empty;
            }
            var result = new Dictionary<int, OfficialDamageTotals>();
            foreach (var slot in expectedSlots)
            {
                var activeValue = active[slot];
                var cacheValue = roomCache[slot];
                var damage = checked(activeValue.Damage + cacheValue.Damage);
                var bossDamage = checked(
                    activeValue.BossDamage + cacheValue.BossDamage);
                if (damage < 0 || bossDamage < 0 || bossDamage > damage)
                {
                    return empty;
                }
                result[slot] = new OfficialDamageTotals
                {
                    Damage = damage,
                    BossDamage = bossDamage,
                };
            }

            if (!_liveOfficialBaselineReady)
            {
                if (result.Values.Any(value => value.Damage != 0 || value.BossDamage != 0))
                {
                    return empty;
                }
                _liveOfficialBaselineReady = true;
            }
            else if (LastLiveOfficialBySlot.Count > 0
                && !LastLiveOfficialBySlot.Keys.ToHashSet().SetEquals(expectedSlots))
            {
                return empty;
            }

            foreach (var (slot, value) in result)
            {
                if (LastLiveOfficialBySlot.TryGetValue(slot, out var previous)
                    && (value.Damage < previous.Damage
                        || value.BossDamage < previous.BossDamage))
                {
                    return empty;
                }
            }
            LastLiveOfficialBySlot.Clear();
            foreach (var (slot, value) in result)
            {
                LastLiveOfficialBySlot[slot] = new OfficialDamageTotals
                {
                    Damage = value.Damage,
                    BossDamage = value.BossDamage,
                };
            }
            return result;
        }
        catch
        {
            return empty;
        }
    }

    private static Dictionary<int, OfficialDamageTotals>
        CaptureLiveOfficialListByIdentity(
            Il2CppSystem.Collections.Generic.List<
                LC2.Statistics.AdventureRecordPlayerData> records,
            IReadOnlyDictionary<string, int> identityToSlot,
            IReadOnlySet<int> expectedSlots)
    {
        var result = new Dictionary<int, OfficialDamageTotals>();
        if (records is null || records.Count < expectedSlots.Count)
        {
            return result;
        }
        var seenPointers = new HashSet<IntPtr>();
        var acceptedSlots = new HashSet<int>();
        for (var index = 0; index < records.Count; index += 1)
        {
            var record = records[index];
            if (record is null)
            {
                return new Dictionary<int, OfficialDamageTotals>();
            }
            if (record.Pointer != IntPtr.Zero && !seenPointers.Add(record.Pointer))
            {
                continue;
            }
            var fingerprint = OfficialIdentityFingerprint(record);
            if (fingerprint is null
                || !identityToSlot.TryGetValue(fingerprint, out var slot))
            {
                // Game-owned NPCs can have official records without party slots.
                continue;
            }
            if (!acceptedSlots.Add(slot))
            {
                return new Dictionary<int, OfficialDamageTotals>();
            }
            var damage = (long)record.mDamageValue;
            var bossDamage = (long)record.mBossDamageValue;
            if (damage < 0 || bossDamage < 0 || bossDamage > damage)
            {
                return new Dictionary<int, OfficialDamageTotals>();
            }
            result[slot] = new OfficialDamageTotals
            {
                Damage = damage,
                BossDamage = bossDamage,
            };
        }
        return acceptedSlots.SetEquals(expectedSlots)
            ? result
            : new Dictionary<int, OfficialDamageTotals>();
    }

    private static List<PartyMemberSnapshot> CapturePartyMembers()
    {
        var result = new List<PartyMemberSnapshot>();
        try
        {
            var manager = PlayerManager.Instance;
            var players = manager?.PlayerList;
            var local = manager?.LocalPlayer;
            var liveBySlot = CaptureLiveOfficialDamageTotals();
            var officialBySlot = CaptureOfficialDamageTotals();
            if (_finalOfficialReady
                && _finalOfficialAccepted
                && FinalPartyBySlot.Count > 0)
            {
                return CaptureFinalPartyMembers(officialBySlot);
            }
            if (players is not null)
            {
                var seen = new HashSet<string>(StringComparer.Ordinal);
                var seenSlots = new HashSet<int>();
                for (var index = 0; index < players.Count && result.Count < 16; index += 1)
                {
                    var player = players[index];
                    if (player is null)
                    {
                        continue;
                    }
                    var candidateToken = PlayerToken(player);
                    var isLocal = local is not null && local.Pointer == player.Pointer;
                    var playerSlot = PlayerSlot(player);
                    if (candidateToken is null || playerSlot is null)
                    {
                        Bridge?.ReportRecoverableIssue("party_identity_unresolved");
                        return new List<PartyMemberSnapshot>();
                    }
                    var playerIndex = playerSlot.Value;
                    var fingerprint = OfficialIdentityFingerprint(player);
                    if (!TryHistoricalPartySlot(
                        candidateToken,
                        fingerprint,
                        out var historicalSlot))
                    {
                        Bridge?.ReportRecoverableIssue("party_identity_collision");
                        return new List<PartyMemberSnapshot>();
                    }
                    var identitySlot = historicalSlot ?? playerIndex;
                    var token = StablePartyToken(
                        candidateToken,
                        identitySlot,
                        fingerprint);
                    if (!seen.Add(token))
                    {
                        Bridge?.ReportRecoverableIssue("party_duplicate_identity");
                        return new List<PartyMemberSnapshot>();
                    }
                    if (!seenSlots.Add(playerIndex))
                    {
                        Bridge?.ReportRecoverableIssue("party_duplicate_slot");
                        return new List<PartyMemberSnapshot>();
                    }
                    KnownPartyBySlot.TryGetValue(identitySlot, out var previous);
                    KnownPartyBySlot[identitySlot] = new KnownPartyIdentity
                    {
                        PlayerId = token,
                        IsLocal = isLocal,
                        OfficialIdentityFingerprint =
                            fingerprint ?? previous?.OfficialIdentityFingerprint,
                    };
                    liveBySlot.TryGetValue(identitySlot, out var live);
                    officialBySlot.TryGetValue(identitySlot, out var official);
                    result.Add(new PartyMemberSnapshot
                    {
                        PlayerId = token,
                        PlayerSlot = playerIndex,
                        IsLocal = isLocal,
                        LiveDamage = live?.Damage,
                        LiveBossDamage = live?.BossDamage,
                        OfficialDamage = official?.Damage,
                        OfficialBossDamage = official?.BossDamage,
                    });
                }
            }
            if (result.Count == 0 && local is not null)
            {
                var token = PlayerToken(local);
                var playerSlot = PlayerSlot(local);
                if (token is not null && playerSlot is not null)
                {
                    var playerIndex = playerSlot.Value;
                    var fingerprint = OfficialIdentityFingerprint(local);
                    if (!TryHistoricalPartySlot(
                        token,
                        fingerprint,
                        out var historicalSlot))
                    {
                        return new List<PartyMemberSnapshot>();
                    }
                    var identitySlot = historicalSlot ?? playerIndex;
                    token = StablePartyToken(
                        token,
                        identitySlot,
                        fingerprint);
                    liveBySlot.TryGetValue(identitySlot, out var live);
                    officialBySlot.TryGetValue(identitySlot, out var official);
                    result.Add(new PartyMemberSnapshot
                    {
                        PlayerId = token,
                        PlayerSlot = playerIndex,
                        IsLocal = true,
                        LiveDamage = live?.Damage,
                        LiveBossDamage = live?.BossDamage,
                        OfficialDamage = official?.Damage,
                        OfficialBossDamage = official?.BossDamage,
                    });
                }
            }
            if (_finalOfficialReady)
            {
                var publishedSlots = result
                    .Where(member => member.PlayerSlot is not null)
                    .Select(member => member.PlayerSlot.Value)
                    .ToHashSet();
                foreach (var (slot, official) in officialBySlot.OrderBy(pair => pair.Key))
                {
                    if (publishedSlots.Contains(slot)
                        || !KnownPartyBySlot.TryGetValue(slot, out var known))
                    {
                        continue;
                    }
                    result.Add(new PartyMemberSnapshot
                    {
                        PlayerId = known.PlayerId,
                        PlayerSlot = slot,
                        IsLocal = known.IsLocal,
                        OfficialDamage = official.Damage,
                        OfficialBossDamage = official.BossDamage,
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

    private static List<PartyMemberSnapshot> CaptureFinalPartyMembers(
        IReadOnlyDictionary<int, OfficialDamageTotals> officialBySlot)
    {
        var result = new List<PartyMemberSnapshot>();
        foreach (var (slot, known) in FinalPartyBySlot.OrderBy(pair => pair.Key))
        {
            if (!officialBySlot.TryGetValue(slot, out var official))
            {
                return new List<PartyMemberSnapshot>();
            }
            result.Add(new PartyMemberSnapshot
            {
                PlayerId = known.PlayerId,
                PlayerSlot = slot,
                IsLocal = known.IsLocal,
                OfficialDamage = official.Damage,
                OfficialBossDamage = official.BossDamage,
            });
        }
        return result;
    }

    private static Dictionary<int, OfficialDamageTotals> CaptureOfficialDamageTotals()
    {
        var result = new Dictionary<int, OfficialDamageTotals>();
        _diagnosticOfficialNetworkRecords = 0;
        _diagnosticOfficialFallbackRecords = 0;
        _diagnosticOfficialRawIndices = "";
        try
        {
            var rawIndices = new List<int>();
            var network = GlobalManager.StageNetworkCtrl?._multiRoundDataDic;
            if (network is not null)
            {
                foreach (var pair in network)
                {
                    var record = pair.Value;
                    if (record is null)
                    {
                        continue;
                    }
                    _diagnosticOfficialNetworkRecords += 1;
                    rawIndices.Add(record.mIndex);
                }
            }
            _diagnosticOfficialRawIndices = string.Join(",", rawIndices.OrderBy(value => value));
        }
        catch
        {
            // The temporary final-settlement inbox may already have been consumed.
        }
        if (_finalOfficialReady)
        {
            CaptureFinalOfficialDamageTotals(result);
        }
        return result;
    }

    private static void CaptureFinalOfficialDamageTotals(
        Dictionary<int, OfficialDamageTotals> result)
    {
        if (_finalOfficialAccepted && FinalOfficialBySlot.Count > 0)
        {
            foreach (var (slot, official) in FinalOfficialBySlot)
            {
                MergeOfficialDamage(
                    result,
                    slot,
                    official.Damage,
                    official.BossDamage);
            }
            _diagnosticFinalOfficialPublishedSlots = result.Count;
            return;
        }
        _diagnosticFinalOfficialRecords = 0;
        _diagnosticFinalOfficialInvalidSlots = 0;
        _diagnosticFinalOfficialDuplicateSlots = 0;
        _diagnosticFinalOfficialRawIndices = "";
        _diagnosticFinalOfficialIdentityMatches = 0;
        _diagnosticFinalOfficialIdentityUnmatched = 0;
        _diagnosticFinalOfficialIdentityCollisions = 0;
        _diagnosticFinalOfficialIndexMismatches = 0;
        _finalOfficialAccepted = false;
        _diagnosticFinalOfficialExpectedSlots = KnownPartyBySlot.Count;
        _diagnosticFinalOfficialPublishedSlots = 0;
        try
        {
            var records = GlobalManager.StatisticsMgr?
                .mCurAdventureRecordSaveData?
                .mAdventureRecordPlayerDataList;
            if (records is null)
            {
                return;
            }
            var rawIndices = new List<int>();
            var seenPointers = new HashSet<IntPtr>();
            var acceptedSlots = new HashSet<int>();
            var duplicateSlots = new HashSet<int>();
            var ambiguousIdentities = new HashSet<string>(StringComparer.Ordinal);
            var identityToSlot = new Dictionary<string, int>(StringComparer.Ordinal);
            foreach (var (slot, known) in KnownPartyBySlot)
            {
                var fingerprint = known.OfficialIdentityFingerprint;
                if (fingerprint is null || ambiguousIdentities.Contains(fingerprint))
                {
                    continue;
                }
                if (!identityToSlot.TryAdd(fingerprint, slot))
                {
                    identityToSlot.Remove(fingerprint);
                    ambiguousIdentities.Add(fingerprint);
                    _diagnosticFinalOfficialIdentityCollisions += 1;
                }
            }
            for (var index = 0; index < records.Count; index += 1)
            {
                var record = records[index];
                if (record is null
                    || (record.Pointer != IntPtr.Zero && !seenPointers.Add(record.Pointer)))
                {
                    continue;
                }
                _diagnosticFinalOfficialRecords += 1;
                var rawSlot = record.mIndex;
                rawIndices.Add(rawSlot);
                if (rawSlot is < 0 or > 15)
                {
                    _diagnosticFinalOfficialInvalidSlots += 1;
                }
                var fingerprint = OfficialIdentityFingerprint(record);
                if (fingerprint is null
                    || ambiguousIdentities.Contains(fingerprint)
                    || !identityToSlot.TryGetValue(fingerprint, out var slot))
                {
                    _diagnosticFinalOfficialIdentityUnmatched += 1;
                    continue;
                }
                _diagnosticFinalOfficialIdentityMatches += 1;
                if (rawSlot != slot)
                {
                    _diagnosticFinalOfficialIndexMismatches += 1;
                }
                if (!acceptedSlots.Add(slot))
                {
                    duplicateSlots.Add(slot);
                    result.Remove(slot);
                    continue;
                }
                MergeOfficialDamage(
                    result,
                    slot,
                    Math.Max(0, record.mDamageValue),
                    Math.Max(0, record.mBossDamageValue));
            }
            _diagnosticFinalOfficialDuplicateSlots = duplicateSlots.Count;
            _diagnosticFinalOfficialRawIndices = string.Join(",", rawIndices.OrderBy(value => value));
            var expectedSlots = KnownPartyBySlot.Keys.ToHashSet();
            if (_diagnosticFinalOfficialDuplicateSlots > 0
                || _diagnosticFinalOfficialIdentityUnmatched > 0
                || _diagnosticFinalOfficialIdentityCollisions > 0
                || expectedSlots.Count == 0
                || _diagnosticFinalOfficialRecords != expectedSlots.Count
                || _diagnosticFinalOfficialIdentityMatches != expectedSlots.Count
                || !result.Keys.ToHashSet().SetEquals(expectedSlots))
            {
                result.Clear();
                return;
            }
            _finalOfficialAccepted = true;
            _diagnosticFinalOfficialPublishedSlots = result.Count;
            FinalPartyBySlot.Clear();
            FinalOfficialBySlot.Clear();
            foreach (var (slot, known) in KnownPartyBySlot)
            {
                FinalPartyBySlot[slot] = new KnownPartyIdentity
                {
                    PlayerId = known.PlayerId,
                    IsLocal = known.IsLocal,
                    OfficialIdentityFingerprint = known.OfficialIdentityFingerprint,
                };
            }
            foreach (var (slot, official) in result)
            {
                FinalOfficialBySlot[slot] = new OfficialDamageTotals
                {
                    Damage = official.Damage,
                    BossDamage = official.BossDamage,
                };
            }
        }
        catch (Exception exception)
        {
            RuntimeLog?.LogWarning(
                $"Final official records unavailable: {exception.GetType().Name}");
        }
    }

    private static string OfficialIdentityFingerprint(Player player)
    {
        try
        {
            return OfficialIdentityFingerprint(player?.PlatformUniqueID);
        }
        catch
        {
            return null;
        }
    }

    private static string OfficialIdentityFingerprint(
        LC2.Statistics.AdventureRecordPlayerData record)
    {
        try
        {
            return OfficialIdentityFingerprint(record?.mPlatformUniqueID);
        }
        catch
        {
            return null;
        }
    }

    private static string OfficialIdentityFingerprint(string platformIdentity)
    {
        if (string.IsNullOrEmpty(platformIdentity))
        {
            return null;
        }
        using var hmac = new HMACSHA256(OfficialIdentityHmacKey);
        return Convert.ToHexString(
            hmac.ComputeHash(Encoding.UTF8.GetBytes(platformIdentity)));
    }

    private static void MergeOfficialDamage(
        Dictionary<int, OfficialDamageTotals> result,
        int? slot,
        long damage,
        long boss)
    {
        if (slot is not >= 0 or > 15)
        {
            return;
        }
        if (!result.TryGetValue(slot.Value, out var totals))
        {
            totals = new OfficialDamageTotals();
            result[slot.Value] = totals;
        }
        totals.Damage = Math.Max(totals.Damage, Math.Max(0, damage));
        totals.BossDamage = Math.Max(totals.BossDamage, Math.Max(0, boss));
    }

    private static Player OwnerPlayer(DisposeHitInfo hit)
    {
        if (hit is null)
        {
            return null;
        }
        try
        {
            // The hit already exposes the gameplay attacker resolved in its
            // hierarchy. Prefer it over creation/transport ownership on a
            // transient projectile entity.
            return OwnerPlayer(hit.mAtkerInHierarchy) ?? OwnerPlayer(hit.mAtker);
        }
        catch
        {
            return null;
        }
    }

    private static Player OwnerPlayer(Entity entity)
    {
        if (entity is null)
        {
            return null;
        }
        var pending = new Queue<Entity>();
        var seen = new HashSet<IntPtr>();
        pending.Enqueue(entity);
        for (var visited = 0; visited < 8 && pending.Count > 0; visited += 1)
        {
            var candidate = pending.Dequeue();
            if (candidate is null || !seen.Add(candidate.Pointer))
            {
                continue;
            }
            var owner = DirectOwnerPlayer(candidate);
            if (owner is not null)
            {
                return owner;
            }
            var player = PlayerForRootCreature(candidate);
            if (player is not null)
            {
                return player;
            }
            EnqueueOwnerCandidate(pending, OwnerEntityInHierarchy(candidate), seen);
            EnqueueOwnerCandidate(pending, OwnerEntity(candidate), seen);
            EnqueueOwnerCandidate(pending, CreatureMaster(candidate), seen);
        }
        return null;
    }

    private static Player DirectOwnerPlayer(Entity entity)
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

    private static Entity OwnerEntityInHierarchy(Entity entity)
    {
        try
        {
            return entity?.OwnerEntityInHierarchy;
        }
        catch
        {
            return null;
        }
    }

    private static Entity OwnerEntity(Entity entity)
    {
        try
        {
            return entity?.OwnerEntity;
        }
        catch
        {
            return null;
        }
    }

    private static Entity CreatureMaster(Entity entity)
    {
        try
        {
            return TryCreature(entity)?.Master;
        }
        catch
        {
            return null;
        }
    }

    private static void EnqueueOwnerCandidate(
        Queue<Entity> pending,
        Entity candidate,
        HashSet<IntPtr> seen)
    {
        if (candidate is not null && !seen.Contains(candidate.Pointer))
        {
            pending.Enqueue(candidate);
        }
    }

    private static Player PlayerForRootCreature(Entity entity)
    {
        try
        {
            var players = PlayerManager.Instance?.PlayerList;
            if (players is null)
            {
                return null;
            }
            for (var index = 0; index < players.Count; index += 1)
            {
                var player = players[index];
                var root = player?.OwnerCreature;
                if (root is not null && root.Pointer == entity.Pointer)
                {
                    return player;
                }
            }
        }
        catch
        {
        }
        return null;
    }

    private static string PlayerToken(Player player)
    {
        if (player is null)
        {
            return null;
        }
        try
        {
            // The local native Player object is stable within a game session,
            // while ID/ClientID/TransportID can populate or change during a
            // real network join.  The pointer is used only as an internal map
            // key and is never sent to the desktop client.
            var identity = player.Pointer != IntPtr.Zero
                ? $"native:{player.Pointer.ToInt64().ToString("X", CultureInfo.InvariantCulture)}"
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
        Plugin.EmitOfficialAttacker(arg);
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

[HarmonyPatch(typeof(StageNetworkCtrl), nameof(StageNetworkCtrl.SyncAdventureRecordDataEnd))]
internal static class FinalOfficialDamageSyncPatch
{
    [HarmonyPrefix]
    private static void Prefix() => Plugin.BeginOfficialDamageSync();

    [HarmonyPostfix]
    private static void Postfix() => Plugin.FinalizeOfficialDamageSync();
}

internal static class SettlementNetworkProbePatchMethods
{
    internal static void SyncSettlementDataClientResultPrefix(
        ulong __0,
        LC2.Statistics.AdventureRecordPlayerData __1) =>
        Plugin.CaptureSettlementNetworkRecord(
            "SyncSettlementData_ClientResult",
            __1);

    internal static void SyncSettlementData2RpcPrefix(
        ulong __0,
        LC2.Statistics.AdventureRecordPlayerData __1) =>
        Plugin.CaptureSettlementNetworkRecord("SyncSettlementData2_Rpc", __1);

    internal static void SyncSettlementDataServerPrefix(
        ulong __0,
        LC2.Statistics.AdventureRecordPlayerData __1) =>
        Plugin.CaptureSettlementNetworkRecord("SyncSettlementData", __1);
}

[HarmonyPatch(typeof(SettlementDataMgr), nameof(SettlementDataMgr.OnChangeRoomEnd))]
internal static class RoomEndLocationPatch
{
    [HarmonyPrefix]
    private static void Prefix() => Plugin.CaptureRoomExit();

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
