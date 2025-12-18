import { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { SearchBar } from '../components/SearchBar';
import { QuestionCard } from '../components/QuestionCard';
import { searchQuestions, type SearchResult } from '../api';

export function Search() {
  const [searchParams] = useSearchParams();
  const query = searchParams.get('q') || '';
  const [results, setResults] = useState<SearchResult[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!query) return;

    setLoading(true);
    setError(null);

    searchQuestions(query)
      .then((data) => {
        setResults(data.results);
        setTotal(data.total);
      })
      .catch((err) => {
        setError('Qidirishda xatolik yuz berdi');
        console.error(err);
      })
      .finally(() => setLoading(false));
  }, [query]);

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Link to="/" className="text-xl font-bold text-blue-600">
              AskAI
            </Link>
            <div className="flex-1">
              <SearchBar initialQuery={query} />
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6">
        {loading ? (
          <div className="text-center py-12 text-gray-500">Qidirilmoqda...</div>
        ) : error ? (
          <div className="text-center py-12 text-red-500">{error}</div>
        ) : results.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            "{query}" bo'yicha natija topilmadi
          </div>
        ) : (
          <>
            <p className="text-sm text-gray-500 mb-4">
              {total} ta natija topildi
            </p>
            <div className="space-y-4">
              {results.map((q) => (
                <QuestionCard key={q.id} question={q} />
              ))}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
