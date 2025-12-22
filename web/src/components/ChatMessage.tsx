import { useState } from 'react';
import type { ChatMessage as ChatMessageType, ChatSource, QuestionDetail } from '../api';
import { getQuestion } from '../api';

interface ChatMessageProps {
  message: ChatMessageType;
  sources?: ChatSource[];
}

interface ModalProps {
  question: QuestionDetail;
  onClose: () => void;
}

function QuestionModal({ question, onClose }: ModalProps) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50" onClick={onClose}>
      <div
        className="bg-white rounded-xl max-w-2xl w-full max-h-[80vh] overflow-hidden shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="bg-blue-600 text-white px-6 py-4 flex justify-between items-start">
          <h2 className="text-lg font-semibold pr-4">{question.title}</h2>
          <button
            onClick={onClose}
            className="text-white/80 hover:text-white text-2xl leading-none"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(80vh-80px)]">
          {question.question && (
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-gray-500 uppercase mb-2">Savol</h3>
              <p className="text-gray-700 whitespace-pre-wrap">{question.question}</p>
            </div>
          )}

          <div>
            <h3 className="text-sm font-semibold text-gray-500 uppercase mb-2">Javob</h3>
            <div className="text-gray-700 whitespace-pre-wrap">{question.answer}</div>
          </div>

          {question.category && (
            <div className="mt-6 pt-4 border-t border-gray-200">
              <span className="inline-block px-3 py-1 bg-gray-100 text-gray-600 text-sm rounded-full">
                {question.category}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function ChatMessage({ message, sources }: ChatMessageProps) {
  const [showSources, setShowSources] = useState(false);
  const [selectedQuestion, setSelectedQuestion] = useState<QuestionDetail | null>(null);
  const [loadingId, setLoadingId] = useState<number | null>(null);
  const isUser = message.role === 'user';

  const handleSourceClick = async (sourceId: number) => {
    setLoadingId(sourceId);
    try {
      const question = await getQuestion(sourceId);
      setSelectedQuestion(question);
    } catch (error) {
      console.error('Failed to load question:', error);
    } finally {
      setLoadingId(null);
    }
  };

  return (
    <>
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
                <ul className="mt-2 space-y-2">
                  {sources.map((source) => (
                    <li key={source.id}>
                      <button
                        onClick={() => handleSourceClick(source.id)}
                        disabled={loadingId === source.id}
                        className="text-left w-full p-2 rounded-lg hover:bg-gray-50 transition-colors flex items-start gap-2 group"
                      >
                        <span className="text-xs text-gray-400 mt-0.5 shrink-0">
                          {Math.round(source.relevance * 100)}%
                        </span>
                        <span className="text-sm text-blue-600 group-hover:text-blue-800 group-hover:underline">
                          {loadingId === source.id ? 'Yuklanmoqda...' : source.title}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      </div>

      {selectedQuestion && (
        <QuestionModal
          question={selectedQuestion}
          onClose={() => setSelectedQuestion(null)}
        />
      )}
    </>
  );
}
