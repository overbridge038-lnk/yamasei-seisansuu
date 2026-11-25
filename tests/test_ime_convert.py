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
    chk("scan input is url type, no autocorrect",pg.get_attribute('#scanIn','type')=="url" and pg.get_attribute('#scanIn','autocorrect')=="off")
    pg.type('#scanIn',f"028031,{A},30,8"); pg.keyboard.press('Enter'); pg.wait_for_timeout(200)
    chk("normal typed scan OK",pg.inner_text('#shipmentCount')=="30")
    pg.evaluate("commitQRRecords(['028031280102010044079​34JH北海道札幌市北区北十九条西30-2〜0002001'])")
    chk("IME-converted QR rejected with clear reason",'日本語入力' in pg.inner_text('#scanResult') and pg.inner_text('#shipmentCount')=="30",pg.inner_text('#scanResult'))
    chk("not misread as part 30-2","30-2" not in pg.inner_text('#grid'))
    pg.evaluate("commitQRRecords(['028031,'+%r+'〜0002001'])"%A)
    chk("wave dash 〜 normalized, counted",pg.evaluate("tally().hit")==2,pg.evaluate("tally().hit"))
    chk("no errors",not errs,errs); b.close()
print(all(R))
