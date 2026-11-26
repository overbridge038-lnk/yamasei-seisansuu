import os, sys, pathlib
HERE=pathlib.Path(__file__).resolve().parent
INDEX=(HERE.parent/'index.html').as_uri()
os.chdir(HERE/'fixtures')
CHROME=os.environ.get('CHROME') or None
from playwright.sync_api import sync_playwright
import json, base64
pairs=json.load(open('pairs.json'))
exp={}
for k,c in pairs:
    if k not in exp or (not exp[k] and c): exp[k]=c
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=CHROME,args=['--no-sandbox'])
    pg=b.new_page(); errs=[]; dialogs=[]
    pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('dialog',lambda d:(dialogs.append(d.message),d.accept()))
    R=[]
    def chk(n,c,i=""): R.append(c); print(("PASS " if c else "FAIL ")+n,i)
    pg.goto(INDEX)
    init=pg.evaluate("Object.fromEntries(PART_CODES)")
    chk("初期一覧に新品番5件",all(k in init for k in ['JH001-001760-11','H2101-60051-2','244410-26A60-1','244410-26A30-1','244410-26A90-2']),len(init))
    chk("初期一覧は2026.11.25版の品番をすべて含む（コードも同じ）",all(init.get(k)==v for k,v in exp.items()),(len(init),[k for k in exp if init.get(k)!=exp[k]][:5]))
    # 1) ファイル選択で .xls
    pg.evaluate("localStorage.removeItem('hinban_parts_v1');PART_CODES.clear()")
    pg.set_input_files('#partFile','list.xls'); pg.wait_for_timeout(800)
    got=pg.evaluate("Object.fromEntries(PART_CODES)")
    chk(".xls 読込：460品番・コード一致",got==exp,(len(got),[k for k in exp if got.get(k)!=exp[k]][:5]))
    chk("右側の列の品番も入る（10-17060-1 → 191978）",got.get('10-17060-1')=='191978')
    chk("全角の品番を半角に（１０－２１０６０－１０）",got.get('10-21060-10')=='192152')
    chk("見出し・月日・GHP板は入らない",not any(k in got for k in ['月日','GHP板','品番']))
    chk("info shows file",'list.xls' in pg.text_content('#partListInfo'),pg.text_content('#partListInfo'))
    # 2) 設定を閉じたまま、画面のどこかにドロップ
    pg.reload(); pg.evaluate("PART_CODES.clear();render()")
    b64=base64.b64encode(open('list.xls','rb').read()).decode()
    pg.evaluate("""(b64)=>{const bin=atob(b64),u=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);
      const f=new File([u],'山清工業3ライン品番一覧2026.22.25.xls',{type:'application/vnd.ms-excel'});const dt=new DataTransfer();dt.items.add(f);
      document.querySelector('#grid').dispatchEvent(new DragEvent('dragover',{bubbles:true,cancelable:true,dataTransfer:dt}));
      document.querySelector('#grid').dispatchEvent(new DragEvent('drop',{bubbles:true,cancelable:true,dataTransfer:dt}));}""",b64)
    pg.wait_for_timeout(800)
    chk("画面のどこにドロップしても読込（設定は閉じたまま）",pg.evaluate("PART_CODES.size")==460,pg.evaluate("PART_CODES.size"))
    # 3) 枠にドロップ（二重に読まない）
    n0=len(dialogs)
    pg.evaluate("document.querySelectorAll('details').forEach(d=>d.open=true)")
    pg.evaluate("""(b64)=>{const bin=atob(b64),u=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);
      const dt=new DataTransfer();dt.items.add(new File([u],'a.xls'));
      document.querySelector('#partDrop').dispatchEvent(new DragEvent('drop',{bubbles:true,cancelable:true,dataTransfer:dt}));}""",b64)
    pg.wait_for_timeout(800); chk("枠へのドロップも読込",pg.evaluate("PART_CODES.size")==460)
    # 4) .xlsx（同じ様式・2組の列）
    pg.evaluate("PART_CODES.clear()"); pg.set_input_files('#partFile','list_conv.xlsx'); pg.wait_for_timeout(800)
    chk(".xlsx（左右2組の様式）も460品番",pg.evaluate("Object.fromEntries(PART_CODES)")==exp,pg.evaluate("PART_CODES.size"))
    # 5) 新品番で照合
    pg.click('[data-pick="1"]')
    for raw,k,q in [("029011 28010 201000808139     2JH001-001760-1+1        0002001","JH001-001760-11",20),("014010 28010 201002108190     20-H2101-60051-+2        0005001","H2101-60051-2",50)]:
        r=pg.evaluate("(r)=>{const x=extractQR(r);return [x.ok,x.extracted,x.qty]}",raw); chk(f"新品番でOK {k}",r==[True,k,q],r)
    # 6) 再読込後も残る
    pg.reload(); chk("再読込後も一覧が残る",pg.evaluate("PART_CODES.size")==460)
    # 7) xlsでもxlsxでもないファイル
    open('bad.xls','wb').write(b'hello'); pg.evaluate("document.querySelectorAll('details').forEach(d=>d.open=true)")
    pg.set_input_files('#partFile','bad.xls'); pg.wait_for_timeout(400)
    chk("壊れたファイルは一覧を変えない",pg.evaluate("PART_CODES.size")==460)
    chk("確認ダイアログなし（件数が減らない）",len(dialogs)==0,dialogs)
    chk("no page errors",not errs,errs); b.close()
print("ALL:",all(R),f"{sum(R)}/{len(R)}")
