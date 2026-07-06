"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { auth, googleProvider, facebookProvider } from "./firebase";
import { signInWithEmailAndPassword, createUserWithEmailAndPassword, onAuthStateChanged, signInWithPopup, User } from "firebase/auth";

const ChatApp = dynamic(() => import("./ChatApp"), { ssr: false });

export default function Page({ currentUser }: { currentUser: User }) {
  // Mounting & Auth States
  const [isMounted, setIsMounted] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [loadingAuth, setLoadingAuth] = useState(true);

  // Login Form States
  const [isLoginMode, setIsLoginMode] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  // ১. Next.js Hydration Warning Fix (Mounting Check)
  useEffect(() => {
    setIsMounted(true);
  }, []);

  // ২. Firebase Auth Auto-Restore (সেশন চেক করা হচ্ছে)
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
      setLoadingAuth(false);
    });
    return () => unsubscribe(); // Cleanup listener
  }, []);

  // ৩. Login / Signup Handler
  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      if (isLoginMode) {
        await signInWithEmailAndPassword(auth, email, password);
      } else {
        await createUserWithEmailAndPassword(auth, email, password);
      }
    } catch (err: any) {
      setError(err.message.replace("Firebase: ", "")); // ক্লিন এরর মেসেজ
    }
  };

  // ☢️ Social Login Handler
  const handleSocialLogin = async (provider: any) => {
    setError("");
    try {
      await signInWithPopup(auth, provider);
    } catch (err: any) {
      setError(err.message.replace("Firebase: ", ""));
    }
  };

  // 🟢 Loading Screen (Mounting + Firebase Checking)
  if (!isMounted || loadingAuth) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-950">
        <div className="text-indigo-500 animate-pulse font-mono font-bold">Initializing Aura OS...</div>
      </div>
    );
  }

  // 🟢 If User is Logged In -> Show the actual App!
  if (user) {
    return <ChatApp currentUser={user} />;
  }

  // 🔴 If NOT Logged In -> Show the Secure Gateway
  return (
    <div className="h-screen w-full bg-gray-950 flex items-center justify-center font-sans px-4">
      <div className="w-full max-w-md bg-gray-900 border border-gray-800 rounded-2xl shadow-[0_0_40px_rgba(79,70,229,0.15)] p-8">
        
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-400 mb-2">
            Aura OS
          </h1>
          <p className="text-gray-400 text-sm">Strictly Encrypted. Deeply Intimate.</p>
        </div>

        <form onSubmit={handleAuth} className="space-y-4">
          <div>
            <label className="block text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">Email / Username</label>
            <input 
              type="email" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-gray-950 border border-gray-800 text-gray-100 rounded-lg px-4 py-3 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
              placeholder="admin@aura.os"
              required
            />
          </div>

          <div>
            <label className="block text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">PIN / Password</label>
            <input 
              type="password" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-gray-950 border border-gray-800 text-gray-100 rounded-lg px-4 py-3 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
              placeholder="••••••••"
              required
            />
          </div>

          {error && <p className="text-red-400 text-xs text-center bg-red-900/20 p-2 rounded">{error}</p>}

          <button 
            type="submit" 
            className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-3 rounded-lg transition-all shadow-[0_0_15px_rgba(79,70,229,0.4)]"
          >
            {isLoginMode ? "Connect to Aura" : "Initialize New Companion"}
          </button>
        </form>

        {/* ☢️ New Social Login Section */}
        <div className="mt-6 flex items-center justify-between">
          <span className="border-b border-gray-700 w-1/5"></span>
          <span className="text-xs text-gray-500 uppercase tracking-widest">Or continue with</span>
          <span className="border-b border-gray-700 w-1/5"></span>
        </div>

        <div className="mt-6 flex gap-4">
          <button 
            onClick={() => handleSocialLogin(googleProvider)}
            className="w-full flex items-center justify-center gap-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 text-gray-300 py-2.5 rounded-lg transition-colors font-medium text-sm"
          >
            🌐 Google
          </button>
          <button 
            onClick={() => handleSocialLogin(facebookProvider)}
            className="w-full flex items-center justify-center gap-2 bg-[#1877F2]/10 hover:bg-[#1877F2]/20 border border-[#1877F2]/30 text-[#1877F2] py-2.5 rounded-lg transition-colors font-medium text-sm"
          >
            📘 Facebook
          </button>
        </div>

        <div className="mt-6 text-center">
          <button 
            onClick={() => setIsLoginMode(!isLoginMode)}
            className="text-gray-400 hover:text-indigo-400 text-sm transition-colors"
          >
            {isLoginMode ? "Need a new instance? Sign up" : "Already have an instance? Log in"}
          </button>
        </div>
        
      </div>
    </div>
  );
}