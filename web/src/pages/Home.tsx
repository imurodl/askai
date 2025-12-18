import { useEffect, useState } from 'react';
import { SearchBar } from '../components/SearchBar';
import { QuestionCard } from '../components/QuestionCard';
import { getPopularQuestions, type SearchResult } from '../api';

export function Home() {
  const [popularQuestions, setPopularQuestions] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getPopularQuestions(6)
      .then((data) => setPopularQuestions(data.results))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-16">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">AskAI</h1>
          <p className="text-lg text-gray-600 mb-8">
            Islomiy savollar va javoblar bazasi
          </p>
          <div className="flex justify-center">
            <SearchBar autoFocus />
          </div>
        </div>

        {!loading && popularQuestions.length > 0 && (
          <div className="mt-16">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Mashhur savollar
            </h2>
            <div className="grid gap-4 md:grid-cols-2">
              {popularQuestions.map((q) => (
                <QuestionCard key={q.id} question={q} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
