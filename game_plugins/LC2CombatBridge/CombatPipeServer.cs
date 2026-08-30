using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Pipes;
using System.Text;
using System.Text.Json;
using System.Threading;
using BepInEx.Logging;

namespace LC2CombatBridge;

internal sealed class RoomLocation
{
    public int StageLevel { get; init; }
    public string ScenarioId { get; init; }
    public int RoomIndex { get; init; }
    public string MapFileName { get; init; }
    public string RoomId => $"L{StageLevel}:{ScenarioId}:{RoomIndex}";
}

internal sealed class PartyMemberSnapshot
{
    public string PlayerId { get; init; }
    public int? PlayerSlot { get; init; }
    public bool IsLocal { get; init; }

    public Dictionary<string, object> ToPayload() => new()
    {
        ["player_id"] = PlayerId,
        ["player_slot"] = PlayerSlot,
        ["is_local"] = IsLocal,
    };

    public string Fingerprint =>
        $"{PlayerId}:{(PlayerSlot is null ? "null" : PlayerSlot.Value)}:{IsLocal}";
}

internal sealed class CombatPipeServer : IDisposable
{
    internal const string PipeName = "LostCastle2Toolbox.Combat.v2";
    internal const int QueueCapacity = 512;
    internal const int HeartbeatIntervalMs = 2000;

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = false,
    };
    private static readonly UTF8Encoding Utf8 = new(false, true);

    private readonly object _stateLock = new();
    private readonly BlockingCollection<string> _outbound =
        new(new ConcurrentQueue<string>(), QueueCapacity);
    private readonly CancellationTokenSource _cancel = new();
    private readonly ManualLogSource _log;
    private readonly Thread _writerThread;

    private NamedPipeServerStream _currentPipe;
    private bool _connected;
    private bool _failed;
    private bool _sessionActive;
    private bool _roundActive = true;
    private string _sessionId = Guid.NewGuid().ToString("N");
    private long _sequence;
    private RoomLocation _room;
    private readonly Dictionary<string, string> _playerTokens = new();
    private readonly HashSet<string> _recoverableIssues = new(StringComparer.Ordinal);
    private int _nextPlayerToken;
    private List<PartyMemberSnapshot> _partyMembers = new();
    private string _partyFingerprint = string.Empty;

    public CombatPipeServer(ManualLogSource log)
    {
        _log = log;
        _writerThread = new Thread(WriterLoop)
        {
            IsBackground = true,
            Name = "LC2CombatBridgePipe",
        };
    }

    public void Start() => _writerThread.Start();

    public void BeginGameSession()
    {
        lock (_stateLock)
        {
            _room = null;
            _roundActive = true;
            _playerTokens.Clear();
            _recoverableIssues.Clear();
            _nextPlayerToken = 0;
            _partyMembers = new List<PartyMemberSnapshot>();
            _partyFingerprint = string.Empty;
            if (!_connected)
            {
                return;
            }
            ClearOutboundLocked();
            StartSessionLocked();
        }
    }

    public void EndGameSession()
    {
        lock (_stateLock)
        {
            _roundActive = false;
            if (!_connected || !_sessionActive || _failed)
            {
                return;
            }
            EnqueueLocked(CreateEventLocked(
                "status",
                aggregate: false,
                "bridge.game_round_end",
                new Dictionary<string, object> { ["status"] = "session_ended" }));
            _sessionActive = false;
        }
    }

    public void PublishRoomStarted(RoomLocation room)
    {
        if (room is null)
        {
            return;
        }
        lock (_stateLock)
        {
            _room = room;
            if (!_connected || !_sessionActive || _failed)
            {
                return;
            }
            EnqueueRoomStartedLocked(room);
        }
    }

    public void PublishRoomEnded()
    {
        Emit(
            "status",
            aggregate: false,
            "bridge.room_end",
            new Dictionary<string, object> { ["status"] = "room_ended" });
    }

    public string GetPlayerToken(string stableIdentity)
    {
        var identity = Bound(stableIdentity, 128);
        if (string.IsNullOrWhiteSpace(identity))
        {
            return null;
        }
        lock (_stateLock)
        {
            if (_playerTokens.TryGetValue(identity, out var known))
            {
                return known;
            }
            var token = $"player-{++_nextPlayerToken}";
            _playerTokens[identity] = token;
            return token;
        }
    }

    public void PublishPartyUpdated(IReadOnlyList<PartyMemberSnapshot> members)
    {
        if (members is null || members.Count == 0)
        {
            return;
        }
        var bounded = new List<PartyMemberSnapshot>();
        for (var index = 0; index < members.Count && bounded.Count < 16; index += 1)
        {
            var member = members[index];
            if (member is null || string.IsNullOrWhiteSpace(member.PlayerId))
            {
                continue;
            }
            bounded.Add(new PartyMemberSnapshot
            {
                PlayerId = Bound(member.PlayerId, 128),
                PlayerSlot = member.PlayerSlot is >= 0 and <= 15
                    ? member.PlayerSlot
                    : null,
                IsLocal = member.IsLocal,
            });
        }
        if (bounded.Count == 0)
        {
            return;
        }
        var fingerprint = string.Join("|", bounded.ConvertAll(member => member.Fingerprint));
        lock (_stateLock)
        {
            if (string.Equals(_partyFingerprint, fingerprint, StringComparison.Ordinal))
            {
                return;
            }
            _partyMembers = bounded;
            _partyFingerprint = fingerprint;
            if (!_connected || !_sessionActive || _failed)
            {
                return;
            }
            EnqueuePartyUpdatedLocked();
        }
    }

    public void EmitCheckpoint(IReadOnlyDictionary<string, object> totals)
    {
        Emit(
            "room_checkpoint",
            aggregate: true,
            "settlement.room_checkpoint",
            new Dictionary<string, object> { ["checkpoint_totals"] = totals });
    }

    public void Emit(
        string eventType,
        bool aggregate,
        string hookPath,
        IReadOnlyDictionary<string, object> fields)
    {
        lock (_stateLock)
        {
            if (!_connected || !_sessionActive || _failed)
            {
                return;
            }
            EnqueueLocked(CreateEventLocked(eventType, aggregate, hookPath, fields));
        }
    }

    public void FailSession(string detailCode)
    {
        lock (_stateLock)
        {
            if (!_connected || !_sessionActive || _failed)
            {
                return;
            }
            ClearOutboundLocked();
            var line = CreateEventLocked(
                "status",
                aggregate: false,
                "bridge.failure",
                new Dictionary<string, object>
                {
                    ["status"] = "error",
                    ["detail"] = Bound(detailCode, 96),
                });
            _failed = true;
            _log.LogWarning($"Combat bridge session failed: {Bound(detailCode, 96)}");
            _outbound.TryAdd(line);
        }
    }

    public void ReportRecoverableIssue(string detailCode)
    {
        var detail = Bound(detailCode, 96);
        if (string.IsNullOrWhiteSpace(detail))
        {
            return;
        }
        lock (_stateLock)
        {
            if (!_recoverableIssues.Add(detail))
            {
                return;
            }
            _log.LogWarning($"Combat bridge event skipped: {detail}");
            if (!_connected || !_sessionActive || _failed)
            {
                return;
            }
            EnqueueLocked(CreateEventLocked(
                "status",
                aggregate: false,
                "bridge.recoverable_issue",
                new Dictionary<string, object>
                {
                    ["status"] = "live",
                    ["detail"] = $"degraded:{detail}",
                }));
        }
    }

    public void Dispose()
    {
        _cancel.Cancel();
        lock (_stateLock)
        {
            _connected = false;
            try
            {
                _currentPipe?.Dispose();
            }
            catch
            {
                // The process is already shutting down.
            }
        }
        if (_writerThread.IsAlive && Thread.CurrentThread != _writerThread)
        {
            _writerThread.Join(1500);
        }
        _outbound.Dispose();
        _cancel.Dispose();
    }

    private void WriterLoop()
    {
        while (!_cancel.IsCancellationRequested)
        {
            try
            {
                using var pipe = new NamedPipeServerStream(
                    PipeName,
                    PipeDirection.Out,
                    1,
                    PipeTransmissionMode.Byte,
                    PipeOptions.None,
                    8192,
                    8192);
                lock (_stateLock)
                {
                    _currentPipe = pipe;
                }
                pipe.WaitForConnection();
                OpenConnection();
                WriteConnectedSession(pipe);
            }
            catch (OperationCanceledException)
            {
                break;
            }
            catch (ObjectDisposedException) when (_cancel.IsCancellationRequested)
            {
                break;
            }
            catch (Exception exception)
            {
                if (!_cancel.IsCancellationRequested)
                {
                    _log.LogWarning($"Combat bridge transport reset: {exception.GetType().Name}");
                }
            }
            finally
            {
                CloseConnection();
            }
        }
    }

    private void WriteConnectedSession(NamedPipeServerStream pipe)
    {
        while (!_cancel.IsCancellationRequested && pipe.IsConnected)
        {
            string line;
            if (_outbound.TryTake(out line, HeartbeatIntervalMs, _cancel.Token))
            {
                WriteLine(pipe, line);
                continue;
            }
            lock (_stateLock)
            {
                line = _connected
                    ? CreateEventLocked(
                        "status",
                        aggregate: false,
                        "bridge.heartbeat",
                        new Dictionary<string, object>
                        {
                            ["status"] = !_sessionActive
                                ? "session_ended"
                                : _failed
                                    ? "error"
                                    : "live",
                            ["detail"] = _failed ? "bridge_failed" : null,
                        })
                    : null;
            }
            if (line is not null)
            {
                WriteLine(pipe, line);
            }
        }
    }

    private static void WriteLine(Stream stream, string line)
    {
        var payload = Utf8.GetBytes(line + "\n");
        stream.Write(payload, 0, payload.Length);
        stream.Flush();
    }

    private void OpenConnection()
    {
        lock (_stateLock)
        {
            ClearOutboundLocked();
            _connected = true;
            _failed = false;
            if (_roundActive)
            {
                StartSessionLocked();
                if (_room is not null)
                {
                    EnqueueRoomStartedLocked(_room);
                }
                if (_partyMembers.Count > 0)
                {
                    EnqueuePartyUpdatedLocked();
                }
            }
            else
            {
                _sessionActive = false;
                EnqueueLocked(CreateEventLocked(
                    "status",
                    aggregate: false,
                    "bridge.reconnect_after_round_end",
                    new Dictionary<string, object> { ["status"] = "session_ended" }));
            }
        }
        _log.LogInfo("Combat bridge client connected; local stream active");
    }

    private void CloseConnection()
    {
        lock (_stateLock)
        {
            _connected = false;
            _sessionActive = false;
            _currentPipe = null;
            ClearOutboundLocked();
        }
    }

    private void StartSessionLocked()
    {
        _sessionId = Guid.NewGuid().ToString("N");
        _sequence = 0;
        _failed = false;
        _recoverableIssues.Clear();
        _sessionActive = true;
        EnqueueLocked(CreateEventLocked(
            "status",
            aggregate: false,
            "bridge.session_start",
            new Dictionary<string, object> { ["status"] = "session_started" }));
    }

    private void EnqueueRoomStartedLocked(RoomLocation room)
    {
        EnqueueLocked(CreateEventLocked(
            "status",
            aggregate: false,
            "stage.room_start",
            new Dictionary<string, object>
            {
                ["status"] = "room_started",
                ["stage_level"] = room.StageLevel,
                ["scenario_id"] = room.ScenarioId,
                ["room_index"] = room.RoomIndex,
                ["map_file_name"] = room.MapFileName,
            }));
    }

    private void EnqueuePartyUpdatedLocked()
    {
        var payload = new List<Dictionary<string, object>>(_partyMembers.Count);
        foreach (var member in _partyMembers)
        {
            payload.Add(member.ToPayload());
        }
        EnqueueLocked(CreateEventLocked(
            "status",
            aggregate: false,
            "player.party_snapshot",
            new Dictionary<string, object>
            {
                ["status"] = "party_updated",
                ["party_members"] = payload,
            }));
    }

    private string CreateEventLocked(
        string eventType,
        bool aggregate,
        string hookPath,
        IReadOnlyDictionary<string, object> fields)
    {
        var sequence = _sequence++;
        var payload = new Dictionary<string, object>
        {
            ["schema_version"] = 2,
            ["event_id"] = $"{_sessionId}:{sequence}",
            ["event_type"] = eventType,
            ["session_id"] = _sessionId,
            ["sequence"] = sequence,
            ["monotonic_ms"] = MonotonicMilliseconds(),
            ["room_id"] = _room?.RoomId,
            ["aggregate"] = aggregate,
            ["hook_path"] = Bound(hookPath, 256),
        };
        foreach (var (key, value) in fields)
        {
            payload[key] = value;
        }
        return JsonSerializer.Serialize(payload, JsonOptions);
    }

    private void EnqueueLocked(string line)
    {
        if (_outbound.TryAdd(line))
        {
            return;
        }
        ClearOutboundLocked();
        if (_failed)
        {
            return;
        }
        var errorLine = CreateEventLocked(
            "status",
            aggregate: false,
            "bridge.failure",
            new Dictionary<string, object>
            {
                ["status"] = "error",
                ["detail"] = "queue_overflow",
            });
        _failed = true;
        _log.LogWarning("Combat bridge session failed: queue_overflow");
        _outbound.TryAdd(errorLine);
    }

    private void ClearOutboundLocked()
    {
        while (_outbound.TryTake(out _))
        {
        }
    }

    private static long MonotonicMilliseconds() =>
        Math.Max(0L, (long)(Stopwatch.GetTimestamp() * 1000.0 / Stopwatch.Frequency));

    internal static string Bound(string value, int maximumLength)
    {
        var clean = string.IsNullOrWhiteSpace(value) ? string.Empty : value.Trim();
        return clean.Length <= maximumLength ? clean : clean[..maximumLength];
    }
}
