# -*- coding: utf-8 -*-
"""
AppSelecter — トースト風セレクターUI
ファイルをダブルクリックした際に表示される、アプリ選択ダイアログ。
拡張子に紐づいたアプリのみを表示し、選択すると起動して自身は終了する。
"""

import subprocess
import sys
import os
import time
import logging
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

# フォールバック用のNullLogger
_null_logger = logging.getLogger("AppSelecter.null")
_null_logger.addHandler(logging.NullHandler())


class LauncherWindow(tk.Tk):
    """拡張子に紐づいた軽量アプリ選択ランチャー"""

    NORMAL_BG = "#1f1f1f"
    NORMAL_FG = "#f4f4f4"
    MUTED_FG = "#b0b0b0"
    SELECTED_BG = "#2d5cff"
    SELECTED_FG = "#ffffff"
    BORDER_COLOR = "#3a3a3a"

    # FocusOutを無視する起動後の猶予時間(ms)
    _FOCUS_GUARD_MS = 1500
    # FocusOut後にフォーカスを再確認するまでの待機時間(ms)
    _FOCUS_RECHECK_MS = 200
    # フォーカス再取得を試みる回数
    _FOCUS_RETRY_MAX = 12
    # フォーカス再取得の間隔(ms)
    _FOCUS_RETRY_INTERVAL_MS = 60

    def __init__(self, file_path: str, logger: logging.Logger = None):
        super().__init__()

        self._log = logger or _null_logger
        self._log.info("LauncherWindow.__init__ start")

        self._file_path = file_path
        self._ext = os.path.splitext(file_path)[1].lower()
        self._settings = load_settings()
        self._apps = get_apps_for_extension(self._settings, self._ext)
        self._timer_sec = get_timer_seconds(self._settings)
        self._remaining = self._timer_sec
        self._timer_id = None
        self._closed = False  # 二重クローズ防止フラグ
        self._birth_time = time.time()

        # === フォーカス管理の状態 ===
        # _ready_to_close: 起動直後のガード期間が終わるまで False
        # _user_interacted: ユーザーが明示的にウィンドウと対話したか (クリック/キー)
        # _focus_in_count: FocusIn を受け取った累積回数
        self._ready_to_close = False
        self._user_interacted = False
        self._focus_in_count = 0

        self._log.info(f"ext={self._ext}, apps={len(self._apps)}, timer={self._timer_sec}s")

        # 起動高速化のため main.py から移動してきたファイルチェック
        if not os.path.exists(self._file_path):
            self._log.warning(f"File not found: {self._file_path}")
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
        self.update_idletasks()
        self._force_focus()
        self.after(0, self._start_timer)

        # 起動直後は Explorer や OS 側のフォーカス遷移が落ち着くまで FocusOut を無視する
        self.after(self._FOCUS_GUARD_MS, self._enable_close)

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

        # ウィンドウ内クリックでユーザー操作を記録
        self.bind("<ButtonPress>", self._on_user_interact)

        self._log.info("LauncherWindow.__init__ complete")

    # ==============================================================
    # フォーカス管理
    # ==============================================================
    def _force_focus(self, count=0):
        """ウィンドウを強制的にフォアグラウンドに持ってくる（複数回試行）"""
        if self._closed:
            return
        self.lift()
        self.attributes("-topmost", True)
        self.focus_force()

        try:
            import ctypes
            # tkinter の winfo_id() で取得したハンドルに対して
            # SetForegroundWindow を呼ぶ。
            hwnd = self.winfo_id()
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass

        # 関連付け起動時はExplorerにフォーカスを奪われやすいため、短い間隔で数回繰り返す
        if count < self._FOCUS_RETRY_MAX:
            self.after(self._FOCUS_RETRY_INTERVAL_MS, lambda: self._force_focus(count + 1))

    def _show_error_and_exit(self, message):
        """エラーを表示して終了する"""
        self._log.error(f"show_error_and_exit: {message}")
        messagebox.showerror(APP_NAME, message)
        self.destroy()
        sys.exit(1)

    def _enable_close(self):
        """ガード期間終了後、FocusOutによる自動クローズを有効にする。"""
        self._ready_to_close = True
        age_ms = int((time.time() - self._birth_time) * 1000)
        self._log.info(
            f"_enable_close called (age={age_ms}ms, focus_in_count={self._focus_in_count})"
        )

    def _on_focus_in(self, event=None):
        """フォーカスを得たことを記録する。"""
        self._focus_in_count += 1
        age_ms = int((time.time() - self._birth_time) * 1000)
        self._log.debug(f"FocusIn #{self._focus_in_count} (age={age_ms}ms)")

    def _on_focus_out(self, event=None):
        """フォーカスが失われた場合の処理。
        
        重要: 拡張子紐づけ起動時は Explorer のシェルプロセスが起動元のため、
        OS レベルのフォーカス遷移が通常と異なり、起動直後に複数回の
        FocusOut が発生する。ここでは慎重にガードを掛ける。
        """
        age_ms = int((time.time() - self._birth_time) * 1000)
        self._log.debug(f"FocusOut (age={age_ms}ms, ready={self._ready_to_close})")

        if not self._ready_to_close:
            self._log.debug("FocusOut ignored: guard period")
            return

        # FocusOut の直後は OS 側のフォーカス遷移がまだ安定していないことがある。
        # 少し待ってからフォーカスの最終状態を確認する。
        self.after(self._FOCUS_RECHECK_MS, self._check_focus_and_close)

    def _check_focus_and_close(self):
        """FocusOut 後のフォーカス最終確認。本当にフォーカスが無ければ閉じる。"""
        if self._closed:
            return
        if not self._ready_to_close:
            return

        # 既にフォーカスが戻っている場合は何もしない
        current_focus = self.focus_get()
        if current_focus is not None:
            self._log.debug(f"_check_focus_and_close: focus recovered → {current_focus}")
            return

        # ユーザーが一度もウィンドウと明示的に対話していない場合、
        # かつ FocusIn が 2 回未満の場合は「OS のフォーカス揺らぎ」と判断して
        # クローズせず、フォーカスの再取得を試みる。
        if not self._user_interacted and self._focus_in_count < 2:
            self._log.info(
                "_check_focus_and_close: no user interaction yet and focus_in < 2 "
                "→ attempting to reclaim focus instead of closing"
            )
            self._force_focus(count=self._FOCUS_RETRY_MAX - 3)
            return

        age_ms = int((time.time() - self._birth_time) * 1000)
        self._log.info(f"Closing due to focus loss (age={age_ms}ms)")
        self._close(reason="Focus Lost")

    def _on_user_interact(self, event=None):
        """ユーザーがウィンドウ内をクリックしたことを記録する。"""
        if not self._user_interacted:
            self._log.info("User interaction detected (click)")
        self._user_interacted = True

    # ==============================================================
    # UI構築
    # ==============================================================
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

    # ==============================================================
    # キーボード操作
    # ==============================================================
    def _on_key_up(self, event):
        self._user_interacted = True
        if not self._apps:
            return "break"
        self._selected_index = (self._selected_index - 1) % len(self._apps)
        self._update_button_selection()
        return "break"

    def _on_key_down(self, event):
        self._user_interacted = True
        if not self._apps:
            return "break"
        self._selected_index = (self._selected_index + 1) % len(self._apps)
        self._update_button_selection()
        return "break"

    def _on_key_enter(self, event):
        self._user_interacted = True
        if 0 <= self._selected_index < len(self._apps):
            self._launch_app(self._selected_index)
        return "break"

    def _on_key_space(self, event):
        self._user_interacted = True
        if 0 <= self._selected_index < len(self._apps):
            self._launch_app(self._selected_index)
        return "break"

    def _on_key_tab(self, event, reverse=False):
        """Tabキーによる項目移動。"""
        self._user_interacted = True
        if not self._apps:
            return "break"

        step = -1 if reverse else 1
        self._selected_index = (self._selected_index + step) % len(self._apps)
        self._update_button_selection()
        return "break"

    # ==============================================================
    # ウィンドウ配置
    # ==============================================================
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

    # ==============================================================
    # アプリ起動
    # ==============================================================
    def _launch_app(self, index: int):
        """選択されたアプリを起動し、自身を終了する。"""
        app = self._apps[index]
        app_path = app["path"]
        self._log.info(f"Launching app: {app['name']} ({app_path})")

        if not os.path.exists(app_path):
            self._log.error(f"App not found: {app_path}")
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
            self._log.info(f"App launched successfully: {command}")
        except Exception as e:
            self._log.error(f"Failed to launch app: {e}")
            messagebox.showerror(
                APP_NAME,
                f"アプリの起動に失敗しました:\n{e}"
            )
            return

        self._close(reason="App Launched")

    # ==============================================================
    # タイマー
    # ==============================================================
    def _start_timer(self):
        """オートクローズタイマーを開始する。"""
        self._update_timer_display()
        self._tick()

    def _tick(self):
        """1秒ごとにカウントダウンする。"""
        if self._closed or not self.winfo_exists():
            return

        if self._remaining <= 0:
            self._close(reason="Timer Expired")
            return

        self._remaining -= 1
        self._update_timer_display()
        self._timer_id = self.after(1000, self._tick)

    def _update_timer_display(self):
        """タイマーの残り時間を表示する。"""
        if not self._closed and self.winfo_exists():
            self._timer_label.configure(
                text=f"{self._remaining}秒後に自動で閉じます"
            )

    # ==============================================================
    # ウィンドウ終了
    # ==============================================================
    def _close(self, event=None, reason="Unknown"):
        """ウィンドウを閉じてアプリケーションを終了する。"""
        if self._closed:
            self._log.debug(f"_close called again (reason={reason}) but already closed")
            return
        self._closed = True

        age_ms = int((time.time() - self._birth_time) * 1000)
        self._log.info(
            f"[Launcher] Closing UI. Reason: {reason}, "
            f"age={age_ms}ms, focus_in_count={self._focus_in_count}, "
            f"user_interacted={self._user_interacted}"
        )

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


def show_launcher(file_path: str, logger: logging.Logger = None):
    """トースト風ランチャーを表示する。"""
    log = logger or _null_logger
    try:
        log.info(f"show_launcher called with file_path={file_path}")
        app = LauncherWindow(file_path, logger=log)
        if app.winfo_exists():
            log.info("Entering mainloop")
            app.mainloop()
            log.info("mainloop exited")
    except Exception as e:
        log.error(f"Exception in show_launcher: {e}", exc_info=True)
        print(f"[Launcher] 終了時のエラーを抑制しました: {e}")
