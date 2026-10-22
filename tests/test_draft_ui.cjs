// Run with: node --test tests/test_draft_ui.cjs
const {test}=require('node:test');
const assert=require('node:assert/strict');
const {readFileSync}=require('node:fs');
const {join}=require('node:path');
const {runInNewContext}=require('node:vm');

function setup(stored={},storageBlocked=false){
  let app,payload;
  const storage=new Map(Object.entries(stored)),calls=[];
  runInNewContext(readFileSync(join(__dirname,'../static/app.js'),'utf8'),{
    Vue:{ref:value=>({value}),computed:fn=>({get value(){return fn();}}),watch:()=>{},onMounted:()=>{},createApp:options=>({mount:()=>{app=options.setup();}})},
    setTimeout:()=>{},requestAnimationFrame:()=>{},
    document:{getElementById:()=>null},
    localStorage:{getItem:key=>{if(storageBlocked)throw Error('disabled');return storage.get(key)||null;},setItem:(key,value)=>{if(storageBlocked)throw Error('disabled');storage.set(key,value);}},
    fetch:async(url,options)=>{calls.push(url);if(options)payload=JSON.parse(options.body);return {ok:true,json:async()=>({recommendations:[],items:[]})};}
  });
  return {app,storage,calls,getPayload:()=>payload};
}

test('arbitrary empty slots serialize as champion IDs without empty entries',async()=>{
  const {app,getPayload}=setup();
  app.selectSlot('allies',3);app.pick('Yasuo');
  app.selectSlot('bans',9);app.pick('Ahri');
  await app.analyze();
  assert.deepEqual(getPayload().allies,['Yasuo']);
  assert.deepEqual(getPayload().bans,['Ahri']);
  assert.deepEqual(getPayload().enemies,[]);
});

test('replacement and removal preserve other slot positions',()=>{
  const {app}=setup();
  app.selectSlot('allies',0);app.pick('Garen');
  app.selectSlot('allies',2);app.pick('Jinx');
  app.selectSlot('allies',0);app.pick('Jax');
  assert.equal(app.draft.value.allies[0],'Jax');
  assert.equal(app.draft.value.allies[2],'Jinx');
  app.remove('allies','Jax');
  assert.equal(app.draft.value.allies[0],null);
  assert.equal(app.draft.value.allies[2],'Jinx');
  assert.equal(app.activeSlot.value,0);
});

test('picked and banned champions cannot be reused, but remain eligible for the pool',()=>{
  const {app}=setup();
  app.selectSlot('enemies',4);app.pick('Ahri');
  app.selectSlot('bans',0);app.pick('Ahri');
  assert.equal(app.draft.value.bans.length,0);
  app.selectSide('pool');app.pick('Ahri');
  assert(app.draft.value.pool.includes('Ahri'));
  app.pick('Ahri');
  assert(!app.draft.value.pool.includes('Ahri'));
});

test('team limits and reset retain the four teammate / five opponent model',()=>{
  const {app}=setup();
  app.selectSide('allies');
  for(const id of ['Garen','Yasuo','Jinx','Leona'])app.pick(id);
  assert.equal(app.draft.value.allies.length,4);
  app.pick('Jax');
  assert.equal(app.draft.value.allies.length,4);
  app.poolOnly.value=true;app.style.value='team';app.query.value='test';
  app.resetDraft();
  assert.equal(app.draft.value.allies.length,0);
  assert.equal(app.poolOnly.value,false);
  assert.equal(app.style.value,'balanced');
  assert.equal(app.query.value,'');
});

test('saved role and personal pool survive reset and example drafts',()=>{
  const preferences={role:'MID',pools:{MID:['Ahri','Orianna'],JUNGLE:['Zac']}};
  const {app}=setup({draftwise_preferences:JSON.stringify(preferences)});
  assert.equal(app.role.value,'MID');
  assert.equal(JSON.stringify(app.draft.value.pool),'["Ahri","Orianna"]');
  app.loadPreset('ap');
  assert.equal(app.role.value,'MID');
  assert.equal(JSON.stringify(app.draft.value.pool),'["Ahri","Orianna"]');
  app.resetDraft();
  assert.equal(app.role.value,'MID');
  assert.equal(JSON.stringify(app.draft.value.pool),'["Ahri","Orianna"]');
});

test('malformed or unavailable browser storage does not prevent drafting',()=>{
  for(const [stored,blocked] of [[{draftwise_preferences:'{broken'},false],[{},true]]){
    const {app}=setup(stored,blocked);
    app.selectSlot('allies',0);app.pick('Garen');
    assert.equal(app.draft.value.allies[0],'Garen');
    if(blocked)assert.equal(app.storageAvailable.value,false);
  }
});

test('comparison switches the preview without changing the draft or making requests',()=>{
  const {app,calls}=setup();
  app.result.value={recommendations:[{id:'Zac',composition_after:{frontline:1}},{id:'Ekko',composition_after:{frontline:0}}]};
  app.selectRecommended('Zac');
  assert.equal(app.selectedPick.value.id,'Zac');
  app.selectRecommended('Ekko');
  assert.equal(app.selectedPick.value.id,'Ekko');
  assert.equal(app.draft.value.allies.length,0);
  assert.equal(calls.length,0);
  app.clearComparison();
  assert.equal(app.selectedPick.value,null);
});

test('history restores slots and settings without replacing personal pool preferences',()=>{
  const saved={role:'MID',pools:{MID:['Ahri']}};
  const {app,storage,calls}=setup({draftwise_preferences:JSON.stringify(saved)});
  app.champions.value=JSON.parse(readFileSync(join(__dirname,'../data/champions.json'),'utf8'));
  const item={created_at:'2026-10-22T00:00:00+00:00',request:{role:'MID',allies:['Jinx'],enemies:['Yasuo'],bans:[],pool:['Orianna'],pool_only:true,style:'team',question:'보호가 필요해',slots:{allies:[null,null,'Jinx'],enemies:[null,null,'Yasuo'],bans:[]}},result:{recommendations:[]}};
  app.restoreHistory(item);
  assert.equal(app.draft.value.allies[2],'Jinx');
  assert.equal(app.draft.value.enemies[2],'Yasuo');
  assert.equal(app.draft.value.pool[0],'Orianna');
  assert.equal(app.style.value,'team');
  assert.equal(app.poolOnly.value,true);
  assert.equal(app.question.value,'보호가 필요해');
  assert.equal(JSON.parse(storage.get('draftwise_preferences')).pools.MID[0],'Ahri');
  assert.equal(app.result.value,item.result);
  assert.equal(calls.length,0);
  item.request.slots=null;
  app.restoreHistory(item);
  assert.equal(app.draft.value.allies[2],'Jinx');
  assert.equal(app.draft.value.enemies[2],'Yasuo');
});
