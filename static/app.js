/* Browser-only Vue 3 app. All OpenAI calls happen on the FastAPI server. */
const { createApp, computed, ref, onMounted } = Vue;
createApp({
  setup() {
    const roles = [
      { id:'TOP', label:'탑',icon:'♜' },
      { id:'JUNGLE',label:'정글',icon:'♧' },
      { id:'MID',label:'미드',icon:'✦' },
      { id:'ADC',label:'원딜',icon:'⌁' },
      { id:'SUPPORT',label:'서포터',icon:'✚' }
    ];
    const styles=[{id:'balanced',label:'⚖ 균형 우선'},{id:'comfort',label:'★ 숙련도 우선'},{id:'team',label:'♜ 조합 우선'}];
    const selectionTypes=[{id:'allies',label:'아군 픽',symbol:'◈',max:4},{id:'enemies',label:'상대 픽',symbol:'◈',max:5},{id:'bans',label:'밴',symbol:'⊘',max:10},{id:'pool',label:'내 주력',symbol:'★',max:12}];
    const champions=ref([]), version=ref('16.18.1'), health=ref({openai_configured:false});
    const role=ref('JUNGLE'),activeSide=ref('allies'),query=ref(''),filterRole=ref('ALL');
    const draft=ref({allies:[],enemies:[],bans:[],pool:['Zyra','Ekko','Zac']});
    const style=ref('balanced'),poolOnly=ref(false),question=ref('');
    const loading=ref(false), result=ref(null),toast=ref('');
    const champMap=computed(()=>Object.fromEntries(champions.value.map(c=>[c.id,c])));
    const filteredChampions=computed(()=>champions.value.filter(c=>
      (filterRole.value==='ALL'||c.roles.includes(filterRole.value)) &&
      (c.name.toLowerCase().includes(query.value.trim().toLowerCase()) || c.id.toLowerCase().includes(query.value.trim().toLowerCase()))));
    const name=(id)=>champMap.value[id]?.name ?? id;
    const imageUrl=(id)=>`https://ddragon.leagueoflegends.com/cdn/${encodeURIComponent(version.value)}/img/champion/${encodeURIComponent(id)}.png`;
    const useFallback=(ev)=>{if(!ev.target.src.endsWith('fallback.svg')) ev.target.src='/static/fallback.svg';};
    function notify(msg){toast.value=msg;setTimeout(()=>{if(toast.value===msg)toast.value='';},3400);}
    function isSelected(id){return Object.values(draft.value).some(x=>x.includes(id));}
    function pick(id){
      let arr=draft.value[activeSide.value];
      if(arr.includes(id)){remove(activeSide.value,id);return;}
      const s=selectionTypes.find(s=>s.id===activeSide.value);
      if(arr.length>=s.max){notify(`${s.label}은 최대 ${s.max}명까지 선택할 수 있어요.`);return;}
      if(activeSide.value!=='pool' && ['allies','enemies','bans'].some(g=>draft.value[g].includes(id))){notify('이미 픽 또는 밴에 포함된 챔피언입니다.');return;}
      arr.push(id);result.value=null;
    }
    function remove(side,id){draft.value[side]=draft.value[side].filter(x=>x!==id);result.value=null;}
    function resetDraft(){draft.value={allies:[],enemies:[],bans:[],pool:['Zyra','Ekko','Zac']};role.value='JUNGLE';result.value=null;question.value='';activeSide.value='allies';notify('밴픽을 초기화했습니다.');}
    function loadPreset(which){
      role.value='JUNGLE';result.value=null;poolOnly.value=false;style.value='balanced';question.value='';
      if(which==='ap'){draft.value={allies:['Yasuo','Jinx'],enemies:['LeeSin','Ahri'],bans:[],pool:['Zyra','Ekko','Zac']};}
      else if(which==='tank'){draft.value={allies:['Jayce','Zed','Jinx'],enemies:['Vi','Leona'],bans:[],pool:['Zac','Sejuani','Zyra','Ekko']};style.value='team';}
      else{draft.value={allies:['Orianna','Jinx'],enemies:['LeeSin','Yasuo'],bans:[],pool:['Zyra','Ekko','Zac']};style.value='comfort';}
      activeSide.value='allies';notify('예시 조합을 불러왔습니다. AI 분석을 눌러 보세요.');
    }
    async function analyze(){
      loading.value=true;result.value=null;
      try{
        const payload={...draft.value,role:role.value,style:style.value,pool_only:poolOnly.value,question:question.value,session_id:localStorage.getItem('draftwise_session_id')||null};
        const response=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
        const json=await response.json();
        if(!response.ok){const detail=json.detail;throw new Error(typeof detail==='string'?detail:JSON.stringify(detail));}
        result.value=json;
        if(json.session_id)localStorage.setItem('draftwise_session_id',json.session_id);
        requestAnimationFrame(()=>document.querySelector('.insights-panel')?.scrollIntoView({behavior:'smooth',block:'nearest'}));
      } catch(err){notify(`분석 오류: ${err.message}`);}finally{loading.value=false;}
    }
    onMounted(async()=>{
      try{
        const [a,b]=await Promise.all([fetch('/api/champions'),fetch('/api/health')]);
        if(!a.ok||!b.ok)throw Error('서버 응답 오류');
        const [data,stat]=await Promise.all([a.json(),b.json()]);
        champions.value=data.champions||[];version.value=data.version||version.value;health.value=stat;
      }catch(e){notify('서버에 연결할 수 없습니다. FastAPI가 실행 중인지 확인하세요.');}
    });
    return {roles,styles,selectionTypes,champions,version,health,role,activeSide,query,filterRole,draft,style,poolOnly,question,loading,result,toast,filteredChampions,name,imageUrl,useFallback,isSelected,pick,remove,resetDraft,loadPreset,analyze};
  }
}).mount('#app');
