const API_BASE = '/api';

export interface SearchResult {
  id: number;
  url: string;
  title: string;
  category: string | null;
  view_count: number | null;
  answer_preview: string;
}

export interface SearchResponse {
  results: SearchResult[];
  total: number;
  query: string;
  limit: number;
  offset: number;
}

export interface RelatedQuestion {
  id: number;
  title: string;
  url: string;
}

export interface QuestionDetail {
  id: number;
  url: string;
  title: string;
  question: string | null;
  answer: string;
  author: string | null;
  category: string | null;
  published_date: string | null;
  view_count: number | null;
  related_questions: RelatedQuestion[];
}

export async function searchQuestions(
  query: string,
  limit = 20,
  offset = 0
): Promise<SearchResponse> {
  const params = new URLSearchParams({
    q: query,
    limit: limit.toString(),
    offset: offset.toString(),
  });
  const response = await fetch(`${API_BASE}/search?${params}`);
  if (!response.ok) {
    throw new Error('Search failed');
  }
  return response.json();
}

export async function getQuestion(id: number): Promise<QuestionDetail> {
  const response = await fetch(`${API_BASE}/questions/${id}`);
  if (!response.ok) {
    throw new Error('Question not found');
  }
  return response.json();
}

export async function getPopularQuestions(
  limit = 10
): Promise<{ results: SearchResult[] }> {
  const response = await fetch(`${API_BASE}/popular?limit=${limit}`);
  if (!response.ok) {
    throw new Error('Failed to fetch popular questions');
  }
  return response.json();
}

// Chat types
export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatSource {
  id: number;
  title: string;
  relevance: number;
}

export interface ChatResponse {
  answer: string;
  sources: ChatSource[];
  source_type: 'database' | 'ai_knowledge' | 'conversational';
  disclaimer?: string;
}

export async function sendChatMessage(
  message: string,
  history: ChatMessage[] = []
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message, history }),
  });
  if (!response.ok) {
    throw new Error('Chat request failed');
  }
  return response.json();
}
