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
    pg.goto(INDEX)
    pg.evaluate("PART_CODES.set('JH001-001930-2','193429')"); pg.click('[data-pick="1"]')
    S="028031②801020100④40⑦9③④Ｊｈ００１－００１９３０－2＋０００２００１"
    H="028031②801020100④40⑦9③④Jh001-001930-2+0002001"
    for n,raw in [("fullwidth sample",S),("halfwidth sample",H)]:
        pg.evaluate("(r)=>commitQRRecords([r])",raw)
    t=pg.evaluate("(()=>{const t=tally();return [t.hit,t.pieces.get('JH001-001930-2'),t.total]})()")
    chk("both samples OK, 20 pcs each",t==[2,40,2],t)
    # 入力欄に全角で打ち込んでも同じ
    pg.fill('#scanIn',S); pg.wait_for_timeout(400); chk("typed fullwidth sample OK",pg.evaluate("tally().hit")==3,pg.evaluate("tally().hit"))
    # IMEが住所に変換した形
    pg.evaluate("(r)=>commitQRRecords([r])","028031②801020100④40⑦9③④JH北海道札幌市北区北十九条西30-2＋０００２００１")
    chk("address-converted string flagged, not counted",pg.evaluate("tally().hit")==3 and '日本語入力' in pg.inner_text('#scanResult'),pg.inner_text('#scanResult'))
    chk("no errors",not errs,errs); b.close()
print(all(R))
