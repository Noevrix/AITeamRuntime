import React, {useEffect, useRef, useState} from 'react';

export default function Collaboration({csrf}) {
  const [items,setItems]=useState([]),[id,setId]=useState(''),[data,setData]=useState(null);
  const [enabled,setEnabled]=useState(false),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const [input,setInput]=useState(''),[consent,setConsent]=useState(false),[codeConsent,setCodeConsent]=useState(false);
  const [planText,setPlanText]=useState(''),[editing,setEditing]=useState(false);
  const pending=useRef(false),request=useRef(crypto.randomUUID());
  async function call(path='',body) {
    const response=await fetch('/api/conversations'+path,{credentials:'same-origin',
      ...(body?{method:'POST',headers:{'Content-Type':'application/json','X-Console-CSRF':csrf},body:JSON.stringify(body)}:{})});
    const result=await response.json();
    if(!response.ok)throw new Error(result.error||'REQUEST_FAILED');
    return result;
  }
  useEffect(()=>{
    let alive=true;
    async function refresh(){
      try {
        const list=await call();
        if(!alive)return;
        setItems(list.items||[]);setEnabled(list.execution_enabled===true);
        if(id){const value=await call('/'+id);if(alive)setData(value);}
      } catch {if(alive)setError('协作记录读取失败');}
    }
    refresh();
    const timer=setInterval(refresh,2500);
    return ()=>{alive=false;clearInterval(timer);};
  },[id]);
  const state=data?.conversation,active=['DISCUSSING','EXECUTING'].includes(state?.status);
  const plan=data?.decisions?.find(d=>d.id===state?.plan_id);
  async function write(path,body) {
    if(pending.current)return;
    pending.current=true;setBusy(true);setError('');
    try {
      const value=await call(path,body);
      const next=id||value.project_id;
      setId(next);setData(await call('/'+next));
      const list=await call();setItems(list.items||[]);
      return value;
    } catch(e){setError(e.message);return null;}
    finally{pending.current=false;setBusy(false);}
  }
  return <div className="collaboration">
    <aside className="panel conversation-list"><h2>会话</h2>
      <button onClick={()=>{setId('');setData(null);setInput('');setConsent(false);setCodeConsent(false);setEditing(false);request.current=crypto.randomUUID();}}>＋ 新建协作</button>
      {items.map(item=><button key={item.project_id} onClick={()=>{setId(item.project_id);setData(null);setEditing(false);setConsent(false);setCodeConsent(false);}}>
        <strong>{item.goal.slice(0,40)}</strong><small>{item.status}</small></button>)}
    </aside>
    <section className="panel conversation-thread">
      <h2>与 AI 团队协作</h2>
      <p>描述目标 → DSH 提案 → Codex 质疑 → DSH 修订 → 你确认 → 执行与交叉审核</p>
      <p className="footnote">{enabled?'真实调用入口已启用，仍需逐阶段确认。':'模型入口已禁用。可以创建和补充会话；启用方法见协作文档。'} WorkBuddy：PARTIAL / AUTH_REQUIRED。</p>
      <p className="footnote">启用前请退出共享同一 home 的 DSH 桌面 / Host。DSH 使用现有 SDK 权限；“不使用工具”是提示约束，不是操作系统隔离。不要提交不可信任务或凭证。</p>
      {error&&<p role="alert">{error}</p>}
      {state&&<><h3>{state.status}{data.interrupted?' · 进程已中断，请取消后另建会话；不会自动重放':''}</h3>
        <article className="chat-message"><strong>你 · 原始目标</strong><pre>{state.goal}</pre></article>
        {(state.comments||[]).map((s,i)=><article className="chat-message" key={i}><strong>你 · 补充 {i+1}</strong><pre>{s}</pre></article>)}
        {(data.messages||[]).map(m=><article className="chat-message" key={m.id}>
          <strong>{m.from_agent} → {m.to_agent} · {m.type}</strong>
          <small>{m.metadata?.mock===true?'MOCK':m.metadata?.mock===false?'真实 Adapter 输出':'系统消息'} · 任务 {m.task_id.slice(0,8)}</small>
          <pre>{m.content}</pre></article>)}
        {state.error&&<p role="alert">已停止：{state.error}。不会自动重试。</p>}
      </>}
      {(!state||['DRAFT','WAITING_FOR_USER','AWAITING_CONFIRMATION'].includes(state.status))&&<form onSubmit={async e=>{
        e.preventDefault();const result=await write(id?'/'+id+'/comment':'',
          id?{content:input}:{goal:input,request_id:request.current});
        if(result){setInput('');setCodeConsent(false);}
      }}><label>目标、补充要求和约束<textarea aria-label="协作输入" value={input} maxLength={id?4000:8000} rows={5} required
        placeholder="希望团队完成什么？验收标准是什么？请勿填写凭证。" onChange={e=>setInput(e.target.value)}/></label>
        <button className="primary" disabled={busy||!csrf}>{id?'补充要求（已有计划将失效）':'创建协作会话'}</button></form>}
      {state?.status==='DRAFT'&&<div>
        <p>已启动讨论 {state.discussion_rounds||0} / 2 轮；第二轮仍需手动确认。</p>
        <label><input type="checkbox" checked={consent} onChange={e=>setConsent(e.target.checked)}/>允许本次规划讨论调用 DSH、Codex，最多 3 次应用层任务；不自动执行实现</label>
        <button disabled={busy||!enabled||!consent} onClick={()=>write('/'+id+'/discuss',{confirm_model_calls:true})}>开始团队讨论</button>
      </div>}
      {state?.status==='AWAITING_CONFIRMATION'&&<div>
        <h3>请审阅执行计划</h3><pre>{plan?.content}</pre>
        <button onClick={()=>{setPlanText(plan?.content||'');setEditing(!editing);}}>修改计划</button>
        {editing&&<><textarea aria-label="编辑计划 JSON" value={planText} rows={10} onChange={e=>setPlanText(e.target.value)}/>
          <button disabled={busy} onClick={async()=>{try{if(await write('/'+id+'/plan',{plan_id:state.plan_id,plan:JSON.parse(planText)}))setEditing(false);}catch{setError('计划必须是有效 JSON');}}}>保存计划修改</button></>}
        <label><input type="checkbox" checked={codeConsent} onChange={e=>setCodeConsent(e.target.checked)}/>确认当前计划，允许 Codex 在独立工作目录写代码和运行测试，再由 DSH 审核；最多 5 次调用</label>
        <button className="primary" disabled={busy||!enabled||!codeConsent||editing}
          onClick={()=>write('/'+id+'/execute',{confirm_model_calls:true,confirm_code_execution:true,plan_id:state.plan_id})}>确认计划并执行</button>
      </div>}
      {state&&!['COMPLETED','FAILED','CANCELLED','CHANGES_REQUESTED'].includes(state.status)&&
        <button disabled={busy} onClick={()=>write('/'+id+'/cancel',{})}>{active?'取消当前运行':'取消会话'}</button>}
      <p className="footnote">串行受控调度，无自动重试。取消尽力终止底层调用，不撤销已写文件。SDK 内部请求次数未知；不支持进程中断后的自动恢复执行。</p>
    </section>
    <aside className="panel conversation-results"><h2>分工与交付</h2>
      <p>DSH：讨论 / 规划 / 审核<br/>Codex：质疑 / 实现 / 测试<br/>WorkBuddy：不可参与真实执行</p>
      {plan&&<details open><summary>批准前的计划与依赖</summary><pre>{plan.content}</pre></details>}
      {(data?.tasks||[]).map(t=><article key={t.id}><strong>{t.assigned_to} · {t.task_type}</strong><p>{t.status} · {t.id.slice(0,8)}</p></article>)}
      <h3>产物引用</h3>{(data?.artifacts||[]).map(a=><p key={a.id}>{a.path}<small>SHA-256 {a.sha256}</small></p>)}
      {state?.review&&<><h3>最终审核：{state.review}</h3><pre>{data.decisions.find(d=>d.id===state.review_id)?.content}</pre>
        <p>审核引用实际文件及命令执行证据；宿主没有独立复跑测试。</p></>}
    </aside>
  </div>;
}
