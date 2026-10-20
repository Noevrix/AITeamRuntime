import React, {act} from 'react';
import {createRoot} from 'react-dom/client';
import {afterEach,beforeEach,describe,it,expect,vi} from 'vitest';
import App,{modeOf} from './App.jsx';

const agents=['DSH','Codex','WorkBuddy'].map((id,i)=>({id,role:['Architect','Engineer','Reviewer'][i],
  status:i===2?'PARTIAL':'REAL_VERIFIED',authorization:i===2?'AUTH_REQUIRED':'UNKNOWN',live_status:'UNKNOWN',
  capabilities:['历史依据'],evidence:[],history:[],failures:[],configuration:{},limits:'未探测',default_mode:'MOCK'}));
let root,container,calls;
beforeEach(()=>{
  globalThis.IS_REACT_ACT_ENVIRONMENT=true;
  container=document.createElement('div');document.body.appendChild(container);root=createRoot(container);calls=[];
  vi.stubGlobal('fetch',vi.fn(async (url,options={})=>{
    calls.push([url,options]);
    const data=url.endsWith('/session')?{csrf:'synthetic-csrf'}:
      url.endsWith('/overview')?{runs:[],counts:{},agents}:
      url.endsWith('/diagnostics')?{data_directory:'test/runs',sqlite:'READ_ONLY_HISTORY',agents,reports:[]}:
      url.endsWith('/drafts')?{id:'draft-id'}:{};
    return {ok:true,json:async()=>data};
  }));
});
afterEach(async()=>{await act(async()=>root.unmount());container.remove();vi.unstubAllGlobals();});
async function render(){await act(async()=>root.render(<App/>));}
async function click(text){const button=[...container.querySelectorAll('button')].find(b=>b.textContent.includes(text));expect(button).toBeTruthy();await act(async()=>button.click());}

describe('local console',()=>{
  it('loads all navigation pages with honest empty states and no model actions',async()=>{
    await render();
    expect(container.textContent).toContain('历史');
    for(const page of ['任务面板','Agent 管理','协作时间线','共享黑板','设置与诊断']) await click(page);
    expect(container.textContent).toContain('AUTH_REQUIRED');
    expect(calls.every(([,o])=>!o.method || o.method==='GET')).toBe(true);
    expect(calls.some(([u])=>/oauth|execute|online/.test(u))).toBe(false);
  });
  it('refreshes using reads only',async()=>{
    await render();await click('刷新');await click('刷新');
    expect(calls.filter(([u])=>u.endsWith('/overview')).length).toBe(3);
    expect(calls.every(([,o])=>!o.method)).toBe(true);
  });
  it('creates a draft only after an explicit submit',async()=>{
    await render();await click('创建草稿');
    expect(calls.some(([,o])=>o.method==='POST')).toBe(false);
    container.querySelector('[name=title]').value='test draft';
    await act(async()=>container.querySelector('form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true})));
    const writes=calls.filter(([,o])=>o.method==='POST');
    expect(writes).toHaveLength(1);
    expect(writes[0][0]).toBe('/api/drafts');
    expect(JSON.parse(writes[0][1].body).title).toBe('test draft');
    expect(container.textContent).toContain('未触发任何模型');
  });
  it('does not turn transport errors into mutations',async()=>{
    fetch.mockImplementation(async()=>{throw new Error('synthetic');});
    await render();
    expect(container.querySelector('[role=alert]').textContent).toContain('无法读取');
    expect(calls.some(([,o])=>o.method==='POST')).toBe(false);
  });
  it('does not infer mock flags from statuses',()=>{
    expect(modeOf({metadata:{mock:false}})).toBe('REAL_OUTPUT');
    expect(modeOf({metadata:{mock:true}})).toBe('MOCK');
    expect(modeOf({type:'APPROVE'})).toBe('UNKNOWN');
  });
  it('reads actual task fields and shows missing retry data without inventing it',async()=>{
    const original=fetch.getMockImplementation();
    const task={id:'task-1',title:'Historical failure',status:'FAILED',assigned_to:'engineer',task_type:'IMPLEMENT'};
    fetch.mockImplementation(async(url,options)=>{
      if(url.endsWith('/overview'))return {ok:true,json:async()=>({runs:[{id:'run-1',name:'fixture',database_status:'READABLE'}],counts:{FAILED:1},agents})};
      if(url.endsWith('/runs/run-1'))return {ok:true,json:async()=>({truncated:[],tables:{tasks:[task],messages:[],events:[],agents:[]}})};
      if(url.endsWith('/tasks/task-1'))return {ok:true,json:async()=>({task,messages:[],decisions:[],events:[],artifacts:[],application_attempts:1,retry_count:null,revision_count:0})};
      return original(url,options);
    });
    await render();await click('任务面板');await click('Historical failure');
    expect(container.textContent).toContain('重试次数无记录');
    expect(container.textContent).toContain('失败');
    expect(calls.some(([,o])=>o?.method==='POST')).toBe(false);
  });
});
