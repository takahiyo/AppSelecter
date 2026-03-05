# -*- coding: utf-8 -*-
"""
AppSelecter — 拡張子・アプリ設定GUI
AppSelecter を引数なしで起動した際に表示される設定画面。
拡張子の追加/削除、アプリの登録、タイマー設定、レジストリ連携を行う。
"""

import customtkinter as ctk
import tkinter.messagebox as messagebox
from tkinter import filedialog
import os

from config import (
    APP_NAME,
    APP_VERSION,
    SETTINGS_WIDTH,
    SETTINGS_HEIGHT,
    UI_THEME,
    UI_COLOR_THEME,
    MIN_TIMER_SEC,
    MAX_TIMER_SEC,
)
from settings import (
    load_settings,
    save_settings,
    add_extension,
    remove_extension,
    add_app_to_extension,
    remove_app_from_extension,
    update_app_in_extension,
    move_app_up,
    move_app_down,
    get_timer_seconds,
    set_timer_seconds,
)
from registry_helper import register_extension, unregister_extension, is_extension_registered


class SettingsWindow(ctk.CTk):
    """AppSelecter の設定管理ウィンドウ"""

    def __init__(self):
        super().__init__()

        self.title(f"{APP_NAME} 設定 (v{APP_VERSION})")
        self.geometry(f"{SETTINGS_WIDTH}x{SETTINGS_HEIGHT}")
        self.minsize(600, 450)

        ctk.set_appearance_mode(UI_THEME)
        ctk.set_default_color_theme(UI_COLOR_THEME)

        self._settings = load_settings()
        self._current_ext = None

        self._build_ui()
        self._load_extensions()

    def _build_ui(self):
        """UIレイアウトの構築"""
        # メインレイアウト: 左側に拡張子リスト、右側に詳細設定
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        # -- 左パネル (拡張子リスト) --
        left_frame = ctk.CTkFrame(self, corner_radius=0)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        left_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(left_frame, text="拡張子", font=ctk.CTkFont(weight="bold", size=14)).grid(
            row=0, column=0, pady=(10, 5), padx=10, sticky="w"
        )

        # リストボックスの代用 (ScrollableFrameとButton)
        self._ext_list_frame = ctk.CTkScrollableFrame(left_frame, fg_color="transparent")
        self._ext_list_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self._ext_buttons = []

        # 拡張子追加領域
        add_ext_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        add_ext_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        add_ext_frame.grid_columnconfigure(0, weight=1)
        
        self._new_ext_entry = ctk.CTkEntry(add_ext_frame, placeholder_text=".ext")
        self._new_ext_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self._new_ext_entry.bind("<Return>", lambda e: self._on_add_extension())
        
        ctk.CTkButton(add_ext_frame, text="+", width=30, command=self._on_add_extension).grid(
            row=0, column=1
        )

        ctk.CTkButton(
            left_frame,
            text="選択した拡張子を削除",
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
            command=self._on_remove_extension
        ).grid(row=3, column=0, pady=(0, 10), padx=10, sticky="ew")

        # -- 右パネル (詳細設定) --
        self._right_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._right_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self._right_frame.grid_columnconfigure(0, weight=1)

        # 初期状態では右パネルは非表示風にしておく
        self._empty_label = ctk.CTkLabel(
            self._right_frame, text="左のリストから拡張子を選択してください", text_color="gray50"
        )
        self._empty_label.grid(row=0, column=0, pady=100)

        # 右パネル中身 (選択時に表示)
        self._detail_frame = ctk.CTkFrame(self._right_frame, fg_color="transparent")
        # detail_frameの子要素
        self._detail_frame.grid_columnconfigure(0, weight=1)
        self._detail_frame.grid_rowconfigure(2, weight=1)

        # ヘッダー部
        header_frame = ctk.CTkFrame(self._detail_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        self._ext_title_label = ctk.CTkLabel(
            header_frame, text="拡張子: ", font=ctk.CTkFont(size=20, weight="bold")
        )
        self._ext_title_label.grid(row=0, column=0, sticky="w")

        # レジストリ連携ボタン
        self._reg_status_label = ctk.CTkLabel(header_frame, text="")
        self._reg_status_label.grid(row=0, column=1, padx=(0, 10))
        self._reg_action_btn = ctk.CTkButton(header_frame, text="", width=120)
        self._reg_action_btn.grid(row=0, column=2)

        # セパレータ
        ctk.CTkFrame(self._detail_frame, height=2, fg_color=("gray70", "gray30")).grid(
            row=1, column=0, sticky="ew", pady=(10, 10)
        )

        # アプリリスト
        ctk.CTkLabel(self._detail_frame, text="登録アプリ一覧:", anchor="w").grid(
            row=2, column=0, sticky="ew", pady=(0, 5)
        )
        self._app_list_frame = ctk.CTkScrollableFrame(self._detail_frame)
        self._app_list_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 10))

        # アプリ追加ボタン群
        app_action_frame = ctk.CTkFrame(self._detail_frame, fg_color="transparent")
        app_action_frame.grid(row=4, column=0, sticky="ew")
        ctk.CTkButton(
            app_action_frame, text="アプリを追加 (参照...)", command=self._on_add_app
        ).pack(side="left", padx=(0, 10))

        # -- 下部パネル (グローバル設定) --
        bottom_frame = ctk.CTkFrame(self, height=60, corner_radius=0)
        bottom_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
        bottom_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(bottom_frame, text="オートクローズ(秒):").grid(
            row=0, column=0, padx=(20, 10), pady=20
        )
        
        self._timer_var = ctk.IntVar(value=get_timer_seconds(self._settings))
        self._timer_slider = ctk.CTkSlider(
            bottom_frame,
            from_=MIN_TIMER_SEC,
            to=MAX_TIMER_SEC,
            number_of_steps=MAX_TIMER_SEC - MIN_TIMER_SEC,
            variable=self._timer_var,
            command=self._on_timer_changed
        )
        self._timer_slider.grid(row=0, column=1, sticky="ew", padx=10)
        
        self._timer_value_label = ctk.CTkLabel(
            bottom_frame, textvariable=self._timer_var, width=30
        )
        self._timer_value_label.grid(row=0, column=2, padx=(0, 20))

    # ==========================================
    # 拡張子リストの管理
    # ==========================================
    def _load_extensions(self):
        """設定から拡張子リストを読み込んでUIに反映する"""
        for btn in self._ext_buttons:
            btn.destroy()
        self._ext_buttons.clear()

        exts = sorted(self._settings.get("extensions", {}).keys())
        
        for ext in exts:
            btn = ctk.CTkButton(
                self._ext_list_frame,
                text=ext,
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                anchor="w",
                command=lambda e=ext: self._select_extension(e)
            )
            btn.pack(fill="x", pady=1)
            self._ext_buttons.append(btn)

        if self._current_ext not in exts:
            self._current_ext = None
            self._detail_frame.grid_remove()
            self._empty_label.grid()
        elif self._current_ext:
            self._select_extension(self._current_ext)

    def _select_extension(self, ext: str):
        """拡張子が選択された時の処理"""
        self._current_ext = ext
        
        # 選択状態の見た目を更新
        for btn in self._ext_buttons:
            if btn.cget("text") == ext:
                btn.configure(fg_color=("gray75", "gray25"))
            else:
                btn.configure(fg_color="transparent")

        self._empty_label.grid_remove()
        self._detail_frame.grid(row=0, column=0, sticky="nsew")
        self._detail_frame.grid_rowconfigure(3, weight=1)

        self._ext_title_label.configure(text=f"拡張子: {ext}")
        self._update_registry_ui()
        self._load_apps()

    def _on_add_extension(self):
        new_ext = self._new_ext_entry.get().strip().lower()
        if not new_ext:
            return
        if not new_ext.startswith("."):
            new_ext = f".{new_ext}"

        self._settings = add_extension(self._settings, new_ext)
        save_settings(self._settings)
        
        self._new_ext_entry.delete(0, "end")
        self._current_ext = new_ext
        self._load_extensions()

    def _on_remove_extension(self):
        if not self._current_ext:
            return
        
        confirm = messagebox.askyesno(
            "確認", f"拡張子 '{self._current_ext}' を削除しますか？"
        )
        if confirm:
            self._settings = remove_extension(self._settings, self._current_ext)
            save_settings(self._settings)
            # レジストリも解除しておくのが親切
            unregister_extension(self._current_ext)
            
            self._current_ext = None
            self._load_extensions()

    # ==========================================
    # アプリリストの管理
    # ==========================================
    def _load_apps(self):
        """選択中の拡張子のアプリリストを再描画する"""
        if not self._current_ext:
            return

        for widget in self._app_list_frame.winfo_children():
            widget.destroy()

        apps = self._settings["extensions"][self._current_ext].get("apps", [])
        
        if not apps:
            ctk.CTkLabel(
                self._app_list_frame, text="登録されたアプリがありません", text_color="gray50"
            ).pack(pady=20)
            return

        for i, app in enumerate(apps):
            app_frame = ctk.CTkFrame(self._app_list_frame, fg_color=("gray85", "gray20"))
            app_frame.pack(fill="x", pady=2, padx=2)
            app_frame.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(app_frame, text=f" {i+1}. ", font=ctk.CTkFont(weight="bold")).grid(
                row=0, column=0, padx=5, pady=5
            )
            
            info_frame = ctk.CTkFrame(app_frame, fg_color="transparent")
            info_frame.grid(row=0, column=1, sticky="ew")
            
            ctk.CTkLabel(info_frame, text=app["name"], anchor="w", font=ctk.CTkFont(weight="bold")).pack(fill="x")
            ctk.CTkLabel(info_frame, text=app["path"], anchor="w", font=ctk.CTkFont(size=10), text_color="gray50").pack(fill="x")

            btn_frame = ctk.CTkFrame(app_frame, fg_color="transparent")
            btn_frame.grid(row=0, column=2, padx=5)

            # ↑↓ ボタン
            ctk.CTkButton(
                btn_frame, text="↑", width=30, 
                state="normal" if i > 0 else "disabled",
                command=lambda idx=i: self._on_move_app_up(idx)
            ).pack(side="left", padx=1)
            
            ctk.CTkButton(
                btn_frame, text="↓", width=30, 
                state="normal" if i < len(apps) - 1 else "disabled",
                command=lambda idx=i: self._on_move_app_down(idx)
            ).pack(side="left", padx=1)

            ctk.CTkButton(
                btn_frame, text="編集", width=50, 
                command=lambda idx=i: self._on_edit_app(idx)
            ).pack(side="left", padx=(5, 2))
            
            ctk.CTkButton(
                btn_frame, text="削除", width=50, fg_color="darkred", hover_color="red",
                command=lambda idx=i: self._on_remove_app(idx)
            ).pack(side="left", padx=2)

    def _on_add_app(self):
        if not self._current_ext:
            return

        filetypes = [("実行ファイル", "*.exe"), ("すべてのファイル", "*.*")]
        path = filedialog.askopenfilename(title="アプリの選択", filetypes=filetypes)
        if path:
            name = os.path.basename(path)
            self._settings = add_app_to_extension(self._settings, self._current_ext, name, path)
            save_settings(self._settings)
            self._load_apps()

    def _on_edit_app(self, index: int):
        app = self._settings["extensions"][self._current_ext]["apps"][index]
        
        # 簡易的なダイアログ (CusomTkinterのInputDialog利用)
        dialog = ctk.CTkInputDialog(text="新しい表示名を入力してください:", title="名前の変更")
        new_name = dialog.get_input()
        
        if new_name and new_name.strip():
            self._settings = update_app_in_extension(
                self._settings, 
                self._current_ext, 
                index, 
                name=new_name.strip()
            )
            save_settings(self._settings)
            self._load_apps()

    def _on_remove_app(self, index: int):
        self._settings = remove_app_from_extension(self._settings, self._current_ext, index)
        save_settings(self._settings)
        self._load_apps()

    def _on_move_app_up(self, index: int):
        self._settings = move_app_up(self._settings, self._current_ext, index)
        save_settings(self._settings)
        self._load_apps()

    def _on_move_app_down(self, index: int):
        self._settings = move_app_down(self._settings, self._current_ext, index)
        save_settings(self._settings)
        self._load_apps()

    # ==========================================
    # タイマー・レジストリ
    # ==========================================
    def _on_timer_changed(self, value):
        val = int(value)
        self._settings = set_timer_seconds(self._settings, val)
        save_settings(self._settings)

    def _update_registry_ui(self):
        if not self._current_ext:
            return

        is_reg = is_extension_registered(self._current_ext)
        if is_reg:
            self._reg_status_label.configure(text="✅ 関連付け済", text_color="green")
            self._reg_action_btn.configure(
                text="関連付けを解除", 
                fg_color="transparent", 
                border_width=1,
                command=self._on_unregister_click
            )
        else:
            self._reg_status_label.configure(text="❌ 未関連付け", text_color="gray50")
            self._reg_action_btn.configure(
                text="関連付ける", 
                fg_color=["#3B8ED0", "#1F6AA5"],
                border_width=0,
                command=self._on_register_click
            )

    def _on_register_click(self):
        if register_extension(self._current_ext):
            self._update_registry_ui()
            messagebox.showinfo("成功", f"Windowsに {self._current_ext} を関連付けました。")
        else:
            messagebox.showerror(
                "エラー", 
                f"関連付けに失敗しました。\n\n"
                f"拡張子: {self._current_ext}\n"
                "原因: アクセスが拒否されたか、システムによってロックされています。\n\n"
                "※.zip 等の一部の拡張子は、Windowsの設定画面から手動で変更が必要な場合があります。"
            )

    def _on_unregister_click(self):
        if unregister_extension(self._current_ext):
            self._update_registry_ui()
            messagebox.showinfo("成功", f"{self._current_ext} の関連付けを解除しました。")
        else:
            messagebox.showerror("エラー", "関連付けの解除に失敗しました。")


def show_settings():
    """設定画面を表示する。"""
    app = SettingsWindow()
    app.mainloop()

if __name__ == "__main__":
    show_settings()
