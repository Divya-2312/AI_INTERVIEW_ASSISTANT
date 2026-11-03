import logging
import re
from app.models.schemas import AnswerEvaluationRequest, EvaluationResponse
from app.models.llama_provider import get_ai_model_provider, calculate_theory_overall
from app.services.rag_service import rag_service
from app.utils.hr_scoring import calculate_hr_overall, build_hr_evaluation_summary
from app.utils.scoring_formulas import build_formula_object

logger = logging.getLogger("ai_service")

class AnswerEvaluator:
    def __init__(self):
        self.provider = get_ai_model_provider()

    def evaluate(self, req: AnswerEvaluationRequest) -> EvaluationResponse:
        # Empty-answer guard lives here so it applies no matter which
        # provider (LlamaModel / DevFallbackModel) ends up handling the
        # request -- never spend an LLM call or fabricate a score for a
        # blank submission.
        if not (req.answer or "").strip():
            module_name = "hr" if req.interviewType.lower() == "hr" else (req.questionFormat or "theory")
            return EvaluationResponse(
                score=0,
                conceptCoverage=0.0,
                correctness=0.0,
                relevance=0.0,
                accuracy=0.0,
                communication=0.0,
                isIrrelevant=False,
                feedback="No answer was provided.",
                strengths=[],
                weaknesses=["No answer submitted"],
                missingConcepts=req.expectedConcepts or [],
                scoreReason="Score is 0% because no answer was submitted for this question.",
                formula=build_formula_object(module_name, 0, 0, 0, 0),
                source="rule",
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
            code_snippet=req.codeSnippet,
            explanation=req.explanation,
            test_cases=[tc.dict() for tc in (req.testCases or [])] or None,
            language=req.language,
            subject=req.subject,
            schema=req.schema_,
            sample_data=req.sampleData,
            reference_solution=req.referenceSolution,
            reference_answer=getattr(req, "referenceAnswer", None),
            **evaluation_options,
        )

        # Delivery adjustment only applies to relevant HR answers; an
        # irrelevant answer stays at the 0 score the relevancy check gave it.
        if hr_delivery_metrics and not eval_data.get("isIrrelevant"):
            eval_data = self._apply_hr_delivery_metrics(eval_data, hr_delivery_metrics)

        eval_data = self._enforce_overall_score_guard(eval_data, req)

        return EvaluationResponse(**eval_data)

    @staticmethod
    def _enforce_overall_score_guard(eval_data: dict, req: AnswerEvaluationRequest) -> dict:
        """
        Guard at the AI-service response boundary (applied to theory and HR responses only):
        if the four parameters are present and score != round(mean), log a warning and
        set score = round(mean).
        It must not run for coding, SQL or output prediction.
        """
        if eval_data.get("source") == "error" or eval_data.get("error"):
            return eval_data

        q_format = (req.questionFormat or "theory").lower()
        inv_type = (req.interviewType or "").lower()
        lang = (req.language or "").lower()
        subj = (req.subject or "").lower()
        ans_text = (req.answer or "").strip()

        # It must not run for coding, SQL or output prediction.
        if q_format in ("coding", "output_prediction"):
            return eval_data
        if lang == "sql":
            return eval_data
        if subj == "dbms" and bool(re.search(r'^\s*(?:--[^\n]*\n\s*)*SELECT\b', ans_text, re.IGNORECASE)):
            return eval_data
        if q_format != "theory" and inv_type != "hr":
            return eval_data

        if eval_data.get("isIrrelevant"):
            return eval_data

        # If formula object is present, its score is the source of truth
        if eval_data.get("formula") and isinstance(eval_data.get("formula"), dict):
            f_score = eval_data["formula"].get("score")
            if f_score is not None:
                eval_data["score"] = f_score
                return eval_data

        if inv_type == "hr":
            rel = eval_data.get("relevance")
            cor = eval_data.get("correctness")
            acc = eval_data.get("accuracy")
            cov = eval_data.get("conceptCoverage")
            comm = eval_data.get("communication")
            if rel is not None and cor is not None and acc is not None:
                expected = calculate_hr_overall(cor, rel, acc, cov, comm)
                if eval_data.get("score") != expected:
                    logger.warning(
                        f"[ScoreGuard] HR score {eval_data.get('score')} != round(mean) {expected} "
                        f"(relevance={rel}, correctness={cor}, accuracy={acc}, conceptCoverage={cov}). Correcting score."
                    )
                    eval_data["score"] = expected
        else:
            rel = eval_data.get("relevance")
            cor = eval_data.get("correctness")
            cov = eval_data.get("conceptCoverage")
            acc = eval_data.get("accuracy")
            comm = eval_data.get("communication")
            if rel is not None and cor is not None and cov is not None:
                expected = calculate_theory_overall(rel, cor, cov, acc, comm)
                if eval_data.get("score") != expected:
                    logger.warning(
                        f"[ScoreGuard] Theory score {eval_data.get('score')} != round(mean) {expected} "
                        f"(relevance={rel}, correctness={cor}, conceptCoverage={cov}, accuracy={acc}). Correcting score."
                    )
                    eval_data["score"] = expected

        if not eval_data.get("formula") or not isinstance(eval_data.get("formula"), dict):
            from app.utils.scoring_formulas import build_formula_object, round_half_up
            mod = "hr" if inv_type == "hr" else (q_format or "theory")
            p_acc = round_half_up(float(eval_data.get("accuracy") or 0.0) * (100.0 if float(eval_data.get("accuracy") or 0.0) <= 1.0 and float(eval_data.get("accuracy") or 0.0) > 0 else 1.0))
            p_cor = round_half_up(float(eval_data.get("correctness") or 0.0) * (100.0 if float(eval_data.get("correctness") or 0.0) <= 1.0 and float(eval_data.get("correctness") or 0.0) > 0 else 1.0))
            p_rel = round_half_up(float(eval_data.get("relevance") or 0.0) * (100.0 if float(eval_data.get("relevance") or 0.0) <= 1.0 and float(eval_data.get("relevance") or 0.0) > 0 else 1.0))
            p_cov = round_half_up(float(eval_data.get("conceptCoverage") or 0.0) * (100.0 if float(eval_data.get("conceptCoverage") or 0.0) <= 1.0 and float(eval_data.get("conceptCoverage") or 0.0) > 0 else 1.0))
            if eval_data.get("score") == 0:
                p_acc = p_cor = p_rel = p_cov = 0
            eval_data["formula"] = build_formula_object(mod, p_acc, p_cor, p_rel, p_cov)

        return eval_data

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
            # HR: communication stays as feedback text only, NOT in average.
            # Delivery issues adjust communication feedback score.
            communication = float(eval_data.get("communication") or 0.0)
            eval_data["communication"] = round(max(0.0, communication - penalty * 4 / 100.0), 2)
            if eval_data.get("formula") and isinstance(eval_data.get("formula"), dict):
                eval_data["score"] = eval_data["formula"]["score"]
            else:
                eval_data["score"] = calculate_hr_overall(
                    eval_data.get("correctness"), eval_data.get("relevance"),
                    eval_data.get("accuracy"), eval_data.get("conceptCoverage"),
                )
            if eval_data["score"] == 0 and not eval_data.get("isIrrelevant"):
                eval_data["score"] = 1
            hr_weaknesses = list(eval_data.get("weaknesses") or []) + observations
            summary, why_not_100 = build_hr_evaluation_summary(
                score=eval_data["score"],
                correctness=eval_data.get("correctness", 0.0),
                relevance=eval_data.get("relevance", 0.0),
                accuracy=eval_data.get("accuracy", 0.0),
                communication=eval_data["communication"],
                answer=eval_data.get("answerText") or eval_data.get("answer") or "",
                weaknesses=hr_weaknesses[:2],
                improvement_suggestion=eval_data.get("improvementSuggestion"),
                delivery_metrics=metrics,
                is_irrelevant=eval_data.get("isIrrelevant", False),
            )
            eval_data["scoreReason"] = summary
            eval_data["whyNot100"] = why_not_100
            eval_data["weaknesses"] = hr_weaknesses[:2]
        else:
            eval_data["score"] = max(0, int(eval_data.get("score", 0)) - penalty)
            eval_data["scoreReason"] = (eval_data.get("scoreReason", "").rstrip() + " Delivery also affected the score: " + " ".join(observations)).strip()
            eval_data["weaknesses"] = list(eval_data.get("weaknesses") or []) + observations
        eval_data["feedback"] = (eval_data.get("feedback", "").rstrip() + " Delivery observations: " + " ".join(observations)).strip()
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
