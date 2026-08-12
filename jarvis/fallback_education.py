"""Education/School fallback app."""

_EDUCATION_APP = """import React,{useState} from 'react';
const courses=[
  {id:1,subject:"Mathematics",teacher:"Mr. Arjun Kumar",grade:"Grade 10",students:42,color:"#3b82f6",icon:"📐",progress:75},
  {id:2,subject:"Science",teacher:"Ms. Priya Sharma",grade:"Grade 10",students:38,color:"#10b981",icon:"🔬",progress:60},
  {id:3,subject:"English",teacher:"Mr. David Raj",grade:"Grade 10",students:45,color:"#8b5cf6",icon:"📚",progress:85},
  {id:4,subject:"History",teacher:"Ms. Anita Singh",grade:"Grade 9",students:36,color:"#f59e0b",icon:"🏛️",progress:50},
  {id:5,subject:"Computer Science",teacher:"Mr. Ravi Patel",grade:"Grade 11",students:30,color:"#ec4899",icon:"💻",progress:90},
  {id:6,subject:"Physics",teacher:"Ms. Kavya Nair",grade:"Grade 11",students:28,color:"#06b6d4",icon:"⚛️",progress:65},
];
const students=[
  {id:1,name:"Aisha Khan",grade:"10-A",marks:92,attendance:"95%",status:"Active"},
  {id:2,name:"Rahul Verma",grade:"10-B",marks:78,attendance:"88%",status:"Active"},
  {id:3,name:"Sneha Patel",grade:"11-A",marks:85,attendance:"92%",status:"Active"},
  {id:4,name:"Arjun Mehta",grade:"9-A",marks:71,attendance:"80%",status:"Warning"},
  {id:5,name:"Priya Reddy",grade:"10-A",marks:95,attendance:"99%",status:"Active"},
  {id:6,name:"Dev Sharma",grade:"11-B",marks:68,attendance:"75%",status:"Warning"},
];
const events=[
  {date:"May 5",title:"Science Exhibition",type:"Event"},
  {date:"May 10",title:"Math Olympiad",type:"Exam"},
  {date:"May 15",title:"Annual Sports Day",type:"Sports"},
  {date:"May 20",title:"Parent-Teacher Meeting",type:"Meeting"},
  {date:"May 25",title:"Final Exams Begin",type:"Exam"},
];
const stats=[
  {label:"Total Students",value:"1,248",icon:"👥",color:"#3b82f6"},
  {label:"Teachers",value:"64",icon:"👨‍🏫",color:"#10b981"},
  {label:"Courses",value:"32",icon:"📖",color:"#8b5cf6"},
  {label:"Avg Attendance",value:"91%",icon:"📊",color:"#f59e0b"},
];

export default function App(){
  const[page,setPage]=useState('dashboard');
  const[selCourse,setSelCourse]=useState(null);
  const[search,setSearch]=useState('');

  const filteredStudents=students.filter(s=>s.name.toLowerCase().includes(search.toLowerCase()));

  return(
    <div style={{fontFamily:"'Inter',sans-serif",display:'flex',minHeight:'100vh',background:'#f1f5f9'}}>
      {/* Sidebar */}
      <div style={{width:240,background:'#1e293b',color:'#fff',display:'flex',flexDirection:'column',position:'fixed',height:'100vh',zIndex:50}}>
        <div style={{padding:'24px 20px',borderBottom:'1px solid #334155'}}>
          <div style={{fontSize:22,fontWeight:900,color:'#6366f1'}}>🎓 EduPortal</div>
          <div style={{fontSize:12,color:'#94a3b8',marginTop:4}}>School Management System</div>
        </div>
        <nav style={{flex:1,padding:'16px 12px'}}>
          {[
            {key:'dashboard',icon:'🏠',label:'Dashboard'},
            {key:'courses',icon:'📚',label:'Courses'},
            {key:'students',icon:'👥',label:'Students'},
            {key:'schedule',icon:'📅',label:'Schedule'},
            {key:'events',icon:'🎯',label:'Events'},
          ].map(item=>(
            <button key={item.key} onClick={()=>setPage(item.key)} style={{width:'100%',display:'flex',alignItems:'center',gap:12,padding:'11px 14px',borderRadius:10,border:'none',cursor:'pointer',marginBottom:4,background:page===item.key?'#6366f1':'transparent',color:page===item.key?'#fff':'#94a3b8',fontWeight:page===item.key?600:400,fontSize:14,textAlign:'left',transition:'all .15s'}}>
              <span>{item.icon}</span>{item.label}
            </button>
          ))}
        </nav>
        <div style={{padding:'16px 20px',borderTop:'1px solid #334155'}}>
          <div style={{display:'flex',alignItems:'center',gap:10}}>
            <div style={{width:36,height:36,borderRadius:'50%',background:'#6366f1',display:'flex',alignItems:'center',justifyContent:'center',fontWeight:700}}>P</div>
            <div><div style={{fontSize:13,fontWeight:600}}>Principal Admin</div><div style={{fontSize:11,color:'#94a3b8'}}>Admin</div></div>
          </div>
        </div>
      </div>

      {/* Main */}
      <div style={{marginLeft:240,flex:1,padding:'32px 32px'}}>
        {/* Header */}
        <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:32}}>
          <div>
            <h1 style={{margin:0,fontSize:26,fontWeight:800,color:'#0f172a'}}>
              {page==='dashboard'&&'Dashboard Overview'}
              {page==='courses'&&'All Courses'}
              {page==='students'&&'Student Directory'}
              {page==='schedule'&&'Class Schedule'}
              {page==='events'&&'Upcoming Events'}
            </h1>
            <p style={{margin:'4px 0 0',color:'#64748b',fontSize:14}}>Academic Year 2025–2026</p>
          </div>
          <div style={{display:'flex',gap:12,alignItems:'center'}}>
            <div style={{background:'#fff',border:'1px solid #e2e8f0',borderRadius:20,padding:'8px 16px',fontSize:14,color:'#475569'}}>📅 April 29, 2026</div>
            <div style={{width:40,height:40,borderRadius:'50%',background:'#6366f1',display:'flex',alignItems:'center',justifyContent:'center',color:'#fff',fontWeight:700,cursor:'pointer'}}>P</div>
          </div>
        </div>

        {/* DASHBOARD */}
        {page==='dashboard'&&<>
          <div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:20,marginBottom:28}}>
            {stats.map((s,i)=>(
              <div key={i} style={{background:'#fff',borderRadius:16,padding:24,border:'1px solid #e2e8f0',boxShadow:'0 1px 3px rgba(0,0,0,.05)'}}>
                <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-start'}}>
                  <div>
                    <p style={{margin:'0 0 8px',fontSize:13,color:'#64748b',fontWeight:500}}>{s.label}</p>
                    <p style={{margin:0,fontSize:30,fontWeight:800,color:'#0f172a'}}>{s.value}</p>
                  </div>
                  <div style={{fontSize:28,background:s.color+'15',padding:10,borderRadius:12}}>{s.icon}</div>
                </div>
                <div style={{marginTop:16,height:4,background:'#f1f5f9',borderRadius:2}}>
                  <div style={{height:'100%',width:'70%',background:s.color,borderRadius:2}}/>
                </div>
              </div>
            ))}
          </div>
          <div style={{display:'grid',gridTemplateColumns:'2fr 1fr',gap:24}}>
            <div style={{background:'#fff',borderRadius:16,padding:24,border:'1px solid #e2e8f0'}}>
              <h3 style={{margin:'0 0 20px',fontSize:16,fontWeight:700,color:'#0f172a'}}>Course Progress</h3>
              {courses.slice(0,5).map(c=>(
                <div key={c.id} style={{marginBottom:16}}>
                  <div style={{display:'flex',justifyContent:'space-between',marginBottom:6}}>
                    <span style={{fontSize:14,fontWeight:500,color:'#334155'}}>{c.icon} {c.subject}</span>
                    <span style={{fontSize:13,color:'#64748b'}}>{c.progress}%</span>
                  </div>
                  <div style={{height:8,background:'#f1f5f9',borderRadius:4}}>
                    <div style={{height:'100%',width:c.progress+'%',background:c.color,borderRadius:4,transition:'width .6s ease'}}/>
                  </div>
                </div>
              ))}
            </div>
            <div style={{background:'#fff',borderRadius:16,padding:24,border:'1px solid #e2e8f0'}}>
              <h3 style={{margin:'0 0 16px',fontSize:16,fontWeight:700,color:'#0f172a'}}>Upcoming Events</h3>
              {events.map((e,i)=>(
                <div key={i} style={{display:'flex',gap:12,marginBottom:16,alignItems:'flex-start'}}>
                  <div style={{background:'#6366f115',color:'#6366f1',padding:'6px 10px',borderRadius:8,fontSize:11,fontWeight:700,whiteSpace:'nowrap'}}>{e.date}</div>
                  <div>
                    <p style={{margin:0,fontSize:13,fontWeight:600,color:'#334155'}}>{e.title}</p>
                    <p style={{margin:'2px 0 0',fontSize:11,color:'#94a3b8'}}>{e.type}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>}

        {/* COURSES */}
        {page==='courses'&&(!selCourse?<>
          <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(300px,1fr))',gap:20}}>
            {courses.map(c=>(
              <div key={c.id} onClick={()=>setSelCourse(c)} style={{background:'#fff',borderRadius:16,padding:24,border:'1px solid #e2e8f0',cursor:'pointer',transition:'all .2s',boxShadow:'0 1px 3px rgba(0,0,0,.05)'}} onMouseEnter={e=>{e.currentTarget.style.transform='translateY(-4px)';e.currentTarget.style.boxShadow='0 8px 24px rgba(0,0,0,.12)'}} onMouseLeave={e=>{e.currentTarget.style.transform='none';e.currentTarget.style.boxShadow='0 1px 3px rgba(0,0,0,.05)'}}>
                <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:16}}>
                  <div style={{fontSize:36}}>{c.icon}</div>
                  <span style={{background:c.color+'15',color:c.color,fontSize:12,fontWeight:700,padding:'4px 10px',borderRadius:12}}>{c.grade}</span>
                </div>
                <h3 style={{margin:'0 0 4px',fontSize:18,fontWeight:700,color:'#0f172a'}}>{c.subject}</h3>
                <p style={{margin:'0 0 16px',fontSize:13,color:'#64748b'}}>{c.teacher}</p>
                <div style={{display:'flex',justifyContent:'space-between',fontSize:13,color:'#94a3b8',marginBottom:12}}>
                  <span>👥 {c.students} students</span><span>{c.progress}% complete</span>
                </div>
                <div style={{height:6,background:'#f1f5f9',borderRadius:3}}>
                  <div style={{height:'100%',width:c.progress+'%',background:c.color,borderRadius:3}}/>
                </div>
              </div>
            ))}
          </div>
        </>:<div>
          <button onClick={()=>setSelCourse(null)} style={{background:'#6366f1',color:'#fff',border:'none',padding:'8px 20px',borderRadius:20,cursor:'pointer',marginBottom:24,fontWeight:600}}>← Back to Courses</button>
          <div style={{background:'#fff',borderRadius:16,padding:32,border:'1px solid #e2e8f0'}}>
            <div style={{display:'flex',gap:20,alignItems:'center',marginBottom:24}}>
              <div style={{fontSize:60}}>{selCourse.icon}</div>
              <div>
                <h2 style={{margin:0,fontSize:28,fontWeight:800,color:'#0f172a'}}>{selCourse.subject}</h2>
                <p style={{margin:'4px 0',color:'#64748b'}}>{selCourse.teacher} • {selCourse.grade}</p>
                <span style={{background:selCourse.color+'15',color:selCourse.color,fontSize:12,fontWeight:700,padding:'4px 12px',borderRadius:12}}>Active Course</span>
              </div>
            </div>
            <div style={{display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:16,marginBottom:24}}>
              {[{l:'Students Enrolled',v:selCourse.students},{l:'Completion',v:selCourse.progress+'%'},{l:'Weekly Hours',v:'5 hrs'}].map((s,i)=>(
                <div key={i} style={{background:'#f8fafc',borderRadius:12,padding:16,textAlign:'center'}}>
                  <p style={{margin:0,fontSize:24,fontWeight:800,color:'#0f172a'}}>{s.v}</p>
                  <p style={{margin:'4px 0 0',fontSize:12,color:'#64748b'}}>{s.l}</p>
                </div>
              ))}
            </div>
            <h3 style={{margin:'0 0 12px',fontSize:16,fontWeight:700}}>Overall Progress</h3>
            <div style={{height:12,background:'#f1f5f9',borderRadius:6}}>
              <div style={{height:'100%',width:selCourse.progress+'%',background:selCourse.color,borderRadius:6}}/>
            </div>
          </div>
        </div>)}

        {/* STUDENTS */}
        {page==='students'&&<>
          <div style={{background:'#fff',borderRadius:16,padding:24,border:'1px solid #e2e8f0'}}>
            <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:24}}>
              <h3 style={{margin:0,fontSize:16,fontWeight:700}}>All Students ({students.length})</h3>
              <input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search students..." style={{padding:'9px 16px',borderRadius:20,border:'1px solid #e2e8f0',fontSize:14,outline:'none',width:220}}/>
            </div>
            <table style={{width:'100%',borderCollapse:'collapse'}}>
              <thead>
                <tr style={{borderBottom:'2px solid #f1f5f9'}}>
                  {['Name','Grade','Marks','Attendance','Status'].map(h=><th key={h} style={{textAlign:'left',padding:'10px 12px',fontSize:12,fontWeight:700,color:'#94a3b8',textTransform:'uppercase'}}>{h}</th>)}
                </tr>
              </thead>
              <tbody>
                {filteredStudents.map(s=>(
                  <tr key={s.id} style={{borderBottom:'1px solid #f8fafc',transition:'background .15s'}} onMouseEnter={e=>e.currentTarget.style.background='#f8fafc'} onMouseLeave={e=>e.currentTarget.style.background='transparent'}>
                    <td style={{padding:'14px 12px'}}><div style={{fontWeight:600,color:'#0f172a',fontSize:14}}>{s.name}</div></td>
                    <td style={{padding:'14px 12px',color:'#64748b',fontSize:14}}>{s.grade}</td>
                    <td style={{padding:'14px 12px'}}><span style={{fontWeight:700,color:s.marks>=85?'#10b981':s.marks>=70?'#f59e0b':'#ef4444'}}>{s.marks}%</span></td>
                    <td style={{padding:'14px 12px',color:'#64748b',fontSize:14}}>{s.attendance}</td>
                    <td style={{padding:'14px 12px'}}><span style={{background:s.status==='Active'?'#d1fae5':'#fef3c7',color:s.status==='Active'?'#065f46':'#92400e',fontSize:12,fontWeight:700,padding:'3px 10px',borderRadius:20}}>{s.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>}

        {/* SCHEDULE */}
        {page==='schedule'&&<div style={{background:'#fff',borderRadius:16,padding:24,border:'1px solid #e2e8f0'}}>
          <h3 style={{margin:'0 0 24px',fontSize:16,fontWeight:700}}>Weekly Timetable</h3>
          <div style={{overflowX:'auto'}}>
            <table style={{width:'100%',borderCollapse:'collapse',minWidth:700}}>
              <thead>
                <tr style={{background:'#f8fafc'}}>
                  {['Time','Monday','Tuesday','Wednesday','Thursday','Friday'].map(d=><th key={d} style={{padding:'12px 16px',textAlign:'left',fontSize:13,fontWeight:700,color:'#475569',borderBottom:'1px solid #e2e8f0'}}>{d}</th>)}
                </tr>
              </thead>
              <tbody>
                {[
                  ['8:00 AM','📐 Mathematics','📚 English','🔬 Science','💻 CS','🏛️ History'],
                  ['9:00 AM','🔬 Science','📐 Math','📚 English','🏛️ History','⚛️ Physics'],
                  ['10:00 AM','💻 CS','⚛️ Physics','📐 Math','🔬 Science','📚 English'],
                  ['11:00 AM','📚 English','💻 CS','⚛️ Physics','📐 Math','🔬 Science'],
                  ['2:00 PM','🏛️ History','🔬 Science','💻 CS','⚛️ Physics','📐 Math'],
                ].map((row,i)=>(
                  <tr key={i} style={{borderBottom:'1px solid #f1f5f9'}} onMouseEnter={e=>e.currentTarget.style.background='#f8fafc'} onMouseLeave={e=>e.currentTarget.style.background='transparent'}>
                    {row.map((cell,j)=><td key={j} style={{padding:'13px 16px',fontSize:13,color:j===0?'#94a3b8':'#334155',fontWeight:j===0?500:400}}>{cell}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>}

        {/* EVENTS */}
        {page==='events'&&<div style={{display:'grid',gap:16}}>
          {events.map((e,i)=>(
            <div key={i} style={{background:'#fff',borderRadius:16,padding:24,border:'1px solid #e2e8f0',display:'flex',gap:20,alignItems:'center',boxShadow:'0 1px 3px rgba(0,0,0,.05)'}}>
              <div style={{background:'#6366f115',color:'#6366f1',padding:'12px 16px',borderRadius:12,textAlign:'center',minWidth:70}}>
                <div style={{fontSize:18,fontWeight:800}}>{e.date.split(' ')[1]}</div>
                <div style={{fontSize:11,fontWeight:600}}>May</div>
              </div>
              <div style={{flex:1}}>
                <h3 style={{margin:0,fontSize:17,fontWeight:700,color:'#0f172a'}}>{e.title}</h3>
                <p style={{margin:'4px 0 0',fontSize:13,color:'#64748b'}}>Academic Event — All students and faculty</p>
              </div>
              <span style={{background:{Event:'#dbeafe',Exam:'#fee2e2',Sports:'#d1fae5',Meeting:'#fef3c7'}[e.type]||'#f1f5f9',color:{Event:'#1d4ed8',Exam:'#991b1b',Sports:'#065f46',Meeting:'#92400e'}[e.type]||'#475569',padding:'6px 14px',borderRadius:20,fontSize:13,fontWeight:700}}>{e.type}</span>
            </div>
          ))}
        </div>}
      </div>
    </div>
  );
}"""

_EDUCATION_BACKEND = """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
app = FastAPI(title="School Portal API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

students_db = [
    {"id":1,"name":"Aisha Khan","grade":"10-A","marks":92,"attendance":"95%"},
    {"id":2,"name":"Rahul Verma","grade":"10-B","marks":78,"attendance":"88%"},
    {"id":3,"name":"Sneha Patel","grade":"11-A","marks":85,"attendance":"92%"},
]
courses_db = [
    {"id":1,"subject":"Mathematics","teacher":"Mr. Arjun Kumar","students":42},
    {"id":2,"subject":"Science","teacher":"Ms. Priya Sharma","students":38},
    {"id":3,"subject":"English","teacher":"Mr. David Raj","students":45},
]

@app.get("/api/health")
def health(): return {"status":"OK","service":"School Portal"}
@app.get("/api/students")
def get_students(): return students_db
@app.get("/api/students/{sid}")
def get_student(sid:int): return next((s for s in students_db if s["id"]==sid),{"error":"not found"})
@app.post("/api/students")
def add_student(s:dict): students_db.append({**s,"id":len(students_db)+1}); return s
@app.get("/api/courses")
def get_courses(): return courses_db
@app.get("/api/stats")
def get_stats(): return {"total_students":1248,"teachers":64,"courses":32,"attendance":"91%"}
"""

def get_fallback_app(domain: str, title: str) -> dict:
    from fallback_templates import get_fallback_app as _base
    if domain == "education":
        return {"app": _EDUCATION_APP, "backend": _EDUCATION_BACKEND}
    return _base(domain, title)
