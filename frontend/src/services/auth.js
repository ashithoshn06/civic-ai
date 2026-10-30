import {auth,googleProvider} from '../firebase';
import {createUserWithEmailAndPassword,signInWithEmailAndPassword,signInWithPopup,signOut} from 'firebase/auth';
export const register=(email,password)=>createUserWithEmailAndPassword(auth,email,password);
export const login=(email,password)=>signInWithEmailAndPassword(auth,email,password);
export const googleLogin=()=>signInWithPopup(auth,googleProvider);
export const logout=()=>signOut(auth);
