import tkinter as tk
from types import SimpleNamespace
import unittest

from toolbox.app_shell import ScrollablePage


class ScrollablePageTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.title('LC2 scroll layout regression fixture')
        self.root.geometry('430x280')
        self.page = ScrollablePage(self.root)
        self.page.pack(fill='both', expand=True)

    def tearDown(self):
        self.root.destroy()

    def test_content_height_tracks_shrinking_text_and_end_action_remains_reachable(self):
        label = tk.Label(self.page.content, text='长中文说明\n' * 28, font=('Microsoft YaHei UI', 12))
        label.pack(fill='x')
        button = tk.Button(self.page.content, text='完成操作', font=('Microsoft YaHei UI', 12))
        button.pack(anchor='e', pady=12)
        self.root.update()
        self.assertTrue(self.page._overflow)
        self.page.canvas.yview_moveto(1.0)
        self.root.update()
        bottom = button.winfo_rooty() - self.page.canvas.winfo_rooty() + button.winfo_height()
        self.assertLessEqual(bottom, self.page.canvas.winfo_height())
        label.configure(text='短说明')
        self.root.update()
        self.assertEqual(self.page.content.winfo_height(), self.page.content.winfo_reqheight())
        self.assertFalse(self.page._overflow)
        self.assertEqual(self.page.canvas.yview()[0], 0.0)

    def test_page_wheel_does_not_override_nested_list_selection_or_scroll(self):
        label = tk.Label(self.page.content, text='说明\n' * 24)
        label.pack()
        choices = tk.Listbox(self.page.content, height=3, exportselection=False)
        choices.insert('end', *range(30))
        choices.selection_set(5)
        choices.pack()
        self.root.update()
        before = self.page.canvas.yview()
        self.assertIsNone(self.page._wheel(SimpleNamespace(widget=choices, delta=-120)))
        self.assertEqual(choices.curselection(), (5,))
        self.assertEqual(self.page.canvas.yview(), before)
        self.assertEqual(self.page._wheel(SimpleNamespace(widget=label, delta=-120)), 'break')
        self.assertGreater(self.page.canvas.yview()[0], before[0])

    def test_focusing_last_navigation_keeps_it_visible_and_can_return_to_top(self):
        buttons = []
        for index in range(12):
            button = tk.Button(self.page.content, text=f'菜单 {index}', font=('Microsoft YaHei UI', 15))
            button.pack(fill='x', pady=5)
            buttons.append(button)
        self.root.update()
        self.page.reveal(buttons[-1])
        self.root.update()
        bottom = buttons[-1].winfo_rooty()-self.page.canvas.winfo_rooty()+buttons[-1].winfo_height()
        self.assertLessEqual(bottom, self.page.canvas.winfo_height()+1)
        self.page.reveal(buttons[0])
        self.assertEqual(self.page.canvas.yview()[0], 0.0)


if __name__ == '__main__':
    unittest.main()
