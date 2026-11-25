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
    pg.goto(INDEX); A=pg.evaluate("[...PART_CODES.keys()][0]"); B=pg.evaluate("[...PART_CODES.keys()][1]")
    pg.click('[data-pick="1"]')
    full=lambda t: "".join(chr(ord(c)+0xFEE0) if 0x21<=ord(c)<=0x7e else ("　" if c==" " else c) for c in t)
    # 全角入力（キー入力）
    pg.fill('#scanIn', full(f"028031,{A},30,8")); pg.wait_for_timeout(400)
    chk("fullwidth input counted as OK, 30 pcs", pg.inner_text('#shipmentCount')=="30" and pg.inner_text('#ngCount')=="0",(pg.inner_text('#shipmentCount'),pg.inner_text('#ngCount')))
    stored=pg.evaluate("files[0].text"); chk("stored text is halfwidth", stored==f"028031,{A},30,8", stored)
    # 全角で2件連続（028031区切り）
    pg.fill('#scanIn', full(f"028031,{A},30,8028031,{B},20,8")); pg.wait_for_timeout(400)
    chk("2 fullwidth chunks split & counted", pg.evaluate("tally().hit")==3, pg.evaluate("tally().hit"))
    chk("input box shows halfwidth", pg.input_value('#scanIn')=="" )
    # 全角ハイフン/カンマ/スペース、末尾7桁パターン
    pg.evaluate("(a)=>commitQRRecords([a])", full(f"{A} 0002001").replace(full("-"),"－"))
    chk("fullwidth pattern2 -> 20", pg.evaluate("tally().pieces.get('%s')"%A)==30+30+20, pg.evaluate("tally().pieces.get('%s')"%A))
    # IME確定（compositionend）
    pg.focus('#scanIn'); pg.evaluate("$('scanIn').dispatchEvent(new CompositionEvent('compositionstart'))")
    pg.evaluate("(v)=>{const i=$('scanIn');i.value=v;i.dispatchEvent(new Event('input'))}", full(f"028031,{A},30,8")); pg.wait_for_timeout(300)
    h=pg.evaluate("tally().hit"); chk("committed once during composition", h==5, h)
    pg.evaluate("$('scanIn').dispatchEvent(new CompositionEvent('compositionend'))"); pg.wait_for_timeout(300)
    chk("no double count after composition end", pg.evaluate("tally().hit")==5 and pg.input_value("#scanIn")=="", pg.evaluate("tally().hit"))
    chk("lang/inputmode attrs", pg.get_attribute('#scanIn','inputmode')=="url")
    chk("no errors", not errs, errs); b.close()
print(all(R))
