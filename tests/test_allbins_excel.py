import os, sys, pathlib
HERE=pathlib.Path(__file__).resolve().parent
INDEX=(HERE.parent/'index.html').as_uri()
os.chdir(HERE/'fixtures')
CHROME=os.environ.get('CHROME') or None
from playwright.sync_api import sync_playwright
import io, zipfile, re, base64
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=CHROME,args=['--no-sandbox'])
    ctx=b.new_context(accept_downloads=True); pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e))); R=[]
    def chk(n,c,i=""): R.append(c); print(("PASS " if c else "FAIL ")+n,i)
    pg.goto(INDEX); K=pg.evaluate("[...PART_CODES.keys()]"); A,B=K[0],K[1]
    chk("disabled when empty",pg.is_disabled('#bXlsxAll'))
    def scan(bin,part,cap,n=1):
        if bin in("3","4","特車"):
            if not pg.is_visible('#binExtra'): pg.click('#binMore')
        pg.click(f'[data-pick="{bin}"]')
        for _ in range(n): pg.evaluate("([a,c])=>commitQRRecords(['028031,'+a+','+c+',8'])",[part,cap])
    scan("1",A,30,2); scan("1",B,20); scan("2",A,30); scan("特車",A,10,3); scan("特車",B,20)
    pg.evaluate("commitQRRecords(['ZZ-NG-1'])")
    chk("未処置NGがあると全便山積みは止まる",pg.is_disabled('#bXlsxAll'))
    pg.evaluate("(()=>{const r=tally().history.find(x=>!x.ok);ngRecord(r).disp={type:'exclude',reason:'テスト',at:'x'};dirty++;save();render()})()")
    pg.click('#binChips [data-bin="1"]')   # 便の絞り込みをしても全便が対象
    chk("enabled",not pg.is_disabled('#bXlsxAll'))
    chk("button below Excel button",pg.evaluate("document.querySelector('#bXlsxAll').getBoundingClientRect().top>document.querySelector('#bXlsx').getBoundingClientRect().bottom-2"))
    with pg.expect_download() as d: pg.click('#bXlsxAll')
    d.value.save_as('allbins.xlsx'); path='allbins.xlsx'; z=zipfile.ZipFile(path); x=z.read('xl/worksheets/sheet1.xml').decode()
    ss=z.read('xl/sharedStrings.xml').decode() if 'xl/sharedStrings.xml' in z.namelist() else x
    print(d.value.suggested_filename)
    import openpyxl; wb=openpyxl.load_workbook(path); ws=wb.active
    rows=[[c for c in r] for r in ws.iter_rows(values_only=True)]
    for r in rows: print(r)
    chk("sheet name",ws.title=="全便合計")
    chk("header bins",rows[0][2:]==['1便（個）','2便（個）','特車（個）','合計 箱数','合計 出荷数(個)'],rows[0])
    ra=[r for r in rows if r[1]==A][0]; rb=[r for r in rows if r[1]==B][0]
    chk("part A stacked: 1便60 2便30 特車30 -> 120, 7箱?",ra[2:]==[60,30,30,6,120],ra)
    chk("part B: 1便20 特車20 -> 40",rb[2:]==[20,None,20,2,40],rb)
    chk("total row",rows[-1][0]=="合計" and rows[-1][-1]==160 and rows[-1][-2]==8,rows[-1])
    chk("NG not included",not any(r[1]=="ZZ-NG-1" for r in rows))
    pg.evaluate("state.bin='2';render()"); chk("still enabled with other filter",not pg.is_disabled('#bXlsxAll'))
    chk("no errors",not errs,errs); b.close()
print(all(R))
