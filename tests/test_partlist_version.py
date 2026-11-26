import os, sys, pathlib
HERE=pathlib.Path(__file__).resolve().parent
INDEX=(HERE.parent/'index.html').as_uri()
os.chdir(HERE/'fixtures')
CHROME=os.environ.get('CHROME') or None
# 2026-11-26b：品番一覧（472品番）をツールに入れた。ドロップした一覧より新しければ、自動でツールの一覧に切り替わる。
from playwright.sync_api import sync_playwright
import openpyxl, unicodedata, re
def nk(v):
    s=unicodedata.normalize('NFKC',str(v or '')); return re.sub('[‐‑‒–—―−ー－]','-',s).upper().replace(' ','').replace('　','')
exp={}
for r in list(openpyxl.load_workbook('parts_2026-11-26b.xlsx',data_only=True).active.iter_rows(values_only=True))[1:]:
    if not r or not r[2]: continue
    k=nk(r[2]); c='' if r[1] is None else str(int(r[1])) if isinstance(r[1],(int,float)) else str(r[1]).strip()
    if k not in exp or (not exp[k] and c): exp[k]=c
R=[]
def chk(n,c,i=""): R.append(c); print(("PASS " if c else "FAIL ")+n,i)
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=CHROME,args=['--no-sandbox'])
    pg=b.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('dialog',lambda d:d.accept())
    pg.goto(INDEX); pg.evaluate("localStorage.clear()"); pg.reload()
    init=pg.evaluate("Object.fromEntries(PART_CODES)")
    chk("ツールの一覧＝2026-11-26b版の品番一覧（472品番・コード一致）",init==exp,(len(init),len(exp),[k for k in exp if init.get(k)!=exp[k]][:5]))
    chk("重複行のコードは空欄で上書きしない",init.get('JH003-002350-10')=='193369' and init.get('JH003-002650-10')=='193382')
    for k in ['44410-26A30-2','JH001-001890-2','JH003-002890-11','JH345-00010-10']: chk(f"新品番 {k}",k in init)
    # 古い版でドロップした一覧（base なし）→ 自動でツールの一覧へ
    pg.evaluate("localStorage.setItem('hinban_parts_v1',JSON.stringify({name:'old.xls',at:'2026/11/25 10:00',list:[['AA-1-1','1']]}))"); pg.reload(); pg.wait_for_timeout(1200)
    chk("古いドロップ一覧はツールの一覧に自動で切り替わる",pg.evaluate("PART_CODES.size")==len(exp) and pg.evaluate("localStorage.getItem('hinban_parts_v1')")==None)
    chk("切り替えたことを知らせる","切り替えました" in pg.inner_text('body'))
    # この版でドロップした一覧は、そのまま使う
    pg.evaluate("document.querySelectorAll('details').forEach(d=>d.open=true)")
    pg.set_input_files('#partFile','parts1.xlsx'); pg.wait_for_timeout(600)
    pg.reload(); chk("同じ版でドロップした一覧は残る",pg.evaluate("PART_CODES.size")==3)
    # 読取：新品番がOK
    pg.evaluate("localStorage.removeItem('hinban_parts_v1')"); pg.reload(); pg.click('[data-pick="1"]')
    r=pg.evaluate("(()=>{const x=extractQR('028031,JH001-001890-2,20,8');return [x.ok,x.extracted,x.qty]})()"); chk("新品番の読取がOK",r==[True,'JH001-001890-2',20],r)
    r=pg.evaluate("(()=>{const x=extractQR('028031,244410-26A30-2,10,8');return [x.ok,x.extracted]})()"); chk("244410-26A30-2 は 44410-26A30-2 で照合",r==[True,'44410-26A30-2'],r)
    chk("ver 2026-11-26b",pg.evaluate("VER")=="2026-11-26b")
    chk("no page errors",not errs,errs); b.close()
print("ALL:",all(R),f"{sum(R)}/{len(R)}")
