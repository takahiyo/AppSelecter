# -*- coding: utf-8 -*-
"""
AppSelecter — 定数・パス管理 (SSOT)
全モジュールで共有される設定値を一元管理するファイル。
ハードコーディングを排除し、このファイルから参照する。
"""

import sys
import os

# =====================================
# アプリケーション情報
# =====================================
APP_NAME = "AppSelecter"
APP_VERSION = "2.1.0"

# Windows App User Model ID (仮想デスクトップ/タスクバー管理用)
# 設定画面用とランチャー（トースト）用で分離することで
# Windowsに別のアプリとして認識させ、デスクトップの独立性を高める
AUMID_SETTINGS = f"Takahiyo.AppSelecter.Settings.{APP_VERSION}"
AUMID_LAUNCHER = f"Takahiyo.AppSelecter.Launcher.{APP_VERSION}"

# =====================================
# タイマー設定
# =====================================
DEFAULT_TIMER_SEC = 5    # デフォルトの自動クローズ秒数
MIN_TIMER_SEC = 1        # 最小値
MAX_TIMER_SEC = 60       # 最大値

# =====================================
# UI設定
# =====================================
# トーストUIのサイズ
TOAST_WIDTH = 400
TOAST_MIN_HEIGHT = 150
TOAST_BUTTON_HEIGHT = 50
TOAST_PADDING = 16

# 設定画面のサイズ
SETTINGS_WIDTH = 700
SETTINGS_HEIGHT = 550

# テーマ
UI_THEME = "dark"          # "dark" or "light"
UI_COLOR_THEME = "blue"    # CustomTkinterのカラーテーマ

# =====================================
# パス解決
# =====================================
def get_app_dir() -> str:
    """
    exe化されている場合はexeのディレクトリ、
    スクリプト実行の場合はスクリプトのディレクトリを返す。
    コンフィグファイルは常にこの場所に保存される。
    """
    if getattr(sys, 'frozen', False):
        # PyInstallerでexe化されている場合
        return os.path.dirname(sys.executable)
    else:
        # Pythonスクリプトとして実行されている場合
        return os.path.dirname(os.path.abspath(__file__))


# 設定ファイル名
SETTINGS_FILENAME = "AppSelect_Settings.json"

def get_settings_path() -> str:
    """設定ファイルの絶対パスを返す。"""
    return os.path.join(get_app_dir(), SETTINGS_FILENAME)

# =====================================
# レジストリ関連の定数
# =====================================
# HKCU\Software\Classes 配下に登録するタイプ名のプレフィックス
REGISTRY_TYPE_PREFIX = "AppSelecter"

def get_registry_type_name(ext: str) -> str:
    """
    拡張子から、レジストリに登録するファイルタイプ名を生成する。
    例: ".txt" → "AppSelecter.txt"
    """
    # ドットを除いた拡張子を使用
    clean_ext = ext.lstrip(".")
    return f"{REGISTRY_TYPE_PREFIX}.{clean_ext}"
