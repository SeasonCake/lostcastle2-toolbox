"""Exercise both real presenters against one replayed multiplayer stream."""
from types import SimpleNamespace
import tkinter as tk
import unittest

from tests.test_combat_aggregator import common_event
from toolbox.app_shell import CombatHudWindow, ToolboxShell
from toolbox.combat_aggregator import CombatAggregator
from toolbox.game_features import DemoGameFeatureService, FeatureSnapshot
from toolbox.team_mini_ui import TeamMiniWindow


class TeamCombatIsolationTests(unittest.TestCase):
    def test_mini_controls_and_stale_team_reads_do_not_move_or_reset_combat_totals(self):
        for party_size, local_slot in ((2, 0), (3, 2), (4, 0), (4, 3)):
            with self.subTest(players=party_size, local_slot=local_slot):
                self.check_party(party_size, local_slot)

    def check_party(self, party_size, local_slot):
        root = tk.Tk()
        root.withdraw()
        errors = []
        root.report_callback_exception = lambda _kind, error, _trace: errors.append(error)
        aggregator = CombatAggregator(clock_ms=lambda: 50000)
        sequence = 0

        def emit(kind, **fields):
            nonlocal sequence
            aggregator.ingest(common_event(kind, sequence, monotonic_ms=48000+sequence, **fields))
            sequence += 1

        members = [{'player_id': f'opaque-{slot}', 'player_slot': slot, 'is_local': slot == local_slot}
                   for slot in range(party_size)]
        emit('status', status='session_started')
        emit('status', status='party_updated', aggregate=False, party_members=members)
        damages = [100, 200, 300, 400][:party_size]
        bosses = [0, 30, 0, 60][:party_size]

        def hit(slot, amount, boss=False):
            emit('damage_resolution', damage_direction='dealt', settlement_damage=amount,
                 applied_hp_damage=amount, mitigated_damage=0, overkill_damage=0,
                 is_boss=boss, owner_player_id=f'opaque-{slot}', source_token='combat.player.normal')

        for slot in range(party_size):
            hit(slot, damages[slot]-bosses[slot])
            if bosses[slot]:
                hit(slot, bosses[slot], True)
        emit('damage_resolution', damage_direction='taken', settlement_damage=15,
             applied_hp_damage=15, mitigated_damage=0, overkill_damage=0,
             damage_outcome='applied', is_boss=False, source_token='enemy.melee')
        for resource, delta in (('hp', 20), ('mp', -40), ('mp', 12)):
            emit('resource_change', resource=resource, effective_delta=delta,
                 blocked=False, overflow=0, source_token='qa.resource')

        service = DemoGameFeatureService()
        service.set_enabled('team_enabled', True)
        sample = service.snapshot(42)
        players = tuple(dict(sample.team[0], slot=slot, name=f'样本{slot+1}',
                             is_local=slot == local_slot, hp=71+slot, max_hp=170+slot,
                             mp=21+slot, max_mp=90+slot) for slot in range(party_size))
        ready = FeatureSnapshot('ready', '测试回放', players, sample.loadout, sample.captured_at)
        service.snapshot = lambda _pid: ready
        mini = TeamMiniWindow(root, service, lambda: 42,
                              lambda: service.set_enabled('team_enabled', not service.settings()['team_enabled']),
                              lambda _visible: None)
        hud = CombatHudWindow(root, aggregator)
        shell = ToolboxShell.__new__(ToolboxShell)
        shell.hud, shell.team_mini, shell.feature_pages = hud, mini, None
        for name in ('_refresh_module_statuses', '_refresh_combat', '_refresh_macro_rows',
                     '_refresh_mod_page', '_refresh_display_settings', '_draw_keyboard_preview'):
            setattr(shell, name, lambda: None)

        def check_values():
            ToolboxShell.refresh(shell)
            root.update()
            value = aggregator.snapshot()
            self.assertEqual(value.total_damage, sum(damages))
            self.assertEqual(value.personal_damage, damages[local_slot])
            self.assertEqual(value.boss_damage, sum(bosses))
            self.assertEqual(value.personal_boss_damage, bosses[local_slot])
            self.assertEqual(value.unattributed_damage, 0)
            self.assertEqual((value.taken_settlement_damage, value.effective_healing,
                              value.mp_spent, value.mp_gained), (15, 20, 40, 12))
            for slot in range(party_size):
                row = value.player_breakdown[f'opaque-{slot}']
                self.assertEqual(row['damage_dealt'], damages[slot])
                self.assertEqual(row['boss_damage'], bosses[slot])
                self.assertAlmostEqual(row['damage_share'], damages[slot]/sum(damages))
            for name, expected in {'damage': str(damages[local_slot]), 'boss': str(bosses[local_slot]),
                                   'hp_loss': '15', 'healing': '回复 +20',
                                   'mp_spent': '40', 'mp_gained': '恢复 +12'}.items():
                self.assertEqual(hud.labels[name].cget('text'), expected)
            self.assertEqual(hud.labels['damage_scope'].cget('text'), '个人伤害')
            return value

        try:
            hud.show()
            initial = check_values()
            self.assertGreater(initial.personal_recent_dps, 0)
            mini.toggle(hud.window)
            for view in ('status', 'bag', 'inscriptions'):
                mini._set_view(view)
                for _ in range(party_size):
                    mini.next_member.invoke()
                    check_values()
                    slot = mini.selected_slot
                    self.assertEqual(mini.hp_meter.value.cget('text'), f'{71+slot} / {170+slot}')
                    self.assertEqual(mini.mp_meter.value.cget('text'), f'{21+slot} / {90+slot}')
            mini._begin_drag(SimpleNamespace(x_root=30, y_root=30))
            mini._drag(SimpleNamespace(x_root=50, y_root=40))
            check_values()
            mini.enable_button.invoke()
            check_values()
            self.assertEqual(mini.hp_meter.value.cget('text'), '未同步')
            mini.enable_button.invoke()
            hit(local_slot, 7)
            damages[local_slot] += 7
            check_values()
            mini.hide()
            hit((local_slot+1) % party_size, 11)
            damages[(local_slot+1) % party_size] += 11
            check_values()
            mini.toggle(hud.window)
            service.snapshot = lambda _pid: FeatureSnapshot('stale', '数据暂未更新')
            check_values()
            self.assertEqual(mini.hp_meter.value.cget('text'), '未同步')
            service.snapshot = lambda _pid: ready
            damages = [value+25 for value in damages]
            bosses = [value+5 for value in bosses]
            emit('status', status='party_updated', aggregate=False,
                 party_members=[dict(member, official_damage=damages[slot], official_boss_damage=bosses[slot])
                                for slot, member in enumerate(members)])
            final = check_values()
            self.assertTrue(final.official_damage_complete)
            self.assertTrue(final.official_boss_damage_complete)
            self.assertEqual(root.state(), 'withdrawn')
        finally:
            mini.close()
            hud.close()
            root.destroy()
        self.assertFalse(errors)


if __name__ == '__main__':
    unittest.main()
