import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Activity, AlertTriangle, BarChart3, Bell, BookOpen, CheckCircle2, ChevronRight,
  Cloud, Database, GraduationCap, LayoutDashboard, LogOut, Menu, Search, Server,
  ShieldCheck, Sparkles, Users, X
} from 'lucide-react';
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import './styles.css';

// In production the API address MUST come from VITE_API_URL (set in Vercel).
// The localhost fallback is only used while developing on your own laptop.
const API = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000/api/v1' : '');

async function request(path, options = {}) {
  if (!API) throw new Error('Backend URL is not configured (VITE_API_URL is missing in this deployment).');
  const token = localStorage.getItem('ss_token');
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers }
  });
  if (response.status === 401) {
    localStorage.removeItem('ss_token');
    localStorage.removeItem('ss_user');
    throw new Error('Your session expired. Please sign in again.');
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || 'Something went wrong');
  return body;
}

const roles = [
  { label: 'Administrator', email: 'admin@studentsphere.edu', password: 'Admin@123' },
  { label: 'Teacher', email: 'teacher@studentsphere.edu', password: 'Teacher@123' },
  { label: 'Student', email: 'student@studentsphere.edu', password: 'Student@123' }
];

function Login({ onLogin }) {
  const [form, setForm] = useState({ email: roles[0].email, password: roles[0].password });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function submit(event) {
    event.preventDefault(); setLoading(true); setError('');
    try {
      const data = await request('/auth/login', { method: 'POST', body: JSON.stringify(form) });
      localStorage.setItem('ss_token', data.access_token);
      localStorage.setItem('ss_user', JSON.stringify(data.user));
      onLogin(data.user);
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }

  return <main className="login-shell">
    <section className="login-story">
      <div className="brand"><span className="brand-mark"><GraduationCap size={24}/></span><span>StudentSphere</span><b>Cloud</b></div>
      <div className="story-copy">
        <span className="eyebrow"><Sparkles size={15}/> Cloud-native campus intelligence</span>
        <h1>Turn student data into <span>timely action.</span></h1>
        <p>A secure academic operations platform for attendance, performance analytics, course capacity, and early-risk intervention.</p>
        <div className="feature-strip">
          <div><ShieldCheck/><span><b>Role-based access</b><small>Admin, teacher and student portals</small></span></div>
          <div><Activity/><span><b>Observable by design</b><small>Metrics, health probes and audit trails</small></span></div>
          <div><Cloud/><span><b>Ready to scale</b><small>Containers, CI/CD and Kubernetes</small></span></div>
        </div>
      </div>
      <p className="story-foot">Built for modern institutions · Version 2.0</p>
    </section>
    <section className="login-panel">
      <form className="login-card" onSubmit={submit}>
        <div className="mobile-brand brand"><span className="brand-mark"><GraduationCap size={21}/></span><span>StudentSphere</span><b>Cloud</b></div>
        <span className="secure"><ShieldCheck size={16}/> Secure portal</span>
        <h2>Welcome back</h2><p>Sign in to your academic workspace.</p>
        <label>Email address<input type="email" value={form.email} onChange={e=>setForm({...form,email:e.target.value})} required /></label>
        <label>Password<input type="password" value={form.password} onChange={e=>setForm({...form,password:e.target.value})} required /></label>
        {error && <div className="error"><AlertTriangle size={16}/>{error}</div>}
        <button className="primary" disabled={loading}>{loading ? 'Signing in…' : 'Sign in securely'}<ChevronRight size={18}/></button>
        <div className="divider"><span>Demo access</span></div>
        <div className="demo-roles">{roles.map(role=><button type="button" key={role.label} onClick={()=>setForm({email:role.email,password:role.password})}>{role.label}</button>)}</div>
      </form>
    </section>
  </main>;
}

const navItems = [
  ['Overview', LayoutDashboard], ['Students', Users], ['Courses', BookOpen], ['Insights', Sparkles], ['Cloud status', Cloud]
];

function StatCard({ icon: Icon, label, value, note, tone }) {
  return <article className="stat-card"><div className={`stat-icon ${tone}`}><Icon/></div><div><span>{label}</span><strong>{value}</strong><small>{note}</small></div></article>;
}

function StatusDot({ ok = true }) { return <span className={`status-dot ${ok ? 'ok' : ''}`}></span>; }

function Dashboard({ user, onLogout }) {
  const [page, setPage] = useState('Overview');
  const [mobileOpen, setMobileOpen] = useState(false);
  const [dashboard, setDashboard] = useState(null);
  const [students, setStudents] = useState([]);
  const [courses, setCourses] = useState([]);
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([request('/dashboard'), request('/students'), request('/courses'), request('/insights')])
      .then(([d,s,c,i])=>{setDashboard(d);setStudents(s);setCourses(c);setInsights(i.items);})
      .catch(err=>setError(err.message)).finally(()=>setLoading(false));
  }, []);

  function logout(){localStorage.clear();onLogout();}
  const k = dashboard?.kpis || { students: 0, courses: 0, attendanceRate: 0, atRisk: 0 };
  const riskData = useMemo(()=>[
    {name:'On track',value:Math.max(k.students-k.atRisk,0),color:'#26d69b'},
    {name:'Needs attention',value:k.atRisk,color:'#ffb454'}
  ],[k]);

  return <div className="app-shell">
    <aside className={`sidebar ${mobileOpen?'open':''}`}>
      <div className="brand"><span className="brand-mark"><GraduationCap size={22}/></span><span>StudentSphere</span><b>Cloud</b></div>
      <button className="close-mobile" onClick={()=>setMobileOpen(false)}><X/></button>
      <nav>{navItems.map(([name,Icon])=><button key={name} className={page===name?'active':''} onClick={()=>{setPage(name);setMobileOpen(false)}}><Icon size={19}/>{name}</button>)}</nav>
      <div className="cloud-mini"><div><Cloud size={18}/><b>Cloud operations</b></div><p><StatusDot/>All systems operational</p><small>Last checked just now</small></div>
      <div className="profile"><div className="avatar">{user.name.split(' ').map(x=>x[0]).slice(0,2).join('')}</div><span><b>{user.name}</b><small>{user.role}</small></span><button onClick={logout} title="Sign out"><LogOut size={18}/></button></div>
    </aside>
    {mobileOpen && <div className="scrim" onClick={()=>setMobileOpen(false)} />}
    <main className="workspace">
      <header><button className="menu" onClick={()=>setMobileOpen(true)}><Menu/></button><div><span className="breadcrumb">Workspace / {page}</span><h1>{page}</h1></div><div className="header-actions"><button><Search size={19}/></button><button className="bell"><Bell size={19}/><i/></button><span className="role-pill"><ShieldCheck size={16}/>{user.role}</span></div></header>
      {loading ? <div className="loading"><div className="spinner"/>Loading cloud workspace…</div> : error ? <div className="page-error"><AlertTriangle/>{error}<button onClick={logout}>Sign in again</button></div> :
      <section className="content">
        {page==='Overview' && <Overview k={k} dashboard={dashboard} students={students} riskData={riskData}/>} 
        {page==='Students' && <Students students={students}/>} 
        {page==='Courses' && <Courses courses={courses}/>} 
        {page==='Insights' && <Insights items={insights}/>} 
        {page==='Cloud status' && <CloudStatus cloud={dashboard.cloud}/>} 
      </section>}
    </main>
  </div>;
}

function Overview({ k, dashboard, students, riskData }) {
  return <>
    <div className="welcome"><div><span className="eyebrow">Academic command center</span><h2>Good to see you. Here’s what needs attention.</h2><p>Live operational view across student engagement and platform health.</p></div><span className="live"><StatusDot/>Live data</span></div>
    <div className="stats-grid">
      <StatCard icon={Users} label="Active students" value={k.students} note="Across all departments" tone="purple"/>
      <StatCard icon={BookOpen} label="Running courses" value={k.courses} note="Current semester" tone="blue"/>
      <StatCard icon={CheckCircle2} label="Attendance rate" value={`${k.attendanceRate}%`} note="Institution average" tone="green"/>
      <StatCard icon={AlertTriangle} label="At-risk students" value={k.atRisk} note="Intervention recommended" tone="orange"/>
    </div>
    <div className="grid-2">
      <article className="panel"><div className="panel-title"><div><h3>Students by department</h3><p>Current enrolment distribution</p></div><BarChart3 size={20}/></div><div className="chart"><ResponsiveContainer width="100%" height={245}><BarChart data={dashboard.departments}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e6eaf0"/><XAxis dataKey="name" tickLine={false} axisLine={false}/><YAxis tickLine={false} axisLine={false}/><Tooltip cursor={{fill:'#f4f1ff'}}/><Bar dataKey="students" fill="#7157e8" radius={[7,7,0,0]} barSize={42}/></BarChart></ResponsiveContainer></div></article>
      <article className="panel"><div className="panel-title"><div><h3>Student success pulse</h3><p>Risk model based on attendance and grades</p></div><Sparkles size={20}/></div><div className="risk-wrap"><ResponsiveContainer width="55%" height={220}><PieChart><Pie data={riskData} dataKey="value" innerRadius={62} outerRadius={88} paddingAngle={5}>{riskData.map(row=><Cell key={row.name} fill={row.color}/>)}</Pie><Tooltip/></PieChart></ResponsiveContainer><div className="risk-legend">{riskData.map(x=><div key={x.name}><StatusDot ok={x.name==='On track'}/><span>{x.name}<b>{x.value}</b></span></div>)}</div></div></article>
    </div>
    <div className="grid-2 lower">
      <article className="panel"><div className="panel-title"><div><h3>Priority students</h3><p>Highest calculated intervention risk</p></div><button className="text-btn">View all <ChevronRight size={16}/></button></div><div className="priority-list">{students.slice().sort((a,b)=>b.risk_score-a.risk_score).slice(0,4).map(s=><div key={s.id}><div className="avatar soft">{s.name.split(' ').map(x=>x[0]).join('')}</div><span><b>{s.name}</b><small>{s.roll_number} · Semester {s.semester}</small></span><em className={s.risk_score>=30?'high':''}>{s.risk_score}% risk</em></div>)}</div></article>
      <article className="panel"><div className="panel-title"><div><h3>Recent audit activity</h3><p>Traceable operations across the platform</p></div><Activity size={20}/></div><div className="activity-list">{dashboard.activity.slice(0,5).map((a,i)=><div key={i}><span className="activity-icon"><CheckCircle2/></span><span><b>{a.action.replaceAll('.',' ')}</b><small>{a.detail}</small></span><time>{new Date(a.at).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}</time></div>)}</div></article>
    </div>
  </>;
}

function Students({students}) {
  const [query,setQuery]=useState('');
  const rows=students.filter(s=>`${s.name} ${s.roll_number} ${s.department}`.toLowerCase().includes(query.toLowerCase()));
  return <article className="panel full"><div className="table-head"><div><h3>Student directory</h3><p>Academic profile, cohort and early-risk indicator</p></div><div className="search-box"><Search size={17}/><input placeholder="Search students" value={query} onChange={e=>setQuery(e.target.value)}/></div></div><div className="table-wrap"><table><thead><tr><th>Student</th><th>Roll number</th><th>Department</th><th>Semester</th><th>Risk status</th></tr></thead><tbody>{rows.map(s=><tr key={s.id}><td><div className="person"><div className="avatar soft">{s.name.split(' ').map(x=>x[0]).join('')}</div><span><b>{s.name}</b><small>{s.email}</small></span></div></td><td>{s.roll_number}</td><td>{s.department}</td><td>Semester {s.semester}</td><td><span className={`risk-tag ${s.risk_score>=30?'high':''}`}>{s.risk_score<20?'On track':'Review'} · {s.risk_score}%</span></td></tr>)}</tbody></table></div></article>;
}

function Courses({courses}) { return <div className="course-grid">{courses.map(c=><article className="course-card" key={c.id}><div className="course-top"><span>{c.code}</span><BookOpen/></div><h3>{c.title}</h3><p>{c.credits} credits · Capacity {c.capacity}</p><div className="capacity"><div><span style={{width:`${Math.min(100,c.enrolled/c.capacity*100)}%`}}/></div><small>{c.enrolled} students enrolled</small></div><button>Open course workspace <ChevronRight size={17}/></button></article>)}</div>; }

function Insights({items}) { return <><div className="welcome compact"><div><span className="eyebrow"><Sparkles size={14}/> Automated analytics</span><h2>Early-intervention insights</h2><p>Explainable risk indicators calculated from attendance and assessment trends.</p></div></div><div className="insight-list">{items.map((item,i)=><article key={i} className={`insight ${item.severity}`}><span><AlertTriangle/></span><div><em>{item.severity} priority</em><h3>{item.title}</h3><p>{item.message}</p></div><button>Review student <ChevronRight size={16}/></button></article>)}</div></>; }

function CloudStatus({cloud}) { const services=[['Frontend edge','Online','Global CDN',Server],['FastAPI service',cloud.api,'Container workload',Activity],['PostgreSQL',cloud.database,'Managed database',Database],['Prometheus',cloud.metrics,'Metrics pipeline',BarChart3]]; return <><div className="welcome compact"><div><span className="eyebrow"><Cloud size={14}/> Platform operations</span><h2>All cloud systems are operational</h2><p>Deployment readiness, infrastructure health and observability signals.</p></div><span className="live"><StatusDot/>Operational</span></div><div className="cloud-grid">{services.map(([name,status,note,Icon])=><article key={name}><span><Icon/></span><div><h3>{name}</h3><p>{note}</p></div><em><StatusDot/>{status}</em></article>)}</div><article className="panel architecture"><h3>Cloud-native capabilities</h3><div><span><CheckCircle2/>Docker multi-container runtime</span><span><CheckCircle2/>Kubernetes health probes and autoscaling</span><span><CheckCircle2/>GitHub Actions CI/CD quality gates</span><span><CheckCircle2/>Prometheus metrics and Grafana dashboards</span><span><CheckCircle2/>Stateless JWT authentication and RBAC</span><span><CheckCircle2/>External PostgreSQL with connection checks</span></div></article></>; }

function App() {
  const [user,setUser]=useState(()=>{try{return JSON.parse(localStorage.getItem('ss_user'))}catch{return null}});
  return user ? <Dashboard user={user} onLogout={()=>setUser(null)}/> : <Login onLogin={setUser}/>;
}

createRoot(document.getElementById('root')).render(<React.StrictMode><App/></React.StrictMode>);

