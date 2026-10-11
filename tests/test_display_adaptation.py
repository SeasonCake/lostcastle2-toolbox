from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

import keyview
from toolbox.app_shell import ToolboxShell, main_font_size, main_pixel_font_size


class DisplayAdaptationTests(unittest.TestCase):
    def test_main_font_uses_display_pixels_and_keeps_readable_floor(self):
        self.assertGreaterEqual(main_font_size(8, .9), 12)
        self.assertEqual(main_font_size(10, 1), 12)
        self.assertEqual(main_font_size(8, 1.15), 12)
        self.assertEqual([main_pixel_font_size(12, 1, dpi) for dpi in (96, 144, 192)], [-16, -24, -32])
        self.assertLess(main_pixel_font_size(12, 1.8, 144), main_pixel_font_size(12, 1, 144))

    def make_shell(self):
        shell = ToolboxShell.__new__(ToolboxShell)
        shell._monitor_dpi = 144
        shell._display_dpi_override = None
        shell._last_monitor_size = (1920, 1350)
        shell.main_ui_scale = 1.5
        shell.root = SimpleNamespace(winfo_width=lambda:1280, winfo_height=lambda:900, winfo_x=lambda:2000, winfo_y=lambda:100, winfo_screenwidth=lambda:3840, winfo_screenheight=lambda:2160, state=Mock(return_value='normal'), update_idletasks=Mock())
        shell.keyboard = SimpleNamespace(set_toolbox_ui_scale=Mock(),set_toolbox_window_size=Mock())
        shell._apply_main_ui_scale = Mock()
        shell._update_main_min_size = Mock()
        shell._refresh_display_settings = Mock()
        shell._main_work_area = lambda:(1920, 0, 3840, 1080)
        return shell

    def test_monitor_move_uses_previous_dip_size_without_double_scaling(self):
        shell = self.make_shell()
        with patch('toolbox.app_shell.window_dpi',return_value=96), patch('toolbox.app_shell.clamp_to_nearest_work_area',return_value=(2000,100)), patch('toolbox.app_shell.place_tk_window') as place:
            shell._refresh_monitor_dpi()
        self.assertEqual(shell._monitor_dpi,96)
        self.assertEqual(shell.main_ui_scale,1.5)
        self.assertEqual(place.call_args.args[1:3],(1280,900))
        shell._apply_main_ui_scale.assert_called_once()

    def test_window_preset_preserves_independent_font_choice(self):
        shell = self.make_shell()
        shell._main_work_area=lambda:(0,0,3840,2088)
        with patch('toolbox.app_shell.clamp_to_nearest_work_area',return_value=(0,0)),patch('toolbox.app_shell.place_tk_window') as place:
            shell._set_toolbox_window_preset('standard')
        self.assertEqual(place.call_args.args[1:3],(1500,1080))
        self.assertEqual(shell.main_ui_scale,1.5)
        shell.keyboard.set_toolbox_ui_scale.assert_not_called()
        shell.keyboard.set_toolbox_window_size.assert_called_with(1000,720)

    def test_manual_font_limit_and_reset_do_not_resize_window(self):
        shell = self.make_shell()
        shell.main_ui_scale=1.75
        shell._set_main_ui_scale(.1)
        self.assertEqual(shell.main_ui_scale,1.8)
        shell._set_main_ui_scale(0)
        self.assertEqual(shell.main_ui_scale,1.15)
        shell.keyboard.set_toolbox_window_size.assert_not_called()

    def test_qa_reads_png_and_actual_jpeg_regardless_of_filename(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'capture.png'
            path.write_bytes(b'\x89PNG\r\n\x1a\n'+b'\x00\x00\x00\rIHDR'+b'\x00\x00\x01\x72\x00\x00\x02\x04')
            self.assertEqual(keyview._image_dimensions(path),(370,516))
            jpeg=b'\xff\xd8\xff\xe0\x00\x04AB\xff\xc2\x00\x0b\x08\x01\xff\x02\x9d\x01\x01\x11\x00\xff\xd9'
            path.write_bytes(jpeg)
            self.assertEqual(keyview._image_dimensions(path),(669,511))
            for invalid in (b'not an image',jpeg[:17],b'\xff\xd8\xff\xc0\x00\x01'):
                path.write_bytes(invalid)
                with self.assertRaises(ValueError):
                    keyview._image_dimensions(path)


if __name__=='__main__':
    unittest.main()
