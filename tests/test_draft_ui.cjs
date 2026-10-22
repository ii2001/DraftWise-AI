// Run with: node --test tests/test_draft_ui.cjs
const {test}=require('node:test');
const assert=require('node:assert/strict');
const {readFileSync}=require('node:fs');
const {join}=require('node:path');
const {runInNewContext}=require('node:vm');

function setup(){
  let app,payload;
  runInNewContext(readFileSync(join(__dirname,'../static/app.js'),'utf8'),{
    Vue:{ref:value=>({value}),computed:fn=>({get value(){return fn();}}),watch:()=>{},onMounted:()=>{},createApp:options=>({mount:()=>{app=options.setup();}})},
    setTimeout:()=>{},requestAnimationFrame:()=>{},
    localStorage:{getItem:()=>null,setItem:()=>{}},
    fetch:async(url,options)=>{payload=JSON.parse(options.body);return {ok:true,json:async()=>({recommendations:[]})};}
  });
  return {app,getPayload:()=>payload};
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
