from pydantic import BaseModel, Field
from typing import List, Optional, Any

class QuestionGenerationRequest(BaseModel):
    interviewType: str = Field(..., description="technical or hr")
    subject: Optional[str] = Field(default="N/A", description="java, dbms, or N/A")
    difficulty: str = Field(default="medium", description="easy, medium, hard")
    previousQuestions: List[str] = Field(default_factory=list)
    previousAnswers: List[str] = Field(default_factory=list)
    questionNumber: int = Field(default=1)
    # "theory" (default) = plain explanation-style question.
    # "output_prediction" = candidate is given a short code snippet and must
    # state what it outputs, instead of explaining a concept in prose.
    # "coding" = candidate is given a coding problem (e.g. "write a program
    # to compute the factorial of a number") plus test cases, and must
    # submit working code -- generated and graded by LLaMA, not executed.
    questionFormat: str = Field(default="theory", description="theory, output_prediction, or coding")

class FollowUpRequest(BaseModel):
    interviewType: str
    subject: Optional[str] = "N/A"
    difficulty: str = "medium"
    previousQuestion: str
    studentAnswer: str
    expectedConcepts: Optional[List[str]] = []
    # Every question (main + follow-up) already asked so far this session,
    # so the model can avoid repeating/paraphrasing a follow-up it already
    # asked earlier in the same interview. Without this the generator only
    # ever sees the single most recent Q/A pair and has no memory of
    # earlier follow-ups, which is why follow-ups could come out looking
    # repetitive across a session.
    previousQuestions: Optional[List[str]] = []

class TestCase(BaseModel):
    input: str = ""
    expectedOutput: str = ""
    # Optional short label shown to the candidate before grading, e.g.
    # "Basic case" or "Edge case: n = 0". Never reveals expectedOutput.
    label: Optional[str] = None

class HRDeliveryMetrics(BaseModel):
    # Approximations from browser-recognition text and callback timestamps,
    # not measurements from raw audio or prosody analysis.
    fillerWordCount: int = 0
    fillerFrequencyPer100Words: float = 0.0
    noticeablePauseCount: int = 0
    repetitionCount: int = 0
    sentenceCompleteness: str = "possible_fragment"
    segmentTimestamps: List[float] = Field(default_factory=list)

class HRDeliveryAssessment(BaseModel):
    fillerWordCount: int
    fillerFrequencyPer100Words: float
    noticeablePauseCount: int
    repetitionCount: int
    sentenceCompleteness: str
    observations: List[str] = Field(default_factory=list)

class AnswerEvaluationRequest(BaseModel):
    interviewType: str
    subject: Optional[str] = "N/A"
    question: str
    answer: str
    expectedConcepts: Optional[List[str]] = []
    questionFormat: str = Field(default="theory", description="theory, output_prediction, or coding")
    # Only used when questionFormat == "output_prediction": the actual
    # ground-truth output of the code snippet the candidate was shown.
    expectedOutput: Optional[str] = None
    # Hidden step-by-step derivation of expectedOutput, carried through
    # from question generation untouched -- shown to the candidate only
    # after they answer, as part of the evaluation result. Also reused for
    # "coding" as the hidden reference approach/solution outline.
    explanation: Optional[str] = None
    # Only used when questionFormat == "coding": the test cases (input +
    # expected output) generated alongside the question, carried through
    # untouched so evaluation can grade the candidate's submitted code
    # against them.
    testCases: Optional[List[TestCase]] = None
    # Only used when questionFormat == "coding": the programming language
    # the candidate is expected to write in (e.g. "java", "python", "sql").
    language: Optional[str] = None
    starterCode: Optional[str] = None
    referenceSolution: Optional[str] = None
    schema_: Optional[str] = Field(default=None, alias="schema")
    sampleData: Optional[str] = None
    hrDeliveryMetrics: Optional[HRDeliveryMetrics] = None

    model_config = {"populate_by_name": True}

class QuestionResponse(BaseModel):
    questionText: str
    questionType: str = "normal"  # 'normal' or 'follow_up'
    subject: str
    difficulty: str
    category: str
    expectedConcepts: List[str]
    questionFormat: str = "theory"
    codeSnippet: Optional[str] = None      # only set when questionFormat == "output_prediction"
    expectedOutput: Optional[str] = None   # only set when questionFormat == "output_prediction" (used later for grading, not shown to candidate)
    explanation: Optional[str] = None      # only set when questionFormat in ("output_prediction", "coding"); hidden until after grading
    language: Optional[str] = None
    title: Optional[str] = None
    schema_: Optional[str] = Field(default=None, alias="schema")
    sampleData: Optional[str] = None
    starterCode: Optional[str] = None
    referenceSolution: Optional[str] = None
    testCases: Optional[List[TestCase]] = None
    modelUsed: str = Field(default="llama3.2:3b", description="The measured model used for generation")

    model_config = {"populate_by_name": True}

class EvaluationResponse(BaseModel):
    score: int
    conceptCoverage: Optional[float] = None
    correctness: Optional[float] = None
    relevance: Optional[float] = None
    communication: Optional[float] = None
    isIrrelevant: bool = False
    feedback: str
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    coveredConcepts: List[str] = Field(default_factory=list)
    partiallyCoveredConcepts: List[str] = Field(default_factory=list)
    missingConcepts: List[str] = Field(default_factory=list)
    deeperConcepts: List[str] = Field(default_factory=list)
    improvementSuggestion: Optional[str] = None
    scoreReason: str = ""
    whyNot100: Optional[str] = None
    stepByStepExplanation: Optional[str] = None
    passedCount: Optional[int] = None
    totalCount: Optional[int] = None
    judgeMode: Optional[str] = None
    compileError: Optional[str] = None
    testCaseResults: Optional[List[Any]] = None
    correctedCode: Optional[str] = None
    correctedQuery: Optional[str] = None
    correctionSummary: Optional[str] = None
    deliveryMetrics: Optional[HRDeliveryAssessment] = None
    accuracy: Optional[float] = None
    timeComplexity: Optional[str] = None
    spaceComplexity: Optional[str] = None
    timeComplexityExplanation: Optional[str] = None
    modelUsed: str = Field(default="llama3.2:3b", description="The measured model used for evaluation")
    usedFallback: bool = Field(default=False, description="True if any non-LLM fallback path produced the content")
    parseFailed: bool = Field(default=False, description="True if JSON extraction failed or required keys were missing")
    scoringSources: List[str] = Field(default_factory=lambda: ["llm", "bert", "rules"], description="Sources used to calculate the score")
