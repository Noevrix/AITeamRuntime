import React,{act} from 'react';
import {createRoot} from 'react-dom/client';
import {beforeEach,afterEach,it,expect,vi} from 'vitest';
import Collaboration from './Collaboration.jsx';
let node,root,writes,state;
beforeEach(()=>{
  globalThis.IS_REACT_ACT_ENVIRONMENT=true;
  node=document.createElement('div');document.body.appendChild(node);root=createRoot(node);
  writes=[];state={project_id:'one',goal:'sample',status:'DRAFT',comments:[]};
  vi.stubGlobal('fetch',vi.fn(async(url,options={})=>{
    if(options.method)writes.push([url,JSON.parse(options.body)]);
    return {ok:true,json:async()=>options.method?state:url==='/api/conversations'?
      {items:[state],execution_enabled:true}:{conversation:state,messages:[],tasks:[],decisions:[],artifacts:[]}};
  }));
});
afterEach(async()=>{await act(async()=>root.unmount());node.remove();vi.unstubAllGlobals();});
async function click(text){
  const b=[...node.querySelectorAll('button')].find(b=>b.textContent.includes(text));
  expect(b).toBeTruthy();await act(async()=>b.click());
}
it('opens history without models and requires consent before discussion',async()=>{
  await act(async()=>root.render(<Collaboration csrf="test"/>));
  await click('sample');
  expect(writes).toHaveLength(0);
  const button=[...node.querySelectorAll('button')].find(b=>b.textContent.includes('开始团队讨论'));
  expect(button.disabled).toBe(true);
  await act(async()=>node.querySelector('input[type=checkbox]').click());
  await click('开始团队讨论');
  expect(writes).toHaveLength(1);
  expect(writes[0]).toEqual(['/api/conversations/one/discuss',{confirm_model_calls:true}]);
});
it('ignores rapid duplicate submits and preserves request identity',async()=>{
  await act(async()=>root.render(<Collaboration csrf="test"/>));
  const textarea=node.querySelector('textarea');
  await act(async()=>{
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(textarea,'new goal');
    textarea.dispatchEvent(new Event('input',{bubbles:true}));
  });
  await act(async()=>{
    const f=node.querySelector('form');
    f.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));
    f.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));
  });
  expect(writes).toHaveLength(1);
  expect(writes[0][1].request_id).toBeTruthy();
});
it('shows agent provenance and requires execution confirmation',async()=>{
  state={...state,status:'AWAITING_CONFIRMATION',plan_id:'plan'};
  const original=fetch.getMockImplementation();
  fetch.mockImplementation(async(url,o)=>{
    if(url==='/api/conversations/one'&&!o?.method)return {ok:true,json:async()=>({
      conversation:state,messages:[{id:'msg',from_agent:'Codex',to_agent:'DSH',type:'CHALLENGE',
        task_id:'task-1',content:'Check assumptions',metadata:{mock:true}}],
      tasks:[],artifacts:[],decisions:[{id:'plan',content:'{"steps":[]}'}]})};
    return original(url,o);
  });
  await act(async()=>root.render(<Collaboration csrf="test"/>));await click('sample');
  expect(node.textContent).toContain('Codex → DSH');
  expect(node.textContent).toContain('MOCK');
  expect([...node.querySelectorAll('button')].find(b=>b.textContent.includes('确认计划并执行')).disabled).toBe(true);
  expect(writes).toHaveLength(0);
});
