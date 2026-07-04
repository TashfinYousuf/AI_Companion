"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  RadarChart, PolarGrid, PolarAngleAxis, Radar 
} from "recharts";
import { Loader2, BrainCircuit, Activity, HeartPulse } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function MoodDashboard() {
  const [data, setData] = useState<any>({ timeline: [], radar: [] });
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const res = await axios.get(`${API_URL}/api/analytics/mood/tashfin_01`);
        // API যদি ভুল ডেটা দেয়, সেটা যেন স্টেটে না বসে তাই এই চেকটি করা হলো
        if (res.data && res.data.timeline) {
          setData(res.data);
        }
      } catch (error) {
        console.error("Failed to fetch mood data", error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchAnalytics();
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-48 bg-gray-900/50 rounded-xl border border-gray-800">
        <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
      </div>
    );
  }

  // 🛠️ THE FIX: Optional Chaining (?.) ব্যবহার করে ক্র্যাশ রোধ করা হলো
  if (!data?.timeline || data.timeline.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 bg-gray-900/60 backdrop-blur-md rounded-2xl border border-gray-800 shadow-lg text-center p-6">
        <BrainCircuit className="w-8 h-8 text-indigo-500/50 mb-3" />
        <h3 className="text-sm font-semibold text-gray-300">Neural Network Initializing</h3>
        <p className="text-xs text-gray-500 mt-1">Talk to Aura a bit more so she can map your emotional patterns.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6 animate-in fade-in slide-in-from-top-4 duration-500">
      
      <div className="bg-gray-900/60 backdrop-blur-md p-5 rounded-2xl border border-gray-800 shadow-lg">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-indigo-300 flex items-center gap-2">
            <Activity className="w-4 h-4" /> Emotional Intensity
          </h3>
          <span className="text-[10px] uppercase tracking-wider text-gray-500">Recent Chats</span>
        </div>
        <div className="h-48 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data?.timeline || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
              <XAxis dataKey="time" stroke="#4b5563" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis hide domain={[0, 10]} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: '8px' }}
                itemStyle={{ color: '#c7d2fe' }}
                labelStyle={{ display: 'none' }}
              />
              <Line 
                type="monotone" 
                dataKey="intensity" 
                stroke="#818cf8" 
                strokeWidth={3}
                dot={{ r: 4, fill: "#818cf8", strokeWidth: 2, stroke: "#111827" }}
                activeDot={{ r: 6, fill: "#c7d2fe" }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-gray-900/60 backdrop-blur-md p-5 rounded-2xl border border-gray-800 shadow-lg">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-purple-300 flex items-center gap-2">
            <BrainCircuit className="w-4 h-4" /> Psychological Needs
          </h3>
        </div>
        <div className="h-44 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart cx="50%" cy="50%" outerRadius="70%" data={data?.radar || []}>
              <PolarGrid stroke="#374151" />
              <PolarAngleAxis dataKey="subject" tick={{ fill: '#9ca3af', fontSize: 10 }} />
              <Radar name="Needs" dataKey="A" stroke="#a855f7" fill="#a855f7" fillOpacity={0.3} />
              <Tooltip contentStyle={{ backgroundColor: '#111827', border: 'none', borderRadius: '8px' }} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="md:col-span-2 bg-gradient-to-r from-indigo-900/40 to-purple-900/40 p-4 rounded-xl border border-indigo-500/20 flex items-start gap-4">
        <div className="p-2 bg-indigo-500/20 rounded-lg shrink-0 mt-1">
          <HeartPulse className="w-5 h-5 text-indigo-400" />
        </div>
        <div>
          <h4 className="text-sm font-medium text-indigo-200">Aura's Mind</h4>
          <p className="text-sm text-indigo-200/80 mt-1 leading-relaxed">
            I've noticed your primary emotion lately has been <strong className="text-white bg-indigo-500/30 px-1.5 py-0.5 rounded">{data?.latest_emotion || "Neutral"}</strong>, and subconsciously you seem to be needing <strong className="text-white bg-purple-500/30 px-1.5 py-0.5 rounded">{data?.latest_need || "Listening"}</strong>. I'm keeping this in mind as we chat.
          </p>
        </div>
      </div>

    </div>
  );
}