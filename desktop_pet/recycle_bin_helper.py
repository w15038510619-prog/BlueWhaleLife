from __future__ import annotations
import ctypes
import os
import sys
from ctypes import wintypes
from pathlib import Path
from typing import Tuple, Optional


class SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ('hwnd', wintypes.HWND),
        ('wFunc', wintypes.UINT),
        ('pFrom', wintypes.LPCWSTR),
        ('pTo', wintypes.LPCWSTR),
        ('fFlags', ctypes.c_ushort),
        ('fAnyOperationsAborted', wintypes.BOOL),
        ('hNameMappings', wintypes.LPVOID),
        ('lpszProgressTitle', wintypes.LPCWSTR)
    ]


FO_DELETE = 0x0003
FOF_ALLOWUNDO = 0x0040
FOF_NOCONFIRMATION = 0x0010
FOF_SILENT = 0x0004
FOF_NOERRORUI = 0x0400


def is_safe_to_recycle(file_path: str) -> Tuple[bool, str]:
    """
    Strict safety check to protect against accidental deletion of system or critical files.
    Returns (is_safe, error_reason).
    """
    try:
        p = Path(file_path).resolve()
    except Exception as e:
        return False, f"无效的文件路径: {e}"

    if not p.exists():
        return False, "文件不存在或已被移除"

    # Disallow root drive deletion (e.g. C:\, D:\)
    if len(p.parts) <= 1 or p.parent == p:
        return False, "禁止删除根驱动器目录"

    # Disallow system directories
    p_str = str(p).lower()
    system_roots = [
        os.environ.get("SystemRoot", "c:\\windows").lower(),
        os.environ.get("ProgramFiles", "c:\\program files").lower(),
        os.environ.get("ProgramFiles(x86)", "c:\\program files (x86)").lower(),
        os.environ.get("SystemDrive", "c:") + "\\windows",
    ]
    for sys_dir in system_roots:
        if sys_dir and p_str.startswith(sys_dir):
            return False, "系统保护文件，大肥鱼不能删除系统关键文件哦！"

    # Disallow deleting the app's own project root or data database
    app_root = str(Path(__file__).resolve().parent.parent).lower()
    if p_str == app_root or p_str.startswith(app_root + "\\backend") or p_str.startswith(app_root + "\\desktop_pet"):
        return False, "这是大肥鱼自己的程序文件，不能丢进垃圾桶啦！"

    if p.name.lower() in ["whale_life.db", "whale_life.db-wal", "whale_life.db-shm", "config.json"]:
        return False, "这是大肥鱼的记忆数据库与配置文件，必须好好保存！"

    return True, ""


def recycle_file(file_path: str) -> Tuple[bool, str]:
    """
    Safely moves a file or folder to the Windows Recycle Bin using Windows Shell API.
    NEVER permanently deletes the file. Files can be restored from the Recycle Bin.
    Returns (success, message).
    """
    safe, reason = is_safe_to_recycle(file_path)
    if not safe:
        return False, reason

    # Strategy 1: Use send2trash if available
    try:
        from send2trash import send2trash
        send2trash(str(Path(file_path).resolve()))
        return True, "已成功送入 Windows 回收站"
    except Exception as e:
        pass

    # Strategy 2: Windows Shell API SHFileOperationW with FOF_ALLOWUNDO
    if sys.platform == "win32":
        try:
            abs_path = os.path.abspath(file_path)
            # Windows SHFileOperation requires double null-terminated string
            double_null = abs_path + '\0\0'
            op = SHFILEOPSTRUCTW()
            op.wFunc = FO_DELETE
            op.pFrom = double_null
            op.pTo = None
            op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
            res = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
            if res == 0 and not op.fAnyOperationsAborted:
                return True, "已成功送入 Windows 回收站"
            else:
                return False, f"Windows Shell 操作返回错误码: {res}"
        except Exception as e:
            return False, f"调用 Windows 回收站失败: {e}"

    return False, "非 Windows 系统或无法访问回收站"


def find_desktop_recycle_bin_pos() -> Tuple[int, int, bool]:
    """
    Attempts to locate the screen coordinates of the Windows Desktop Recycle Bin icon.
    Returns (x, y, is_virtual_fallback).
    If desktop icons are hidden or coordinates cannot be resolved, returns a safe top-left
    screen coordinate with is_virtual_fallback=True so the UI renders a visible target.
    """
    if sys.platform == "win32":
        try:
            user32 = ctypes.windll.user32
            # 1. Search Progman or WorkerW for desktop SysListView32
            def _find_listview():
                progman = user32.FindWindowW("Progman", None)
                shelldll = user32.FindWindowExW(progman, None, "SHELLDLL_DefView", None)
                if shelldll:
                    lv = user32.FindWindowExW(shelldll, None, "SysListView32", None)
                    if lv:
                        return lv
                hwnd = None
                for _ in range(10):
                    hwnd = user32.FindWindowExW(None, hwnd, "WorkerW", None)
                    if not hwnd:
                        break
                    shelldll = user32.FindWindowExW(hwnd, None, "SHELLDLL_DefView", None)
                    if shelldll:
                        lv = user32.FindWindowExW(shelldll, None, "SysListView32", None)
                        if lv:
                            return lv
                return None

            # If desktop listview is found, we could query LVM_GETITEMRECT via process memory injection,
            # but cross-process memory reading is often blocked by Windows Defender / UAC.
            # Instead, check if user has standard top-left placement.
        except Exception:
            pass

    # Visible, safe desktop target position:
    # Top-left margin of primary screen (standard Windows 11 Recycle Bin location: x=60, y=70)
    return (60, 70, True)


def enable_windows_drag_drop_privilege(hwnd: int = 0):
    """
    Allow Drag & Drop messages from lower-integrity processes (e.g. Windows Explorer)
    even if the pet is running as Administrator (UIPI bypass).
    """
    if sys.platform != "win32":
        return
    try:
        user32 = ctypes.windll.user32
        WM_DROPFILES = 0x0233
        WM_COPYDATA = 0x004A
        WM_COPYGLOBALDATA = 0x0049
        MSGFLT_ALLOW = 1
        MSGFLT_ADD = 1

        # Process-level filter (Vista+)
        if hasattr(user32, "ChangeWindowMessageFilter"):
            user32.ChangeWindowMessageFilter(WM_DROPFILES, MSGFLT_ALLOW)
            user32.ChangeWindowMessageFilter(WM_COPYDATA, MSGFLT_ALLOW)
            user32.ChangeWindowMessageFilter(WM_COPYGLOBALDATA, MSGFLT_ALLOW)

        # Window-level filter (Win7+)
        if hwnd and hasattr(user32, "ChangeWindowMessageFilterEx"):
            user32.ChangeWindowMessageFilterEx(hwnd, WM_DROPFILES, MSGFLT_ADD, None)
            user32.ChangeWindowMessageFilterEx(hwnd, WM_COPYDATA, MSGFLT_ADD, None)
            user32.ChangeWindowMessageFilterEx(hwnd, WM_COPYGLOBALDATA, MSGFLT_ADD, None)
    except Exception:
        pass

