from app.models.schemas import AnswerEvaluationRequest, EvaluationResponse
from app.models.llama_provider import get_ai_model_provider
from app.services.rag_service import rag_service
from app.utils.hr_scoring import calculate_hr_overall

class AnswerEvaluator:
    def __init__(self):
        self.provider = get_ai_model_provider()

    def evaluate(self, req: AnswerEvaluationRequest) -> EvaluationResponse:
        # Empty-answer guard lives here so it applies no matter which
        # provider (LlamaModel / DevFallbackModel) ends up handling the
        # request -- never spend an LLM call or fabricate a score for a
        # blank submission.
        if not (req.answer or "").strip():
            return EvaluationResponse(
                score=0,
                conceptCoverage=0.0,
                correctness=0.0,
                relevance=0.0,
                communication=0.0,
                isIrrelevant=False,
                feedback="No answer was provided.",
                strengths=[],
                weaknesses=["No answer submitted"],
                missingConcepts=req.expectedConcepts or [],
                scoreReason="Score is 0% because no answer was submitted for this question.",
            )

        hr_delivery_metrics = (
            req.hrDeliveryMetrics.dict()
            if req.interviewType.lower() == "hr" and req.hrDeliveryMetrics
            else None
        )
        # interview_type lets the provider pick the HR evaluator (average of
        # correctness/relevance/accuracy/communication) -- every other type keeps
        # its own scoring.
        evaluation_options = {"interview_type": req.interviewType}
        if hr_delivery_metrics:
            evaluation_options["hr_delivery_metrics"] = hr_delivery_metrics

        context = rag_service.retrieve_context(req.subject or "general", req.question, top_k=2)
        eval_data = self.provider.evaluate_answer(
            req.question, req.answer, req.expectedConcepts or [], context,
            question_format=req.questionFormat or "theory",
            expected_output=req.expectedOutput,
            explanation=req.explanation,
            test_cases=[tc.dict() for tc in (req.testCases or [])] or None,
            language=req.language,
            schema=req.schema_,
            sample_data=req.sampleData,
            reference_solution=req.referenceSolution,
            **evaluation_options,
        )

        # Delivery adjustment only applies to relevant HR answers; an
        # irrelevant answer stays at the 0 score the relevancy check gave it.
        if hr_delivery_metrics and not eval_data.get("isIrrelevant"):
            eval_data = self._apply_hr_delivery_metrics(eval_data, hr_delivery_metrics)
        return EvaluationResponse(**eval_data)

    @staticmethod
    def _apply_hr_delivery_metrics(eval_data: dict, metrics: dict) -> dict:
        # Only penalize repeated, noticeable patterns; one pause or isolated
        # self-correction is normal conversation, not evidence of poor delivery.
        filler_count = metrics.get("fillerWordCount", 0)
        filler_frequency = metrics.get("fillerFrequencyPer100Words", 0)
        pause_count = metrics.get("noticeablePauseCount", 0)
        repetition_count = metrics.get("repetitionCount", 0)
        fragment = metrics.get("sentenceCompleteness") == "possible_fragment"
        penalty = 0
        observations = []

        if filler_count >= 3 or (filler_count >= 2 and filler_frequency >= 5):
            penalty += min(5, 1 + filler_count // 2)
            observations.append(f"Frequent filler words were recognized ({filler_count} total).")
        if pause_count >= 3:
            penalty += min(3, pause_count - 2)
            observations.append(f"Several noticeable pauses were recognized ({pause_count} gaps over 1.8 seconds).")
        elif pause_count == 2:
            penalty += 1
            observations.append("Two noticeable pauses were recognized (gaps over 1.8 seconds).")
        if repetition_count >= 2:
            penalty += min(4, repetition_count // 2)
            observations.append(f"Several repeated words or phrases were recognized ({repetition_count} repetitions).")
        if fragment:
            penalty += 3
            observations.append("The transcript may contain a fragment or trail off before completing a sentence.")

        if not observations:
            eval_data["deliveryMetrics"] = {
                "fillerWordCount": filler_count,
                "fillerFrequencyPer100Words": filler_frequency,
                "noticeablePauseCount": pause_count,
                "repetitionCount": repetition_count,
                "sentenceCompleteness": metrics.get("sentenceCompleteness", "possible_fragment"),
                "observations": observations,
            }
            return eval_data

        if eval_data.get("accuracy") is not None:
            # HR: the overall score is the average of correctness, relevance,
            # accuracy and communication, so delivery issues lower the
            # Communication factor (same point impact on the overall score)
            # instead of being subtracted from the average afterwards.
            communication = float(eval_data.get("communication") or 0.0)
            eval_data["communication"] = round(max(0.0, communication - penalty * 4 / 100.0), 2)
            eval_data["score"] = calculate_hr_overall(
                eval_data.get("correctness"), eval_data.get("relevance"),
                eval_data.get("accuracy"), eval_data["communication"],
            )
        else:
            eval_data["score"] = max(0, int(eval_data.get("score", 0)) - penalty)
        eval_data["feedback"] = (eval_data.get("feedback", "").rstrip() + " Delivery observations: " + " ".join(observations)).strip()
        eval_data["scoreReason"] = (eval_data.get("scoreReason", "").rstrip() + " Delivery also affected the score: " + " ".join(observations)).strip()
        eval_data["weaknesses"] = list(eval_data.get("weaknesses") or []) + observations
        eval_data["deliveryMetrics"] = {
            "fillerWordCount": filler_count,
            "fillerFrequencyPer100Words": filler_frequency,
            "noticeablePauseCount": pause_count,
            "repetitionCount": repetition_count,
            "sentenceCompleteness": metrics.get("sentenceCompleteness", "possible_fragment"),
            "observations": observations,
        }
        return eval_data

answer_evaluator = AnswerEvaluator()

answer_evaluator = AnswerEvaluator()
