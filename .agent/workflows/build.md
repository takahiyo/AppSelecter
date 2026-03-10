---
description: PyInstallerを使用してアプリケーションをビルドし、実行ファイルを確認する
---
このワークフローは、プロジェクトをビルドして `dist/AppSelecter/AppSelecter.exe` を生成します。

1. 以前のビルド成果物を削除する（クリーンビルド）
// turbo
run_command: `Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue` (Cwd: e:\Local_Storage\GitHub\AppSelecter\AppSelecter)

2. PyInstallerを実行してビルドする
// turbo
run_command: `pyinstaller AppSelecter.spec --noconfirm` (Cwd: e:\Local_Storage\GitHub\AppSelecter\AppSelecter)

3. 生成された実行ファイルの存在を確認する
// turbo
run_command: `Test-Path dist/AppSelecter/AppSelecter.exe` (Cwd: e:\Local_Storage\GitHub\AppSelecter\AppSelecter)

4. 実行ファイルをテスト起動する（引数付き）
// turbo
run_command: `start dist/AppSelecter/AppSelecter.exe "test.txt"` (Cwd: e:\Local_Storage\GitHub\AppSelecter\AppSelecter)
