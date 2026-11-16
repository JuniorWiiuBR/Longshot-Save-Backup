"""JPEG to PNG with the decoder Windows has built in (GDI+), for Tk, which shows PNG but not JPEG. Nothing to install.

    png_bytes = jpeg_to_png(jpeg_bytes)      # None when it cannot (not Windows, not a picture)
"""
import ctypes
import os
import tempfile
try:
    from ctypes import wintypes
except (ImportError, ValueError):     # (not Windows)
    wintypes = None


def _jpeg_to_png_elsewhere(data):
    """Linux and other systems: Pillow when installed, else ImageMagick or ffmpeg; None when none of them is there."""
    try:
        import io
        from PIL import Image
        out = io.BytesIO()
        Image.open(io.BytesIO(data)).save(out, 'PNG')
        return out.getvalue()
    except Exception:
        pass
    import shutil
    import subprocess
    for cmd in (['magick', 'jpg:-', 'png:-'], ['convert', 'jpg:-', 'png:-'],
                ['ffmpeg', '-loglevel', 'quiet', '-f', 'image2pipe', '-i', '-', '-f', 'image2', '-c:v', 'png', '-']):
        if shutil.which(cmd[0]):
            try:
                r = subprocess.run(cmd, input=data, capture_output=True, timeout=20)
                if r.returncode == 0 and r.stdout[:8] == b'\x89PNG\r\n\x1a\n':
                    return r.stdout
            except (OSError, subprocess.SubprocessError):
                pass
    return None

PNG_ENCODER = '{557CF406-1A04-11D3-9A73-0000F81EF32E}'   # GDI+'s PNG encoder


class _GUID(ctypes.Structure):
    # (plain ctypes sizes, the same as Windows' DWORD / WORD / BOOL, so this file also loads on Linux)
    _fields_ = [('a', ctypes.c_uint32), ('b', ctypes.c_uint16), ('c', ctypes.c_uint16), ('d', ctypes.c_ubyte * 8)]


class _StartupInput(ctypes.Structure):
    _fields_ = [('version', ctypes.c_uint32), ('callback', ctypes.c_void_p),
                ('no_thread', ctypes.c_int), ('no_codecs', ctypes.c_int)]


_token = None


def _gdiplus():
    global _token
    g = ctypes.windll.gdiplus
    if _token is None:
        token = ctypes.c_size_t()
        si = _StartupInput(1, None, False, False)
        if g.GdiplusStartup(ctypes.byref(token), ctypes.byref(si), None) != 0:
            raise OSError('GDI+ did not start')
        _token = token
    return g


def jpeg_to_png(data):
    if not data or data[:2] != b'\xff\xd8':
        return None
    if os.name != 'nt':
        return _jpeg_to_png_elsewhere(data)
    tmp = tempfile.mkdtemp(prefix='nxsave-')
    src, dst = os.path.join(tmp, 'in.jpg'), os.path.join(tmp, 'out.png')
    try:
        with open(src, 'wb') as f:
            f.write(data)
        g = _gdiplus()
        image = ctypes.c_void_p()
        if g.GdipLoadImageFromFile(ctypes.c_wchar_p(src), ctypes.byref(image)) != 0:
            return None
        try:
            clsid = _GUID()
            ctypes.windll.ole32.CLSIDFromString(ctypes.c_wchar_p(PNG_ENCODER), ctypes.byref(clsid))
            if g.GdipSaveImageToFile(image, ctypes.c_wchar_p(dst), ctypes.byref(clsid), None) != 0:
                return None
        finally:
            g.GdipDisposeImage(image)
        with open(dst, 'rb') as f:
            return f.read()
    except OSError:
        return None
    finally:
        for p in (src, dst):
            try:
                os.remove(p)
            except OSError:
                pass
        try:
            os.rmdir(tmp)
        except OSError:
            pass
