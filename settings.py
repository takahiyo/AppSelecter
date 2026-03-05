# -*- coding: utf-8 -*-
"""
AppSelecter — 設定管理
JSON形式の設定ファイルの読み書きを一元管理する。
"""

import json
import os
from config import (
    get_settings_path,
    DEFAULT_TIMER_SEC,
    MIN_TIMER_SEC,
    MAX_TIMER_SEC,
)


def _create_default_settings() -> dict:
    """デフォルト設定を生成する。"""
    return {
        "timer_seconds": DEFAULT_TIMER_SEC,
        "extensions": {}
    }


def load_settings() -> dict:
    """
    設定ファイルを読み込む。
    存在しない場合はデフォルト設定を新規作成して返す。
    """
    path = get_settings_path()

    if not os.path.exists(path):
        default = _create_default_settings()
        save_settings(default)
        return default

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # バリデーション: timer_seconds の範囲チェック
        timer = data.get("timer_seconds", DEFAULT_TIMER_SEC)
        data["timer_seconds"] = max(MIN_TIMER_SEC, min(MAX_TIMER_SEC, timer))

        # extensions キーがなければ空辞書を補完
        if "extensions" not in data:
            data["extensions"] = {}

        return data

    except (json.JSONDecodeError, OSError) as e:
        print(f"[Settings] 設定ファイルの読み込みに失敗: {e}")
        default = _create_default_settings()
        save_settings(default)
        return default


def save_settings(data: dict) -> None:
    """設定ファイルをJSONとして保存する。"""
    path = get_settings_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except OSError as e:
        print(f"[Settings] 設定ファイルの保存に失敗: {e}")


# =====================================
# 拡張子・アプリ操作のヘルパー関数
# =====================================

def get_apps_for_extension(settings: dict, ext: str) -> list:
    """
    指定した拡張子に登録されているアプリのリストを返す。
    拡張子が未登録の場合は空リストを返す。
    ext は ".txt" のようにドット付きで渡す。
    """
    ext = ext.lower()
    ext_data = settings.get("extensions", {}).get(ext, {})
    return ext_data.get("apps", [])


def add_extension(settings: dict, ext: str) -> dict:
    """
    拡張子を設定に追加する。
    既に存在する場合は何もしない。
    """
    ext = ext.lower()
    if not ext.startswith("."):
        ext = f".{ext}"

    if ext not in settings.get("extensions", {}):
        settings.setdefault("extensions", {})[ext] = {"apps": []}

    return settings


def remove_extension(settings: dict, ext: str) -> dict:
    """拡張子を設定から削除する。"""
    ext = ext.lower()
    settings.get("extensions", {}).pop(ext, None)
    return settings


def add_app_to_extension(settings: dict, ext: str, name: str, path: str) -> dict:
    """
    指定した拡張子にアプリを追加する。
    拡張子が存在しなければ先に作成する。
    """
    ext = ext.lower()
    settings = add_extension(settings, ext)
    apps = settings["extensions"][ext]["apps"]
    apps.append({"name": name, "path": path})
    return settings


def remove_app_from_extension(settings: dict, ext: str, index: int) -> dict:
    """指定した拡張子のアプリをインデックスで削除する。"""
    ext = ext.lower()
    apps = settings.get("extensions", {}).get(ext, {}).get("apps", [])
    if 0 <= index < len(apps):
        apps.pop(index)
    return settings


def update_app_in_extension(
    settings: dict, ext: str, index: int, name: str = None, path: str = None
) -> dict:
    """指定した拡張子のアプリ情報を更新する。"""
    ext = ext.lower()
    apps = settings.get("extensions", {}).get(ext, {}).get("apps", [])
    if 0 <= index < len(apps):
        if name is not None:
            apps[index]["name"] = name
        if path is not None:
            apps[index]["path"] = path
    return settings


def move_app_up(settings: dict, ext: str, index: int) -> dict:
    """アプリの表示順を一つ上げる。"""
    ext = ext.lower()
    apps = settings.get("extensions", {}).get(ext, {}).get("apps", [])
    if 1 <= index < len(apps):
        apps[index - 1], apps[index] = apps[index], apps[index - 1]
    return settings


def move_app_down(settings: dict, ext: str, index: int) -> dict:
    """アプリの表示順を一つ下げる。"""
    ext = ext.lower()
    apps = settings.get("extensions", {}).get(ext, {}).get("apps", [])
    if 0 <= index < len(apps) - 1:
        apps[index], apps[index + 1] = apps[index + 1], apps[index]
    return settings


def get_timer_seconds(settings: dict) -> int:
    """タイマー秒数を取得する（バリデーション済み）。"""
    val = settings.get("timer_seconds", DEFAULT_TIMER_SEC)
    return max(MIN_TIMER_SEC, min(MAX_TIMER_SEC, val))


def set_timer_seconds(settings: dict, seconds: int) -> dict:
    """タイマー秒数を設定する（範囲内にクランプ）。"""
    settings["timer_seconds"] = max(MIN_TIMER_SEC, min(MAX_TIMER_SEC, seconds))
    return settings
