# -*- coding: utf-8 -*-
"""
AppSelecter — エントリーポイント
引数に応じて、トースト風起動UI または 設定GUI を表示する。
"""

import sys
import os

from launcher_ui import show_launcher
from settings_ui import show_settings
from config import APP_NAME

def main():
    """
    sys.argv を解析して起動モードを決定する。
    - 引数あり: 指定されたファイルパスの拡張子に対応するランチャーUIを起動
    - 引数なし: 設定UIを起動
    """
    # sys.argv[0] はスクリプト名または exe名
    args = sys.argv[1:]

    # 引数が複数渡された場合（パスにスペースが含まれている場合など）
    # 通常、Windowsの関連付けからは1つの引数として "%1" で渡される。
    if args:
        # 稀に分割されて渡されるケースを考慮し結合
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
        # 引数なしは設定画面
        show_settings()


if __name__ == "__main__":
    main()
