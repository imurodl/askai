import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { SearchBar } from '../components/SearchBar';
import { getQuestion, type QuestionDetail } from '../api';

export function Question() {
  const { id } = useParams<{ id: string }>();
  const [question, setQuestion] = useState<QuestionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;

    let cancelled = false;

    async function fetchQuestion() {
      try {
        const data = await getQuestion(Number(id));
        if (!cancelled) {
          setQuestion(data);
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError('Savol topilmadi');
          setLoading(false);
          console.error(err);
        }
      }
    }

    // eslint-disable-next-line react-hooks/set-state-in-effect -- Reset state on id change is valid
    setQuestion(null);
    setLoading(true);
    setError(null);
    fetchQuestion();

    return () => {
      cancelled = true;
    };
  }, [id]);

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Link to="/" className="text-xl font-bold text-blue-600">
              AskAI
            </Link>
            <div className="flex-1">
              <SearchBar />
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6">
        {loading ? (
          <div className="text-center py-12 text-gray-500">Yuklanmoqda...</div>
        ) : error ? (
          <div className="text-center py-12 text-red-500">{error}</div>
        ) : question ? (
          <article className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <div className="p-6">
              <h1 className="text-2xl font-bold text-gray-900 mb-4">
                {question.title}
              </h1>

              <div className="flex items-center gap-3 text-sm text-gray-500 mb-6">
                {question.category && (
                  <span className="px-2 py-1 bg-blue-50 text-blue-700 rounded">
                    {question.category}
                  </span>
                )}
                {question.view_count !== null && question.view_count > 0 && (
                  <span>{question.view_count.toLocaleString()} ko'rilgan</span>
                )}
                {question.published_date && (
                  <span>{question.published_date}</span>
                )}
              </div>

              {question.question && (
                <div className="mb-6">
                  <h2 className="text-lg font-semibold text-gray-800 mb-2">
                    Savol
                  </h2>
                  <p className="text-gray-700 whitespace-pre-wrap">
                    {question.question}
                  </p>
                </div>
              )}

              <div className="border-t border-gray-200 pt-6">
                <h2 className="text-lg font-semibold text-gray-800 mb-2">
                  Javob
                </h2>
                <div className="text-gray-700 whitespace-pre-wrap">
                  {question.answer}
                </div>
                {question.author && (
                  <p className="mt-4 text-sm text-gray-500">
                    Javob beruvchi: {question.author}
                  </p>
                )}
              </div>
            </div>

            {question.related_questions.length > 0 && (
              <div className="border-t border-gray-200 bg-gray-50 p-6">
                <h2 className="text-lg font-semibold text-gray-800 mb-3">
                  O'xshash savollar
                </h2>
                <ul className="space-y-2">
                  {question.related_questions.map((rq) => (
                    <li key={rq.id}>
                      <Link
                        to={`/question/${rq.id}`}
                        className="text-blue-600 hover:text-blue-800 hover:underline"
                      >
                        {rq.title}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </article>
        ) : null}
      </main>
    </div>
  );
}
