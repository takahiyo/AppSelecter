# -*- coding: utf-8 -*-
"""
AppSelecter — エントリーポイント
引数に応じて、トースト風起動UI または 設定GUI を表示する。
"""

import sys
import os
import ctypes
import traceback
import datetime
import logging

# =========================================================
# デバッグログ出力の設定
# =========================================================
_log_file_handle = None  # ファイルハンドルを保持（GC防止）

def setup_logging():
    """標準出力・標準エラー出力をログファイルにリダイレクトする。"""
    global _log_file_handle
    # 開発時とexe化時でログファイルの出力先を統一
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    log_path = os.path.join(base_dir, "AppSelecter_CrashLog.txt")
    
    # 標準出力・標準エラー出力をファイルにリダイレクト
    try:
        _log_file_handle = open(log_path, "a", encoding="utf-8")
        sys.stdout = _log_file_handle
        sys.stderr = _log_file_handle
        print(f"\n--- AppSelecter Launched at {datetime.datetime.now()} ---")
        print(f"sys.argv: {sys.argv}")
        sys.stdout.flush()
    except Exception:
        pass


def setup_debug_logger() -> logging.Logger:
    """launcher_ui 向けの詳細デバッグロガーを構成して返す。
    
    ランチャーモード（拡張子紐づけ起動）は速度優先のため stdout リダイレクトは
    行わないが、問題切り分け用に専用のファイルロガーを用意する。
    """
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    debug_log_path = os.path.join(base_dir, "AppSelecter_Debug.log")

    logger = logging.getLogger("AppSelecter")
    logger.setLevel(logging.DEBUG)

    # 既にハンドラがあれば再追加しない
    if not logger.handlers:
        fh = logging.FileHandler(debug_log_path, encoding="utf-8", mode="a")
        fh.setLevel(logging.DEBUG)
        fmt = logging.Formatter(
            "%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    logger.info("=" * 60)
    logger.info("AppSelecter Launcher started")
    logger.info(f"sys.argv: {sys.argv}")
    logger.info(f"PID: {os.getpid()}")
    return logger

# [BEFORE] 
# from launcher_ui import show_launcher
# from settings_ui import show_settings
# [AFTER]
# show_launcher と show_settings のインポートを _main_logic 内へ移動（遅延インポート）による軽量化

try:
    from config import APP_NAME, AUMID_SETTINGS, AUMID_LAUNCHER
except Exception as e:
    print(f"Import Error: {traceback.format_exc()}")
    sys.exit(1)

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
    try:
        _main_logic()
    except Exception as e:
        print(f"Unhandled Exception: {traceback.format_exc()}")
        import tkinter.messagebox as messagebox
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("AppSelecter Error", f"起動中にエラーが発生しました。\n詳細は AppSelecter_CrashLog.txt を確認してください。\n\n{e}")

def _main_logic():
    """
    sys.argv を解析して起動モードを決定する。
    - 引数あり: 指定されたファイルパスの拡張子に対応するランチャーUIを起動
    - 引数なし: 設定UIを起動
    """
    args = sys.argv[1:]

    if args:
        # ランチャーモード: AUMIDにPIDを付与して完全にユニークにする。
        # これにより、Windows 11 の仮想デスクトップでの「同一アプリの引き寄せ」を防ぐ。
        unique_aumid = f"{AUMID_LAUNCHER}.PID.{os.getpid()}"
        set_aumid(unique_aumid)

        # デバッグロガーの初期化（ファイル出力のみ、stdout はリダイレクトしない）
        logger = setup_debug_logger()

        # 引数を結合し、前後にある引用符を確実に削除。
        # Windowsの関連付けから渡されるパスを正しく扱う。
        file_path = " ".join(args).strip().strip('"')
        logger.info(f"Resolved file_path: {file_path}")
        
        # 遅延インポートによる起動高速化
        logger.info("Importing launcher_ui")
        from launcher_ui import show_launcher
        logger.info("Calling show_launcher")
        show_launcher(file_path, logger=logger)
    else:
        # 設定画面モード
        setup_logging()  # 設定画面は速度優先ではないためログを有効化
        set_aumid(AUMID_SETTINGS)
        mutex_name = f"Global\\{APP_NAME}_Settings_Mutex"
        if is_already_running(mutex_name):
            print("Settings window is already running. Exiting.")
            # 既に開いている場合は何もしない（静かに終了）
            # 本当はウィンドウを前面に出したいが、onefile環境ではハンドル取得が複雑なため終了のみ
            return
            
        print("Starting settings_ui")
        # [BEFORE]
        # show_settings()
        # [AFTER]
        # 遅延インポートによるメモリ節約
        from settings_ui import show_settings
        show_settings()


if __name__ == "__main__":
    main()
