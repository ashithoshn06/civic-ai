import {auth} from '../firebase';
const base=import.meta.env.VITE_API_BASE_URL||'http://127.0.0.1:8000';
export async function api(path,options={}) {
 const token=auth?.currentUser?await auth.currentUser.getIdToken():null;
 const headers={...(options.body instanceof FormData?{}:{'Content-Type':'application/json'}),...(token?{Authorization:`Bearer ${token}`}:{}) ,...(options.headers||{})};
 const res=await fetch(`${base}${path}`,{...options,headers});
 const data=await res.json().catch(()=>({detail:'Unexpected server response'}));
 if(!res.ok)throw new Error(data.detail||`Request failed (${res.status})`);
 return data;
}
