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
    ex=lambda r: pg.evaluate("(r)=>{const x=extractQR(r);return [x.ok,x.extracted||x.matchedKey,x.qty,x.reason]}",r)
    for raw,exp in [("028031,JH339-000060-11-A,20,8",[True,"JH339-000060-11",20,""]),
                    ("028031,JH341-000040-11-A,25,8",[True,"JH341-000040-11",25,""]),
                    ("028031 28010 201004407934     JH341-000040-1 / 1-A+         0002001",[True,"JH341-000040-11",20,""]),
                    ("JH341-000040-1 1-A",[True,"JH341-000040-11",1,""]),
                    ("028031,JH339-000060-11,20,8",[True,"JH339-000060-11",20,""]),
                    ("028031,JH339-000060-10,20,8",[True,"JH339-000060-10",20,""])]:
        r=ex(raw); chk(f"{raw[:40]!r}",r==exp,r)
    for raw in ["028031,JH339-000060-12,20,8","028031,JH339-000060-1,20,8","028031,JH339-000060-12-A,20,8","028031,JH001-001760-1,20,8"]:
        r=ex(raw); chk(f"stays NG {raw[10:34]}",r[0]==False,r)
    # 別品番の区別（-1 と -11 の取り違え防止）
    r1=ex("028031,JH001-001830-1,25,8"); r11=ex("028031,JH001-001830-11,25,8"); chk("-1 and -11 distinct",r1[1]=="JH001-001830-1" and r11[1]=="JH001-001830-11",(r1,r11))
    # 履歴の判定し直し：旧版でNGだった記録がOKになる
    pg.click('[data-pick="1"]')
    pg.evaluate("""()=>{const raw='028031,JH339-000060-11-A,20,8';files=[{name:'t',hash:'manual',text:raw+'\\n'+raw+'\\n'+raw+'\\n'+raw,at:'x',results:[0,1,2,3].map(()=>({ok:false,matchedKey:'JH339-000060-11-A',extracted:'JH339-000060-11-A',reason:'品番一覧にありません',bin:'1',date:'2026-11-25',time:'x',cap:0}))}];save();render()}""")
    chk("old NG records re-judged: 4 boxes, 80 pcs, NG 0",pg.inner_text('#boxCount')=="4" and pg.inner_text('#shipmentCount')=="80" and pg.inner_text('#ngCount')=="0",(pg.inner_text('#boxCount'),pg.inner_text('#shipmentCount'),pg.inner_text('#ngCount')))
    # 日本語混入NGは判定し直さない
    pg.evaluate("commitQRRecords(['028031 JH北海道札幌市30-2'])"); chk("JP-converted stays NG",pg.inner_text('#ngCount')=="1")
    chk("no errors",not errs,errs); b.close()
print(all(R))
