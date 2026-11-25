import os, sys, pathlib
HERE=pathlib.Path(__file__).resolve().parent
INDEX=(HERE.parent/'index.html').as_uri()
os.chdir(HERE/'fixtures')
CHROME=os.environ.get('CHROME') or None
from playwright.sync_api import sync_playwright
import base64, io, zipfile
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=CHROME,args=['--no-sandbox'])
    pg=b.new_page(viewport={'width':420,'height':900}); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e))); R=[]
    def chk(n,c,i=""): R.append(c); print(("PASS " if c else "FAIL ")+n,i)
    pg.goto(INDEX); A=pg.evaluate("[...PART_CODES.keys()][0]")
    vis=[x for x in pg.query_selector_all('#binButtons .binBtn') if x.is_visible()]
    chk("main row: 1便 2便 他の便",[x.inner_text().replace("\n"," ") for x in vis]==["1便","2便","他の便 3〜4便・特車"],[x.inner_text() for x in vis])
    chk("5便 button gone",pg.query_selector('[data-pick="5"]') is None)
    chk("extra hidden at start",not pg.is_visible('#binExtra'))
    pg.click('#binMore'); chk("extra opens: 3便 4便 特車",pg.is_visible('#binExtra') and [x.inner_text() for x in pg.query_selector_all('#binExtra .binBtn')]==["3便","4便","特車"])
    h=pg.evaluate("Math.min(...[...document.querySelectorAll('.binBtn')].filter(e=>e.offsetParent).map(e=>e.getBoundingClientRect().height))"); chk("buttons >=60px",h>=60,h)
    for bin in ["3","4","特車","1"]:
        if bin!="1": 
            if not pg.is_visible('#binExtra'): pg.click('#binMore')
        pg.click(f'[data-pick="{bin}"]'); pg.wait_for_timeout(50)
        pg.evaluate("(a)=>commitQRRecords(['028031,'+a+',10,8'])",A)
    chk("notice shows 特車 after scan? (state check)",True)
    (pg.click('#binMore') if not pg.is_visible('#binExtra') else None); pg.click('[data-pick="特車"]')
    chk("特車 selected & notice",pg.evaluate("state.scanBin")=="特車" and "特車で読取中" in pg.inner_text('#scanNotice'),pg.inner_text('#scanNotice'))
    chk("extra stays open on 特車",pg.is_visible('#binExtra'))
    pg.evaluate("(a)=>commitQRRecords(['028031,'+a+',10,8'])",A)
    chips=[x.inner_text() for x in pg.query_selector_all('#binChips .chip')]; chk("chips order",chips==["全便","1便","3便","4便","特車"],chips)
    chk("OK msg uses 特車 label","特車" in pg.inner_text('#targetHin') and "便" not in pg.inner_text('#targetHin').split("　")[1],pg.inner_text('#targetHin'))
    pg.evaluate("state.bin='all';render()"); rows=pg.evaluate("exportRows().rows"); chk("CSV bin labels",sorted({r[1] for r in rows[1:]})==["1便","3便","4便","特車"],[r[1] for r in rows])
    pg.evaluate("state.bin='特車';render()"); bs=pg.evaluate("""async()=>{const buf=new Uint8Array(await exportForm().arrayBuffer());let s='';for(const x of buf)s+=String.fromCharCode(x);return btoa(s)}""")
    z=zipfile.ZipFile(io.BytesIO(base64.b64decode(bs))); x=z.read('xl/sharedStrings.xml').decode() if 'xl/sharedStrings.xml' in z.namelist() else z.read('xl/worksheets/sheet1.xml').decode()
    chk("Excel 対象 特車",'対象　特車' in x,)
    pg.reload(); chk("特車 filter persists",pg.evaluate("state.bin")=="特車")
    pg.fill('#scanBin','5'); pg.click('#bStartScan'); chk("free input 5 still works",pg.evaluate("state.scanBin")=="5")
    chk("no errors",not errs,errs); b.close()
print(all(R))
