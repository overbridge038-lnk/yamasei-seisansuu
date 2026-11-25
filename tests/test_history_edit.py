import os, sys, pathlib
HERE=pathlib.Path(__file__).resolve().parent
INDEX=(HERE.parent/'index.html').as_uri()
os.chdir(HERE/'fixtures')
CHROME=os.environ.get('CHROME') or None
from playwright.sync_api import sync_playwright
import base64, io, zipfile, openpyxl
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=CHROME,args=['--no-sandbox'])
    pg=b.new_page(viewport={'width':600,'height':1000}); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e))); R=[]
    def chk(n,c,i=""): R.append(c); print(("PASS " if c else "FAIL ")+n,i)
    pg.goto(INDEX)
    tot=lambda: (pg.inner_text('#shipmentCount'),pg.inner_text('#boxCount'),pg.inner_text('#ngCount'))
    pg.click('[data-pick="1"]')
    for q in ["028031,JH001-001830-1,25,8","028031,JH001-001830-11,25,8","028031,JH001-001830-1,25,8","ZZ-NG-1"]:
        pg.evaluate("(q)=>commitQRRecords([q])",q)
    chk("start: 75個 3箱 NG1",tot()==("75","3","1"),tot())
    btns=pg.query_selector_all('#scanHistory .histEdit'); chk("品番がボタン",len(btns)==4)
    h=pg.evaluate("Math.min(...[...document.querySelectorAll('.histEdit')].map(e=>e.getBoundingClientRect().height))"); chk("押しやすい高さ(>=44)",h>=44,h)
    # 1件目：品番の取り違えを直す（-1 → -10、数量24）
    btns[0].click(); chk("修正画面が開く",pg.is_visible('#editOverlay'))
    chk("現在の値が入っている",pg.input_value('#ePart')=="JH001-001830-1" and pg.input_value('#eQty')=="25")
    pg.fill('#ePart','jh001-001830-10'); pg.fill('#eQty','24'); pg.click('#eSave')
    chk("修正後：74個 3箱",tot()==("74","3","1"),tot())
    t=pg.evaluate("tally().history[0]"); chk("1件目＝JH001-001830-10・24個",t['part']=="JH001-001830-10" and t['cap']==24 and t['ok'],t)
    chk("一覧に「修正済み（元…）」",'修正済み（元：JH001-001830-1・25個）' in pg.inner_text('#scanHistory'))
    # NGを直す（一覧にない品番→警告→もう一度でOK）
    pg.query_selector_all('#scanHistory .histEdit')[3].click()
    chk("NGは品番欄が空・数量空",pg.input_value('#eQty')=="")
    pg.fill('#ePart','JH001-001830-11'); pg.click('#eSave'); chk("数量なしは止める",pg.inner_text('#eErr')!="" and pg.is_visible('#editOverlay'))
    pg.fill('#eQty','25'); pg.click('#eSave'); chk("NG→OK：99個 4箱 NG0",tot()==("99","4","0"),tot())
    # 一覧にない品番
    pg.query_selector_all('#scanHistory .histEdit')[1].click(); pg.fill('#ePart','XX-1-1'); pg.fill('#eQty','5'); pg.click('#eSave')
    chk("一覧外は1回目は警告で止まる",'品番一覧にありません' in pg.inner_text('#eErr') and pg.is_visible('#editOverlay'))
    pg.click('#eSave'); chk("2回目で記録",pg.evaluate("tally().history[1].part")=="XX-1-1")
    # 元に戻す
    pg.query_selector_all('#scanHistory .histEdit')[1].click(); chk("元に戻すボタン表示",pg.is_visible('#eRestore'))
    pg.click('#eRestore'); chk("元の読取に戻る",pg.evaluate("tally().history[1].part")=="JH001-001830-11" and pg.evaluate("tally().history[1].edited")==None)
    # 再修正しても『元』は最初の読取のまま
    pg.query_selector_all('#scanHistory .histEdit')[0].click(); pg.fill('#eQty','20'); pg.click('#eSave')
    chk("再修正でも元は最初の値",pg.evaluate("tally().history[0].edited.part")=="JH001-001830-1" and pg.evaluate("tally().history[0].cap")==20)
    # やめる・Esc
    pg.query_selector_all('#scanHistory .histEdit')[2].click(); pg.click('#eCancel'); chk("やめるで閉じる",not pg.is_visible('#editOverlay'))
    # 保存・再読込
    pg.reload(); chk("再読込後も修正が残る",pg.evaluate("tally().history[0].part")=="JH001-001830-10" and pg.evaluate("tally().history[0].cap")==20)
    # Excel / CSV
    bs=pg.evaluate("""async()=>{state.bin='all';const buf=new Uint8Array(await exportForm().arrayBuffer());let s='';for(const x of buf)s+=String.fromCharCode(x);return btoa(s)}""")
    wb=openpyxl.load_workbook(io.BytesIO(base64.b64decode(bs)))
    hist=[r for r in wb['読取履歴'].iter_rows(values_only=True)]
    chk("Excel履歴に修正の記録・QR原文は元のまま",hist[1][4]=="JH001-001830-10" and hist[1][6]==20 and "修正（元：JH001-001830-1・25個）" in hist[1][8] and "JH001-001830-1,25" in hist[1][9],hist[1])
    main=[r for r in wb['山清報告書'].iter_rows(values_only=True)]
    chk("帳票に修正後の品番",any(r[1]=="JH001-001830-10" and r[3]==20 for r in main))
    rows=pg.evaluate("exportRows().rows"); chk("CSV合計＝画面",sum(r[5] for r in rows[1:])==int(pg.inner_text('#shipmentCount')))
    # 取消ボタンとの両立：最後の記録を修正してから取消
    pg.click('[data-pick="1"]'); pg.evaluate("commitQRRecords(['028031,JH001-001830-1,25,8'])")
    n=pg.evaluate("tally().hit"); pg.query_selector_all('#scanHistory .histEdit')[-1].click(); pg.fill('#eQty','10'); pg.click('#eSave')
    pg.click('#bUndo'); chk("修正した最後の読取も取消できる",pg.evaluate("tally().hit")==n-1)
    chk("no page errors",not errs,errs); b.close()
print("ALL:",all(R),f"{sum(R)}/{len(R)}")
