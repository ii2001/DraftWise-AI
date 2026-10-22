/* Browser-only Vue 3 app. All OpenAI calls happen on the FastAPI server. */
const { createApp, computed, ref, watch, onMounted } = Vue;
createApp({
  setup() {
    const roles = [
      {id:'TOP',label:'탑',icon:'♜'},
      {id:'JUNGLE',label:'정글',icon:'♧'},
      {id:'MID',label:'미드',icon:'✦'},
      {id:'ADC',label:'원딜',icon:'⌁'},
      {id:'SUPPORT',label:'서포터',icon:'✚'}
    ];
    const styles=[{id:'balanced',label:'균형'},{id:'comfort',label:'숙련도'},{id:'team',label:'팀 조합'}];
    const selectionTypes=[{id:'allies',label:'아군 픽',max:4},{id:'enemies',label:'상대 픽',max:5},{id:'bans',label:'밴',max:10},{id:'pool',label:'내 주력',max:12}];
    const comparisonMetrics={ad:'물리 피해',ap:'마법 피해',frontline:'앞라인',hard_cc:'강한 CC',engage:'교전 개시',peel:'아군 보호'};
    const toast=ref(''),storageAvailable=ref(true);
    function readStorage(key){try{return localStorage.getItem(key);}catch{storageAvailable.value=false;return null;}}
    function saveStorage(key,value){try{localStorage.setItem(key,value);}catch{storageAvailable.value=false;}}
    let saved={};
    try{saved=JSON.parse(readStorage('draftwise_preferences')||'{}')||{};}catch{}
    const pools=Object.fromEntries(roles.map(r=>[r.id,Array.isArray(saved.pools?.[r.id])?[...new Set(saved.pools[r.id].filter(id=>typeof id==='string' && /^[A-Za-z0-9]+$/.test(id)))].slice(0,12):[]]));
    const role=ref(roles.some(r=>r.id===saved.role)?saved.role:'JUNGLE');
    const champions=ref([]),version=ref('16.21.1');
    const catalogLoading=ref(true),catalogError=ref(false);
    const activeSide=ref('allies'),activeSlot=ref(0),query=ref(''),filterRole=ref('ALL');
    const emptyDraft=()=>({allies:[],enemies:[],bans:[],pool:[...pools[role.value]]});
    const draft=ref(emptyDraft());
    const style=ref('balanced'),poolOnly=ref(false),question=ref('');
    const loading=ref(false),result=ref(null),selectedId=ref(null);
    const historyOpen=ref(false),historyLoading=ref(false),historyError=ref(''),historyItems=ref([]),restoredAt=ref(null);
    let revision=0,restoringHistory=false;
    const persistPreferences=()=>saveStorage('draftwise_preferences',JSON.stringify({role:role.value,pools}));
    watch([draft,role,style,poolOnly,question],()=>{result.value=null;selectedId.value=null;restoredAt.value=null;revision++;},{deep:true,flush:'sync'});
    watch(role,(next)=>{
      if(restoringHistory)return;
      draft.value.pool=[...pools[next]];
      query.value='';filterRole.value=activeSide.value==='pool'?next:'ALL';
      persistPreferences();
    },{flush:'sync'});
    watch(()=>draft.value.pool,pool=>{
      if(!restoringHistory){pools[role.value]=[...pool];persistPreferences();}
    },{deep:true,flush:'sync'});
    const champMap=computed(()=>Object.fromEntries(champions.value.map(c=>[c.id,c])));
    const selectedPick=computed(()=>result.value?.recommendations.find(c=>c.id===selectedId.value)||null);
    const filteredChampions=computed(()=>champions.value.filter(c=>
      (filterRole.value==='ALL'||c.roles.includes(filterRole.value)) &&
      (c.name.toLowerCase().includes(query.value.trim().toLowerCase())||c.id.toLowerCase().includes(query.value.trim().toLowerCase()))));
    const name=id=>champMap.value[id]?.name??id;
    const roleName=id=>roles.find(r=>r.id===id)?.label||id;
    const imageUrl=id=>`https://ddragon.leagueoflegends.com/cdn/${encodeURIComponent(version.value)}/img/champion/${encodeURIComponent(id)}.png`;
    const splashUrl=id=>`https://ddragon.leagueoflegends.com/cdn/img/champion/splash/${encodeURIComponent(id)}_0.jpg`;
    const useFallback=ev=>{if(!ev.target.src.endsWith('fallback.svg'))ev.target.src='/static/fallback.svg';};
    const allyIndex=i=>i-(i>roles.findIndex(r=>r.id===role.value)?1:0);
    const formatDate=value=>new Date(value).toLocaleString('ko-KR',{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',timeZone:'Asia/Seoul'});
    function notify(msg){toast.value=msg;setTimeout(()=>{if(toast.value===msg)toast.value='';},3400);}
    function isUnavailable(id){return activeSide.value!=='pool' && ['allies','enemies','bans'].some(side=>draft.value[side].some((picked,i)=>picked===id && !(side===activeSide.value && i===activeSlot.value)));}
    function selectSlot(side,index){activeSide.value=side;activeSlot.value=index;}
    function selectSide(side){
      const max=selectionTypes.find(s=>s.id===side).max;
      const empty=Array.from({length:max},(_,i)=>i).find(i=>!draft.value[side][i]);
      selectSlot(side,empty??0);
      if(side==='pool')filterRole.value=role.value;
    }
    function pick(id){
      const side=activeSide.value,arr=draft.value[side];
      if(side==='pool'){
        if(arr.includes(id)){remove(side,id);return;}
        if(arr.length>=12){notify('내 주력은 최대 12명까지 등록할 수 있어요.');return;}
        arr.push(id);return;
      }
      if(isUnavailable(id)){notify('이미 픽 또는 밴에 포함된 챔피언입니다.');return;}
      if(arr[activeSlot.value]===id){remove(side,id);return;}
      arr[activeSlot.value]=id;
      const max=selectionTypes.find(s=>s.id===side).max;
      const next=Array.from({length:max},(_,i)=>(activeSlot.value+1+i)%max).find(i=>!arr[i]);
      if(next!==undefined)activeSlot.value=next;
    }
    function remove(side,id){
      if(side==='pool')draft.value.pool=draft.value.pool.filter(x=>x!==id);
      else{const index=draft.value[side].indexOf(id);if(index!==-1){draft.value[side][index]=null;selectSlot(side,index);}}
    }
    function resetDraft(){draft.value=emptyDraft();question.value='';style.value='balanced';poolOnly.value=false;query.value='';filterRole.value='ALL';selectSlot('allies',0);notify('밴픽을 초기화했습니다. 내 포지션과 주력 목록은 유지됩니다.');}
    function loadPreset(which){
      poolOnly.value=false;style.value=which==='tank'?'team':'balanced';question.value='';query.value='';filterRole.value='ALL';
      const allies=which==='tank'?['Fiora','Khazix','Akali','Jinx','Senna']:['Jayce','LeeSin','Yasuo','Jinx','Pyke'];
      draft.value={allies:allies.filter((id,i)=>roles[i].id!==role.value),enemies:['Ornn','Vi','Ahri','Caitlyn','Leona'],bans:[],pool:[...pools[role.value]]};
      selectSide('allies');notify(`${roleName(role.value)} 예시 조합을 불러왔습니다. 내 주력 목록은 유지됩니다.`);
    }
    function selectRecommended(id){
      const candidate=result.value?.recommendations.find(c=>c.id===id);
      if(!candidate?.composition_after){notify('이전 분석에는 비교 정보가 없습니다. 다시 분석해 주세요.');return;}
      selectedId.value=id;
    }
    function clearComparison(){selectedId.value=null;}
    async function analyze(){
      if(loading.value)return;
      loading.value=true;result.value=null;selectedId.value=null;restoredAt.value=null;
      const requestedRevision=revision;
      try{
        // Preserve visual slots for history; scoring receives only champion IDs.
        const slots=Object.fromEntries(['allies','enemies','bans'].map(side=>[side,Array.from(draft.value[side],id=>id||null)]));
        const picks=Object.fromEntries(Object.entries(draft.value).map(([side,ids])=>[side,ids.filter(Boolean)]));
        const payload={...picks,slots,role:role.value,style:style.value,pool_only:poolOnly.value,question:question.value,session_id:readStorage('draftwise_session_id')||null};
        const response=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
        const json=await response.json();
        if(!response.ok){const detail=json.detail;throw new Error(typeof detail==='string'?detail:JSON.stringify(detail));}
        if(json.session_id)saveStorage('draftwise_session_id',json.session_id);
        if(historyOpen.value)await loadHistory();
        if(requestedRevision!==revision){notify('밴픽이 변경되었습니다. 현재 조합으로 다시 분석해 주세요.');return;}
        result.value=json;
        requestAnimationFrame(()=>document.querySelector('.insights-panel')?.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'}));
      }catch(err){notify(`분석 오류: ${err.message}`);}finally{loading.value=false;}
    }
    async function loadHistory(){
      historyLoading.value=true;historyError.value='';
      try{
        const session=readStorage('draftwise_session_id');
        if(!session){historyItems.value=[];return;}
        const response=await fetch(`/api/history/${encodeURIComponent(session)}`);
        if(!response.ok)throw Error('분석 이력을 불러오지 못했습니다.');
        const data=await response.json();
        historyItems.value=data.items||[];
      }catch(err){historyError.value=err.message;}
      finally{historyLoading.value=false;}
    }
    function toggleHistory(){historyOpen.value=!historyOpen.value;if(historyOpen.value)loadHistory();}
    function restoreHistory(item){
      const req=item.request;
      if(!roles.some(r=>r.id===req.role)||req.allies.length>4||req.pool.length>12||[...req.allies,...req.enemies,...req.bans,...req.pool].some(id=>!champMap.value[id])){
        notify('현재 편집창에서 지원하지 않는 챔피언 또는 입력 크기를 가진 이력입니다.');return;
      }
      function restoreSlots(side){
        if(req.slots?.[side])return [...req.slots[side]];
        // Older records contain compact lists; infer their positions from curated roles.
        const positions=roles.filter(r=>side!=='allies'||r.id!==req.role);
        const max=side==='bans'?10:positions.length;
        const slots=Array(max).fill(null);
        for(const id of req[side]){
          let index=-1;
          if(side!=='bans'){
            for(const championRole of champMap.value[id].roles){
              index=positions.findIndex((r,i)=>!slots[i]&&r.id===championRole);
              if(index!==-1)break;
            }
          }
          if(index===-1)index=slots.indexOf(null);
          slots[index]=id;
        }
        return slots;
      }
      restoringHistory=true;
      try{
        role.value=req.role;
        draft.value={allies:restoreSlots('allies'),enemies:restoreSlots('enemies'),bans:restoreSlots('bans'),pool:[...req.pool]};
        style.value=req.style;poolOnly.value=req.pool_only;question.value=req.question||'';
        query.value='';filterRole.value='ALL';selectSide('allies');
      }finally{restoringHistory=false;}
      persistPreferences();
      result.value=item.result;selectedId.value=null;restoredAt.value=item.created_at;
      notify('저장 당시의 밴픽과 분석 결과를 불러왔습니다.');
    }
    async function loadCatalog(){
      catalogLoading.value=true;catalogError.value=false;
      try{
        const response=await fetch('/api/champions');
        if(!response.ok)throw Error('서버 응답 오류');
        const data=await response.json();
        if(!data.champions?.length)throw Error('챔피언 목록 없음');
        champions.value=data.champions;version.value=data.version||version.value;
        for(const r of roles)pools[r.id]=pools[r.id].filter(id=>champMap.value[id]);
        draft.value.pool=[...pools[role.value]];
      }catch(e){catalogError.value=true;notify('챔피언을 불러오지 못했습니다. 다시 시도해 주세요.');}
      finally{catalogLoading.value=false;}
    }
    onMounted(loadCatalog);
    return {roles,styles,selectionTypes,comparisonMetrics,champions,version,catalogLoading,catalogError,role,activeSide,activeSlot,query,filterRole,draft,style,poolOnly,question,loading,result,selectedPick,storageAvailable,toast,historyOpen,historyLoading,historyError,historyItems,restoredAt,filteredChampions,name,roleName,formatDate,imageUrl,splashUrl,useFallback,allyIndex,isUnavailable,selectSlot,selectSide,pick,remove,resetDraft,loadPreset,selectRecommended,clearComparison,analyze,loadCatalog,toggleHistory,loadHistory,restoreHistory};
  }
}).mount('#app');
document.getElementById('boot-status')?.remove();
