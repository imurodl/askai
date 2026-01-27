import { useState } from 'react';
import { v4 as uuidv4 } from 'uuid';

const SESSION_KEY = 'askai_session_id';

export function useSession() {
  const [sessionId] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(SESSION_KEY);
      if (saved) return saved;
      const newId = uuidv4();
      localStorage.setItem(SESSION_KEY, newId);
      return newId;
    }
    return uuidv4();
  });

  return { sessionId };
}
