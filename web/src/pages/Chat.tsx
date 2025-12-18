import { useState, useRef, useEffect } from 'react';
import { ChatMessage } from '../components/ChatMessage';
import { ChatInput } from '../components/ChatInput';
import {
  sendChatMessage,
  type ChatMessage as ChatMessageType,
  type ChatSource,
} from '../api';

interface Message extends ChatMessageType {
  sources?: ChatSource[];
}

export function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (text: string) => {
    // Add user message
    const userMessage: Message = { role: 'user', content: text };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    try {
      // Build history for API (exclude sources)
      const history: ChatMessageType[] = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      // Send to API
      const response = await sendChatMessage(text, history);

      // Add assistant message with sources
      const assistantMessage: Message = {
        role: 'assistant',
        content: response.answer,
        sources: response.sources,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage: Message = {
        role: 'assistant',
        content: 'Kechirasiz, xatolik yuz berdi. Iltimos, qaytadan urinib ko\'ring.',
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-4 py-3">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <h1 className="text-xl font-bold text-blue-600">AskAI</h1>
          <span className="text-sm text-gray-500">Islomiy savol-javob</span>
        </div>
      </header>

      {/* Messages */}
      <main className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-3xl mx-auto">
          {messages.length === 0 ? (
            <div className="text-center py-20">
              <h2 className="text-2xl font-bold text-gray-800 mb-2">
                Assalomu alaykum!
              </h2>
              <p className="text-gray-600 mb-8">
                Islomiy savollaringizga javob olish uchun savolingizni yozing.
              </p>
              <div className="flex flex-wrap justify-center gap-2">
                {[
                  'Namoz qanday o\'qiladi?',
                  'Ro\'za tutish haqida',
                  'Zakot nima?',
                ].map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => handleSend(suggestion)}
                    className="px-4 py-2 bg-white border border-gray-300 rounded-full text-sm text-gray-700 hover:bg-gray-50 hover:border-blue-300 transition-colors"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {messages.map((message, index) => (
                <ChatMessage
                  key={index}
                  message={message}
                  sources={message.sources}
                />
              ))}
              {loading && (
                <div className="flex justify-start mb-4">
                  <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-md px-4 py-3">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>
      </main>

      {/* Input */}
      <footer className="bg-white border-t border-gray-200 px-4 py-4">
        <div className="max-w-3xl mx-auto">
          <ChatInput onSend={handleSend} disabled={loading} />
        </div>
      </footer>
    </div>
  );
}
