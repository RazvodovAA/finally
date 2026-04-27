'use client';

import { useState } from 'react';

interface ChatPanelProps {
  isOpen?: boolean;
  onToggle?: () => void;
}

export function ChatPanel({ isOpen = true, onToggle }: ChatPanelProps) {
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([
    {
      role: 'assistant',
      content: 'Welcome to FinAlly! I can help you analyze your portfolio, execute trades, and manage your watchlist. Ask me anything about your positions or the market.',
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage = { role: 'user', content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content:
            'Chat integration coming soon. The AI assistant will help you analyze trades and manage your portfolio.',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className="terminal-panel h-full flex flex-col rounded-l">
      <div className="grid-header p-4 border-b border-terminal-border">
        <h3 className="ticker-label text-accent-yellow text-sm">AI Assistant</h3>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`px-3 py-2 rounded text-sm max-w-xs ${
                msg.role === 'user'
                  ? 'bg-accent-purple/30 text-accent-purple border border-accent-purple/50'
                  : 'bg-accent-blue/20 text-accent-blue border border-accent-blue/50'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="px-3 py-2 text-sm text-terminal-muted animate-pulse">
              Thinking...
            </div>
          </div>
        )}
      </div>

      <div className="border-t border-terminal-border p-4">
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Ask me anything..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter' && !loading) {
                handleSend();
              }
            }}
            disabled={loading}
            className="flex-1"
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="btn-trade btn-secondary disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
