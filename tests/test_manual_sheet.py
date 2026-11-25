import os, sys, pathlib
HERE=pathlib.Path(__file__).resolve().parent
INDEX=(HERE.parent/'index.html').as_uri()
os.chdir(HERE/'fixtures')
CHROME=os.environ.get('CHROME') or None
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=CHROME,args=['--no-sandbox'])
    pg=b.new_page(viewport={'width':420,'height':900}); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e))); R=[]
    def chk(n,c,i=""): R.append(c); print(("PASS " if c else "FAIL ")+n,i)
    pg.goto(INDEX)
    chk("manual hidden until settings opened",not pg.is_visible('#manualSheet'))
    pg.click('summary:has-text("設定・データ管理")'); chk("manual visible in settings",pg.is_visible('#manualSheet'))
    t=pg.inner_text('#manualSheet'); chk("half-width banner first","必ず「半角」にする" in t.split("\n")[1] or "半角" in t[:60],t[:60])
    chk("two keyboard settings",("① キーボードを「半角英数」" in t) and ("② 予測変換・自動修正を切る" in t))
    chk("12-key note",'あa1' in t)
    box=pg.evaluate("(()=>{const r=document.querySelector('.halfBanner').getBoundingClientRect();return [r.width,getComputedStyle(document.querySelector('.halfBanner')).fontSize,getComputedStyle(document.querySelector('.halfBanner')).color]})()"); chk("banner prominent",float(box[1][:-2])>=18,box)
    chk("scan area reminder","必ず半角" in pg.inner_text('.stdWork'))
    chk("no horizontal overflow",pg.evaluate("document.documentElement.scrollWidth<=window.innerWidth+1"))
    pg.locator('#manualSheet').screenshot(path='man.png')
    chk("no errors",not errs,errs); b.close()
print(all(R))
