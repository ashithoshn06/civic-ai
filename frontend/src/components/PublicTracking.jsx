import React,{useState} from 'react';
import {api} from '../services/api';
export default function PublicTracking(){
 const [id,setId]=useState(''),[result,setResult]=useState(null),[error,setError]=useState('');
 async function submit(e){e.preventDefault();setError('');setResult(null);try{setResult(await api('/api/track/'+encodeURIComponent(id.trim())))}catch(e){setError(e.message)}}
 return <section className="panel"><h3>Track a complaint</h3><p className="muted">Enter your complaint ID. Personal information is never displayed here.</p><form onSubmit={submit} className="tracking-form"><input value={id} onChange={e=>setId(e.target.value)} placeholder="CAI-XXXXXXXX" required/><button className="primary">Track</button></form>{error&&<p className="error">{error}</p>}{result&&<div className="track-result"><b>{result.public_id}</b><strong>{result.status} · {result.priority}</strong><span>{result.category}</span><p>{result.public_summary}</p>{(result.timeline||[]).map((x,i)=><small key={i}>{x.status}: {x.note}</small>)}</div>}</section>
}
