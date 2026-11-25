import os, sys, pathlib
HERE=pathlib.Path(__file__).resolve().parent
INDEX=(HERE.parent/'index.html').as_uri()
os.chdir(HERE/'fixtures')
CHROME=os.environ.get('CHROME') or None
from playwright.sync_api import sync_playwright
import base64, io, zipfile, re, json
F=INDEX
res=[]
def chk(n,c,i=""):
    res.append((n,bool(c))); print(("PASS " if c else "FAIL ")+n,i)
def xl(pg):
    b=pg.evaluate("""async()=>{const buf=new Uint8Array(await exportForm().arrayBuffer());let s='';for(const x of buf)s+=String.fromCharCode(x);return btoa(s)}""")
    open('out7.xlsx','wb').write(base64.b64decode(b)); return zipfile.ZipFile(io.BytesIO(base64.b64decode(b)))
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=CHROME,args=['--no-sandbox','--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream'])
    ctx=b.new_context(viewport={'width':420,'height':900},permissions=['camera'])
    pg=ctx.new_page(); errs=[]; dialogs=[]; ext=[]
    pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('dialog',lambda d:(dialogs.append(d.message),d.dismiss()))
    pg.on('request',lambda r: ext.append(r.url) if r.url.startswith('http') else None)
    pg.goto(F); keys=pg.evaluate("[...PART_CODES.keys()]"); A,B,C=keys[0],keys[1],keys[2]
    cases=[("028031,JH002-001671-1,30,8",30),("28031,JH002-001671-1,30,8",30),("X "+A+" 0002001",20),("X 0000101",1),("X 0000001",1),("no digits",1),("a,b,xx",1),("Y 12345678",1),("028031，"+A+"，45，8",45),("028031,"+A+",0,8 0002001",20)]
    for raw,exp in cases:
        got=pg.evaluate("(r)=>parseCapacity(r)",raw); chk(f"capacity {raw[:34]!r} -> {exp}", got==exp, got)
    c=lambda q: pg.evaluate("(q)=>commitQRRecords([q])",q)
    pg.click('[data-pick="2"]')
    c(f"028031,{A},30,8"); c(f"028031,{A},30,8"); c(f"028031 {B} 0002001")
    t=pg.evaluate("(()=>{const t=tally();return [t.hit,[...t.pieces.values()].reduce((a,b)=>a+b,0),[...t.count.values()].reduce((a,b)=>a+b,0)]})()")
    chk("boxes=3 pieces=80", t==[3,80,3], t)
    chk("tile 総出荷数=80個 箱数=3", pg.inner_text('#shipmentCount')=="80" and pg.inner_text('#boxCount')=="3", (pg.inner_text('#shipmentCount'),pg.inner_text('#boxCount')))
    chk("OK title shows pieces", "+30個" in pg.inner_text('#scanResult') or "+20個" in pg.inner_text('#scanResult'), pg.inner_text('#scanResult'))
    chk("card shows 個 and 箱", "60" in pg.inner_text('#grid') and "2箱" in pg.inner_text('#grid'), pg.inner_text('#grid').replace("\n"," ")[:80])
    # NG: 止めない
    c("ZZZ-NOPE-1"); chk("NG no hold", pg.evaluate("scanHold")==None)
    chk("NG shown (non-blocking)", pg.get_attribute('#resultBox','data-result')=="ng", pg.inner_text('#scanResult'))
    c(f"028031,{A},30,8"); chk("next scan counted right after NG", pg.evaluate("tally().hit")==4)
    chk("NG tile=1 warn", pg.inner_text('#ngCount')=="1" and "warn" in pg.get_attribute('#ngTile','class'))
    chk("input not locked", not pg.evaluate("$('scanIn').readOnly"))
    # 高速連続（ハンディ）：同じ品番20連続、ダイアログ・待ち無し
    pg.evaluate("(a)=>{const t0=performance.now();for(let i=0;i<20;i++)commitQRRecords(['028031,'+a+',30,8']);window.__ms=performance.now()-t0}",A)
    chk("20 consecutive same-part scans counted", pg.evaluate("tally().hit")==24, pg.evaluate("tally().hit"))
    chk("no dialogs / confirm", not dialogs, dialogs); chk("20 scans fast (<2s)", pg.evaluate("window.__ms")<2000, pg.evaluate("window.__ms"))
    # 入力欄経由（キー入力＋Enter）
    pg.evaluate("$('scanIn').focus()"); h=pg.evaluate("tally().hit")
    for _ in range(3):
        pg.type('#scanIn',f"028031,{A},30,8"); pg.keyboard.press('Enter')
    pg.wait_for_timeout(150); chk("typed scans x3 counted", pg.evaluate("tally().hit")==h+3, pg.evaluate("tally().hit")-h)
    # undo NG / OK
    pg.evaluate("commitQRRecords(['ZZZ-NOPE-2'])"); lab=pg.inner_text('#bUndo'); pg.click('#bUndo')
    chk("undo NG record", "NG" in lab and pg.inner_text('#ngCount')=="1", lab)
    pcs=pg.evaluate("[...tally().pieces.values()].reduce((a,b)=>a+b,0)"); pg.click('#bUndo')
    chk("undo OK reduces pieces by 30", pg.evaluate("[...tally().pieces.values()].reduce((a,b)=>a+b,0)")==pcs-30)
    # Excel / CSV 一致
    pg.evaluate("state.bin='all';render()")
    ui=int(pg.inner_text('#shipmentCount')); boxes=int(pg.inner_text('#boxCount'))
    z=xl(pg); sh2=z.read('xl/worksheets/sheet2.xml').decode(); sh1=z.read('xl/worksheets/sheet1.xml').decode(); sh3=z.read('xl/worksheets/sheet3.xml').decode()
    tot=re.findall(r'<c r="G(\d+)" s="\d+"><v>(\d+)</v>',sh2); tb=re.findall(r'<c r="F(\d+)" s="\d+"><v>(\d+)</v>',sh2)
    rows=pg.evaluate("exportRows().rows")
    chk("Excel 一覧 total pieces == screen", int(tot[-1][1])==ui, (tot[-1],ui))
    chk("Excel 一覧 total boxes == screen", int(tb[-1][1])==boxes, (tb[-1],boxes))
    chk("CSV sum == screen", sum(r[5] for r in rows[1:])==ui and sum(r[4] for r in rows[1:])==boxes, rows[0])
    chk("form header says 個", "個" in sh1 and "箱</t>" not in sh1)
    chk("history sheet has NG row fill", 'NG' in sh3)
    # 保存済み旧スコールドの読込
    pg.evaluate("""()=>{const d=JSON.parse(localStorage.getItem(LS_KEY));d.scanHold={reason:'NG　品番一覧にありません',detail:'x'};localStorage.setItem(LS_KEY,JSON.stringify(d))}""")
    pg.reload(); chk("old saved scanHold ignored on load", pg.evaluate("scanHold")==None)
    # カメラ
    pg.evaluate("window.__qr=null; window.jsQR=()=>window.__qr?{data:window.__qr}:null")
    pg.click('#binMore'); pg.click('[data-pick="4"]'); pg.click('#modeCamera'); pg.wait_for_timeout(1200)
    hits=lambda: pg.evaluate("tally(state.bin).hit"); setq=lambda v: pg.evaluate("(v)=>{window.__qr=v}",v)
    q=f"028031,{A},30,8"; h0=hits()
    setq(q); pg.wait_for_timeout(500); chk("cam: first read", hits()==h0+1)
    pg.wait_for_timeout(2500); chk("cam: held QR not re-added", hits()==h0+1, hits()-h0)
    setq(None); pg.wait_for_timeout(500); setq(q); pg.wait_for_timeout(500)
    chk("cam fast: same QR after leaving view counted (no wait)", hits()==h0+2, hits()-h0)
    for _ in range(4):
        setq(None); pg.wait_for_timeout(450); setq(q); pg.wait_for_timeout(350)
    chk("cam fast: 4 more box swaps counted", hits()==h0+6, hits()-h0)
    setq("ZZZ-NOPE-3"); pg.wait_for_timeout(500)
    chk("cam NG recorded, no stop, note not OK", pg.evaluate("scanHold")==None and "NG" in pg.inner_text('#cameraNote'), pg.inner_text('#cameraNote'))
    setq(q); pg.wait_for_timeout(500); chk("cam continues after NG", hits()==h0+7)
    pg.uncheck('#camFast'); setq(None); pg.wait_for_timeout(500); setq(q); pg.wait_for_timeout(500); n1=hits()
    setq(None); pg.wait_for_timeout(500); setq(q); pg.wait_for_timeout(800)
    chk("cam fast OFF: same QR not auto re-added", hits()==n1, (n1,hits()))
    pg.click('#repeatCamera'); pg.wait_for_timeout(600); chk("cam fast OFF: button adds 1", hits()==n1+1, hits()-n1)
    chk("no external requests (offline)", not ext, ext[:3]); chk("no page errors", not errs, errs)
    b.close()
print("FAILED:",[n for n,o in res if not o])
