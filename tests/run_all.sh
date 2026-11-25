#!/usr/bin/env bash
# すべての自動テストを実行します。
# 使い方：  bash tests/run_all.sh
# Chromeの場所を指定するとき： CHROME="/path/to/chrome" bash tests/run_all.sh
# 事前に：  pip install playwright openpyxl  →  playwright install chromium（CHROMEを指定しない場合）
cd "$(dirname "$0")"
fail=0
for f in test_*.py; do
  out=$(python3 "$f" 2>&1)
  p=$(echo "$out" | grep -c '^PASS')
  n=$(echo "$out" | grep -c 'FAIL \|Error:')
  printf "%-28s %3s PASS / %s FAIL\n" "$f" "$p" "$n"
  if [ "$n" != "0" ]; then echo "$out" | grep 'FAIL \|Error:' | head -5; fail=1; fi
done
exit $fail
