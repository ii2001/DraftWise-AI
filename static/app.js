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
    const champions=ref([]),version=ref('16.18.1');
    const catalogLoading=ref(true),catalogError=ref(false);
    const role=ref('JUNGLE'),activeSide=ref('allies'),activeSlot=ref(0),query=ref(''),filterRole=ref('ALL');
    const emptyDraft=()=>({allies:[],enemies:[],bans:[],pool:['Zyra','Ekko','Zac']});
    const draft=ref(emptyDraft());
    const style=ref('balanced'),poolOnly=ref(false),question=ref('');
    const loading=ref(false),result=ref(null),toast=ref('');
    let revision=0;
    watch([draft,role,style,poolOnly,question],()=>{result.value=null;revision++;},{deep:true,flush:'sync'});
    const champMap=computed(()=>Object.fromEntries(champions.value.map(c=>[c.id,c])));
    const filteredChampions=computed(()=>champions.value.filter(c=>
      (filterRole.value==='ALL'||c.roles.includes(filterRole.value)) &&
      (c.name.toLowerCase().includes(query.value.trim().toLowerCase())||c.id.toLowerCase().includes(query.value.trim().toLowerCase()))));
    const name=id=>champMap.value[id]?.name??id;
    const imageUrl=id=>`https://ddragon.leagueoflegends.com/cdn/${encodeURIComponent(version.value)}/img/champion/${encodeURIComponent(id)}.png`;
    const splashUrl=id=>`https://ddragon.leagueoflegends.com/cdn/img/champion/splash/${encodeURIComponent(id)}_0.jpg`;
    const useFallback=ev=>{if(!ev.target.src.endsWith('fallback.svg'))ev.target.src='/static/fallback.svg';};
    const allyIndex=i=>i-(i>roles.findIndex(r=>r.id===role.value)?1:0);
    function notify(msg){toast.value=msg;setTimeout(()=>{if(toast.value===msg)toast.value='';},3400);}
    function isUnavailable(id){return activeSide.value!=='pool' && ['allies','enemies','bans'].some(side=>draft.value[side].some((picked,i)=>picked===id && !(side===activeSide.value && i===activeSlot.value)));}
    function selectSlot(side,index){activeSide.value=side;activeSlot.value=index;}
    function selectSide(side){
      const max=selectionTypes.find(s=>s.id===side).max;
      const empty=Array.from({length:max},(_,i)=>i).find(i=>!draft.value[side][i]);
      selectSlot(side,empty??0);
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
    function resetDraft(){draft.value=emptyDraft();role.value='JUNGLE';question.value='';style.value='balanced';poolOnly.value=false;query.value='';filterRole.value='ALL';selectSlot('allies',0);notify('밴픽을 초기화했습니다.');}
    function loadPreset(which){
      role.value='JUNGLE';poolOnly.value=false;style.value='balanced';question.value='';query.value='';filterRole.value='ALL';
      if(which==='ap')draft.value={allies:[null,'Yasuo','Jinx'],enemies:[null,'LeeSin','Ahri'],bans:[],pool:['Zyra','Ekko','Zac']};
      else if(which==='tank'){draft.value={allies:['Jayce','Zed','Jinx'],enemies:[null,'Vi',null,null,'Leona'],bans:[],pool:['Zac','Sejuani','Zyra','Ekko']};style.value='team';}
      else{draft.value={allies:[null,'Orianna','Jinx'],enemies:[null,'LeeSin','Yasuo'],bans:[],pool:['Zyra','Ekko','Zac']};style.value='comfort';}
      selectSide('allies');notify('예시 조합을 불러왔습니다. AI 픽 추천을 눌러 보세요.');
    }
    async function analyze(){
      if(loading.value)return;
      loading.value=true;result.value=null;
      const requestedRevision=revision;
      try{
        // Empty visual slots must never reach the API's champion ID lists.
        const picks=Object.fromEntries(Object.entries(draft.value).map(([side,ids])=>[side,ids.filter(Boolean)]));
        const payload={...picks,role:role.value,style:style.value,pool_only:poolOnly.value,question:question.value,session_id:localStorage.getItem('draftwise_session_id')||null};
        const response=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
        const json=await response.json();
        if(!response.ok){const detail=json.detail;throw new Error(typeof detail==='string'?detail:JSON.stringify(detail));}
        if(requestedRevision!==revision){notify('밴픽이 변경되었습니다. 현재 조합으로 다시 분석해 주세요.');return;}
        result.value=json;
        if(json.session_id)localStorage.setItem('draftwise_session_id',json.session_id);
        requestAnimationFrame(()=>document.querySelector('.insights-panel')?.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'}));
      }catch(err){notify(`분석 오류: ${err.message}`);}finally{loading.value=false;}
    }
    async function loadCatalog(){
      catalogLoading.value=true;catalogError.value=false;
      try{
        const response=await fetch('/api/champions');
        if(!response.ok)throw Error('서버 응답 오류');
        const data=await response.json();
        if(!data.champions?.length)throw Error('챔피언 목록 없음');
        champions.value=data.champions;version.value=data.version||version.value;
      }catch(e){catalogError.value=true;notify('챔피언을 불러오지 못했습니다. 다시 시도해 주세요.');}
      finally{catalogLoading.value=false;}
    }
    onMounted(loadCatalog);
    return {roles,styles,selectionTypes,champions,version,catalogLoading,catalogError,role,activeSide,activeSlot,query,filterRole,draft,style,poolOnly,question,loading,result,toast,filteredChampions,name,imageUrl,splashUrl,useFallback,allyIndex,isUnavailable,selectSlot,selectSide,pick,remove,resetDraft,loadPreset,analyze,loadCatalog};
  }
}).mount('#app');
