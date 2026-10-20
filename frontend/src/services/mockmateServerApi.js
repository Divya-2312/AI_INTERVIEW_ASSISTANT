// frontend/src/services/mockmateServerApi.js
const SERVER_URL = import.meta.env.VITE_MOCKMATE_SERVER_URL || 'http://127.0.0.1:8001';

export const mockmateServerApi = {
  // Check if server and model are online
  async checkHealth() {
    const res = await fetch(`${SERVER_URL}/health`);
    if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
    return await res.json();
  },

  // Get a random HR question (optional category filter)
  async getRandomQuestion(category = null) {
    const url = category
      ? `${SERVER_URL}/questions/random?category=${encodeURIComponent(category)}`
      : `${SERVER_URL}/questions/random`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Failed to load question: ${res.statusText}`);
    return await res.json();
  },

  // Evaluate candidate's HR answer
  async evaluateHR(questionId, answerText) {
    const res = await fetch(`${SERVER_URL}/evaluate_hr`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question_id: questionId,
        answer: answerText,
      }),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || 'Evaluation failed');
    }
    return data;
  },

  // Analyze code time and space complexity
  async checkComplexity(code, questionText = '') {
    const res = await fetch(`${SERVER_URL}/complexity`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        code: code,
        question: questionText || 'Find the time and space complexity.',
      }),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || 'Complexity analysis failed');
    }
    return data;
  },
};
