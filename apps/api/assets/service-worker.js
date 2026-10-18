'use strict';
const CACHE='myagentsales-public-v1';
const PUBLIC=['/offline','/assets/icon-192.png','/assets/icon-512.png'];
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(PUBLIC))));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key.startsWith('myagentsales-public-')&&key!==CACHE).map(key=>caches.delete(key)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',event=>{
 const request=event.request,url=new URL(request.url);
 if(request.method!=='GET'||url.origin!==self.location.origin)return;
 // OAuth callback must never be redirected to an offline page or replayed.
 if(url.pathname==='/m0/connect'&&request.mode==='navigate'){
  event.respondWith(fetch(request).catch(()=>caches.match('/offline')));return;
 }
 if(PUBLIC.includes(url.pathname)&&!url.search)event.respondWith(caches.match(request).then(cached=>cached||fetch(request)));
 // API, OAuth, auth services, webhook and cockpit HTML are never cached.
});
