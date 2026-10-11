using BepInEx;
using BepInEx.Unity.IL2CPP;
using Il2CppInterop.Runtime.Attributes;
using LC2;
using System.Diagnostics;
using System.Text.Json;
using System.Text.RegularExpressions;
using UnityEngine;

namespace LC2ToolboxFeatures;

[BepInPlugin("cn.zidus.lc2.toolbox.features", "LC2 工具箱 · 队伍状态与配装助手", "1.9.0")]
public sealed class Plugin : BasePlugin
{
    internal static readonly string DirectoryPath = Path.Combine(Paths.ConfigPath, "LC2Toolbox");
    public override void Load()
    {
        AddComponent<FeatureDriver>();
        Log.LogInfo("LC2 Toolbox features 1.9.0 loaded; team default off, loadout viewing default on; changes require manual camp requests; no gameplay hooks installed.");
    }
}

public sealed class FeatureDriver : MonoBehaviour
{
    private double _nextTick;
    private string _lastRequest = "";
    private bool _wasActive;
    private double _nextSnapshot;
    private double _nextCatalog;
    private double _nextAssetRequest;
    private int _catalogTotal;
    private int _catalogFinished;
    private int _catalogShown;
    private List<object> _equipmentCatalog = new();
    private PendingChange _pending;
    private readonly Stopwatch _clock = Stopwatch.StartNew();
    private FeatureOptions _options = new();
    private static readonly JsonSerializerOptions JsonOptions = new() {PropertyNameCaseInsensitive=true};
    private static int ProcessId => Process.GetCurrentProcess().Id;
    public FeatureDriver(IntPtr pointer) : base(pointer) {}

    public void Update()
    {
        if (_clock.Elapsed.TotalSeconds < _nextTick) return;
        _nextTick = _clock.Elapsed.TotalSeconds + 0.5;
        try
        {
            _options = Read<FeatureOptions>("settings.json", 16 * 1024) ?? new();
            ConfirmPendingChange();
            ProcessRequest();
            if (!_options.team_enabled && !_options.loadout_enabled)
            {
                if (_wasActive) WriteSnapshot(new List<object>(), null, "disabled");
                _wasActive = false;
                return;
            }
            _wasActive = true;
            if (_clock.Elapsed.TotalSeconds < _nextSnapshot) return;
            _nextSnapshot = _clock.Elapsed.TotalSeconds + 1.0;
            var manager = PlayerManager.Instance;
            var local = manager?.LocalPlayer;
            var players = manager?.PlayerList;
            var team = new List<object>();
            if (players is not null)
            {
                for (int i = 0; i < players.Count && i < 16; i++)
                {
                    var player = players[i];
                    if (player is null || player.Pointer == IntPtr.Zero || player.IsDestroy || player.mIsLeaveRoom) continue;
                    if (!_options.team_enabled && (local is null || player.Pointer != local.Pointer)) continue;
                    team.Add(CapturePlayer(player));
                }
            }
            WriteSnapshot(team, _options.loadout_enabled ? CaptureLoadout(local) : null, local is null ? "waiting_player" : "ready");
        }
        catch (Exception error)
        {
            try { WriteSnapshot(new List<object>(), null, "unavailable", error.GetType().Name); } catch { }
        }
    }

    private static T Read<T>(string filename, long maxBytes)
    {
        var path = Path.Combine(Plugin.DirectoryPath, filename);
        if (!File.Exists(path) || new FileInfo(path).Length > maxBytes) return default;
        return JsonSerializer.Deserialize<T>(File.ReadAllText(path), JsonOptions);
    }

    private static void Write(string filename, object data)
    {
        Directory.CreateDirectory(Plugin.DirectoryPath);
        var path = Path.Combine(Plugin.DirectoryPath, filename);
        var temporary = path + ".tmp";
        File.WriteAllText(temporary, JsonSerializer.Serialize(data));
        File.Move(temporary, path, true);
    }

    [HideFromIl2Cpp]
    private void WriteSnapshot(List<object> team, object loadout, string state, string error = null)
    {
        Write("snapshot.json", new {
            schema_version=1, version="1.9.0", game_pid=ProcessId,
            captured_at=DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(),
            team_enabled=_options.team_enabled, loadout_enabled=_options.loadout_enabled,
            state, error, team, loadout,
        });
    }

    private static string Text(string value, int limit=160)
    {
        var plain = Regex.Replace(value ?? "", "<[^>]*>", "");
        return plain.Length > limit ? plain[..limit] : plain;
    }

    private static object CapturePlayer(Player player)
    {
        var bag = player.OwnBagSystem;
        var creature = player.OwnerCreature;
        var runtime = creature?.RuntimeData;
        var local = player.IsLocal;
        var items = new List<object>();
        string inventoryState = bag is null || !bag.IsInit ? "unavailable" : "ready";
        if (inventoryState == "ready")
        {
            foreach (var type in new[]{ItemType.Weapon,ItemType.Armor,ItemType.PassiveProps,ItemType.ActiveProps,ItemType.AlchemyMix})
            {
                var list=bag!.GetAllItem(type);
                if (list is null) continue;
                for (int i=0;i<list.Count && items.Count<256;i++)
                {
                    var item=list[i];
                    if(item?.RuntimeData is null) continue;
                    items.Add(new {kind=type.ToString(), name=Text(item.RuntimeData.NameText), id=Text(item.RuntimeData.ID,80), count=item.StackCount});
                }
            }
        }
        var inscriptions=new List<object>();
        var mgr=GlobalManager.InscriptionMgr;
        var usingList=mgr?.GetUsingInscriptionList(player);
        if(usingList is not null)
        {
            for(int i=0;i<usingList.Count && i<24;i++)
            {
                var inscription=usingList[i];
                if(inscription is null) continue;
                var gems=new List<object>();
                for(int slot=0;slot<Inscription.MaxSlotCount && slot<32;slot++)
                {
                    var gem=inscription.GetGem(slot);
                    if(gem is null || gem.IsEmptyData) continue;
                    gems.Add(new {name=Text(gem.GemNameText),main=Text(gem.MainSkillNameText),sub=gem.HaveSubSkill?Text(gem.SubSkillNameText):"",slot});
                }
                inscriptions.Add(new {id=Text(inscription.ID,80),name=Text(inscription.Name),gems});
            }
        }
        var hero = player.OwnerHero;
        var weapon = hero?.Weapon;
        var armor = hero?.TryGetArmor();
        return new {
            slot=player.Index, name=Text(player.NickName,64), is_local=local, is_host=player.IsRoomMaster,
            hp=runtime is null ? (float?)null : runtime.CurHP.GetDecrypted(),
            max_hp=runtime is null ? (float?)null : runtime.MaxHP.GetDecrypted(),
            mp=runtime is null ? (float?)null : runtime.CurMP.GetDecrypted(),
            max_mp=runtime is null ? (float?)null : runtime.MaxMP.GetDecrypted(),
            resources=new {gold=local && bag is not null?(int?)bag.Coin:null, crystal=local && bag is not null?(int?)bag.Crystal:null, iron=local && bag is not null?(int?)bag.IronPowder:null, coins=local && bag is not null?(int?)bag.GetValue_Internal(ItemType.Ticket):null},
            resources_state=local?"ready":"not_synced", inventory_state=inventoryState,
            items, inscriptions, partial=!local,
            equipment=new {weapon=Text(weapon?.RuntimeData?.NameText),armor=Text(armor?.RuntimeData?.NameText)},
        };
    }

    [HideFromIl2Cpp]
    private object CaptureLoadout(Player local)
    {
        var equipment = new List<object>();
        var assets = GlobalManager.EntityDataAssetMgr;
        var enchantmentMgr=GlobalManager.EnchantmentMgr;
        var goodAsset=enchantmentMgr?._dataAsset_Good;
        if(local?.OwnerHero is not null && StageMgr.Instance?.IsInCamp is true && goodAsset is not null && (goodAsset.Datas?.Count ?? 0)==0 && (goodAsset.mConfigs?.Count ?? 0)>0)
            goodAsset.CheckData();
        if(local?.OwnerHero is not null && StageMgr.Instance?.IsInCamp is true && _clock.Elapsed.TotalSeconds>=_nextAssetRequest)
        {
            var emptyEquipment=assets is not null && (assets.GetItemDataListByType(ItemType.Weapon)?.Count ?? 0)==0;
            var emptyEnchantments=enchantmentMgr is not null && (enchantmentMgr._dataAsset_Good?.Datas?.Count ?? 0)==0;
            if(emptyEquipment || emptyEnchantments)
            {
                _nextAssetRequest=_clock.Elapsed.TotalSeconds+30.0;
                if(emptyEquipment) _=assets.LoadInGameAssetAsync();
                if(emptyEnchantments) _=enchantmentMgr.LC2_IInGameAssetLoader_LoadInGameAssetAsync();
            }
        }
        if(assets is not null && (_equipmentCatalog.Count==0 || _clock.Elapsed.TotalSeconds>=_nextCatalog))
        {
            _catalogTotal=0; _catalogFinished=0; _catalogShown=0;
            foreach(var kind in new[]{ItemType.Weapon, ItemType.Armor})
            {
                var list=assets.GetItemDataListByType(kind);
                if(list is null) continue;
                for(int i=0;i<list.Count && i<1200;i++)
                {
                    var item=list[i];
                    if(item is null) continue;
                    _catalogTotal++;
                    if(item.IsFinished) _catalogFinished++;
                    if(item.IsGmModeShow) _catalogShown++;
                    if(!item.IsFinished) continue;
                    equipment.Add(new {id=Text(item.ID,80),name=Text(item.NameText),kind=kind.ToString()});
                }
            }
            _equipmentCatalog=equipment;
            _nextCatalog=_clock.Elapsed.TotalSeconds+30.0;
        }
        else equipment=_equipmentCatalog;
        var inscriptions = new List<object>();
        var gems = new List<object>();
        var mgr=GlobalManager.InscriptionMgr;
        if(local is not null && mgr is not null)
        {
            var list=mgr.GetInscriptionList(local);
            if(list is not null)
            {
                for(int i=0;i<list.Count && i<128;i++)
                {
                    var inscription=list[i];
                    if(inscription is null) continue;
                    var slots=new List<object>();
                    for(int slot=0;slot<inscription.UnlockSlotCount && slot<32;slot++)
                    {
                        var gem=inscription.GetGem(slot);
                        slots.Add(new {slot,kind=inscription.GetSlotType(slot).ToString(),name=gem is null||gem.IsEmptyData?"空槽":Text(gem.GemNameText)});
                    }
                    inscriptions.Add(new {id=Text(inscription.ID,80),name=Text(inscription.Name),weapon_type=inscription.WeaponType.ToString(),slots});
                }
            }
            var owned=mgr.InscriptionGemList;
            if(owned is not null)
            {
                for(int i=0;i<owned.Count && i<2000;i++)
                {
                    var gem=owned[i];
                    if(gem is null || gem.IsEmptyData) continue;
                    gems.Add(new {id=gem.DataHashID,name=Text(gem.GemNameText),main=Text(gem.MainSkillNameText),sub=gem.HaveSubSkill?Text(gem.SubSkillNameText):"",kind=gem.SlotType.ToString()});
                }
            }
        }
        var enchantments=new List<object>();
        if(enchantmentMgr is not null && local is not null)
        {
            var source=enchantmentMgr._dataAsset_Good?.Datas;
            if(source is not null)
                for(int i=0;i<source.Count && i<256;i++)
                    enchantments.Add(new {id=i,name=Text(source[i].UI_GetShowStr(PlayerManager.Instance?.InputPlayer))});
        }
        Write("catalog-state.json",new {schema_version=1,game_pid=ProcessId,captured_at=DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(),assets_available=assets is not null,enchantment_mgr_available=enchantmentMgr is not null,good_enchantment_asset=enchantmentMgr?._dataAsset_Good is not null,good_enchantment_configs=enchantmentMgr?._dataAsset_Good?.mConfigs?.Count,good_enchantment_entries=enchantmentMgr?._dataAsset_Good?.Datas?.Count,normal_enchantment_entries=enchantmentMgr?._dataAsset_Normal?.Datas?.Count,total_equipment=_catalogTotal,finished_equipment=_catalogFinished,shown_equipment=_catalogShown,listed_equipment=equipment.Count,listed_enchantments=enchantments.Count});
        return new {in_camp=StageMgr.Instance?.IsInCamp is true,equipment,inscriptions,gems,enchantments};
    }

    private void ProcessRequest()
    {
        var request=Read<FeatureRequest>("request.json",64*1024);
        if(request is null || request.schema_version!=1 || request.request_id==_lastRequest || !Regex.IsMatch(request.request_id??"","^[a-f0-9]{32}$")) return;
        _lastRequest=request.request_id;
        try
        {
            if(request.game_pid!=ProcessId || Math.Abs(DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()-request.created_at)>15000) throw new InvalidOperationException("请求已过期，请在工具箱重试。");
            if(!_options.loadout_enabled) throw new InvalidOperationException("配装助手已关闭。");
            if(_pending is not null) throw new InvalidOperationException("上一个配装请求仍在等待游戏确认。");
            if(StageMgr.Instance?.IsInCamp is not true) throw new InvalidOperationException("请回到营地后再使用配装助手。");
            var local=PlayerManager.Instance?.LocalPlayer;
            var hero=local?.OwnerHero;
            if(local is null || !local.IsLocal || hero is null) throw new InvalidOperationException("本地角色尚未就绪。");
            var pending=new PendingChange {Request=request,HeroPointer=hero.Pointer,Started=_clock.Elapsed.TotalSeconds};
            if(request.action=="equipment")
            {
                var item=GlobalManager.EntityDataAssetMgr?.GetItemDataByID(request.item_id);
                if(item is null || (item.ItemType!=ItemType.Weapon && item.ItemType!=ItemType.Armor) || !item.IsFinished) throw new InvalidOperationException("装备不在当前游戏可用目录中。");
                pending.Kind=item.ItemType;
                pending.BeforePointer=item.ItemType==ItemType.Weapon?hero.Weapon?.Pointer??IntPtr.Zero:hero.TryGetArmor()?.Pointer??IntPtr.Zero;
                hero.CreateItemAndPickUp(item,default(ItemSource));
            }
            else if(request.action=="gem")
            {
                var mgr=GlobalManager.InscriptionMgr;
                var inscription=mgr?.GetInscriptionByID(local,request.inscription_id);
                var owned=mgr?.InscriptionGemList;
                Gem gem=null;
                if(owned is not null) for(int i=0;i<owned.Count && i<2000;i++) if(owned[i].DataHashID==request.gem_id){gem=owned[i];break;}
                if(inscription is null || gem is null || request.slot<0 || request.slot>=inscription.UnlockSlotCount || !inscription.CouldPutGem(request.slot,gem)) throw new InvalidOperationException("灵魂石与刻印槽不匹配，或该槽尚未解锁。");
                mgr!.EquipGem(hero,inscription.WeaponType,inscription.ID,request.slot,gem);
                mgr.SaveDataAsync();
            }
            else if(request.action=="enchantment")
            {
                var weapon=hero.Weapon;
                var source=GlobalManager.EnchantmentMgr?._dataAsset_Good?.Datas;
                if(weapon is null || source is null || request.enchantment_id<0 || request.enchantment_id>=source.Count) throw new InvalidOperationException("请先装备武器，并选择当前可用附魔。");
                var selected=new Il2CppSystem.Collections.Generic.List<EnchanceEntryData>();
                selected.Add(source[request.enchantment_id]);
                var data=new EnchanceData();
                var inputPlayer=PlayerManager.Instance?.InputPlayer;
                if(inputPlayer is null) throw new InvalidOperationException("本地输入角色尚未就绪。");
                data.SetDataList(inputPlayer,selected);
                weapon.EnchanceData?.UnTakeEffect(hero);
                weapon.EnchanceData=data;
                data.TakeEffect(hero);
                pending.ExpectedPointer=data.Pointer;
            }
            else throw new InvalidOperationException("不支持的配装操作。");
            _pending=pending;
            Write("result.json",new {schema_version=1,request_id=request.request_id,game_pid=ProcessId,state="pending",message="已发送，正在等待游戏确认…"});
        }
        catch(Exception error)
        {
            Write("result.json",new {schema_version=1,request_id=request.request_id,game_pid=ProcessId,state="error",message=Text(error.Message,200)});
        }
    }

    private void ConfirmPendingChange()
    {
        if(_pending is null) return;
        var pending=_pending;
        try
        {
            var local=PlayerManager.Instance?.LocalPlayer;
            var hero=local?.OwnerHero;
            if(!_options.loadout_enabled || hero is null || hero.Pointer!=pending.HeroPointer)
                throw new InvalidOperationException("角色或功能状态已变化，请重新选择配装。");
            bool confirmed=false;
            var request=pending.Request;
            if(request.action=="equipment")
            {
                var item=pending.Kind==ItemType.Weapon?(Item)hero.Weapon:hero.TryGetArmor();
                confirmed=item is not null && item.Pointer!=pending.BeforePointer && item.RuntimeData?.ID==request.item_id;
            }
            else if(request.action=="gem")
            {
                var inscription=GlobalManager.InscriptionMgr?.GetInscriptionByID(local,request.inscription_id);
                confirmed=inscription?.GetGem(request.slot)?.DataHashID==request.gem_id;
            }
            else if(request.action=="enchantment")
                confirmed=hero.Weapon?.EnchanceData?.Pointer==pending.ExpectedPointer;
            if(confirmed)
            {
                Write("result.json",new {schema_version=1,request_id=request.request_id,game_pid=ProcessId,state="complete",message="已确认当前角色的配装更新。"});
                _pending=null;
            }
            else if(_clock.Elapsed.TotalSeconds-pending.Started>8.0)
                throw new InvalidOperationException("尚未确认配装结果；请在游戏中核对后再试，工具箱不会自动重复执行。");
        }
        catch(Exception error)
        {
            Write("result.json",new {schema_version=1,request_id=pending.Request.request_id,game_pid=ProcessId,state="error",message=Text(error.Message,200)});
            _pending=null;
        }
    }

    private sealed class PendingChange
    {
        public FeatureRequest Request;
        public IntPtr HeroPointer;
        public IntPtr BeforePointer;
        public IntPtr ExpectedPointer;
        public ItemType Kind;
        public double Started;
    }
}

public sealed class FeatureOptions
{
    public bool team_enabled {get;set;}
    public bool loadout_enabled {get;set;} = true;
}
public sealed class FeatureRequest
{
    public int schema_version {get;set;}
    public string request_id {get;set;}="";
    public int game_pid {get;set;}
    public long created_at {get;set;}
    public string action {get;set;}="";
    public string item_id {get;set;}="";
    public string inscription_id {get;set;}="";
    public int gem_id {get;set;}
    public int slot {get;set;}
    public int enchantment_id {get;set;}
}
