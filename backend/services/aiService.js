/**
 * Node.js AI Service Wrapper
 * Communicates via HTTP with the Python FastAPI AI Service (port 8000),
 * which is backed by the fine-tuned LLaMA model (question/follow-up
 * generation) and BERT sentence embeddings (semantic/meaning-based answer
 * evaluation), with a curated knowledge base used only as RAG context.
 *
 * There is intentionally NO local static question bank and NO local
 * keyword/length-based scoring here. If the Python AI microservice (and
 * therefore the fine-tuned LLaMA model) is unreachable, calls fail with a
 * clear error instead of silently degrading to canned questions or a crude
 * heuristic score -- both of which would defeat the point of generating
 * from the model and grading by meaning.
 */

const configuredAiServiceUrl = (process.env.AI_SERVICE_URL || 'http://localhost:8000/api/ai').replace(/\/+$/, '');
const AI_SERVICE_URL = configuredAiServiceUrl.endsWith('/api/ai')
  ? configuredAiServiceUrl
  : configuredAiServiceUrl.endsWith('/api')
    ? `${configuredAiServiceUrl}/ai`
    : `${configuredAiServiceUrl}/api/ai`;

const AI_SERVICE_UNAVAILABLE_MESSAGE =
  'The AI engine (fine-tuned LLaMA + BERT) is unavailable right now. Please make sure the ' +
  'Python AI microservice is running and Ollama has the configured model pulled, then try again.';

async function callAiService(path, body) {
  let response;
  try {
    response = await fetch(`${AI_SERVICE_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  } catch (error) {
    console.error(`[AI Service] Could not reach Python AI microservice at ${AI_SERVICE_URL}${path} (${error.message}).`);
    throw new Error(AI_SERVICE_UNAVAILABLE_MESSAGE);
  }

  if (response.ok) {
    return response.json();
  }

  const errBody = await response.text().catch(() => '');
  console.error(`[AI Service] Python AI microservice returned ${response.status} for ${path}: ${errBody.slice(0, 300)}`);

  // The Python service returns 503 with a helpful `detail` message when
  // generation specifically needs LLaMA and it isn't reachable -- surface
  // that message rather than a generic one when we have it.
  let detail;
  try {
    detail = JSON.parse(errBody).detail;
  } catch (_) {
    // not JSON / no detail field, fall through to the generic message
  }
  throw new Error(detail || AI_SERVICE_UNAVAILABLE_MESSAGE);
}

export const aiService = {
  // Generate Next Adaptive Question (theory or "predict the output"),
  // always via the fine-tuned LLaMA model in the Python AI microservice.
  async generateQuestion({ interviewType, subject, difficulty, previousQuestions, previousAnswers, questionNumber, questionFormat }) {
    return callAiService('/generate-question', {
      interviewType,
      subject: subject || 'N/A',
      difficulty: difficulty || 'medium',
      previousQuestions: previousQuestions || [],
      previousAnswers: previousAnswers || [],
      questionNumber: questionNumber || 1,
      questionFormat: questionFormat || 'theory',
    });
  },

  // Generate Adaptive Follow-Up Question, always via the fine-tuned LLaMA model.
  async generateFollowUp({ interviewType, subject, difficulty, previousQuestion, studentAnswer, expectedConcepts, previousQuestions }) {
    return callAiService('/generate-followup', {
      interviewType,
      subject: subject || 'N/A',
      difficulty: difficulty || 'medium',
      previousQuestion,
      studentAnswer,
      expectedConcepts: expectedConcepts || [],
      // Every question already asked this session, so the AI service can
      // avoid repeating a follow-up shape it already used earlier -- see
      // ai-service/app/models/llama_provider.py generate_followup.
      previousQuestions: previousQuestions || [],
    });
  },

  // Evaluate Student Response using meaning-based (BERT embedding
  // similarity, blended with the LLaMA grader) semantic matching -- never
  // keyword substring matching or a bare answer-length heuristic.
  async evaluateAnswer({ interviewType, subject, question, answer, expectedConcepts, questionFormat, expectedOutput, explanation, testCases, language, schema, sampleData, referenceSolution, hrDeliveryMetrics }) {
    return callAiService('/evaluate-answer', {
      interviewType,
      subject: subject || 'N/A',
      question,
      answer,
      expectedConcepts: expectedConcepts || [],
      questionFormat: questionFormat || 'theory',
      expectedOutput: expectedOutput || null,
      explanation: explanation || null,
      testCases: testCases || null,
      language: language || null,
      schema: schema || null,
      sampleData: sampleData || null,
      referenceSolution: referenceSolution || null,
      ...(interviewType === 'hr' && hrDeliveryMetrics ? { hrDeliveryMetrics } : {}),
    });
  },
};
