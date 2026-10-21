
import { useState } from "react";
import { Send } from "lucide-react";

import AnalysisCard from "../components/AnalysisCard";
import { sendMessage } from "../services/chatApi";

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(null);

  async function handleSend() {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput("");

    setMessages((prev) => [
      ...prev,
      {
        role: "user",
        content: userMessage,
      },
    ]);

    try {
      setLoading(true);

      const response = await sendMessage(userMessage, sessionId);

      console.log("Backend Response:", response);

      if (!sessionId && response.session_id) {
        setSessionId(response.session_id);
      }

      // Preserve all fields returned by the backend,
      // including tile_url, bounds, and visualization.
      setMessages((prev) => [
        ...prev,
        {
          ...response,
          role: "assistant",
        },
      ]);

      console.log("Interactive map fields:", {
        tile_url: response.tile_url,
        bounds: response.bounds,
        visualization: response.visualization,
        preview_url: response.preview_url,
      });
    } catch (error) {
      console.error("Chat request failed:", error);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          reply: "Error while processing request. Please try again.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-screen flex-col bg-slate-50 transition-all duration-300 dark:bg-[#0f172a]">
      {/* Header */}
      <div className="border-b border-slate-200 bg-white px-8 py-4 dark:border-slate-800 dark:bg-[#111827]">
        <div className="mx-auto max-w-6xl">
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-white">
            GeoVision AI
          </h1>

          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Natural Language Earth Observation &amp; Satellite Analytics
          </p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-8">
        <div className="mx-auto max-w-6xl space-y-6">
          {messages.map((msg, index) => (
            <div key={index}>
              {/* User message */}
              {msg.role === "user" && (
                <div className="flex justify-end">
                  <div className="max-w-2xl rounded-2xl bg-blue-600 px-5 py-4 text-white">
                    {msg.content}
                  </div>
                </div>
              )}

              {/* Assistant response */}
              {msg.role === "assistant" && (
                <AnalysisCard data={msg} />
              )}
            </div>
          ))}

          {/* Loading */}
          {loading && (
            <div className="text-slate-500 dark:text-slate-400">
              Processing satellite analysis...
            </div>
          )}
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-slate-200 bg-white px-6 py-5 dark:border-slate-800 dark:bg-[#111827]">
        <form
          className="mx-auto flex max-w-6xl gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            handleSend();
          }}
        >
          <input
            type="text"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Ask about NDVI, NDWI, SAR, Flood Mapping, Urban Heat Island..."
            disabled={loading}
            className="flex-1 rounded-2xl border border-slate-300 bg-white px-5 py-4 text-slate-900 outline-none placeholder:text-slate-400 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
          />

          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="rounded-2xl bg-blue-600 px-6 text-white transition-all hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            aria-label="Send message"
          >
            <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
}
