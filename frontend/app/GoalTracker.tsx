"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import { Target, CheckCircle2, Circle, Loader2, Rocket } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type Task = { id: number; title: string; is_completed: boolean };
type GoalType = { id: number; title: string; description: string; progress: number; tasks: Task[] };

export default function GoalTracker() {
  const [goals, setGoals] = useState<GoalType[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchGoals = async () => {
      try {
        const res = await axios.get(`${API_URL}/api/analytics/goals/tashfin_01`);
        setGoals(res.data);
      } catch (error) {
        console.error("Failed to fetch goals", error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchGoals();
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-32 bg-gray-900/50 rounded-xl border border-gray-800 mt-4">
        <Loader2 className="w-5 h-5 animate-spin text-indigo-500" />
      </div>
    );
  }

  if (goals.length === 0) {
    return null; // কোনো গোল না থাকলে হাইড থাকবে
  }

  return (
    <div className="mt-6 space-y-4 animate-in fade-in slide-in-from-top-4 duration-500">
      <h3 className="text-sm font-semibold text-indigo-300 flex items-center gap-2 px-1">
        <Rocket className="w-4 h-4" /> Active Directives & Goals
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {goals.map((goal) => (
          <div key={goal.id} className="bg-gray-900/60 backdrop-blur-md p-5 rounded-2xl border border-gray-800 shadow-lg">
            
            {/* Goal Header */}
            <div className="flex justify-between items-start mb-2">
              <h4 className="text-base font-medium text-gray-100 flex items-center gap-2">
                <Target className="w-4 h-4 text-purple-400" /> {goal.title}
              </h4>
              <span className="text-xs font-mono font-bold text-indigo-400">{goal.progress}%</span>
            </div>
            
            <p className="text-[11px] text-gray-400 mb-4 line-clamp-1">{goal.description}</p>

            {/* Progress Bar */}
            <div className="w-full h-1.5 bg-gray-800 rounded-full mb-5 overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-700"
                style={{ width: `${goal.progress}%` }}
              />
            </div>

            {/* Sub Tasks */}
            <div className="space-y-2">
              {goal.tasks.map((task) => (
                <div key={task.id} className="flex items-start gap-2.5 group">
                  {task.is_completed ? (
                    <CheckCircle2 className="w-4 h-4 text-green-500 shrink-0 mt-0.5" />
                  ) : (
                    <Circle className="w-4 h-4 text-gray-600 shrink-0 mt-0.5 group-hover:text-indigo-400 transition-colors" />
                  )}
                  <span className={`text-sm ${task.is_completed ? 'text-gray-500 line-through' : 'text-gray-300'}`}>
                    {task.title}
                  </span>
                </div>
              ))}
            </div>
            
          </div>
        ))}
      </div>
    </div>
  );
}