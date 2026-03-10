#!/usr/bin/env bash

# Bicep デプロイコマンドを実行し、実行ログを logs 配下へ保存する。
# 引数:
#   $1: log_key
#       - ログファイル名の識別子。例: "aks", "firewall"
#       - 出力先は "${logs_dir}/${timestamp}-${log_key}.log" になる。
#   $2 以降: 実行するコマンド本体
#       - 期待する形式はコマンドと引数を分割した配列/可変長引数。
#       - 例: az deployment group create --name ... --resource-group ...
# 出力/副作用:
#   - 標準出力(stdout): ログファイルへ上書き保存する。
#   - 標準エラー(stderr): ログファイルへ追記しつつ、端末にも表示する。
#   - 関数自体はコマンドの終了コードをそのまま返す（set -e の影響を受ける）。
run_bicep_deployment() {
  local log_key="$1"
  shift
  local log_file
  log_file="$logs_dir/${timestamp}-${log_key}.log"

  "$@" >"$log_file" 2> >(tee -a "$log_file" >&2)
}

# deploy フラグに応じて group deployment を実行/スキップする共通処理。
# 引数:
#   $1: deploy_flag
#       - "true" のときのみデプロイ実行。その他はスキップ扱い。
#   $2: deploy_message
#       - 実行時に表示するメッセージ（"==> " の後ろに表示）。
#   $3: log_key
#       - `run_bicep_deployment` のログ識別子。
#   $4: deployment_name
#       - `az deployment group create --name` に渡すデプロイ名。
#   $5: resource_group
#       - `--resource-group` に渡す対象 RG 名。
#   $6: params_file
#       - `--parameters` に渡す .bicepparam ファイル。
#   $7: skip_message
#       - スキップ時に表示するメッセージ（"==> " の後ろに表示）。
#   $8 以降: extra_args（任意）
#       - 追加の CLI 引数。例: `--parameters administratorPassword=...`
# 挙動:
#   - deploy_flag != "true" の場合は skip_message を表示して return する。
#   - deploy 時は `az deployment group create` の基本引数を組み立て、
#     extra_args と `what_if`（設定時）を末尾に追加して実行する。
# 出力/副作用:
#   - 実行本体は `run_bicep_deployment` を通るため、ログファイル保存ルールを継承する。
#   - Azure の Group Scope デプロイを実行する（--what-if 時は差分確認のみ）。
deploy_group_if_enabled() {
  local deploy_flag="$1"
  local deploy_message="$2"
  local log_key="$3"
  local deployment_name="$4"
  local resource_group="$5"
  local params_file="$6"
  local skip_message="$7"
  shift 7
  local -a extra_args=("$@")

  if [[ "$deploy_flag" != "true" ]]; then
    echo "==> $skip_message"
    return
  fi

  echo "==> $deploy_message"
  local -a deploy_cmd=(
    az deployment group create
    --name "$deployment_name"
    --resource-group "$resource_group"
    --parameters "$params_file"
  )
  if ((${#extra_args[@]} > 0)); then
    deploy_cmd+=("${extra_args[@]}")
  fi
  if [[ -n "${what_if:-}" ]]; then
    deploy_cmd+=("$what_if")
  fi
  run_bicep_deployment "$log_key" "${deploy_cmd[@]}"
}
