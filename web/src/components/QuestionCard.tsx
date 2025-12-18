import { Link } from 'react-router-dom';
import type { SearchResult } from '../api';

interface QuestionCardProps {
  question: SearchResult;
}

export function QuestionCard({ question }: QuestionCardProps) {
  return (
    <Link
      to={`/question/${question.id}`}
      className="block p-4 bg-white rounded-lg border border-gray-200 hover:border-blue-300 hover:shadow-md transition-all"
    >
      <h3 className="text-lg font-medium text-gray-900 mb-2 line-clamp-2">
        {question.title}
      </h3>
      <p className="text-gray-600 text-sm mb-3 line-clamp-2">
        {question.answer_preview}...
      </p>
      <div className="flex items-center gap-3 text-sm text-gray-500">
        {question.category && (
          <span className="px-2 py-1 bg-blue-50 text-blue-700 rounded">
            {question.category}
          </span>
        )}
        {question.view_count !== null && question.view_count > 0 && (
          <span>{question.view_count.toLocaleString()} ko'rilgan</span>
        )}
      </div>
    </Link>
  );
}
