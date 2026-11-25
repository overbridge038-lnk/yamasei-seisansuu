import os, sys, pathlib
HERE=pathlib.Path(__file__).resolve().parent
INDEX=(HERE.parent/'index.html').as_uri()
os.chdir(HERE/'fixtures')
CHROME=os.environ.get('CHROME') or None
from playwright.sync_api import sync_playwright
import json
rows=json.load(open('hist.json'))
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=CHROME,args=['--no-sandbox'])
    pg=b.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e))); R=[]
    def chk(n,c,i=""): R.append(c); print(("PASS " if c else "FAIL ")+n,"→",i)
    pg.goto(INDEX)
    ex=lambda r: pg.evaluate("(r)=>{const x=extractQR(r);return [x.extracted||x.matchedKey,x.ok?'OK':'NG',x.qty,x.reason]}",r)
    reg=lambda: pg.evaluate("PART_CODES.set('JH001-001760-11','test');PART_CODES.set('H2101-60051-2','test')")
    unreg=lambda: pg.evaluate("PART_CODES.delete('JH001-001760-11');PART_CODES.delete('H2101-60051-2')")
    print("== 合格条件")
    unreg()
    for raw,exp in [("028031,JH001-001830-1+1,50,8",["JH001-001830-11","OK",50]),
                    ("028031,JH001-001830-1+0,50,8",["JH001-001830-10","OK",50]),
                    ("028031,JH001-001830-+1,50,8",["JH001-001830-1","OK",50]),
                    ("028031,JH001-002020-1+1,50,8",["JH001-002020-11","OK",50]),
                    ("028031,JH001-001760-1+1,50,8",["JH001-001760-11","NG"]),
                    ("028031,20-H2101-60051-+2,50,8",["H2101-60051-2","NG"])]:
        r=ex(raw); chk(f"[初期一覧] {raw}", r[:len(exp)]==exp and (exp[1]=="OK" or r[3]=="品番一覧にありません"), r)
    reg()
    for raw,exp in [("028031,JH001-001760-1+1,50,8",["JH001-001760-11","OK",50]),
                    ("028031,20-H2101-60051-+2,50,8",["H2101-60051-2","OK",50]),
                    ("20-H2101-60051-+2 0005001",["H2101-60051-2","OK",50])]:
        r=ex(raw); chk(f"[検査用登録] {raw}", r[:3]==exp, r)
    unreg()
    print("== 回帰（直後が空白・末尾・\\・既存形式）")
    for raw,exp in [("029011 28010 201006208109     2JH001-001830-1+1        0002501",["JH001-001830-11","OK",25]),
                    ("JH001-001830-1+1",["JH001-001830-11","OK",1]),
                    ("JH001-001830-1+0\\x",["JH001-001830-10","OK",1]),
                    ("028031 28010 201006107769     2 JH001-001830-+1        0002001",["JH001-001830-1","OK",20]),
                    ("029011 28010 201005908120     2JH001-001930-1+0        0002501",["JH001-001930-10","OK",25]),
                    ("028031,JH001-001830-1,20,8",["JH001-001830-1","OK",20]),
                    ("28031, JH001-001830-1,20,29",["JH001-001830-1","OK",20]),
                    ("29011,JH001-001830-11,25,5",["JH001-001830-11","OK",25]),
                    ("028031,JH339-000060-11-A,20,8",["JH339-000060-11","OK",20]),
                    ("028031 28010 201004308164     2JH339-000060-1+1-A      0002001",["JH339-000060-11","OK",20]),
                    ("028031 28010 x     JH341-000040-1 / 1-A+         0002001",["JH341-000040-11","OK",20]),
                    ("028031 28010 201004407934     2JH001-001930-2+         0002001",["JH001-001930-2","OK",20]),
                    ("028031,10-17060-1,30,8",["10-17060-1","OK",30]),
                    ("028031,JH001-001830-1+12,20,8",["JH001-001830-1","OK",20])]:
        r=ex(raw); chk(raw, r[:len(exp)]==exp, r)
    print("== 誤ってOKにしない（ポカヨケ）")
    for raw in ["028031,JH001-001830-1+5,20,8","028031,JH001-001830-12,20,8","028031,JH001-001760-1,20,8","028031,JH339-000060-12-A,20,8"]:
        r=ex(raw); chk(raw, r[1]=="NG", r)
    print("== 実データ（読取履歴）の再判定")
    for n,part,j,raw in rows:
        if n in (23,24,63,64,50,27,28,29,66,67):
            r=ex(raw); print(f"  {n:>2} 旧:{part:<16}{j}  →  {r[0]} {r[1]} {r[2] or ''}")
    m={n:ex(raw)[0] for n,_,_,raw in rows}
    chk("23・24・63・64番 → JH001-001830-11",all(m[n]=="JH001-001830-11" for n in (23,24,63,64)))
    chk("50番 → JH001-002020-11",m[50]=="JH001-002020-11")
    # 保存データ経由：旧OK記録は自動で再判定、手入力は維持
    pg.click('[data-pick="1"]')
    pg.evaluate("""()=>{const a='029011 28010 201006208109     2JH001-001830-1+1        0002501';
      files=[{name:'t',hash:'manual',text:a+'\\n手入力 JH003-002350 数量25',at:'x',results:[
        {ok:true,matchedKey:'JH001-001830-1',extracted:'JH001-001830-1',reason:'',bin:'1',date:'2026-11-25',time:'x',cap:25},
        {ok:true,manual:true,matchedKey:'JH003-002350',extracted:'JH003-002350',reason:'',bin:'1',date:'2026-11-25',time:'x',cap:25,qty:25}]}];save();render()}""")
    h=pg.evaluate("tally().history.map(r=>[r.part,r.ok,r.cap,r.manual])")
    chk("保存済みOK記録は再判定・手入力は維持",h==[["JH001-001830-11",True,25,False],["JH003-002350",True,25,True]],h)
    chk("no page errors",not errs,errs); b.close()
print("ALL:",all(R), f"{sum(R)}/{len(R)}")
