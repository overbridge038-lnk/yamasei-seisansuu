/* 山清工業㈱生産数集計：オフラインで使うための Service Worker（2026-11-26a）
   - 一度オンラインで開くと、index.html などを端末に保存する。
   - ページを開くとき：オンラインなら最新版を取りにいき（4秒まで）、保存も更新する。つながらなければ保存した版を出す。
   - 読取データは localStorage にあり、ここでは扱わない（消さない）。 */
const CACHE = "yamasei-seisansuu-v1";
const FILES = ["./", "./index.html", "./manifest.json", "./icon-192.png", "./icon-512.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES.map(f => new Request(f, {cache: "reload"})))).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
function withTimeout(p, ms){
  return new Promise((ok, ng) => { const t = setTimeout(() => ng(new Error("timeout")), ms); p.then(v => { clearTimeout(t); ok(v); }, err => { clearTimeout(t); ng(err); }); });
}
self.addEventListener("fetch", e => {
  const req = e.request, url = new URL(req.url);
  if(req.method !== "GET" || url.origin !== self.location.origin) return;
  const isPage = req.mode === "navigate" || url.pathname.endsWith("/") || url.pathname.endsWith("/index.html");
  if(isPage){
    e.respondWith((async () => {
      const c = await caches.open(CACHE);
      try{
        const res = await withTimeout(fetch(req, {cache: "no-store"}), 4000);
        if(res.ok){ await c.put("./index.html", res.clone()); await c.put("./", res.clone()); }
        return res;
      }catch(err){
        return (await c.match("./index.html")) || (await c.match("./")) || Response.error();
      }
    })());
    return;
  }
  e.respondWith(caches.match(req, {ignoreSearch: true}).then(hit => hit || fetch(req)));
});
