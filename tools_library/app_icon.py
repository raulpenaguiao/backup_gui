from PIL import Image, ImageDraw
from PIL.ImageTk import PhotoImage as TkPhotoImage


def setup_icon(root):
    photo = TkPhotoImage(_draw_icon())
    root.iconphoto(True, photo)
    root._app_icon = photo  # prevent GC


def _draw_icon():
    sz = 256
    cx = sz // 2
    img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    bg    = (30, 110, 140)
    white = (255, 255, 255)
    light = (190, 225, 238)

    # Background
    d.rounded_rectangle([0, 0, sz - 1, sz - 1], radius=52, fill=bg)

    # ── Save symbol (down-arrow) ──────────────────────────────────────────────
    # Shaft
    d.rounded_rectangle([cx - 14, 26, cx + 14, 86], radius=8, fill=white)
    # Arrowhead — tip lands on the box lid below
    d.polygon([cx - 40, 80, cx + 40, 80, cx, 120], fill=white)

    # ── Box lid (also acts as the arrow's landing line) ───────────────────────
    d.rounded_rectangle([28, 118, 228, 156], radius=10, fill=light)
    # Lid clasp
    d.rounded_rectangle([cx - 28, 127, cx + 28, 147], radius=5, fill=white)

    # ── Box body ──────────────────────────────────────────────────────────────
    d.rounded_rectangle([40, 152, 216, 232], radius=10, fill=white)
    # Horizontal strap
    d.rectangle([40, 172, 216, 186], fill=light)

    return img
