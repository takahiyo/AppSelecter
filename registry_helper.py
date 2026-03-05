# -*- coding: utf-8 -*-
"""
AppSelecter — レジストリ操作ヘルパー
HKCU\Software\Classes に対して最小限の書き込みを行い、
拡張子の関連付けを登録 / 解除する。
"""

import winreg
import os
import sys
from config import get_registry_type_name, get_app_dir


def _get_exe_path() -> str:
    """AppSelecterの実行ファイルパスを取得する。"""
    if getattr(sys, "frozen", False):
        return sys.executable
    else:
        # 開発中は python.exe + スクリプトパスの組み合わせ
        return os.path.abspath(__file__).replace("registry_helper.py", "main.py")


def register_extension(ext: str) -> bool:
    """
    指定拡張子をAppSelecterに関連付ける。
    HKCU\Software\Classes のみを変更する。

    登録内容:
      HKCU\Software\Classes\.ext             → (Default) = "AppSelecter.ext"
      HKCU\Software\Classes\AppSelecter.ext\shell\open\command
                                              → (Default) = '"path\to\AppSelecter.exe" "%1"'

    戻り値: 成功なら True
    """
    ext = ext.lower()
    if not ext.startswith("."):
        ext = f".{ext}"

    type_name = get_registry_type_name(ext)
    exe_path = _get_exe_path()

    # 開発中は python.exe 経由で main.py を呼ぶコマンドを登録
    if getattr(sys, "frozen", False):
        command = f'"{exe_path}" "%1"'
    else:
        python_exe = sys.executable
        main_py = os.path.join(get_app_dir(), "main.py")
        command = f'"{python_exe}" "{main_py}" "%1"'

    try:
        # 拡張子キーの登録
        # KEY_ALL_ACCESS を試行し、失敗したら KEY_WRITE
        access = winreg.KEY_ALL_ACCESS
        try:
            with winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER,
                rf"Software\Classes\{ext}",
                0,
                access,
            ) as key:
                # 既存のデフォルト値をバックアップ
                try:
                    old_val, _ = winreg.QueryValueEx(key, "")
                    if old_val and old_val != type_name:
                        winreg.SetValueEx(
                            key, "AppSelecter_Backup", 0, winreg.REG_SZ, old_val
                        )
                except FileNotFoundError:
                    pass

                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, type_name)
        except OSError:
            access = winreg.KEY_WRITE
            with winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER,
                rf"Software\Classes\{ext}",
                0,
                access,
            ) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, type_name)

        # コマンドの登録
        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            rf"Software\Classes\{type_name}\shell\open\command",
            0,
            winreg.KEY_WRITE,
        ) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)

        print(f"[Registry] 登録完了: {ext} → {type_name}")
        return True

    except OSError as e:
        print(f"[Registry] 登録失敗: {ext} — {e}")
        # 例外を再送出せず、Falseを返すが、呼び出し側で詳細を拾えるようにする
        return False


def unregister_extension(ext: str) -> bool:
    """
    指定拡張子のAppSelecter関連付けを解除する。
    バックアップされた元の関連付けがあれば復元する。

    戻り値: 成功なら True
    """
    ext = ext.lower()
    if not ext.startswith("."):
        ext = f".{ext}"

    type_name = get_registry_type_name(ext)

    try:
        # 元の関連付けの復元を試みる
        try:
            with winreg.OpenKeyEx(
                winreg.HKEY_CURRENT_USER,
                rf"Software\Classes\{ext}",
                0,
                winreg.KEY_READ | winreg.KEY_WRITE,
            ) as key:
                try:
                    backup_val, _ = winreg.QueryValueEx(key, "AppSelecter_Backup")
                    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, backup_val)
                    winreg.DeleteValue(key, "AppSelecter_Backup")
                    print(f"[Registry] 元の関連付けを復元: {ext} → {backup_val}")
                except FileNotFoundError:
                    # バックアップがなければデフォルト値を削除
                    try:
                        winreg.DeleteValue(key, "")
                    except FileNotFoundError:
                        pass
        except FileNotFoundError:
            pass

        # AppSelecter.ext のキーツリーを削除
        _delete_key_tree(
            winreg.HKEY_CURRENT_USER, rf"Software\Classes\{type_name}"
        )

        print(f"[Registry] 解除完了: {ext}")
        return True

    except OSError as e:
        print(f"[Registry] 解除失敗: {ext} — {e}")
        return False


def is_extension_registered(ext: str) -> bool:
    """指定拡張子がAppSelecterに関連付けられているかチェックする。"""
    ext = ext.lower()
    if not ext.startswith("."):
        ext = f".{ext}"

    type_name = get_registry_type_name(ext)

    try:
        with winreg.OpenKeyEx(
            winreg.HKEY_CURRENT_USER,
            rf"Software\Classes\{ext}",
            0,
            winreg.KEY_READ,
        ) as key:
            val, _ = winreg.QueryValueEx(key, "")
            return val == type_name
    except (FileNotFoundError, OSError):
        return False


def _delete_key_tree(root_key, sub_key: str) -> None:
    """
    レジストリキーをそのサブキーごと再帰的に削除する。
    winreg.DeleteKey は空でないキーを削除できないため、
    子キーを先に削除する必要がある。
    """
    try:
        with winreg.OpenKeyEx(root_key, sub_key, 0, winreg.KEY_READ) as key:
            # サブキーを列挙
            sub_keys = []
            i = 0
            while True:
                try:
                    sub_keys.append(winreg.EnumKey(key, i))
                    i += 1
                except OSError:
                    break

        # 子キーを再帰的に削除
        for child in sub_keys:
            _delete_key_tree(root_key, rf"{sub_key}\{child}")

        # 自身を削除
        winreg.DeleteKey(root_key, sub_key)
    except FileNotFoundError:
        pass
