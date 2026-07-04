"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";

// SSR পুরোপুরি অফ করা হলো
const ChatApp = dynamic(() => import("./ChatApp"), { ssr: false });

export default function Page() {
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  if (!isMounted) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-900">
        <div className="text-blue-500 animate-pulse font-mono">Initializing Aura OS...</div>
      </div>
    );
  }

  return <ChatApp />;
}