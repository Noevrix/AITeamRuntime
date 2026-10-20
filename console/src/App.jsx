import React, {useEffect, useState} from 'react';

const pages = [
  ['overview','◈','团队总览','Team Overview'],['tasks','▤','任务面板','Task Board'],
  ['agents','◎','Agent 管理','Agent Management'],['timeline','⌁','协作时间线','Workflow Timeline'],
  ['blackboard','▦','共享黑板','Blackboard Explorer'],['settings','⚙','设置与诊断','Settings & Diagnostics'],
];
const names = {PENDING:'待处理',ASSIGNED:'已分配',RUNNING:'运行中',REVIEW:'待审核',
  COMPLETED:'已完成',FAILED:'失败',CANCELLED:'已取消',ESCALATED:'需要关注',CHANGES_REQUESTED:'要求修改'};
const label = v => names[v] || v || '无记录';
const short = v => v ? String(v).slice(0,8) : '无记录';
const time = v => v ? new Date(v).toLocaleString('zh-CN',{hour12:false}) : '无记录';
const text = v => typeof v === 'string' ? v : JSON.stringify(v, null, 2);
export function modeOf(record) {
  const value=record?.metadata?.mock;
  return value===true ? 'MOCK' : value===false ? 'REAL_OUTPUT' : 'UNKNOWN';
}
function Badge({value}) {return <span className={`badge ${['REAL_VERIFIED','COMPLETED','APPROVE','MATCH'].includes(value)?'good':['FAILED','AUTH_REQUIRED','MISMATCH'].includes(value)?'bad':['MOCK','PARTIAL','ESCALATED','COMPLETION_UNCONFIRMED'].includes(value)?'warn':''}`}>{label(value)}</span>;}
function Empty({message='暂无记录'}) {return <div className="empty"><span>◇</span><strong>{message}</strong><p>这里只显示已持久化的数据，不生成演示记录。</p></div>;}
async function api(path, options={}) {
  const response=await fetch('/api/'+path,{credentials:'same-origin',...options});
  if (!response.ok) throw new Error((await response.json()).error || 'REQUEST_FAILED');
  return response.json();
}
function JsonView({value}) {return <pre className="json">{text(value) || '无记录'}</pre>;}

export default function App() {
  const [page,setPage]=useState('overview'), [overview,setOverview]=useState(null);
  const [run,setRun]=useState(''), [snapshot,setSnapshot]=useState(null),[error,setError]=useState('');
  const [busy,setBusy]=useState(false),[detail,setDetail]=useState(null),[status,setStatus]=useState('ALL');
  const [agentFilter,setAgentFilter]=useState('ALL'),[collection,setCollection]=useState('decisions');
  const [draft,setDraft]=useState(false),[saved,setSaved]=useState(''),[diagnostics,setDiagnostics]=useState(null);
  const [csrf,setCsrf]=useState(''),[refresh,setRefresh]=useState(0);
  useEffect(()=>{let alive=true; Promise.all([api('session'),api('overview')]).then(([s,o])=>{
    if(alive){setCsrf(s.csrf);setOverview(o);setRun(current=>current || o.runs[0]?.id || '');}
  }).catch(()=>{if(alive)setError('无法读取本地数据，请检查后端服务。');}); return ()=>{alive=false;};},[refresh]);
  useEffect(()=>{let alive=true;setSnapshot(null);setDetail(null);
    if(run)api('runs/'+run).then(v=>{if(alive)setSnapshot(v);}).catch(()=>{if(alive)setError('运行记录读取失败，后端任务未被修改。');});
    return ()=>{alive=false;};},[run,refresh]);
  useEffect(()=>{if(page==='settings')api('diagnostics').then(setDiagnostics).catch(()=>setError('诊断信息不可用。'));},[page,refresh]);
  const tables=snapshot?.tables || {}, tasks=tables.tasks || [], events=tables.events || [];
  const messages=tables.messages || [], agentNames=Object.fromEntries((tables.agents||[]).map(a=>[a.id,a.name]));
  const current=pages.find(p=>p[0]===page), counts=overview?.counts || {};
  const go=p=>{setPage(p);setDetail(null);};
  const showTask=async id=>{try{setDetail({kind:'task',data:await api(`runs/${run}/tasks/${id}`)});}catch{setError('任务不存在或无法读取。');}};
  const showRecord=(kind,record)=>setDetail({kind,data:record});
  const verifyHash=async artifact=>{
    try{setDetail({kind:'哈希核验',data:{artifact,...await api(`runs/${run}/artifacts/${artifact.id}/hash`)}});}
    catch{setError('产物不可访问：仅允许受控工作目录内的安全引用。');}
  };
  const latest=events.slice().sort((a,b)=>(b.timestamp||'').localeCompare(a.timestamp||''));
  const actor=e=>tasks.find(t=>t.id===e.task_id)?.assigned_to;
  const eventMode=e=>modeOf(messages.find(m=>m.id===e.metadata?.message_id));

  return <div className="shell">
    <aside className="sidebar"><div className="brand"><span className="brandmark">a<span>t</span></span><div>AI TEAM<span>RUNTIME CONSOLE</span></div></div>
      <div className="workspace"><i/>本地工作空间 <span>⌄</span><small>AITeamRuntime</small></div>
      <div className="nav-label">WORKSPACE</div>
      <nav>{pages.map(([id,icon,title])=><button key={id} className={page===id?'selected':''} onClick={()=>go(id)}><span>{icon}</span>{title}{page===id&&<i/>}</button>)}</nav>
      <div className="sidebar-foot"><span className="local-dot"/> LOCAL ONLY<p>模型执行已禁用<br/>打开或刷新不会产生模型调用</p><div>v0.2.2 <span>Windows Console</span></div></div>
    </aside>
    <div className="main">
      <header className="topbar"><div><span className="crumb">WORKSPACE</span><span className="slash">/</span>{current[2]}</div><div className="top-actions"><span className="local-pill">◉ 本地数据</span><button title="只读刷新" onClick={()=>{setError('');setRefresh(v=>v+1);}}>↻ 刷新</button></div></header>
      <main><div className="page-heading"><div><div className="eyebrow">{current[3].toUpperCase()}</div><h1>{current[2]}</h1><p>每一次协作都有迹可循。</p></div><button className="primary" onClick={()=>{setDraft(true);setSaved('');}}>＋ 创建草稿</button></div>
        {error&&<div role="alert" className="alert">{error}<button onClick={()=>setError('')}>关闭</button></div>}
        {saved&&<div role="status" className="notice">{saved}</div>}
        <div className="runbar"><span>运行记录</span><select aria-label="运行记录" value={run} onChange={e=>setRun(e.target.value)}><option value="">选择记录</option>{overview?.runs.map(r=><option key={r.id} value={r.id}>{r.name} {r.database_status!=='READABLE'?'· 不可读':''}</option>)}</select><span className="subtle">{snapshot?.truncated.length ? '部分集合超过 1000 条，当前为最新窗口' : '只读历史 · 草稿独立保存'}</span></div>

        {page==='overview'&&<>
          <div className="stats">{[['团队成员',overview?.agents.length||0,'AGENTS'],['已完成',counts.COMPLETED||0,'COMPLETED'],['运行中',counts.RUNNING||0,'RUNNING'],['待处理',(counts.PENDING||0)+(counts.ASSIGNED||0),'PENDING'],['失败',counts.FAILED||0,'FAILED']].map(([name,n,hint])=><div className="stat" key={name}><span>{name}</span><strong>{n.toString().padStart(2,'0')}</strong><small>{hint}</small></div>)}</div>
          <section><div className="section-head"><h2>你的 AI 团队 <span>03 / ROLES</span></h2><button className="text-button" onClick={()=>go('agents')}>管理 Agent ↗</button></div>
          <div className="agent-grid">{overview?.agents.map((a,i)=><button className="agent-card" key={a.id} onClick={()=>{go('agents');showRecord('agent',a);}}><div className="agent-top"><span className={'avatar avatar-'+i}>{a.id==='WorkBuddy'?'W':a.id[0]}</span><span className="agent-index">0{i+1}</span></div><h3>{a.id}</h3><p>{a.role}</p><Badge value={a.status}/>{a.id==='WorkBuddy'&&<Badge value={a.authorization}/>}<div className="agent-bottom">实时在线 <span>未探测</span></div></button>)}</div>
          <div className="flow-caption"><span>01 规划</span><i>→</i><span>02 实现与测试</span><i>→</i><span>03 独立审核</span><small>角色分工 · 非当前执行状态</small></div></section>
          <div className="two-col"><section className="panel"><div className="section-head"><h2>最近事件</h2><button className="text-button" onClick={()=>go('timeline')}>全部 ↗</button></div>{latest.length?latest.slice(0,5).map(e=><button className="event-mini" key={e.id} onClick={()=>showRecord('event',e)}><span className="event-dot"/><div><strong>{e.type}</strong><small>{time(e.timestamp)} · {short(e.task_id)}</small></div><Badge value={eventMode(e)}/></button>):<Empty message="当前运行没有事件"/>}</section>
          <section className="panel"><div className="section-head"><h2>最近产物</h2><span className="subtle">已登记引用</span></div>{tables.artifacts?.length?tables.artifacts.slice(0,5).map(a=><button className="artifact-row" key={a.id} onClick={()=>verifyHash(a)}><span className="file-icon">⌘</span><div><strong>{a.path}</strong><small>SHA-256 · {short(a.sha256)}…</small></div><span>↗</span></button>):<Empty message="当前运行没有产物"/>}</section></div>
          <section className="panel"><h2>最近工作流</h2><div className="run-list">{overview?.runs.slice(0,5).map(r=><button key={r.id} onClick={()=>{setRun(r.id);go('timeline');}}><strong>{r.name}</strong><span>{time(r.last_event)}</span><Badge value={r.database_status}/></button>)}</div></section>
        </>}

        {page==='tasks'&&<section className="panel"><div className="section-head"><h2>任务 <span>{tasks.length}</span></h2><div className="filters"><select aria-label="任务状态" value={status} onChange={e=>setStatus(e.target.value)}><option value="ALL">所有状态</option>{Object.entries(names).map(([v,t])=><option key={v} value={v}>{t}</option>)}</select><select aria-label="任务 Agent" value={agentFilter} onChange={e=>setAgentFilter(e.target.value)}><option value="ALL">所有 Agent</option>{[...new Set(tasks.map(t=>t.assigned_to).filter(Boolean))].map(a=><option key={a}>{a}</option>)}</select></div></div>
          <div className="table-wrap"><table><thead><tr><th>任务 / ID</th><th>Agent</th><th>阶段</th><th>状态</th><th>更新</th><th>返工</th></tr></thead><tbody>{tasks.filter(t=>(status==='ALL'||t.status===status)&&(agentFilter==='ALL'||t.assigned_to===agentFilter)).map(t=><tr key={t.id}><td><button className="task-link" onClick={()=>showTask(t.id)}>{t.title}<small>{short(t.id)}</small></button></td><td>{agentNames[t.assigned_to]||t.assigned_to||'无记录'}</td><td>{t.task_type||'无记录'}</td><td><Badge value={t.status}/></td><td>{time(t.updated_at)}</td><td>{t.revision_count??'无记录'}</td></tr>)}</tbody></table></div>{!tasks.filter(t=>(status==='ALL'||t.status===status)&&(agentFilter==='ALL'||t.assigned_to===agentFilter)).length&&<Empty message="没有符合筛选条件的任务"/>}<p className="footnote">草稿状态为 PENDING。本版本没有执行、重试或取消模型任务的 API。</p></section>}

        {page==='agents'&&<div className="agent-detail-grid">{overview?.agents.map((a,i)=><section className="panel" key={a.id}><div className="section-head"><div className="agent-title"><span className={'avatar avatar-'+i}>{a.id[0]}</span><h2>{a.id}<small>{a.role}</small></h2></div><Badge value={a.status}/></div><dl><dt>实时在线</dt><dd>UNKNOWN · 未调用 Provider</dd><dt>授权状态</dt><dd><Badge value={a.authorization}/></dd><dt>默认模式</dt><dd>{a.default_mode}</dd></dl><div className="chips">{a.capabilities.map(c=><span key={c}>{c}</span>)}</div><p className="agent-note">{a.limits}</p><h4>历史验证依据</h4>{a.evidence.length?a.evidence.map(e=><button className="reference" key={e.message_id} onClick={()=>{setRun(e.run_id);go('tasks');}}>{e.result} · {short(e.task_id)} <small>{time(e.time)}</small></button>):<p className="subtle">无真实模型验收证据</p>}<button className="secondary" onClick={()=>showRecord('agent',a)}>关联任务、失败与配置详情 ↗</button></section>)}</div>}

        {page==='timeline'&&<section className="panel"><div className="section-head"><h2>事件轨迹</h2><span className="subtle">{events.length} 条已记录事件</span></div><p className="footnote">UNKNOWN 表示未记录 Mock/真实标记；不依据报告推断事件。点击查看引用。</p><div className="timeline">{events.slice().sort((a,b)=>(a.timestamp||'').localeCompare(b.timestamp||'')).map(e=><button className="timeline-item" key={e.id} onClick={()=>showRecord('event',e)}><time>{time(e.timestamp)}</time><span className="timeline-node"/><div><strong>{e.type}</strong><p>{actor(e)||'Agent 无记录'} · {tasks.find(t=>t.id===e.task_id)?.task_type||'阶段无记录'} · {short(e.task_id)}</p></div><Badge value={eventMode(e)}/></button>)}</div>{!events.length&&<Empty message="没有已持久化的事件"/>}</section>}

        {page==='blackboard'&&<section className="panel"><div className="section-head"><h2>Blackboard</h2><span className="subtle">原始记录 · 不自动解释为验收通过</span></div><div className="tabs">{[['projects','项目'],['tasks','任务'],['messages','Agent 消息'],['decisions','规划 / 决策'],['artifacts','产物引用']].map(([v,t])=><button key={v} className={collection===v?'active':''} onClick={()=>setCollection(v)}>{t} <span>{tables[v]?.length||0}</span></button>)}</div>{tables[collection]?.length?<div className="records">{tables[collection].map(r=><button key={r.id} className="record" onClick={()=>showRecord(collection,r)}><div><span className="record-icon">▧</span><strong>{r.title||r.path||r.type||short(r.id)}</strong>{collection==='messages'&&<Badge value={modeOf(r)}/>}</div><p>{String(r.goal||r.content||r.description||r.sha256||'无内容摘要').slice(0,180)}</p><small>{short(r.id)} · {time(r.created_at||r.timestamp)} · 任务 {short(r.task_id)}</small></button>)}</div>:<Empty/>}</section>}

        {page==='settings'&&<section className="panel"><h2>本地诊断</h2><p className="footnote">仅检查配置存在性与历史数据，不联网、不启动模型、不授权。</p>{diagnostics?<><dl><dt>数据目录</dt><dd>{diagnostics.data_directory}</dd><dt>SQLite</dt><dd>{diagnostics.sqlite}</dd><dt>模型执行 / OAuth</dt><dd>DISABLED / DISABLED</dd></dl><h3>Provider 配置</h3>{diagnostics.agents.map(a=><div className="config-row" key={a.id}><strong>{a.id}</strong><Badge value={a.authorization}/><button onClick={()=>showRecord('配置检查',a.configuration)}>查看非敏感结果 ↗</button></div>)}<h3>诊断报告与测试记录</h3><p className="subtle">{diagnostics.test_note}</p><div className="report-list">{diagnostics.reports.map(r=><button key={r.id} disabled={!r.exists} onClick={()=>api('reports/'+r.id).then(d=>showRecord('报告',d)).catch(()=>setError('报告不可用'))}>{r.name}<span>{r.exists?'读取 ↗':'尚未生成'}</span></button>)}</div><p>日志和运行记录：从上方选择运行记录，再进入任务、时间线或黑板。不提供任意文件读取。</p></>:<Empty message="正在读取诊断"/>}</section>}
        <footer>AI TEAM RUNTIME <span>所有状态来自本地持久化记录 · 缺失字段显示“无记录”</span></footer>
      </main>
    </div>
    {detail&&<aside className="drawer"><div className="drawer-head"><span>记录详情 / {detail.kind}</span><button aria-label="关闭详情" onClick={()=>setDetail(null)}>✕</button></div>
      {detail.kind==='task'?<><h2>{detail.data.task.title}</h2><Badge value={detail.data.task.status}/><dl><dt>创建时间</dt><dd>{time(detail.data.task.created_at)}</dd><dt>应用层任务次数</dt><dd>{detail.data.application_attempts}</dd><dt>重试次数</dt><dd>{detail.data.retry_count??'无记录'}</dd><dt>返工次数</dt><dd>{detail.data.revision_count}</dd></dl><h3>输入</h3><JsonView value={detail.data.task.description}/><h3>消息与输出</h3>{detail.data.messages.map(m=><div key={m.id} className="detail-record"><Badge value={m.type}/><Badge value={modeOf(m)}/><JsonView value={m.content}/></div>)}<h3>明确关联的 Blackboard 决策</h3><JsonView value={detail.data.decisions}/><h3>产物</h3>{detail.data.artifacts.map(a=><button className="reference" key={a.id} onClick={()=>verifyHash(a)}>{a.path} · 核验哈希 ↗</button>)}<h3>事件与失败原因</h3><JsonView value={detail.data.events}/></>:
      <><JsonView value={detail.data}/>{detail.data.task_id&&<button className="secondary" onClick={()=>showTask(detail.data.task_id)}>打开关联任务 ↗</button>}{detail.kind==='event'&&detail.data.metadata?.decision_id&&<button className="secondary" onClick={()=>showRecord('decisions',(tables.decisions||[]).find(d=>d.id===detail.data.metadata.decision_id)||{note:'引用的决策未在当前窗口内'})}>打开决策引用 ↗</button>}{detail.kind==='artifacts'&&<button className="secondary" onClick={()=>verifyHash(detail.data)}>核验文件哈希</button>}</>}
      <p className="footnote">内容经过展示过滤。未知字段不会自动补全。</p></aside>}
    {draft&&<div className="modal-backdrop"><form className="modal" onSubmit={async e=>{e.preventDefault();if(busy)return;setBusy(true);const values=new FormData(e.currentTarget);
      try{const result=await api('drafts',{method:'POST',headers:{'Content-Type':'application/json','X-Console-CSRF':csrf},body:JSON.stringify({title:values.get('title'),description:values.get('description'),agent:values.get('agent'),request_id:values.get('request_id')})});setSaved('草稿已保存 · '+short(result.id)+' · 未触发任何模型');setDraft(false);setRefresh(v=>v+1);}
      catch{setError('草稿未确认保存。请检查记录后重试；不会执行模型。');}finally{setBusy(false);}
    }}><div className="section-head"><h2>创建任务草稿</h2><button type="button" onClick={()=>setDraft(false)}>✕</button></div><p>只保存到现有任务系统，状态为待处理。不会分配或执行模型。</p><DraftID/><label>标题<input name="title" aria-label="草稿标题" required maxLength={160} placeholder="例如：检查 TODO CLI 的边界行为"/></label><label>目标 Agent<select name="agent"><option>DSH</option><option>Codex</option><option>WorkBuddy</option></select></label><label>任务说明<textarea name="description" aria-label="任务说明" maxLength={8000} rows={5} placeholder="描述目标和验收标准。请勿填写密钥或私人凭证。"/></label><button className="primary" disabled={busy||!csrf}>{busy?'保存中…':'保存草稿'}</button></form></div>}
  </div>;
}
function DraftID(){const [id]=useState(()=>crypto.randomUUID().replaceAll('-',''));return <input type="hidden" name="request_id" value={id}/>;}
