# -*- coding: utf-8 -*-
"""
AppSelecter — エントリーポイント
引数に応じて、トースト風起動UI または 設定GUI を表示する。
"""

import sys
import os
import ctypes

from launcher_ui import show_launcher
from settings_ui import show_settings
from config import APP_NAME, AUMID_SETTINGS, AUMID_LAUNCHER

def set_aumid(aumid):
    """WindowsのApp User Model IDを設定する"""
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(aumid)
    except Exception:
        pass

# 全局でハンドルを保持（ガベージコレクション防止）
_mutex_handle = None

def is_already_running(mutex_name):
    """
    WindowsのMutexを使用して、既に同一名のプロセスが動いているかチェックする。
    """
    global _mutex_handle
    kernel32 = ctypes.windll.kernel32
    # Mutexを作成
    _mutex_handle = kernel32.CreateMutexW(None, False, mutex_name)
    last_error = kernel32.GetLastError()
    # 183 = ERROR_ALREADY_EXISTS
    return last_error == 183

def main():
    """
    sys.argv を解析して起動モードを決定する。
    - 引数あり: 指定されたファイルパスの拡張子に対応するランチャーUIを起動
    - 引数なし: 設定UIを起動
    """
    args = sys.argv[1:]

    if args:
        # ランチャーモード
        set_aumid(AUMID_LAUNCHER)
        file_path = " ".join(args).strip('"')
        
        if not os.path.exists(file_path):
            import tkinter.messagebox as messagebox
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(APP_NAME, f"ファイルが見つかりません:\n{file_path}")
            return
            
        show_launcher(file_path)
    else:
        # 設定画面モード
        set_aumid(AUMID_SETTINGS)
        mutex_name = f"Global\\{APP_NAME}_Settings_Mutex"
        if is_already_running(mutex_name):
            # 既に開いている場合は何もしない（静かに終了）
            # 本当はウィンドウを前面に出したいが、onefile環境ではハンドル取得が複雑なため終了のみ
            return
            
        show_settings()


if __name__ == "__main__":
    main()
