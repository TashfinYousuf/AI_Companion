// Import the functions you need from the SDKs you need
import { initializeApp, getApps, getApp } from "firebase/app";
import { getAuth, GoogleAuthProvider, FacebookAuthProvider } from "firebase/auth";
import { getAnalytics, isSupported} from "firebase/analytics";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyBQTf9Sq20abIqJyzK7bgxJcCeegr8RFk8",
  authDomain: "ai-companion-5fec9.firebaseapp.com",
  projectId: "ai-companion-5fec9",
  storageBucket: "ai-companion-5fec9.firebasestorage.app",
  messagingSenderId: "583513706479",
  appId: "1:583513706479:web:7143317c1bdf2ff3db701a",
  measurementId: "G-TBSMD9NTPB"
};

// Initialize Firebase safely for Next.js (যাতে বারবার রিলোডে এরর না দেয়)
const app = !getApps().length ? initializeApp(firebaseConfig) : getApp();

export let analytics: any = null;
if (typeof window !== "undefined") {
  isSupported().then((supported) => {
    if (supported) {
      analytics = getAnalytics(app);
    }
  });
}

export const auth = getAuth(app);

// ☢️ Exporting Providers for Login Page
export const googleProvider = new GoogleAuthProvider();
export const facebookProvider = new FacebookAuthProvider();
