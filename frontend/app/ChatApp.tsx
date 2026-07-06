"use client";
import { useState, useRef, useEffect } from "react";
import axios from "axios";
import { Mic, Send, Square, Loader2, ImagePlus } from "lucide-react";
import { useReactMediaRecorder } from "react-media-recorder";
import MoodDashboard from './MoodDashboard';
import GoalTracker from './GoalTracker';
import { signOut } from "firebase/auth";
import { auth } from "./firebase";
import { User } from "firebase/auth";

// ১. টাইপস্ক্রিপ্ট ইন্টারফেস (যাতে Message টাইপ নিয়ে কোনো এরর না আসে)
export interface Message {
    role: 'ai' | 'user';
    id: string;
    content: string;
    audioBase64?: string; // অডিও সেভ রাখার জন্য
    isVoiceNote?: boolean; // মেসেঞ্জারের মতো ভয়েস নোট
    imageUrl?: string;     // ছবির লিংক
    userAudioUrl?: string; // ইউজারের নিজের অডিও শোনার জন্য
    reaction?: string; // রিয়্যাকশনের জন্য
    replyTo?: string; // কোন মেসেজের রিপ্লাই দেওয়া হয়েছে
    videoUrl?: string; // ভিডিওর জন্য
}

// 🌍 SAFE DYNAMIC URLS
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || (typeof window !== "undefined" ? `http://${window.location.hostname}:8000` : "http://127.0.0.1:8000");
  const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || (typeof window !== "undefined" ? `ws://${window.location.hostname}:8000` : "ws://127.0.0.1:8000");

export default function ChatApp({ currentUser }: { currentUser: User }) {

  // ==========================================
  // ২. কোর স্টেটস (Core States)
  // ==========================================
  const [messages, setMessages] = useState<Message[]>([
    { id: Date.now().toString(), role: "ai", content: "Hey there. I'm here. How's your mind feeling right now?" },
  ]);
  const [showDashboard, setShowDashboard] = useState(false);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [relationship, setRelationship] = useState({ level: 1, title: "Acquaintance", progress: 0 });
  const [isRecording, setIsRecording] = useState(false);
  const [showClearConfirm, setShowClearConfirm] = useState(false); // ওয়ার্নিং পপ-আপের জন্য
  const [isIncognito, setIsIncognito] = useState(false);
  const [showMediaGallery, setShowMediaGallery] = useState(false); // গ্যালারির জন্য
  const [hoveredMsgIdx, setHoveredMsgIdx] = useState<number | null>(null); // রিয়্যাকশন হোভারের জন্য
  const [replyingToMsg, setReplyingToMsg] = useState<string | null>(null);
  const [editingMsgIdx, setEditingMsgIdx] = useState<number | null>(null);
  const [viewingImage, setViewingImage] = useState<string | null>(null); // Image Zoom-এর জন্য
  

  // ==========================================
  // ৩. রেফারেন্স (Refs)
  // ==========================================
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const ws = useRef<WebSocket | null>(null);
  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const audioChunks = useRef<Blob[]>([]);

  // User লাস্ট কীভাবে মেসেজ দিয়েছে তা মনে রাখার জন্য
  const lastInputMode = useRef<'text' | 'voice'>('text');

  // 🔔 Request Browser Notification Permission
  useEffect(() => {
    if ("Notification" in window && Notification.permission !== "granted") {
      Notification.requestPermission();
    }
  }, []);

  // ==========================================
  // ৪. অটো স্ক্রল (Auto Scroll)
  // ==========================================
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ==========================================
  // ৫. রিলেশনশিপ অ্যানালিটিক্স লোডার
  // ==========================================
  useEffect(() => {
    const fetchRelationship = async () => {
      try {
        const res = await axios.get(`${API_BASE}/api/analytics/relationship/${currentUser.uid}`);
        if (res.data) {
          setRelationship({
            level: res.data.current_level,
            title: res.data.title,
            progress: res.data.progress_to_next_level
          });
        }
      } catch (err) {
        console.error("Failed to load relationship stats", err);
      }
    };
    
    // শুধু চ্যাট আপডেট হলেই রিলেশনশিপ চেক করবে
    if (messages.length > 1) {
      fetchRelationship();
    }
  }, [messages.length, API_BASE]);

  // ☁️ SYNC: Fetch history across devices from OWN BACKEND
  useEffect(() => {
    if (!currentUser) return;
    
    const fetchCloudChats = async () => {
      try {
        const res = await axios.get(`${API_BASE}/api/chat/history/${currentUser.uid}`);
        if (res.data && res.data.length > 0) {
          setMessages(res.data);
        }
      } catch (error) {
        console.error("Error loading chats:", error);
      }
    };

    fetchCloudChats();
  }, [currentUser]);


  // ==========================================
  // ৬. কোর ইঞ্জিন (Permanent History Sync)
  // ==========================================
  useEffect(() => {
    if (!currentUser) return; // ☢️ ইউজার লগিন না থাকলে লোড করবে না

    // ✅ এখানে আর ডাবল কোটেশন ("") হবে না, সরাসরি ভ্যারিয়েবল
    const user_id = currentUser.uid; 
    
    // ☢️ Cache Buster + History Endpoint
    const historyUrl = `${API_BASE}/api/chat/history/${user_id}?t=${new Date().getTime()}`;
    
    fetch(historyUrl, {
      method: "GET",
      headers: {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
      }
    })
      .then(res => res.json())
      .then(data => {
        // আমাদের নতুন API ডিরেক্ট Array রিটার্ন করে
        if (Array.isArray(data) && data.length > 0) {
          setMessages(data);
        } else if (data.status === "success" && data.history && data.history.length > 0) {
          setMessages(data.history);
        } else {
          setMessages([{
            id: "welcome-msg",
            role: "ai",
            content: "Hi! I'm Aura. Let's chat!",
          }]);
        }
      })
      .catch(err => console.error("History fetch error:", err));

    // খ) নোটিফিকেশন পারমিশন
    if ("Notification" in window && Notification.permission === "default") {
      Notification.requestPermission();
    }

    const connectWebSocket = () => {
      // ☢️ PRO-TRICK: ব্রাউজার যে IP তে চলবে, ওয়েবসকেট অটোমেটিক সেই IP ধরে নেবে
      const currentHost = window.location.hostname;
      
      const socket = new WebSocket(`${WS_BASE}/api/voice/ws/live-chat/${user_id}`);
      ws.current = socket;

    const playSweetBeep = () => {
      try {
        const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.type = "sine";
        osc.frequency.setValueAtTime(880, ctx.currentTime); 
        gain.gain.setValueAtTime(0.1, ctx.currentTime); 
        osc.start();
        osc.stop(ctx.currentTime + 0.15);
      } catch (e) {}
    };

    socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "reply") {
            setMessages(prev => [...prev, { 
              id: Date.now().toString(),
              role: 'ai', 
              content: data.content,
              audioBase64: data.audio_base64,
              isVoiceNote: data.is_voice_note,
              imageUrl: data.image_url,
              videoUrl: data.video_url,
            }]);
            setIsLoading(false);

            // 💾 Save AI Message to Permanent DB
            fetch(`${API_BASE}/api/chat/save`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                user_id: currentUser.uid,
                role: "ai",
                content: data.content,
                image_url: null
              })
            });

            // মেসেজ আসার সাথে সাথে বিপ সাউন্ড প্লে হবে
            if (typeof playSweetBeep === "function") {
              playSweetBeep(); 
            }
          }

          // 🔔 PUSH NOTIFICATION (যদি ইউজার অন্য ট্যাবে থাকে)
          if (document.hidden && "Notification" in window && Notification.permission === "granted") {
            new Notification("Aura 💜", {
              body: data.content,
              icon: data.image_url || "/default-avatar.png",
            });
          }
        } catch (err) {
          console.error("Parse error:", err);
        }
      };

      socket.onclose = () => {
        console.log("❌ WebSocket Disconnected. Reconnecting in 3 seconds...");
        setTimeout(connectWebSocket, 3000); // ৩ সেকেন্ড পর আবার এই ফাংশনটাই কল হবে
      };
    };

    // প্রথমবার ম্যানুয়ালি কানেক্ট করার জন্য ফাংশনটা কল করা হলো
    connectWebSocket();

    // ক্লিনআপ ফাংশন (কম্পোনেন্ট আনমাউন্ট হলে কানেকশন কেটে দেবে)
    return () => {
      if (ws.current) {
        ws.current.onclose = null; // রিকানেক্ট লুপ বন্ধ করা
        ws.current.close();
      }
    };
  }, [currentUser]); // currentUser চেঞ্জ হলে আবার লোড হবে

  // ==========================================
  // ৭. ইউটিলিটি: ইমেজ টু Base64
  // ==========================================
  const convertToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve((reader.result as string).split(",")[1]);
      reader.onerror = (error) => reject(error);
    });
  };

  const submitEdit = (idx: number, newContent: string) => {
    const msgId = messages[idx].id;

    // 1. Update Frontend
    setMessages(prev => {
      const newMsgs = [...prev];
      newMsgs[idx] = { ...newMsgs[idx], content: newContent };
      return newMsgs;
    });
    setEditingMsgIdx(null);
    setInput("");

    // 2. Send to Backend via WebSocket
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ 
        type: "edit", 
        message_id: msgId, 
        new_content: newContent 
      }));
    }
  };
  
  // ===========================================================
  // ৮. টেক্সট ও ইমেজ সেন্ড (Old API Removed, Now fully WebSocket)
  // ===========================================================
  const handleTextSend = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() && !selectedImage) return;

    let base64Image = null;
    if (selectedImage) {
      base64Image = await convertToBase64(selectedImage);
    }

    const userMsg = input.trim() ? input.trim() : "📸 Sent an image";
    
    const finalContent = replyingToMsg ? `[Replying to: "${replyingToMsg}"] ${userMsg}` : userMsg;

    // UI Update
    setInput("");
    setSelectedImage(null);
    setMessages((prev) => [...prev, { id: Date.now().toString(), role: "user", content: userMsg }]);
    setReplyingToMsg(null); // রিপ্লাই সেন্ড হলে ক্লিয়ার করে দেওয়া
    setIsLoading(true);

    // 💾 Save User Message to Permanent DB (NEW)
    try {
      await fetch(`${API_BASE}/api/chat/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: currentUser.uid,
          role: "user",
          content: finalContent,
          image_url: base64Image || null
        })
      });
    } catch (err) {
      console.error("DB Save Error:", err);
    }

    // Send via WebSocket (JSON format)
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      lastInputMode.current = 'text';
      lastInputMode.current = 'voice';
      ws.current.send(JSON.stringify({ 
        type: "text", 
        content: finalContent,
        image_base64: base64Image, // ভবিষ্যতে মাল্টিমোডাল ভিশনের জন্য রেডি রাখা হলো
        incognito: isIncognito
      }));
    } else {
      console.error("WebSocket disconnected!");
      setIsLoading(false);
    }
  };

  // ==========================================
  // ৯. রিয়েলটাইম মাইক্রোফোন (STT) সেন্ড 
  // ==========================================
  const recordingStartTime = useRef<number>(0);

  const toggleRecording = async () => {
    if (isRecording) {
      // স্টপ রেকর্ডিং
      mediaRecorder.current?.stop();
      setIsRecording(false);
    } else {
      // স্টার্ট রেকর্ডিং
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder.current = new MediaRecorder(stream);
        audioChunks.current = [];
        recordingStartTime.current = Date.now();

        mediaRecorder.current.ondataavailable = (e) => {
          if (e.data.size > 0) audioChunks.current.push(e.data);
        };

        mediaRecorder.current.onstop = () => {
          const duration = Date.now() - recordingStartTime.current;
          if (duration < 1000) {
            console.warn("Recording too short, ignored.");
            return; // ১ সেকেন্ডের কম হলে সেন্ড হবে না
          }

          const audioBlob = new Blob(audioChunks.current, { type: 'audio/webm' });
          const userAudioObjectUrl = URL.createObjectURL(audioBlob); // ইউজারের প্লেয়ারের জন্য

          const reader = new FileReader();
          reader.readAsDataURL(audioBlob);
          reader.onloadend = () => {
            const base64Audio = (reader.result as string).split(',')[1];
            
            setMessages(prev => [...prev, { 
              id: Date.now().toString(),
              role: 'user', 
              content: "🎤 Voice Message",
              isVoiceNote: true,
              userAudioUrl: userAudioObjectUrl 
            }]);
            setIsLoading(true);
            
            if (ws.current && ws.current.readyState === WebSocket.OPEN) {
              ws.current.send(JSON.stringify({ type: "audio", content: base64Audio , incognito: isIncognito}));
            }
          };
          stream.getTracks().forEach(track => track.stop());
        };

        mediaRecorder.current.start();
        setIsRecording(true);
      } catch (err) {
        console.error("Mic error:", err);
      }
    }
  };

  // 🔊 প্লে ভয়েস লজিক (শুধু ক্লিক করলে বাজবে)
  // কোনো API কল লাগবে না, সরাসরি স্টেট থেকে Base64 প্লে করবে
  const playVoice = (audioBase64?: string) => {
    if (audioBase64) {
      const audio = new Audio("data:audio/mp3;base64," + audioBase64);
      audio.play();
    }
  };

  const handleClearHistory = async () => {
    if (!confirm("Are you sure you want to clear all chats? This cannot be undone.")) return;
    try {
      await axios.delete(`${API_BASE}/api/chat/history/${currentUser.uid}`);
      setMessages([]);
    } catch (err) {
      console.error("Failed to clear history", err);
    }
  };

  const handleReaction = (idx: number, emoji: string) => {
    const msgId = messages[idx].id;
    const currentReaction = messages[idx].reaction;
    const finalEmoji = currentReaction === emoji ? null : emoji; // টগল সিস্টেম

    // 1. Update Frontend instantly
    setMessages(prev => {
      const newMsgs = [...prev];
      newMsgs[idx] = { ...newMsgs[idx], reaction: finalEmoji || undefined };
      return newMsgs;
    });
    setHoveredMsgIdx(null);

    // 2. Send to Backend via WebSocket
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ 
        type: "reaction", 
        message_id: msgId, 
        emoji: finalEmoji 
      }));
    }
  };
  
  return (
    <div className="flex flex-col h-screen bg-gray-950 text-gray-100 font-sans">
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center p-3 sm:p-4 border-b border-gray-800 bg-gray-900/50 backdrop-blur-md sticky top-0 z-10 gap-3 sm:gap-0">
        
        {/* Top Row for Mobile (Title + Level) */}
        <div className="flex justify-between items-center w-full sm:w-auto">
          <h1 className="text-lg sm:text-xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-400">
            Aura Companion OS
          </h1>
          <div className="flex items-center gap-2 sm:ml-4">
            <span className="text-[10px] sm:text-xs px-2 py-0.5 bg-indigo-500/20 text-indigo-300 rounded border border-indigo-500/30 whitespace-nowrap">
              Lv. {relationship.level} | {relationship.title}
            </span>
            <div className="w-16 sm:w-24 h-1.5 bg-gray-700 rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-500"
                style={{ width: `${relationship.progress}%` }}
              />
            </div>
          </div>
        </div>

        {/* Bottom Row for Mobile (Scrollable Action Buttons) */}
        <div className="flex items-center gap-2 overflow-x-auto w-full sm:w-auto pb-1 sm:pb-0 no-scrollbar">
          <button 
            onClick={() => setShowMediaGallery(!showMediaGallery)} 
            className="px-3 py-1.5 sm:px-4 sm:py-2 bg-pink-600/20 text-pink-400 rounded-lg text-xs sm:text-sm font-medium hover:bg-pink-600/30 transition whitespace-nowrap"
          >
            Gallery 🖼️
          </button>

          <button 
            onClick={() => setIsIncognito(!isIncognito)} 
            className={`px-3 py-1.5 sm:px-4 sm:py-2 rounded-lg text-xs sm:text-sm font-medium transition flex items-center gap-1.5 sm:gap-2 whitespace-nowrap ${
              isIncognito 
                ? "bg-purple-600 text-white shadow-[0_0_15px_rgba(147,51,234,0.5)]" 
                : "bg-gray-800/50 text-gray-400 hover:text-purple-400"
            }`}
          >
            {isIncognito ? "👻 Incognito ON" : "👁️ Incognito OFF"}
          </button>

          <button onClick={() => setShowClearConfirm(true)} className="px-3 py-1.5 sm:px-4 sm:py-2 bg-red-600/20 text-red-400 rounded-lg text-xs sm:text-sm font-medium hover:bg-red-600/30 transition whitespace-nowrap">
            Clear Chat
          </button>

          <button 
            onClick={() => setShowDashboard(!showDashboard)}
            className="px-3 py-1.5 sm:px-4 sm:py-2 bg-indigo-600/20 text-indigo-400 rounded-lg hover:bg-indigo-600/30 transition-colors text-xs sm:text-sm font-medium whitespace-nowrap"
          >
            {showDashboard ? "Hide Analytics" : "View Analytics"}
          </button>

          <button 
            onClick={() => signOut(auth)} 
            className="px-3 py-1.5 sm:px-4 sm:py-2 bg-gray-800 text-gray-400 rounded-lg text-xs sm:text-sm font-medium hover:text-red-400 hover:bg-gray-800/80 transition whitespace-nowrap">
            Log Out
          </button>
        </div>
      </header>

      {showDashboard && (
        <div className="px-4 pt-4">
          <MoodDashboard currentUser={currentUser}/>
          <GoalTracker currentUser={currentUser} />
        </div>
      )}

      {/* Chat Area - Centered and clean */}  
      <main className="flex-1 overflow-y-auto p-4 space-y-6 scroll-smooth pb-32 max-w-4xl mx-auto w-full">
        {messages.map((msg, idx) => (
          <div 
            key={idx} 
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} animate-in fade-in duration-300 relative`}
            onMouseEnter={() => setHoveredMsgIdx(idx)}
            onMouseLeave={() => setHoveredMsgIdx(null)}
          >
            
            {/* MESSENGER STYLE REACTION & ACTION BAR */}
            {hoveredMsgIdx === idx && (
              <div className={`absolute -top-5 ${msg.role === "user" ? "right-10" : "left-10"} bg-gray-800 border border-gray-700 rounded-full px-3 py-1.5 flex items-center gap-3 z-10 shadow-lg`}>
                {['❤️', '😆', '🔥'].map(emoji => (
                  <button key={emoji} onClick={() => handleReaction(idx, emoji)} className="hover:scale-125 transition-transform text-sm">
                    {emoji}
                  </button>
                ))}
                <div className="w-px h-4 bg-gray-600"></div>
                
                {/* REPLY BUTTON */}
                <button onClick={() => setReplyingToMsg(msg.content.substring(0, 50))} className="text-xs text-gray-400 hover:text-indigo-400 transition" title="Reply">
                  ↩️
                </button>

                {/* EDIT BUTTON (Only for User) */}
                {msg.role === "user" && (
                  <button onClick={() => { setInput(msg.content); setEditingMsgIdx(idx); }} className="text-xs text-gray-400 hover:text-indigo-400 transition" title="Edit">
                    ✏️
                  </button>
                )}
              </div>
            )}

            <div className={`max-w-[85%] md:max-w-[70%] rounded-2xl px-5 py-3.5 shadow-sm flex flex-col gap-3 relative ${
              msg.role === "user" ? "bg-indigo-600 text-white rounded-br-none" : "bg-gray-800 text-gray-200 rounded-bl-none border border-gray-700/50"
            }`}>
              
              {/* MESSENGER STYLE RESIZED IMAGE WITH CLICK-TO-ZOOM */}
              {msg.imageUrl && (
                <div className="relative group overflow-hidden rounded-xl w-48 md:w-56 cursor-pointer shadow-md border border-gray-700/50 hover:opacity-85 transition-opacity" onClick={() => setViewingImage(msg.imageUrl!)}>
                  <img 
                    src={msg.imageUrl} 
                    alt="AI Selfie" 
                    className="w-full h-auto object-cover" 
                    onError={(e) => (e.target as HTMLImageElement).parentElement!.style.display = 'none'} 
                  />
                  {/* ছোট একটা জুম আইকন হোভার করলে দেখাবে */}
                  <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/30">
                    <span className="text-white text-2xl">🔍</span>
                  </div>
                </div>
              )}

              {/* 🎬 VIDEO PLAYER */}
              {msg.videoUrl && (
                <div className="relative group overflow-hidden rounded-xl w-56 md:w-64 shadow-md border border-gray-700/50">
                  <video 
                    src={msg.videoUrl} 
                    autoPlay 
                    loop 
                    muted 
                    playsInline
                    className="w-full h-auto object-cover"
                  />
                </div>
              )}
              
              {/* MESSENGER STYLE VOICE NOTE PLAYER */}
              {msg.isVoiceNote ? (
                <div className={`flex items-center gap-3 p-2 rounded-xl ${msg.role === "user" ? "bg-indigo-500/30 border-indigo-400/30" : "bg-gray-900/50 border-gray-700"} border`}>
                  <button 
                    onClick={() => {
                      const audio = new Audio(msg.userAudioUrl || (msg.audioBase64 ? `data:audio/mp3;base64,${msg.audioBase64}` : ""));
                      audio.play();
                    }}
                    className={`w-10 h-10 rounded-full flex items-center justify-center transition shadow-md ${msg.role === "user" ? "bg-white text-indigo-600 hover:bg-gray-100" : "bg-indigo-500 text-white hover:bg-indigo-400"}`}
                  >
                    ▶️
                  </button>
                  <div className="flex-1 h-1.5 bg-gray-950/30 rounded-full overflow-hidden w-24">
                    <div className="w-full h-full bg-current opacity-50"></div>
                  </div>
                  <span className="text-xs font-medium opacity-70">Voice</span>
                </div>
              ) : (

                /* NORMAL TEXT CHAT WITH SLEEK SPEAKER ICON */
                <div>
                  {/* ☢️ NORMAL TEXT OR EDIT MODE */}
                  {editingMsgIdx === idx ? (
                    <div className="flex flex-col gap-2 w-full mt-1">
                      <textarea 
                        value={input} 
                        onChange={(e) => setInput(e.target.value)}
                        className="bg-gray-900 text-white p-3 rounded-lg w-full text-sm border border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 resize-none min-h-[60px]"
                      />
                      <div className="flex gap-2 justify-end">
                        <button 
                          onClick={() => { setEditingMsgIdx(null); setInput(""); }} 
                          className="text-xs bg-gray-700 hover:bg-gray-600 px-3 py-1.5 rounded-md transition"
                        >
                          Cancel
                        </button>
                        <button 
                          onClick={() => submitEdit(idx, input)} 
                          className="text-xs bg-indigo-600 hover:bg-indigo-500 px-3 py-1.5 rounded-md transition shadow-md"
                        >
                          Save
                        </button>
                      </div>
                    </div>
                  ) : (
                    <span className="whitespace-pre-wrap leading-relaxed">{msg.content}</span>
                  )}

                  {msg.role !== "user" && msg.audioBase64 && (
                    <div className="mt-2">
                      <audio 
                        controls 
                        controlsList="nodownload noplaybackrate" 
                        className="h-8 w-48 opacity-80 drop-shadow-md rounded-md" 
                        src={`data:audio/mp3;base64,${msg.audioBase64}`} 
                      />
                    </div>
                  )}
                </div>
              )}
              
              {/* SHOW APPLIED REACTION */}
              {msg.reaction && (
                <div className={`absolute -bottom-3 ${msg.role === "user" ? "left-2" : "right-2"} bg-gray-900 border border-gray-700 rounded-full p-1 text-xs shadow-md`}>
                  {msg.reaction}
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-800 rounded-2xl rounded-bl-none px-5 py-4 border border-gray-700/50 flex items-center gap-2 h-12 w-20">
              <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
              <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
              <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce"></div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </main>

      {/* CLEAR CHAT CONFIRMATION MODAL */}
      {showClearConfirm && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 animate-in fade-in">
          <div className="bg-gray-900 border border-gray-700 p-6 rounded-2xl max-w-sm w-full mx-4 shadow-2xl">
            <h3 className="text-xl font-bold text-white mb-2">Clear All Chats?</h3>
            <p className="text-gray-400 text-sm mb-6">Are you sure you want to delete this conversation? This will permanently wipe our memory.</p>
            <div className="flex justify-end gap-3">
              <button 
                onClick={() => setShowClearConfirm(false)} 
                className="px-4 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-700 transition"
              >
                Cancel
              </button>
              <button 
                onClick={() => { handleClearHistory(); setShowClearConfirm(false); }} 
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition shadow-lg shadow-red-900/50"
              >
                Yes, Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* EXCLUSIVE MEDIA GALLERY SECTION */}
      {showMediaGallery && (
        <div className="absolute inset-0 bg-gray-950/95 z-40 flex flex-col p-6 animate-in fade-in slide-in-from-bottom-10">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-pink-400 to-indigo-400">Media & Voice Notes</h2>
            <button onClick={() => setShowMediaGallery(false)} className="p-2 bg-gray-800 rounded-full text-white hover:bg-gray-700">❌</button>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 overflow-y-auto pb-20">
            {messages.filter(m => m.imageUrl || m.isVoiceNote).reverse().map((media, i) => (
              <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl p-3 flex flex-col gap-2 shadow-lg">
                {media.imageUrl && 
                <img src={media.imageUrl} 
                alt="Aura Selfie" 
                className="w-full max-h-72 sm:max-h-80 object-cover rounded-2xl mt-2 shadow-md border border-gray-700/50" 
                loading="lazy"/>}
                {media.isVoiceNote && (
                  <audio controls className="w-full h-8" src={media.userAudioUrl || `data:audio/mp3;base64,${media.audioBase64}`} />
                )}
                <span className="text-xs text-gray-500 text-center">{media.role === 'ai' ? 'Aura' : 'You'}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Footer Area */}
      <footer className="fixed bottom-0 w-full p-4 bg-gradient-to-t from-gray-950 via-gray-950 to-transparent">
        
        {/* REPLY PREVIEW BAR */}
        {replyingToMsg && (
          <div className="max-w-3xl mx-auto mb-2 bg-gray-900 border border-gray-700 rounded-lg p-2 flex justify-between items-center text-sm shadow-md animate-in slide-in-from-bottom-2">
            <div className="flex flex-col border-l-2 border-indigo-500 pl-2">
              <span className="text-indigo-400 font-medium text-xs">Replying to Aura</span>
              <span className="text-gray-400 truncate max-w-xs">{replyingToMsg}...</span>
            </div>
            <button onClick={() => setReplyingToMsg(null)} className="text-gray-500 hover:text-white p-1">❌</button>
          </div>
        )}

        <div className="max-w-3xl mx-auto flex items-center gap-2 bg-gray-900 border border-gray-700 rounded-full p-2 shadow-2xl">
          
          <input 
            type="file" 
            accept="image/*" 
            className="hidden" 
            ref={fileInputRef} 
            onChange={(e) => setSelectedImage(e.target.files?.[0] || null)} 
          />

          {/* ইমেজ অ্যাটাচমেন্ট বাটন */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className={`p-3 rounded-full transition-all flex-shrink-0 ${
              selectedImage 
                ? "text-indigo-400 bg-indigo-500/20" 
                : "text-gray-400 hover:text-indigo-400 hover:bg-gray-800"
            }`}
          >
            <ImagePlus className="w-5 h-5" />
          </button>
          
          {/* TAP TO TOGGLE MICROPHONE */}
          <button
            type="button"
            onClick={toggleRecording}
            className={`p-3 rounded-full transition-all duration-300 flex-shrink-0 ${
              isRecording ? "bg-red-500 text-white animate-pulse" : "bg-gray-800 text-gray-400 hover:text-indigo-400"
            }`}
          >
            {isRecording ? <Square className="w-5 h-5 fill-current" /> : <Mic className="w-5 h-5" />}
          </button>

          {/* টেক্সট ইনপুট এবং সেন্ড বাটন */}
          <form onSubmit={handleTextSend} className="flex-1 flex items-center gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={selectedImage ? "Add a message about the image..." : "Tell me what's on your mind..."}
              className="w-full bg-transparent border-none focus:ring-0 text-white placeholder-gray-500 text-[15px] px-2 outline-none"
              disabled={isLoading || isRecording} // রেকর্ডিং চলাকালীন টাইপিং বন্ধ থাকবে
            />
            <button
              type="submit"
              disabled={(!input.trim() && !selectedImage) || isLoading}
              className="p-3 bg-indigo-600 text-white rounded-full hover:bg-indigo-700 disabled:opacity-50 disabled:hover:bg-indigo-600 transition-colors flex-shrink-0 shadow-md shadow-indigo-600/20"
            >
              <Send className="w-5 h-5 ml-0.5" />
            </button>
          </form>

        </div>
      </footer>

      {/* MESSENGER STYLE IMAGE ZOOM MODAL */}
      {viewingImage && (
        <div 
          className="fixed inset-0 bg-black/95 z-[9999] flex items-center justify-center p-4 backdrop-blur-md animate-in fade-in duration-200"
          onClick={() => setViewingImage(null)} // বাইরে ক্লিক করলেই ক্লোজ হয়ে যাবে
        >
          <button 
            onClick={() => setViewingImage(null)} 
            className="absolute top-6 right-6 text-white bg-gray-800/50 hover:bg-red-500 rounded-full w-10 h-10 flex items-center justify-center transition-colors text-xl"
          >
            ❌
          </button>
          <img 
            src={viewingImage} 
            className="max-w-full max-h-[90vh] object-contain rounded-lg shadow-[0_0_50px_rgba(0,0,0,0.5)]" 
            alt="Zoomed Selfie" 
            onClick={(e) => e.stopPropagation()} // ছবির উপর ক্লিক করলে যেন ক্লোজ না হয়
          />
        </div>
      )}
    </div>
  );
}