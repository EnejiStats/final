
(function(){
'use strict';
const {h,render}=preact; const html=htm.bind(h);
const TABS=window.ENEJISTATS_TABS; const CHANNEL='enejistats.club-dashboard';
function Shell(){
 const [active,setActive]=preactHooks.useState('profile');
 const [loaded,setLoaded]=preactHooks.useState({profile:true});
 const [sidebar,setSidebar]=preactHooks.useState(false);
 const [identity,setIdentity]=preactHooks.useState({clubName:'Club Dashboard',category:'',badgeUrl:'',balance:0,locked:0,unread:0});
 const [errors,setErrors]=preactHooks.useState({});
 const [toast,setToast]=preactHooks.useState('');
 const [routes,setRoutes]=preactHooks.useState({});
 const frameRefs=preactHooks.useRef({});
 const loadedRef=preactHooks.useRef(loaded); loadedRef.current=loaded;
 const activate=(id,route)=>{
   const tab=TABS.find(x=>x.id===id); if(!tab)return;
   setActive(id);setSidebar(false);
   if(route) setRoutes(p=>({...p,[id]:route}));
   if(!loadedRef.current[id]) setLoaded(p=>({...p,[id]:true}));
   const frame=frameRefs.current[id];
   if(frame && frame.contentWindow && route){
     frame.contentWindow.postMessage({channel:CHANNEL,version:1,type:'SET_ROUTE',payload:route},location.origin);
   }
 };
 preactHooks.useEffect(()=>{
   let alive=true;
   fetch('/api/auth/me',{credentials:'include',cache:'no-store'}).then(r=>{
     if((r.status===401||r.status===403)&&alive) location.replace('/login');
     if(!r.ok) throw new Error('Session check failed');
   }).catch(()=>{});
   const onMessage=e=>{
     if(e.origin!==location.origin)return;
     const frame=Object.values(frameRefs.current).find(f=>f&&f.contentWindow===e.source);
     if(!frame)return;
     const m=e.data;if(!m||m.channel!==CHANNEL||m.version!==1||!m.payload)return;
     if(m.type==='TAB_READY'){
       const p=m.payload;setIdentity(x=>({...x,clubName:p.clubName||x.clubName,category:p.clubCategory||x.category,badgeUrl:p.badgeUrl||x.badgeUrl,clubId:p.clubId||x.clubId,balance:p.tokenBalance??x.balance,locked:p.tokenLocked??x.locked,unread:p.unreadCount??x.unread}));
     }else if(m.type==='NAVIGATE'){
       const p=m.payload;setIdentity(x=>({...x,clubName:p.clubName||x.clubName,category:p.clubCategory||x.category,badgeUrl:p.badgeUrl||x.badgeUrl,clubId:p.clubId||x.clubId,balance:p.tokenBalance??x.balance,locked:p.tokenLocked??x.locked,unread:p.unreadCount??x.unread}));
       activate(p.tab,p.route);
       const target=frameRefs.current[p.tab];
       if(target&&target.contentWindow)target.contentWindow.postMessage({channel:CHANNEL,version:1,type:'SET_ROUTE',payload:p.route||{}},location.origin);
     }else if(m.type==='REQUEST_LOGOUT'){logout();}
     else if(m.type==='OPEN_TOKEN_PURCHASE'){activate('tokens');}
     else if(m.type==='SHOW_TOAST'){setToast(String(m.payload.message||''));}
   };
   addEventListener('message',onMessage);return()=>removeEventListener('message',onMessage);
 },[]);
 const logout=async()=>{try{await fetch('/api/auth/logout',{method:'POST',credentials:'include'});}catch(_){}try{localStorage.clear();sessionStorage.clear();}catch(_){}location.replace('/login');};
 const retry=id=>{const f=frameRefs.current[id];if(f){setErrors(p=>({...p,[id]:false}));f.src=TABS.find(t=>t.id===id).src+'?retry='+Date.now();}};
 return html`<div>
 <header class="shell-header"><button aria-label="Toggle navigation" onClick=${()=>setSidebar(v=>!v)}><i class="fas fa-bars"></i></button><div class="brand">ENEJI<span>STATS</span></div><div class="club-meta">${identity.clubName}</div><button onClick=${logout}><i class="fas fa-sign-out-alt"></i> Logout</button></header>
 <div class=${'mobile-overlay '+(sidebar?'show':'')} onClick=${()=>setSidebar(false)}></div>
 <aside class=${'sidebar '+(sidebar?'open':'')}>
 <div class="club-card">${identity.badgeUrl?html`<img class="club-avatar" src=${identity.badgeUrl} alt="Club badge" />`:null}<div class="club-name">${identity.clubName}</div><div class="club-category">${identity.category||'Club Dashboard'}</div></div>
 <div class="token-widget" role="button" tabindex="0" onClick=${()=>activate('tokens')}><div class="token-number">${identity.balance}</div><div class="token-label">Token balance · ${identity.locked} locked</div></div>
 <nav class="nav-list" aria-label="Primary navigation">${TABS.map(t=>html`<button class=${'nav-item '+(active===t.id?'active':'')} aria-current=${active===t.id?'page':null} onClick=${()=>activate(t.id)}><i class=${'fas '+t.icon}></i><span>${t.label}</span>${t.id==='notifications'&&identity.unread>0?html`<span class="count">${identity.unread}</span>`:''}</button>`)}</nav>
 </aside>
 <main class="workspace">${TABS.map(t=>loaded[t.id]?html`<iframe key=${t.id} ref=${el=>{if(el)frameRefs.current[t.id]=el;}} class=${'tab-frame '+(active===t.id?'active':'')} title=${t.label+' application'} id=${'enejistats-tab-'+t.id} src=${t.src} loading=${t.id==='profile'?'eager':'lazy'}
 onLoad=${()=>{const f=frameRefs.current[t.id];if(f&&f.contentWindow){f.contentWindow.postMessage({channel:CHANNEL,version:1,type:'SET_ACTIVE_TAB',payload:{tab:t.id}},location.origin);if(routes[t.id])f.contentWindow.postMessage({channel:CHANNEL,version:1,type:'SET_ROUTE',payload:routes[t.id]},location.origin);}}}
 onError=${()=>setErrors(p=>({...p,[t.id]:true}))}></iframe>`:null)}
 ${errors[active]?html`<div class="frame-error"><h3>Unable to load ${TABS.find(t=>t.id===active).label}</h3><p>Check your connection and try again.</p><button onClick=${()=>retry(active)}>Retry</button></div>`:null}
 </main>
 ${toast?html`<div role="status" style="position:fixed;z-index:80;right:18px;top:72px;background:#1e293b;color:#fff;padding:12px 16px;border-radius:8px;box-shadow:0 4px 16px #0003" onClick=${()=>setToast('')}>${toast}</div>`:null}
 </div>`;
}
render(h(Shell),document.getElementById('app'));
})();
