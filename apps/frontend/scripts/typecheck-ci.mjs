import { spawnSync } from "node:child_process";

/**
 * CI 向け TypeScript チェックを実行します。
 *
 * - `tsc --noEmit` を実行して型エラーを取得
 * - 生成物/外部コードに相当する除外対象パスのエラーは無視
 * - それ以外の型エラーが 1 件でもあれば終了コード 1 を返す
 */
const tsc = spawnSync(
  "pnpm",
  ["exec", "tsc", "--noEmit", "--pretty", "false"],
  {
    encoding: "utf8",
    env: process.env,
  },
);

const combinedOutput = `${tsc.stdout ?? ""}${tsc.stderr ?? ""}`;
const lines = combinedOutput.split(/\r?\n/);

/**
 * CI の判定対象にする型エラー行だけを抽出します。
 * `app/components/ui/**` など、チーム方針で除外しているパスのエラーは除外します。
 */
const nonUiErrorLines = lines.filter((line) => {
  if (!line.includes("error TS")) {
    return false;
  }

  if (
    line.includes("app/components/ui/") ||
    line.includes("app/lib/utils.ts") ||
    line.includes("app/hooks/use-mobile.ts")
  ) {
    return false;
  }

  return true;
});

// 除外対象以外の TypeScript エラーが残っている場合は CI を失敗させます。
if (nonUiErrorLines.length > 0) {
  process.stderr.write(`${nonUiErrorLines.join("\n")}\n`);
  process.exit(1);
}

// tsc が失敗でも、失敗要因が除外対象のみなら CI 上は成功扱いにします。
if (tsc.status !== 0) {
  process.stdout.write(
    "typecheck:ci ignored TypeScript errors under app/components/ui/**\n",
  );
}

// ここまで到達した場合は CI チェック成功です。
process.exit(0);
