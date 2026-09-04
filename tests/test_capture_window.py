from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from PIL import Image

from tools.capture_window import save_png_atomic


class CaptureWindowTests(unittest.TestCase):
    def test_atomic_png_replaces_stale_output_without_leaving_a_partial(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "window.png"
            output.write_bytes(b"stale")

            save_png_atomic(Image.new("RGB", (17, 11), "#123456"), output)

            with Image.open(output) as captured:
                self.assertEqual(captured.size, (17, 11))
                self.assertEqual(captured.format, "PNG")
            self.assertEqual(list(output.parent.glob("*.tmp.png")), [])


if __name__ == "__main__":
    unittest.main()
