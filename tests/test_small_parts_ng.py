import os, sys, pathlib
HERE=pathlib.Path(__file__).resolve().parent
INDEX=(HERE.parent/'index.html').as_uri()
os.chdir(HERE/'fixtures')
CHROME=os.environ.get('CHROME') or None
from playwright.sync_api import sync_playwright
import base64, io, zipfile, re
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=CHROME,args=['--no-sandbox'])
    pg=b.new_page(viewport={'width':420,'height':900}); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto(INDEX)
    A=pg.evaluate("[...PART_CODES.keys()][0]"); R=[]
    def chk(n,c,i=""): R.append(c); print(("PASS " if c else "FAIL ")+n,i)
    pg.click('[data-pick="1"]')
    pg.evaluate("(a)=>commitQRRecords(['028031,'+a+',30,8'])",A)
    pg.evaluate("commitQRRecords(['028031,ZZ-99999-1,12,8'])")
    chk("NG recorded",pg.inner_text('#ngCount')=="1")
    chk("button hot",'hot' in pg.get_attribute('#bManual','class'))
    pg.click('#bManual'); chk("panel open, part prefilled",pg.is_visible('#manualPanel') and "ZZ-99999-1" in pg.inner_text('#sqPicked'),pg.inner_text('#sqPicked'))
    pg.click('#mAdd'); chk("qty required",pg.inner_text('#mErr')!="")
    pg.fill('#mQty','12'); pg.click('#mAdd')
    chk("NG converted: ng=0, total=42",pg.inner_text('#ngCount')=="0" and pg.inner_text('#shipmentCount')=="42",(pg.inner_text('#ngCount'),pg.inner_text('#shipmentCount')))
    chk("panel closed",not pg.is_visible('#manualPanel'))
    # new manual add (no NG)
    pg.evaluate("localStorage.setItem('hinban_small_list_v1',JSON.stringify(['ABC-123-1']))"); pg.click('#bManual'); pg.click('#mSaved .use[data-p="ABC-123-1"]'); pg.fill('#mQty','5'); pg.click('#mAdd')
    chk("manual new: total 47",pg.inner_text('#shipmentCount')=="47",pg.inner_text('#shipmentCount'))
    pg.click('#bManual'); pg.fill('#mQty','5'); pg.click('#mAdd'); chk("no part picked -> rejected",pg.inner_text('#mErr')!="" and pg.inner_text('#shipmentCount')=="47")
    pg.click('#mCancel')
    pg.click('#bUndo'); chk("undo manual -> 42",pg.inner_text('#shipmentCount')=="42")
    # reload persistence
    pg.reload(); pg.click('[data-pick="1"]')
    chk("persist after reload",pg.inner_text('#shipmentCount')=="42" and "ZZ-99999-1" in pg.inner_text('#grid'))
    rows=pg.evaluate("exportRows().rows"); chk("CSV has manual part",any(r[2]=="ZZ-99999-1" and r[5]==12 for r in rows),rows)
    bs=pg.evaluate("""async()=>{const buf=new Uint8Array(await exportForm().arrayBuffer());let s='';for(const x of buf)s+=String.fromCharCode(x);return btoa(s)}""")
    z=zipfile.ZipFile(io.BytesIO(base64.b64decode(bs))); allx=''.join(z.read(n).decode('utf8','ignore') for n in z.namelist() if 'sheet' in n or 'sharedStrings' in n)
    chk("Excel has part & 手入力",'ZZ-99999-1' in allx and '少量品' in allx)
    pg.evaluate("commitQRRecords(['ZZZ'])"); chk("scan continues normally",pg.inner_text('#ngCount')=="1")
    chk("no errors",not errs,errs)
    pg.screenshot(path='s.png'); b.close()
print(all(R))
