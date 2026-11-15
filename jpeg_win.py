"""JPEG to PNG with the decoder Windows has built in (GDI+), for Tk, which shows PNG but not JPEG. Nothing to install.

    png_bytes = jpeg_to_png(jpeg_bytes)      # None when it cannot (not Windows, not a picture)
"""
import ctypes
import os
import tempfile
from ctypes import wintypes

PNG_ENCODER = '{557CF406-1A04-11D3-9A73-0000F81EF32E}'   # GDI+'s PNG encoder


class _GUID(ctypes.Structure):
    _fields_ = [('a', wintypes.DWORD), ('b', wintypes.WORD), ('c', wintypes.WORD), ('d', ctypes.c_ubyte * 8)]


class _StartupInput(ctypes.Structure):
    _fields_ = [('version', ctypes.c_uint32), ('callback', ctypes.c_void_p),
                ('no_thread', wintypes.BOOL), ('no_codecs', wintypes.BOOL)]


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
    if os.name != 'nt' or not data or data[:2] != b'\xff\xd8':
        return None
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
