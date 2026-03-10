# -*- coding: utf-8 -*-
"""
AppSelecter — トースト風セレクターUI
ファイルをダブルクリックした際に表示される、アプリ選択ダイアログ。
拡張子に紐づいたアプリのみを表示し、選択すると起動して自身は終了する。
"""

import subprocess
import sys
import os
import tkinter as tk
from tkinter import messagebox

from config import (
    APP_NAME,
    TOAST_WIDTH,
    TOAST_MIN_HEIGHT,
    TOAST_BUTTON_HEIGHT,
    TOAST_PADDING,
)
from settings import load_settings, get_apps_for_extension, get_timer_seconds


class LauncherWindow(tk.Tk):
    """拡張子に紐づいた軽量アプリ選択ランチャー"""

    NORMAL_BG = "#1f1f1f"
    NORMAL_FG = "#f4f4f4"
    MUTED_FG = "#b0b0b0"
    SELECTED_BG = "#2d5cff"
    SELECTED_FG = "#ffffff"
    BORDER_COLOR = "#3a3a3a"

    def __init__(self, file_path: str):
        super().__init__()

        self._file_path = file_path
        self._ext = os.path.splitext(file_path)[1].lower()
        self._settings = load_settings()
        self._apps = get_apps_for_extension(self._settings, self._ext)
        self._timer_sec = get_timer_seconds(self._settings)
        self._remaining = self._timer_sec
        self._timer_id = None

        # 起動直後の一時的な FocusOut では閉じないようにする
        self._ready_to_close = False
        self._once_focused = False

        # 起動高速化のため main.py から移動してきたファイルチェック
        if not os.path.exists(self._file_path):
            self._show_error_and_exit(f"ファイルが見つかりません:\n{self._file_path}")
            return

        # ウィンドウ設定
        self.title(f"{APP_NAME} — {self._ext}")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=self.NORMAL_BG, bd=1, highlightthickness=1, highlightbackground=self.BORDER_COLOR)

        self._build_ui()
        self._position_at_cursor()

        # まず可視化とフォーカス取得を優先し、その後タイマーを開始する
        self.deiconify()
        self.update()
        self._force_focus()
        self.after(0, self._start_timer)

        # 起動直後は Explorer や OS 側のフォーカス遷移が落ち着くまで FocusOut を無視する
        self.after(1000, self._enable_close)

        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)
        self.bind("<Escape>", lambda e: self._close(reason="Escape Key"))

        # キーボード操作対応
        self.bind("<Up>", self._on_key_up)
        self.bind("<Down>", self._on_key_down)
        self.bind("<Return>", self._on_key_enter)
        self.bind("<space>", self._on_key_space)
        self.bind("<Tab>", self._on_key_tab)
        self.bind("<ISO_Left_Tab>", lambda e: self._on_key_tab(e, reverse=True))
        self.bind("<Shift-Tab>", lambda e: self._on_key_tab(e, reverse=True))
        for i in range(1, 10):
            self.bind(str(i), lambda e, idx=i - 1: self._launch_app(idx) if idx < len(self._apps) else None)

    def _force_focus(self, count=0):
        """ウィンドウを強制的にフォアグラウンドに持ってくる（複数回試行）"""
        self.lift()
        self.attributes("-topmost", True)
        self.focus_force()

        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            hwnd = self.winfo_id()
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass

        # 関連付け起動時はExplorerにフォーカスを奪われやすいため、短い間隔で数回繰り返す
        if count < 8:
            self.after(50, lambda: self._force_focus(count + 1))

    def _show_error_and_exit(self, message):
        """エラーを表示して終了する"""
        messagebox.showerror(APP_NAME, message)
        self.destroy()
        sys.exit(1)

    def _enable_close(self):
        self._ready_to_close = True

    def _on_focus_in(self, event=None):
        """一度でもフォーカスを得たことを記録する。"""
        self._once_focused = True

    def _on_focus_out(self, event=None):
        """起動直後の一時的なフォーカス喪失では閉じない。"""
        if not self._ready_to_close:
            return

        self.after(120, lambda: self._close(check_focus=True, reason="Focus Lost"))

    def _build_ui(self):
        """軽量なTkウィジェットだけでUIを構築する。"""
        main_frame = tk.Frame(self, bg=self.NORMAL_BG)
        main_frame.pack(fill="both", expand=True, padx=1, pady=1)

        file_name = os.path.basename(self._file_path)
        header_text = f"{file_name} ({self._ext})"
        tk.Label(
            main_frame,
            text=header_text,
            bg=self.NORMAL_BG,
            fg=self.NORMAL_FG,
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 11, "bold"),
        ).pack(fill="x", padx=TOAST_PADDING, pady=(TOAST_PADDING, 4))

        tk.Label(
            main_frame,
            text="Tab / ↑↓ で選択、Enter / Space / 数字で実行",
            bg=self.NORMAL_BG,
            fg=self.MUTED_FG,
            anchor="w",
            justify="left",
            font=("Yu Gothic UI", 9),
        ).pack(fill="x", padx=TOAST_PADDING, pady=(0, 8))

        if not self._apps:
            tk.Label(
                main_frame,
                text="この拡張子にアプリが登録されていません。\nAppSelecter.exe を直接起動して設定してください。",
                bg=self.NORMAL_BG,
                fg=self.MUTED_FG,
                justify="left",
                wraplength=TOAST_WIDTH - TOAST_PADDING * 2,
                font=("Yu Gothic UI", 10),
            ).pack(fill="x", padx=TOAST_PADDING, pady=(8, 16))
        else:
            self._app_buttons = []
            self._selected_index = 0
            for i, app in enumerate(self._apps):
                btn = tk.Button(
                    main_frame,
                    text=f"{i + 1}. {app['name']}",
                    anchor="w",
                    relief="flat",
                    bd=0,
                    activebackground=self.SELECTED_BG,
                    activeforeground=self.SELECTED_FG,
                    bg=self.NORMAL_BG,
                    fg=self.NORMAL_FG,
                    highlightthickness=0,
                    padx=12,
                    pady=8,
                    font=("Yu Gothic UI", 11),
                    command=lambda idx=i: self._launch_app(idx),
                    takefocus=False,
                )
                btn.pack(fill="x", padx=TOAST_PADDING, pady=1)
                self._app_buttons.append(btn)
            self._update_button_selection()

        self._timer_label = tk.Label(
            main_frame,
            text="",
            bg=self.NORMAL_BG,
            fg=self.MUTED_FG,
            font=("Yu Gothic UI", 9),
            anchor="w",
            justify="left",
        )
        self._timer_label.pack(fill="x", padx=TOAST_PADDING, pady=(8, TOAST_PADDING))

        num_buttons = max(len(self._apps), 1)
        self._calculated_height = (
            TOAST_PADDING * 2
            + 52
            + num_buttons * (TOAST_BUTTON_HEIGHT - 10)
            + 42
        )
        self._calculated_height = max(self._calculated_height, TOAST_MIN_HEIGHT)
        self.geometry(f"{TOAST_WIDTH}x{self._calculated_height}")

    def _update_button_selection(self):
        """ボタンの選択状態（見た目）を更新する。"""
        if not hasattr(self, "_app_buttons"):
            return

        for i, btn in enumerate(self._app_buttons):
            if i == self._selected_index:
                btn.configure(bg=self.SELECTED_BG, fg=self.SELECTED_FG)
            else:
                btn.configure(bg=self.NORMAL_BG, fg=self.NORMAL_FG)

    def _on_key_up(self, event):
        if not self._apps:
            return "break"
        self._selected_index = (self._selected_index - 1) % len(self._apps)
        self._update_button_selection()
        return "break"

    def _on_key_down(self, event):
        if not self._apps:
            return "break"
        self._selected_index = (self._selected_index + 1) % len(self._apps)
        self._update_button_selection()
        return "break"

    def _on_key_enter(self, event):
        if 0 <= self._selected_index < len(self._apps):
            self._launch_app(self._selected_index)
        return "break"

    def _on_key_space(self, event):
        if 0 <= self._selected_index < len(self._apps):
            self._launch_app(self._selected_index)
        return "break"

    def _on_key_tab(self, event, reverse=False):
        """Tabキーによる項目移動。"""
        if not self._apps:
            return "break"

        step = -1 if reverse else 1
        self._selected_index = (self._selected_index + step) % len(self._apps)
        self._update_button_selection()
        return "break"

    def _position_at_cursor(self):
        """マウスカーソルの位置にウィンドウを配置する。"""
        x = self.winfo_pointerx()
        y = self.winfo_pointery()

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        win_w = TOAST_WIDTH
        win_h = self._calculated_height

        if x + win_w > screen_w:
            x = screen_w - win_w - 10
        if y + win_h > screen_h:
            y = screen_h - win_h - 10

        self.geometry(f"+{x}+{y}")

    def _launch_app(self, index: int):
        """選択されたアプリを起動し、自身を終了する。"""
        app = self._apps[index]
        app_path = app["path"]

        if not os.path.exists(app_path):
            messagebox.showerror(
                APP_NAME,
                f"アプリが見つかりません:\n{app_path}"
            )
            return

        try:
            resolved_file = os.path.normpath(self._file_path)
            command = [app_path, resolved_file]

            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS

            subprocess.Popen(
                command,
                shell=False,
                creationflags=creation_flags
            )
        except Exception as e:
            messagebox.showerror(
                APP_NAME,
                f"アプリの起動に失敗しました:\n{e}"
            )
            return

        self._close(reason="App Launched")

    def _start_timer(self):
        """オートクローズタイマーを開始する。"""
        self._update_timer_display()
        self._tick()

    def _tick(self):
        """1秒ごとにカウントダウンする。"""
        if not self.winfo_exists():
            return

        if self._remaining <= 0:
            self._close(reason="Timer Expired")
            return

        self._remaining -= 1
        self._update_timer_display()
        self._timer_id = self.after(1000, self._tick)

    def _update_timer_display(self):
        """タイマーの残り時間を表示する。"""
        if self.winfo_exists():
            self._timer_label.configure(
                text=f"{self._remaining}秒後に自動で閉じます"
            )

    def _close(self, event=None, check_focus=False, reason="Unknown"):
        """ウィンドウを閉じてアプリケーションを終了する。"""
        if check_focus:
            if not self._ready_to_close:
                return
            if not self._once_focused:
                return
            if self.focus_get() is not None:
                return

        print(f"[Launcher] Closing UI. Reason: {reason}")

        if self._timer_id:
            try:
                self.after_cancel(self._timer_id)
            except Exception:
                pass
            self._timer_id = None

        if self.winfo_exists():
            try:
                self.quit()
                self.destroy()
            except Exception:
                pass


def show_launcher(file_path: str):
    """トースト風ランチャーを表示する。"""
    try:
        app = LauncherWindow(file_path)
        if app.winfo_exists():
            app.mainloop()
    except Exception as e:
        print(f"[Launcher] 終了時のエラーを抑制しました: {e}")
