import os, sys, pathlib
HERE=pathlib.Path(__file__).resolve().parent
INDEX=(HERE.parent/'index.html').as_uri()
os.chdir(HERE/'fixtures')
CHROME=os.environ.get('CHROME') or None
from playwright.sync_api import sync_playwright
import io, openpyxl, base64
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=CHROME,args=['--no-sandbox'])
    R=[]
    def chk(n,c,i=""): R.append(c); print(("PASS " if c else "FAIL ")+n,i)
    for vw in (1200,420):
        pg=b.new_page(viewport={'width':vw,'height':1000}); pg.on('dialog',lambda d:d.accept())
        pg.goto(INDEX)
        pg.click('[data-pick="1"]'); pg.evaluate("commitQRRecords(['028031,JH001-001830-1,25,8'])")
        bm=pg.evaluate("document.querySelector('#bManual').getBoundingClientRect().toJSON()"); bb=pg.evaluate("document.querySelector('#mascotSay').getBoundingClientRect().toJSON()")
        chk(f"[{vw}] 少量品ボタンがセリフの上",bm['bottom']<=bb['top']+1)
        chk(f"[{vw}] 名前が「少量品」",pg.inner_text('#bManual').startswith("📦 少量品"),pg.inner_text('#bManual'))
        chk(f"[{vw}] 横はみ出しなし",pg.evaluate("document.documentElement.scrollWidth<=innerWidth+1"))
        pg.close()
    ctx=b.new_context(accept_downloads=True,viewport={'width':800,'height':1000}); pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e))); dl=[]; pg.on('dialog',lambda d:(dl.append(d.message),d.accept()))
    pg.goto(INDEX)
    # 前の版の「よく使う品番」を引き継ぐ
    pg.evaluate("localStorage.removeItem('hinban_small_list_v1');localStorage.setItem('hinban_manual_saved_v1',JSON.stringify([{part:'OLD-1-1',qty:3}]))"); pg.reload()
    pg.click('[data-pick="1"]'); pg.click('#bManual')
    chk("前の版の保存品番を引き継ぐ",[x.inner_text() for x in pg.query_selector_all('#mSaved .use')]==["OLD-1-1"])
    pg.click('#mSaved .del[data-p="OLD-1-1"]'); chk("×で外す（確認あり）",not pg.query_selector_all('#mSaved .use') and pg.is_visible('#sqEmpty'))
    # ハンド入力で登録
    pg.click('#sqManage summary')
    for x in ["jh003-002350-10","１０－２－１","XX-99-1"]:
        pg.fill('#sqNew',x); pg.click('#sqAddBtn')
    items=[x.inner_text() for x in pg.query_selector_all('#mSaved .use')]
    chk("ハンド入力で登録（半角・大文字にそろえる）",items==["10-2-1","JH003-002350-10","XX-99-1"],items)
    pg.fill('#sqNew','XX-99-1'); pg.click('#sqAddBtn'); chk("二重登録は止める",'もう登録' in pg.inner_text('#sqErr'))
    pg.fill('#sqNew','日本'); pg.click('#sqAddBtn'); chk("品番でない文字は止める",'半角' in pg.inner_text('#sqErr'))
    chk("設定の品番一覧は変わらない",not pg.evaluate("PART_CODES.has('XX-99-1')"))
    # 選んで追加
    pg.click('#mAdd'); chk("品番を選ばないと追加しない",'選んで' in pg.inner_text('#mErr'))
    pg.click('#mSaved .use[data-p="JH003-002350-10"]'); chk("選ぶと表示・数量欄へ","JH003-002350-10" in pg.inner_text('#sqPicked') and pg.evaluate("document.activeElement.id")=="mQty")
    pg.click('#mAdd'); chk("数量なしは止める",'数量' in pg.inner_text('#mErr'))
    pg.fill('#mQty','25'); pg.click('#mAdd')
    chk("少量品として記録：25個",pg.inner_text('#shipmentCount')=="25" and not pg.is_visible('#manualPanel'),pg.inner_text('#shipmentCount'))
    chk("一覧に「少量品」",'少量品' in pg.inner_text('#scanHistory'))
    pg.click('#bManual'); pg.click('#mSaved .use[data-p="XX-99-1"]'); pg.fill('#mQty','8'); pg.click('#mAdd')
    chk("一覧外の品番も少量品ならOK",pg.inner_text('#shipmentCount')=="33" and pg.inner_text('#ngCount')=="0")
    # 書き出し
    pg.click('#bManual'); pg.evaluate("document.querySelector('#sqManage').open=true")
    with pg.expect_download() as d: pg.click('#sqExport')
    d.value.save_as('sq.xlsx'); ws=openpyxl.load_workbook('sq.xlsx').active
    rows=[r for r in ws.iter_rows(values_only=True)]
    chk("書き出し：見出し品番＋3品番",rows==[("品番",),("10-2-1",),("JH003-002350-10",),("XX-99-1",)] and ws.title=="少量品一覧",rows)
    chk("ファイル名",d.value.suggested_filename.startswith("少量品一覧_"),d.value.suggested_filename)
    # 直して読み込む（置き換え）
    wb=openpyxl.Workbook(); w=wb.active; w.append(["品番"]); [w.append([x]) for x in ["AA-1-1","ｂｂ－２－２","10-2-1","メモ"]]; wb.save('sq2.xlsx')
    pg.set_input_files('#sqFile','sq2.xlsx'); pg.wait_for_timeout(500)
    items=[x.inner_text() for x in pg.query_selector_all('#mSaved .use')]
    chk("Excel読込で置き換え（確認あり）",items==["AA-1-1","BB-2-2","10-2-1"] and any("置き換えます" in m for m in dl),items)
    pg.set_input_files('#sqFile','list.xls'); pg.wait_for_timeout(800)
    chk(".xls も読める（品番列）",len(pg.query_selector_all('#mSaved .use'))>=400,len(pg.query_selector_all('#mSaved .use')))
    chk("多いときはしぼり込み欄",pg.is_visible('#sqFilter'))
    pg.fill('#sqFilter','001760'); chk("しぼり込み",[x.inner_text() for x in pg.query_selector_all('#mSaved .use')]==["JH001-001760-11"])
    pg.click('#mCancel')
    # 日付クリア・再読込後も残る
    pg.evaluate("dataDate='2026-11-24';save()"); pg.reload()
    chk("日付クリア後も少量品一覧は残る",pg.evaluate("loadSmall().length")>=400 and pg.evaluate("files.length")==0)
    # Excel帳票
    pg.click('[data-pick="2"]'); pg.click('#bManual'); pg.fill('#sqFilter','10-17060-1'); pg.click('#mSaved .use[data-p="10-17060-1"]'); pg.fill('#mQty','6'); pg.click('#mAdd')
    bs=pg.evaluate("""async()=>{state.bin='all';const buf=new Uint8Array(await exportForm().arrayBuffer());let s='';for(const x of buf)s+=String.fromCharCode(x);return btoa(s)}""")
    wb=openpyxl.load_workbook(io.BytesIO(base64.b64decode(bs)))
    chk("帳票に少量品の品番",any(r[1]=="10-17060-1" and r[3]==6 for r in wb['山清報告書'].iter_rows(values_only=True)))
    chk("読取履歴の理由「少量品」",any(r[4]=="10-17060-1" and r[8]=="少量品（手入力）" for r in wb['読取履歴'].iter_rows(values_only=True)))
    # 修正・削除
    pg.query_selector_all('#scanHistory .histEdit')[0].click(); pg.click('#eDelete'); chk("削除",pg.evaluate("files.length")==0)
    chk("no page errors",not errs,errs); b.close()
print("ALL:",all(R),f"{sum(R)}/{len(R)}")
