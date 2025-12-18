import { useState } from 'react';
import type { ChatMessage as ChatMessageType, ChatSource } from '../api';

interface ChatMessageProps {
  message: ChatMessageType;
  sources?: ChatSource[];
}

export function ChatMessage({ message, sources }: ChatMessageProps) {
  const [showSources, setShowSources] = useState(false);
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-blue-600 text-white rounded-br-md'
            : 'bg-white border border-gray-200 text-gray-800 rounded-bl-md'
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>

        {!isUser && sources && sources.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-200">
            <button
              onClick={() => setShowSources(!showSources)}
              className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
            >
              <span>{showSources ? '▼' : '▶'}</span>
              <span>{sources.length} ta manba</span>
            </button>

            {showSources && (
              <ul className="mt-2 space-y-1">
                {sources.map((source) => (
                  <li
                    key={source.id}
                    className="text-sm text-gray-600 flex items-center gap-2"
                  >
                    <span className="text-xs text-gray-400">
                      {Math.round(source.relevance * 100)}%
                    </span>
                    <span>{source.title}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
