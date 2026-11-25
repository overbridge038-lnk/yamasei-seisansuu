import os, sys, pathlib
HERE=pathlib.Path(__file__).resolve().parent
INDEX=(HERE.parent/'index.html').as_uri()
os.chdir(HERE/'fixtures')
CHROME=os.environ.get('CHROME') or None
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=CHROME,args=['--no-sandbox'])
    pg=b.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e))); R=[]
    def chk(n,c,i=""): R.append(c); print(("PASS " if c else "FAIL ")+n,i)
    pg.goto(INDEX); A=pg.evaluate("[...PART_CODES.keys()][0]")
    pg.click('[data-pick="1"]')
    chk("lock default ON",pg.is_checked('#hanLock') and "ON" in pg.inner_text('#lockBadge'))
    pg.focus('#scanIn'); pg.keyboard.type(f"028031,{A},30,8",delay=5); pg.keyboard.press('Enter'); pg.wait_for_timeout(250)
    chk("typed halfwidth scan counted",pg.inner_text('#shipmentCount')=="30")
    # 全角キー入力（IMEなしでも全角文字が来る場合）→半角に直して入る
    pg.keyboard.type(f"０２８０３１,{A},３０,８",delay=5); pg.keyboard.press('Enter'); pg.wait_for_timeout(250)
    chk("fullwidth keys become halfwidth & counted",pg.inner_text('#shipmentCount')=="60",pg.inner_text('#shipmentCount'))
    # かな入力はロックで入らない＋警告
    pg.focus('#scanIn'); pg.keyboard.type("あ"); pg.wait_for_timeout(100)
    pg.wait_for_timeout(400); chk("kana rejected + warning + NG logged",pg.input_value('#scanIn')=="" and pg.is_visible('#imeWarn') and pg.inner_text('#ngCount')=="1",(pg.input_value('#scanIn'),pg.inner_text('#ngCount')))
    # 変換済み（住所）混入は警告とNG
    pg.evaluate("commitQRRecords(['028031 JH北海道札幌市北区北十九条西30-2+ 0002001'])")
    chk("converted QR -> NG + red warning",pg.inner_text('#ngCount')=="2" and pg.is_visible('#imeWarn'),pg.inner_text('#ngCount'))
    pg.evaluate("commitQRRecords(['028031,%s,30,8'])"%A); chk("warning cleared by next good scan",not pg.is_visible('#imeWarn'))
    # OFF
    pg.evaluate("document.querySelectorAll('details').forEach(d=>d.open=true)"); pg.uncheck('#hanLock'); chk("badge OFF",'OFF' in pg.inner_text('#lockBadge'))
    pg.reload(); chk("setting persists",not pg.is_checked('#hanLock'))
    chk("no errors",not errs,errs); b.close()
print(all(R))
