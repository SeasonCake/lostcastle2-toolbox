from pathlib import Path
from types import SimpleNamespace
import unittest

from toolbox.app_shell import ToolboxShell
from toolbox.mod_categories import MOD_CATEGORIES, MOD_CATEGORY_IDS, filter_mods, mod_category
from toolbox.mod_manager import ModCatalog


class ModCategoryTests(unittest.TestCase):
    def setUp(self):
        self.catalog = ModCatalog.from_file(Path(__file__).resolve().parents[1] / 'assets/community_mod_catalog.json')

    def test_curated_ids_have_one_category_and_unknown_imports_use_other_tools(self):
        for entry in self.catalog.entries:
            self.assertEqual(sum(entry.mod_id in ids for ids in MOD_CATEGORY_IDS.values()), 1, entry.mod_id)
        self.assertEqual(mod_category('user-added-unknown'), 'utility')
        self.assertEqual(mod_category('monster-treasure'), 'loot')
        self.assertEqual(mod_category('stage-countdown'), 'room')

    def test_search_and_category_intersect_including_author_and_usage(self):
        self.assertEqual([e.mod_id for e in filter_mods(self.catalog.entries, '茶橘柚', 'information')], ['evil-spirit-stack'])
        self.assertEqual([e.mod_id for e in filter_mods(self.catalog.entries, '懒虫桑', 'information')], ['player-live-stats', 'inventory-source-panel', 'unified-tools'])
        self.assertEqual(filter_mods(self.catalog.entries, '没有这个MOD', 'combat'), [])
        self.assertIn('weapon-picker', [e.mod_id for e in filter_mods(self.catalog.entries, '1.2.7', 'loadout')])

    def test_primary_enhancement_uses_its_page_and_status_filter_keeps_category(self):
        variable = lambda value: SimpleNamespace(get=lambda: value)
        shell = SimpleNamespace(mod_manager=SimpleNamespace(catalog=self.catalog), mod_search_var=variable(''), mod_category_var=variable(MOD_CATEGORIES['all']), mod_state_var=variable('全部状态'), _mod_status_cache={})
        self.assertNotIn('enhancement-plan', [e.mod_id for e in ToolboxShell._filtered_mod_descriptors(shell)])
        self.assertIsNotNone(self.catalog.get('enhancement-plan'))
        shell.mod_category_var = variable(MOD_CATEGORIES['room'])
        shell.mod_state_var = variable('已安装')
        shell._mod_status_cache = {'stage-countdown': SimpleNamespace(installed=True), 'ice-system-enhancement': SimpleNamespace(installed=True)}
        self.assertEqual([e.mod_id for e in ToolboxShell._filtered_mod_descriptors(shell)], ['stage-countdown'])


if __name__ == '__main__':
    unittest.main()
