#!/usr/bin/env bash

# meta.json から指定キーの値を取得する。
# 引数:
#   $1: meta_file
#       - 読み取り対象の meta.json ファイルパス。
#   $2: key
#       - 取得したいトップレベルキー名。例: "resourceGroupName", "paramsFile"
# 出力:
#   - 取得した値を標準出力へ 1 行で出力する。
#   - キーが存在しない場合は空文字を出力する。
# 注意:
#   - JSON の値型は Python 側の print で文字列表現に変換される。
#   - 呼び出し側は通常コマンド置換で受け取り、空文字かどうかを後続で検証する。
meta_get() {
  local meta_file="$1"
  local key="$2"

  META_FILE="$meta_file" META_KEY="$key" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(meta.get(os.environ["META_KEY"], ""))
PY
}

# meta.json の真偽値キーを、"true" / "false" の文字列として取得する。
# 引数:
#   $1: meta_file
#       - 読み取り対象の meta.json ファイルパス。
#   $2: key
#       - 取得したい真偽値キー名。例: "deploy"
#   $3: default_value（省略可, 既定値: "true"）
#       - キー未存在時に使うデフォルト値（"true" または "false" を想定）。
# 出力:
#   - 標準出力に "true" または "false" を出力する（小文字固定）。
# 挙動:
#   - JSON 側の値を bool 化してから文字列化するため、呼び出し側は
#     `if [[ "$flag" == "true" ]]; then ...` の形で統一して扱える。
meta_bool() {
  local meta_file="$1"
  local key="$2"
  local default_value="${3:-true}"

  META_FILE="$meta_file" META_KEY="$key" META_DEFAULT="$default_value" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
default_value = os.environ.get("META_DEFAULT", "true").lower() == "true"
print(str(bool(meta.get(os.environ["META_KEY"], default_value))).lower())
PY
}

# meta.json から文字列を取得し、前後の空白を除去して返す。
# 引数:
#   $1: meta_file
#       - 読み取り対象の meta.json ファイルパス。
#   $2: key
#       - 取得したいトップレベルキー名。
# 出力:
#   - 取得値を文字列化し、strip（前後空白除去）した結果を標準出力へ出力する。
#   - キー未存在時は空文字を出力する。
# 用途:
#   - 名前や ID 文字列などで、設定値に不要な空白が混ざる可能性を排除したい場合に使う。
#   - 空白除去が不要な通常取得は `meta_get` を使う。
meta_get_stripped() {
  local meta_file="$1"
  local key="$2"

  META_FILE="$meta_file" META_KEY="$key" python - <<'PY'
import json
import os
from pathlib import Path

meta = json.loads(Path(os.environ["META_FILE"]).read_text(encoding="utf-8"))
print(str(meta.get(os.environ["META_KEY"], "")).strip())
PY
}
