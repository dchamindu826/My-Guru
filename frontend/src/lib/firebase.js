import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyAC_pHHWH112RZhxHqz7ftrwNTpKMgf3DE",
  authDomain: "my-guru-51071.firebaseapp.com",
  projectId: "my-guru-51071",
  storageBucket: "my-guru-51071.firebasestorage.app",
  messagingSenderId: "408556655871",
  appId: "1:408556655871:web:bb9b545e83cdd8545528ca",
  measurementId: "G-M0YNGPXRZ2"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();