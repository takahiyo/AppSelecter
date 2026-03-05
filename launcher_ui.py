# -*- coding: utf-8 -*-
"""
AppSelecter — トースト風セレクターUI
ファイルをダブルクリックした際に表示される、アプリ選択ダイアログ。
拡張子に紐づいたアプリのみを表示し、選択すると起動して自身は終了する。
"""

import subprocess
import sys
import os
import customtkinter as ctk

from config import (
    APP_NAME,
    TOAST_WIDTH,
    TOAST_MIN_HEIGHT,
    TOAST_BUTTON_HEIGHT,
    TOAST_PADDING,
    UI_THEME,
    UI_COLOR_THEME,
)
from settings import load_settings, get_apps_for_extension, get_timer_seconds


class LauncherWindow(ctk.CTk):
    """拡張子に紐づいたアプリ選択トースト"""

    def __init__(self, file_path: str):
        super().__init__()

        self._file_path = file_path
        self._ext = os.path.splitext(file_path)[1].lower()
        self._settings = load_settings()
        self._apps = get_apps_for_extension(self._settings, self._ext)
        self._timer_sec = get_timer_seconds(self._settings)
        self._remaining = self._timer_sec
        self._timer_id = None

        # テーマ設定
        ctk.set_appearance_mode(UI_THEME)
        ctk.set_default_color_theme(UI_COLOR_THEME)

        # ウィンドウ設定
        self.title(f"{APP_NAME} — {self._ext}")
        self.overrideredirect(True)      # タイトルバーなし
        self.attributes("-topmost", True)  # 最前面
        self.attributes("-alpha", 0.97)    # わずかな透過

        self._build_ui()
        self._position_at_cursor()
        self._start_timer()

        # フォーカスが外れたら閉じる
        self.bind("<FocusOut>", lambda e: self._close())
        # Escで閉じる
        self.bind("<Escape>", lambda e: self._close())

    def _build_ui(self):
        """UIを構築する。"""
        # メインフレーム（角丸風の見た目）
        main_frame = ctk.CTkFrame(self, corner_radius=16)
        main_frame.pack(fill="both", expand=True, padx=2, pady=2)

        # ヘッダー: 拡張子情報とファイル名
        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=TOAST_PADDING, pady=(TOAST_PADDING, 8))

        file_name = os.path.basename(self._file_path)
        ctk.CTkLabel(
            header_frame,
            text=f"📂 {file_name}",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).pack(fill="x")

        ctk.CTkLabel(
            header_frame,
            text=f"拡張子: {self._ext}  —  アプリを選択してください",
            font=ctk.CTkFont(size=11),
            text_color="gray60",
            anchor="w",
        ).pack(fill="x")

        # アプリが登録されていない場合
        if not self._apps:
            ctk.CTkLabel(
                main_frame,
                text="この拡張子にアプリが登録されていません。\n"
                     "AppSelecter.exe を直接起動して設定してください。",
                font=ctk.CTkFont(size=12),
                text_color="gray50",
                wraplength=TOAST_WIDTH - TOAST_PADDING * 2,
            ).pack(padx=TOAST_PADDING, pady=20)
        else:
            # アプリボタンの一覧
            for i, app in enumerate(self._apps):
                btn = ctk.CTkButton(
                    main_frame,
                    text=f"  {app['name']}",
                    font=ctk.CTkFont(size=14),
                    height=TOAST_BUTTON_HEIGHT,
                    anchor="w",
                    command=lambda idx=i: self._launch_app(idx),
                )
                btn.pack(
                    fill="x",
                    padx=TOAST_PADDING,
                    pady=(2, 2),
                )

        # フッター: タイマー表示
        self._timer_label = ctk.CTkLabel(
            main_frame,
            text="",
            font=ctk.CTkFont(size=10),
            text_color="gray50",
        )
        self._timer_label.pack(pady=(8, TOAST_PADDING))

        # ウィンドウサイズの計算
        num_buttons = max(len(self._apps), 1)
        height = (
            TOAST_PADDING * 2    # 上下パディング
            + 55                 # ヘッダー
            + num_buttons * (TOAST_BUTTON_HEIGHT + 4)  # ボタン群
            + 40                 # フッター
        )
        height = max(height, TOAST_MIN_HEIGHT)
        self.geometry(f"{TOAST_WIDTH}x{height}")

    def _position_at_cursor(self):
        """マウスカーソルの位置にウィンドウを配置する。"""
        self.update_idletasks()
        # マウスカーソルの座標を取得
        x = self.winfo_pointerx()
        y = self.winfo_pointery()

        # 画面端からはみ出さないよう調整
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        win_w = self.winfo_width()
        win_h = self.winfo_height()

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
            # アプリが見つからない場合のフォールバック
            from tkinter import messagebox
            messagebox.showerror(
                APP_NAME,
                f"アプリが見つかりません:\n{app_path}"
            )
            return

        try:
            # ファイルパスを正規化
            resolved_file = os.path.normpath(self._file_path)
            command = [app_path, resolved_file]
            subprocess.Popen(command, shell=False)
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror(
                APP_NAME,
                f"アプリの起動に失敗しました:\n{e}"
            )
            return

        self._close()

    def _start_timer(self):
        """オートクローズタイマーを開始する。"""
        self._update_timer_display()
        self._tick()

    def _tick(self):
        """1秒ごとにカウントダウンする。"""
        if not self.winfo_exists():
            return

        if self._remaining <= 0:
            self._close()
            return

        self._remaining -= 1
        self._update_timer_display()
        self._timer_id = self.after(1000, self._tick)

    def _update_timer_display(self):
        """タイマーの残り時間を表示する。"""
        if self.winfo_exists():
            self._timer_label.configure(
                text=f"⏱  {self._remaining}秒後に自動的に閉じます"
            )

    def _close(self, event=None):
        """ウィンドウを閉じてアプリケーションを終了する。"""
        # タイマーを確実に止める
        if self._timer_id:
            try:
                self.after_cancel(self._timer_id)
            except Exception:
                pass
            self._timer_id = None

        # Tclインタープリタを停止させてから破棄
        if self.winfo_exists():
            try:
                self.quit()  # mainloop を安全に抜ける
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
        # 稀に発生する初期化中の破棄エラー(TclError)を無視して静かに終了
        print(f"[Launcher] 終了時のエラーを抑制しました: {e}")
