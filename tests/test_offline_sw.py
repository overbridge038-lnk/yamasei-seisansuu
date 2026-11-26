# 2026-11-26a：オフラインで使う（Service Worker）。一度オンラインで開けば、オフラインでも開ける／オンラインで開くと更新が入る
import os, pathlib, shutil, tempfile, threading, http.server, socketserver, functools
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parent
CHROME=os.environ.get('CHROME') or None
from playwright.sync_api import sync_playwright
tmp=pathlib.Path(tempfile.mkdtemp())
for f in ["index.html","sw.js","manifest.json","icon-192.png","icon-512.png"]: shutil.copy(ROOT/f, tmp/f)
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
srv=socketserver.TCPServer(("127.0.0.1",0),functools.partial(Q,directory=str(tmp))); port=srv.server_address[1]
threading.Thread(target=srv.serve_forever,daemon=True).start()
URL=f"http://127.0.0.1:{port}/"
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=CHROME,args=['--no-sandbox'])
    ctx=b.new_context(); pg=ctx.new_page()
    errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    R=[]
    def chk(n,c,i=""): R.append(c); print(("PASS " if c else "FAIL ")+n,i)
    pg.goto(URL)
    ver=pg.evaluate("VER")
    chk("manifestとアイコンを読める",pg.evaluate("fetch('manifest.json').then(r=>r.json()).then(j=>j.short_name)")=="山清生産数")
    pg.wait_for_function("navigator.serviceWorker && navigator.serviceWorker.controller",timeout=10000)
    chk("Service Workerが動く",True)
    pg.wait_for_timeout(300)
    chk("オフライン対応の表示","オフライン対応" in pg.inner_text('#offBadge'),pg.inner_text('#offBadge'))
    pg.click('[data-pick="1"]'); pg.evaluate("commitQRRecords(['028031,JH001-001810-1,20,45'])")
    print("== オフラインで開き直す")
    ctx.set_offline(True)
    pg.reload(); pg.wait_for_timeout(500)
    chk("オフラインでもツールが開く",pg.evaluate("typeof VER")=="string" and pg.evaluate("VER")==ver)
    chk("読取データが残る",pg.evaluate("tally().hit")==1)
    chk("オフライン中の表示","オフラインで使用中" in pg.inner_text('#offBadge'),pg.inner_text('#offBadge'))
    pg2=ctx.new_page(); pg2.goto(URL); chk("新しいタブでもオフラインで開ける",pg2.evaluate("VER")==ver); pg2.close()
    if not pg.evaluate("state.scanBin"): pg.click('[data-pick="1"]')
    pg.evaluate("commitQRRecords(['028031,JH001-001810-1,20,46'])"); chk("オフラインで読取できる",pg.evaluate("tally().hit")==2)
    print("== オンラインで開くと更新が入る")
    s=(tmp/"index.html").read_text(encoding='utf-8').replace(f'const VER = "{ver}"','const VER = "9999-99-99z"'); (tmp/"index.html").write_text(s,encoding='utf-8')
    ctx.set_offline(False); pg.reload(); pg.wait_for_timeout(1100)
    chk("オンラインで開くと新しい版",pg.evaluate("VER")=="9999-99-99z",pg.evaluate("VER"))
    chk("更新のお知らせ","9999-99-99z に更新しました" in pg.inner_text('body'))
    ctx.set_offline(True); pg.reload(); pg.wait_for_timeout(500)
    chk("更新後はオフラインでも新しい版",pg.evaluate("VER")=="9999-99-99z")
    chk("更新してもデータは残る",pg.evaluate("tally().hit")==2)
    chk("JSエラーなし",not errs,errs)
    print("RESULT",sum(R),"/",len(R))
srv.shutdown()
