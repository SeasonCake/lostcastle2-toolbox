from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
ASSET_DIR = ROOT / "assets"
ASSET_DIR.mkdir(parents=True, exist_ok=True)


def rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], radius: int, **kwargs: object) -> None:
    draw.rounded_rectangle(box, radius=radius, **kwargs)


image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)
rounded(draw, (10, 10, 246, 246), 54, fill="#0F1217", outline="#555F6E", width=8)
rounded(draw, (47, 48, 209, 205), 34, fill="#191D23", outline="#FFE8A1", width=7)
rounded(draw, (54, 57, 202, 194), 29, fill="#F4C74D")

font_candidates = (
    Path(r"C:\Windows\Fonts\seguisb.ttf"),
    Path(r"C:\Windows\Fonts\arialbd.ttf"),
)
font_path = next((path for path in font_candidates if path.exists()), None)
font = ImageFont.truetype(str(font_path), 112) if font_path else ImageFont.load_default()
draw.text((128, 123), "K", font=font, fill="#211A08", anchor="mm", stroke_width=1)

png_path = ASSET_DIR / "keyview.png"
ico_path = ASSET_DIR / "keyview.ico"
image.save(png_path)
image.save(ico_path, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print(ico_path)
