import { useState } from 'react';
import Markdown from 'react-markdown';
import type { ChatMessage as ChatMessageType, ChatSource, QuestionDetail, ChatResponse } from '../api';
import { getQuestion } from '../api';

/**
 * Format text with Arabic quotes and nested Q&A patterns
 * - Arabic text (U+0600-U+06FF) → newline + italic quote style
 * - Nested Q&A (Савол:, ЖАВОБ:, etc.) → newline before
 */
function formatText(text: string): React.ReactNode[] {
  // Pattern for Arabic text (includes Arabic letters, marks, and common punctuation)
  const arabicPattern = /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+(?:[\s\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\u060C\u061B\u061F\u0640\.:,]+[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+)*/g;

  // Pattern for nested Q&A markers (case insensitive)
  const qaPattern = /(Савол:|Cавол:|САВОЛ:|ЖАВОБ:|Жавоб:|савол:|жавоб:)/g;

  // Pattern for numbered list items (1., 2., etc.) - only match if not at start of text
  const numberedPattern = /(?<=.)(\d+\.)/g;

  // First, mark positions for all patterns
  const segments: { start: number; end: number; type: 'arabic' | 'qa' | 'numbered'; text: string }[] = [];

  // Find Arabic segments
  let match;
  while ((match = arabicPattern.exec(text)) !== null) {
    // Only include if it's substantial (more than just punctuation)
    if (match[0].length > 3) {
      segments.push({
        start: match.index,
        end: match.index + match[0].length,
        type: 'arabic',
        text: match[0]
      });
    }
  }

  // Find Q&A markers
  while ((match = qaPattern.exec(text)) !== null) {
    segments.push({
      start: match.index,
      end: match.index + match[0].length,
      type: 'qa',
      text: match[0]
    });
  }

  // Find numbered list items
  while ((match = numberedPattern.exec(text)) !== null) {
    segments.push({
      start: match.index,
      end: match.index + match[0].length,
      type: 'numbered',
      text: match[0]
    });
  }

  // Sort by position
  segments.sort((a, b) => a.start - b.start);

  // Build result
  const result: React.ReactNode[] = [];
  let lastEnd = 0;

  segments.forEach((seg, idx) => {
    // Add text before this segment
    if (seg.start > lastEnd) {
      const beforeText = text.slice(lastEnd, seg.start);
      if (beforeText) {
        result.push(<span key={`text-${idx}`}>{beforeText}</span>);
      }
    }

    // Add the formatted segment
    if (seg.type === 'arabic') {
      result.push(
        <span key={`arabic-${idx}`} className="block my-2 pr-4 py-1 text-gray-800 dark:text-gray-200 font-arabic text-right italic border-r-2 border-emerald-500 dark:border-emerald-400" dir="rtl">
          {seg.text}
        </span>
      );
    } else if (seg.type === 'qa') {
      // Just add newline before, keep text flowing
      result.push(
        <span key={`qa-${idx}`}>
          <br />{seg.text}
        </span>
      );
    } else if (seg.type === 'numbered') {
      // Newline before, indent, then text continues
      result.push(
        <span key={`num-${idx}`}>
          <br />{'    '}{seg.text}
        </span>
      );
    }

    lastEnd = seg.end;
  });

  // Add remaining text
  if (lastEnd < text.length) {
    result.push(<span key="text-end">{text.slice(lastEnd)}</span>);
  }

  return result.length > 0 ? result : [<span key="plain">{text}</span>];
}

interface ChatMessageProps {
  message: ChatMessageType;
  sources?: ChatSource[];
  sourceType?: ChatResponse['source_type'];
  disclaimer?: string;
}

interface ModalProps {
  question: QuestionDetail;
  onClose: () => void;
}

function QuestionModal({ question, onClose }: ModalProps) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50" onClick={onClose}>
      <div
        className="bg-white dark:bg-gray-800 rounded-xl max-w-2xl w-full max-h-[80vh] overflow-hidden shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="bg-blue-600 dark:bg-blue-700 text-white px-6 py-4 flex justify-between items-start">
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
              <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase mb-2">Savol</h3>
              <div className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{formatText(question.question)}</div>
            </div>
          )}

          <div>
            <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase mb-2">Javob</h3>
            <div className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{formatText(question.answer)}</div>
          </div>

          {question.category && (
            <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
              <span className="inline-block px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 text-sm rounded-full">
                {question.category}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function ChatMessage({ message, sources, sourceType, disclaimer }: ChatMessageProps) {
  const [showSources, setShowSources] = useState(false);
  const [selectedQuestion, setSelectedQuestion] = useState<QuestionDetail | null>(null);
  const [loadingId, setLoadingId] = useState<number | null>(null);
  const isUser = message.role === 'user';
  const isAiKnowledge = sourceType === 'ai_knowledge';

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
              ? 'bg-blue-600 dark:bg-blue-500 text-white rounded-br-md'
              : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-800 dark:text-gray-200 rounded-bl-md'
          }`}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <Markdown>{message.content}</Markdown>
            </div>
          )}

          {/* Sources section for database answers */}
          {!isUser && sources && sources.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={() => setShowSources(!showSources)}
                className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 flex items-center gap-1"
              >
                <span>{showSources ? '▼' : '▶'}</span>
                <span>{sources.length} ta manba</span>
              </button>

              {showSources && (
                <ul className="mt-2 space-y-2">
                  {sources.map((source, index) => (
                    <li key={source.id}>
                      <button
                        onClick={() => handleSourceClick(source.id)}
                        disabled={loadingId === source.id}
                        className="text-left w-full p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors flex items-start gap-2 group"
                      >
                        <span className="text-xs text-gray-400 dark:text-gray-500 mt-0.5 shrink-0">
                          {index + 1}.
                        </span>
                        <span className="text-sm text-blue-600 dark:text-blue-400 group-hover:text-blue-800 dark:group-hover:text-blue-300 group-hover:underline">
                          {loadingId === source.id ? 'Yuklanmoqda...' : source.title}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {/* Disclaimer for AI-generated answers */}
          {!isUser && isAiKnowledge && disclaimer && (
            <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
              <div className="flex items-start gap-2 p-2 bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-700 rounded-lg">
                <span className="text-amber-500 shrink-0">⚠️</span>
                <p className="text-xs text-amber-700 dark:text-amber-300">{disclaimer}</p>
              </div>
              <p className="mt-2 text-xs text-gray-400 dark:text-gray-500 flex items-center gap-1">
                <span>🤖</span>
                <span>AI bilimi asosida</span>
              </p>
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
