"""Core image engine. No UI code here - pure Pillow operations."""
import io

from PIL import Image, ImageChops, ImageEnhance, ImageOps

SUPPORTED = (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tif", ".tiff")


def load_image(path):
    im = Image.open(path)
    return ImageOps.exif_transpose(im).convert("RGB")


def make_preview(im, max_side):
    if max(im.size) <= max_side:
        return im
    p = im.copy()
    p.thumbnail((max_side, max_side))
    return p


def adjust(im, angle=0.0, brightness=0, contrast=0):
    """Straighten (degrees), brightness and contrast (-100..100)."""
    if abs(angle) > 0.01:
        im = im.rotate(angle, resample=Image.BICUBIC, expand=True,
                       fillcolor=(255, 255, 255))
    if brightness:
        im = ImageEnhance.Brightness(im).enhance(1 + brightness / 100)
    if contrast:
        im = ImageEnhance.Contrast(im).enhance(1 + contrast / 100)
    return im


def crop(im, box):
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    box = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
    if box[2] - box[0] < 2 or box[3] - box[1] < 2:
        return None
    return im.crop(box)


def find_content_box(im, tolerance=25):
    """Bounding box of content that differs from the corner (background) colour."""
    bg = Image.new("RGB", im.size, im.getpixel((0, 0)))
    diff = ImageChops.difference(im, bg).convert("L").point(
        lambda p: 255 if p > tolerance else 0)
    box = diff.getbbox()
    if not box or box == (0, 0, im.width, im.height):
        return None
    return box


def auto_crop(im, tolerance=25):
    box = find_content_box(im, tolerance)
    return im.crop(box) if box else None


def resize(im, w, h):
    return im.resize((int(w), int(h)), Image.LANCZOS)


def rotate90(im, clockwise=True):
    return im.rotate(-90 if clockwise else 90, expand=True)


def flip(im, horizontal=True):
    return ImageOps.mirror(im) if horizontal else ImageOps.flip(im)


def encode_jpeg_under_kb(im, kb, min_q=5, max_q=95):
    """Return (bytes, (w, h), quality) with size <= kb, or None if impossible."""
    target = kb * 1024
    cur = im.convert("RGB")
    for _ in range(25):
        lo, hi, best, best_q = min_q, max_q, None, None
        while lo <= hi:
            q = (lo + hi) // 2
            buf = io.BytesIO()
            cur.save(buf, "JPEG", quality=q, optimize=True)
            if buf.tell() <= target:
                best, best_q = buf.getvalue(), q
                lo = q + 1
            else:
                hi = q - 1
        if best:
            return best, cur.size, best_q
        cur = cur.resize((max(1, int(cur.width * 0.9)), max(1, int(cur.height * 0.9))),
                         Image.LANCZOS)
    return None


def save_image(im, path, jpeg_quality=92):
    if path.lower().endswith((".jpg", ".jpeg")):
        im.save(path, quality=jpeg_quality, optimize=True)
    else:
        im.save(path)
