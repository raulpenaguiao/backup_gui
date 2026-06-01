from PIL import Image, ImageDraw
from PIL.ImageTk import PhotoImage as TkPhotoImage


def setup_icon(root):
    photo = TkPhotoImage(_draw_icon())
    root.iconphoto(True, photo)
    root._app_icon = photo  # prevent GC


def _draw_icon():
    sz = 256
    img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Teal background
    d.rounded_rectangle([0, 0, sz - 1, sz - 1], radius=52, fill=(30, 110, 140))

    # Ears (drawn before head so head overlaps inner portion)
    d.ellipse([28, 56, 112, 150], fill=(200, 228, 236))   # left ear
    d.ellipse([144, 56, 228, 150], fill=(200, 228, 236))  # right ear

    # Head
    d.ellipse([60, 58, 196, 194], fill=(255, 255, 255))

    # Trunk — vertical bar then right curl
    d.rounded_rectangle([146, 168, 170, 232], radius=12, fill=(255, 255, 255))
    d.rounded_rectangle([170, 214, 212, 238], radius=12, fill=(255, 255, 255))

    # Eyes with highlight
    d.ellipse([88, 102, 116, 130], fill=(30, 110, 140))
    d.ellipse([96, 108, 108, 120], fill=(255, 255, 255))
    d.ellipse([140, 102, 168, 130], fill=(30, 110, 140))
    d.ellipse([148, 108, 160, 120], fill=(255, 255, 255))

    return img
