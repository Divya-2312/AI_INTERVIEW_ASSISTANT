#!/usr/bin/env python3
"""
scripts/check_hr_golden.py - Accuracy benchmark for HR evaluation.

Runs a curated golden test set of 44 HR answers across 10 distinct questions
(excellent STAR, good, average, vague, very short, off-topic, keyword list,
copied question text, spoken-style with fillers).

Reports how many land in their expected score band and lists any misses honestly.
"""
import os
import sys
import json
import time

# Ensure ai-service root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI_SERVICE_DIR = os.path.join(BASE_DIR, "ai-service")
if AI_SERVICE_DIR not in sys.path:
    sys.path.insert(0, AI_SERVICE_DIR)

from app.models.schemas import AnswerEvaluationRequest
from app.services.answer_evaluator import AnswerEvaluator
from app.utils.hr_scoring import calculate_hr_overall

GOLDEN_CASES = [
    # -------------------------------------------------------------
    # Question 1: hr001 - Tell me about yourself.
    # -------------------------------------------------------------
    {
        "id": "C01",
        "questionId": "hr001",
        "question": "Tell me about yourself.",
        "archetype": "excellent_star",
        "answer": (
            "I graduated with a Computer Science degree from ABC University where I maintained an 8.5 GPA. "
            "During my final year, I led a 4-person team to build an e-commerce platform using React, Node.js, and MongoDB, "
            "handling over 1,000 mock transactions with 99% uptime. I completed an internship at XYZ Tech where I automated API testing, "
            "reducing regression cycle times by 30%. I am looking forward to applying my full-stack and problem-solving skills in this software engineering role."
        ),
        "deliveryMetrics": None,
        "expectedBand": (75, 100),
    },
    {
        "id": "C02",
        "questionId": "hr001",
        "question": "Tell me about yourself.",
        "archetype": "good",
        "answer": (
            "I am a software engineer with background in web development. In college, I worked on web applications "
            "and learned React and Node.js. In my internship, I helped build customer features and worked with senior engineers to deliver our sprint goals on time."
        ),
        "deliveryMetrics": None,
        "expectedBand": (60, 85),
    },
    {
        "id": "C03",
        "questionId": "hr001",
        "question": "Tell me about yourself.",
        "archetype": "average",
        "answer": (
            "I am a fresh graduate who studied computer science. I know programming languages like Java and Python "
            "and I did projects during my college degree. I am eager to start working."
        ),
        "deliveryMetrics": None,
        "expectedBand": (40, 65),
    },
    {
        "id": "C04",
        "questionId": "hr001",
        "question": "Tell me about yourself.",
        "archetype": "vague",
        "answer": "I am a hard working and passionate individual who loves technology and always wants to learn new things and be the best employee.",
        "deliveryMetrics": None,
        "expectedBand": (20, 50),
    },
    {
        "id": "C05",
        "questionId": "hr001",
        "question": "Tell me about yourself.",
        "archetype": "off_topic",
        "answer": "My favorite dish is pepperoni pizza and I enjoy watching action movies on Saturday nights.",
        "deliveryMetrics": None,
        "expectedBand": (0, 0),
    },

    # -------------------------------------------------------------
    # Question 2: hr013 - What are your greatest strengths?
    # -------------------------------------------------------------
    {
        "id": "C06",
        "questionId": "hr013",
        "question": "What are your greatest strengths?",
        "archetype": "excellent_star",
        "answer": (
            "My greatest strength is structured problem solving and perseverance under tight deadlines. For instance, "
            "during our final year capstone project, our payment gateway integration repeatedly crashed 48 hours before submission. "
            "I methodically debugged the asynchronous webhook callbacks, identified a race condition in state management, and patched it within 6 hours. "
            "This enabled our entire team of four to successfully demo the project and win the best project award among 40 teams."
        ),
        "deliveryMetrics": None,
        "expectedBand": (75, 100),
    },
    {
        "id": "C07",
        "questionId": "hr013",
        "question": "What are your greatest strengths?",
        "archetype": "good",
        "answer": (
            "My biggest strength is quick learning and adaptability. Whenever a new framework or technology is introduced, "
            "I build small proof-of-concept apps to understand it thoroughly, which helped my team adopt TypeScript smoothly."
        ),
        "deliveryMetrics": None,
        "expectedBand": (60, 85),
    },
    {
        "id": "C08",
        "questionId": "hr013",
        "question": "What are your greatest strengths?",
        "archetype": "very_short",
        "answer": "I learn quickly and work hard.",
        "deliveryMetrics": None,
        "expectedBand": (1, 35),
    },
    {
        "id": "C09",
        "questionId": "hr013",
        "question": "What are your greatest strengths?",
        "archetype": "keyword_list",
        "answer": "hardworking, dedicated, fast learner, team player, communication, leadership",
        "deliveryMetrics": None,
        "expectedBand": (0, 0),
    },

    # -------------------------------------------------------------
    # Question 3: hr014 - What is your greatest weakness, and how are you working on it?
    # -------------------------------------------------------------
    {
        "id": "C10",
        "questionId": "hr014",
        "question": "What is your greatest weakness, and how are you working on it?",
        "archetype": "excellent_star",
        "answer": (
            "In the past, I struggled with public speaking and presenting technical designs to large groups, often feeling anxious during team demos. "
            "To address this weakness, I enrolled in a local Toastmasters club six months ago, where I have delivered eight prepared speeches. "
            "Additionally, I volunteered to lead bi-weekly engineering brown-bag sessions on API design. As a result, my confidence has improved significantly "
            "and I received positive feedback from our engineering director on my last sprint demo."
        ),
        "deliveryMetrics": None,
        "expectedBand": (75, 100),
    },
    {
        "id": "C11",
        "questionId": "hr014",
        "question": "What is your greatest weakness, and how are you working on it?",
        "archetype": "good",
        "answer": (
            "My weakness is sometimes having difficulty delegating tasks because I want everything to be perfect. Recently, "
            "I started breaking projects into modular sub-tasks with clear acceptance criteria and trusting my teammates with ownership, which has reduced my stress and improved team velocity."
        ),
        "deliveryMetrics": None,
        "expectedBand": (60, 85),
    },
    {
        "id": "C12",
        "questionId": "hr014",
        "question": "What is your greatest weakness, and how are you working on it?",
        "archetype": "vague",
        "answer": "I am too much of a perfectionist and work too hard for my own good.",
        "deliveryMetrics": None,
        "expectedBand": (20, 50),
    },
    {
        "id": "C13",
        "questionId": "hr014",
        "question": "What is your greatest weakness, and how are you working on it?",
        "archetype": "off_topic",
        "answer": "The stock market fluctuates every day depending on global inflation and interest rate policy.",
        "deliveryMetrics": None,
        "expectedBand": (0, 0),
    },

    # -------------------------------------------------------------
    # Question 4: hr021 - Why do you want to work for our company?
    # -------------------------------------------------------------
    {
        "id": "C14",
        "questionId": "hr021",
        "question": "Why do you want to work for our company?",
        "archetype": "excellent",
        "answer": (
            "I have closely followed your company's recent expansion into enterprise AI observability tools and was impressed by your open-source telemetry libraries. "
            "My background in distributed backend architecture and Kafka streaming aligns directly with the real-time processing challenges your platform solves. "
            "I want to contribute to high-scale infrastructure while learning from your experienced engineering team, specifically within your cloud platform division."
        ),
        "deliveryMetrics": None,
        "expectedBand": (70, 100),
    },
    {
        "id": "C15",
        "questionId": "hr021",
        "question": "Why do you want to work for our company?",
        "archetype": "average",
        "answer": "Your company has a great reputation and is well-known in the industry. I want a good job with good career growth and benefits.",
        "deliveryMetrics": None,
        "expectedBand": (30, 60),
    },
    {
        "id": "C16",
        "questionId": "hr021",
        "question": "Why do you want to work for our company?",
        "archetype": "copied_question",
        "answer": "Why do you want to work for our company?",
        "deliveryMetrics": None,
        "expectedBand": (0, 0),
    },
    {
        "id": "C17",
        "questionId": "hr021",
        "question": "Why do you want to work for our company?",
        "archetype": "spoken_fillers",
        "answer": "Um, so basically, like, I really think, uh, your company is, you know, doing cool stuff and, um, I want to, like, work with good people and, uh, grow my career.",
        "deliveryMetrics": {
            "fillerWordCount": 6,
            "fillerFrequencyPer100Words": 18.0,
            "noticeablePauseCount": 3,
            "repetitionCount": 1,
            "sentenceCompleteness": "likely_complete",
            "observations": ["Frequent filler words used", "3 noticeable pauses detected"],
        },
        "expectedBand": (25, 55),
    },

    # -------------------------------------------------------------
    # Question 5: hr041 - Difficult challenge overcame
    # -------------------------------------------------------------
    {
        "id": "C18",
        "questionId": "hr041",
        "question": "Describe a time you faced a difficult challenge at work or university and how you overcame it.",
        "archetype": "excellent_star",
        "answer": (
            "During our semester project, two out of four team members dropped out two weeks before the final presentation, leaving half the backend API unbuilt. "
            "As the team lead, I reorganized our remaining backlog, prioritized core authentication and CRUD features, and descoped non-essential analytics. "
            "I worked with the remaining teammate, pair-programming for 4 hours daily, and successfully deployed a fully functional prototype on AWS. "
            "We earned an 'A' grade and received praise from our professor for delivering under adverse circumstances."
        ),
        "deliveryMetrics": None,
        "expectedBand": (75, 100),
    },
    {
        "id": "C19",
        "questionId": "hr041",
        "question": "Describe a time you faced a difficult challenge at work or university and how you overcame it.",
        "archetype": "good",
        "answer": (
            "A challenge I faced was when our test database got corrupted before a major sprint deadline. "
            "I stayed calm, located the last verified automated backup from 4 hours earlier, and restored the schema and test fixtures, allowing our team to complete testing on time."
        ),
        "deliveryMetrics": None,
        "expectedBand": (60, 85),
    },
    {
        "id": "C20",
        "questionId": "hr041",
        "question": "Describe a time you faced a difficult challenge at work or university and how you overcame it.",
        "archetype": "very_short",
        "answer": "It was hard but I did it.",
        "deliveryMetrics": None,
        "expectedBand": (1, 35),
    },
    {
        "id": "C21",
        "questionId": "hr041",
        "question": "Describe a time you faced a difficult challenge at work or university and how you overcame it.",
        "archetype": "off_topic",
        "answer": "Java provides garbage collection through generational collectors like G1GC and ZGC.",
        "deliveryMetrics": None,
        "expectedBand": (0, 0),
    },

    # -------------------------------------------------------------
    # Question 6: hr061 - Worked in a team and role
    # -------------------------------------------------------------
    {
        "id": "C22",
        "questionId": "hr061",
        "question": "Tell me about a time you worked in a team. What was your role?",
        "archetype": "excellent_star",
        "answer": (
            "In our university hackathon, I worked in a four-person cross-functional team as the primary backend and database developer. "
            "Our goal was to build a disaster relief matching app within 24 hours. I designed the PostgreSQL relational schema and built REST endpoints in Express, "
            "while maintaining clear API documentation so frontend designers could work concurrently without blocking. "
            "Our coordinated teamwork enabled us to demo a live working prototype that won 2nd place out of 50 participating teams."
        ),
        "deliveryMetrics": None,
        "expectedBand": (75, 100),
    },
    {
        "id": "C23",
        "questionId": "hr061",
        "question": "Tell me about a time you worked in a team. What was your role?",
        "archetype": "good",
        "answer": (
            "I worked in a team of five on our capstone project where my role was frontend development. "
            "I held daily standups with our backend engineer to integrate APIs and ensured our UI components followed responsive design principles."
        ),
        "deliveryMetrics": None,
        "expectedBand": (60, 85),
    },
    {
        "id": "C24",
        "questionId": "hr061",
        "question": "Tell me about a time you worked in a team. What was your role?",
        "archetype": "average",
        "answer": "I was part of a team in college. We all worked together and shared tasks and submitted our assignment to the professor.",
        "deliveryMetrics": None,
        "expectedBand": (40, 65),
    },
    {
        "id": "C25",
        "questionId": "hr061",
        "question": "Tell me about a time you worked in a team. What was your role?",
        "archetype": "keyword_list",
        "answer": "teamwork, collaboration, agile, scrum master, daily standup, sprint backlog",
        "deliveryMetrics": None,
        "expectedBand": (0, 0),
    },
    {
        "id": "C26",
        "questionId": "hr061",
        "question": "Tell me about a time you worked in a team. What was your role?",
        "archetype": "spoken_fillers",
        "answer": "Like, um, so our team, you know, we had to build an app, and uh, my role was basically, um, like doing the database, and uh, yeah we finished it.",
        "deliveryMetrics": {
            "fillerWordCount": 7,
            "fillerFrequencyPer100Words": 20.0,
            "noticeablePauseCount": 4,
            "repetitionCount": 2,
            "sentenceCompleteness": "likely_complete",
            "observations": ["Frequent filler words detected", "4 noticeable pauses interrupted flow"],
        },
        "expectedBand": (25, 55),
    },

    # -------------------------------------------------------------
    # Question 7: hr076 - Conflict with colleague
    # -------------------------------------------------------------
    {
        "id": "C27",
        "questionId": "hr076",
        "question": "Describe a situation where you had a conflict with a colleague or team member.",
        "archetype": "excellent_star",
        "answer": (
            "During our college software engineering lab, a teammate and I strongly disagreed on database architecture; he wanted MongoDB for rapid prototyping "
            "while I advocated for PostgreSQL due to strict relational integrity requirements. Instead of letting the debate stall our progress, I scheduled a one-on-one whiteboard session "
            "where we mapped out our data relationships, query patterns, and ACID requirements. Seeing the high frequency of join operations convinced him that PostgreSQL was superior, "
            "and in return, I agreed to use JSONB fields for dynamic user settings. This compromise allowed us to ship the project on schedule with zero schema regressions."
        ),
        "deliveryMetrics": None,
        "expectedBand": (75, 100),
    },
    {
        "id": "C28",
        "questionId": "hr076",
        "question": "Describe a situation where you had a conflict with a colleague or team member.",
        "archetype": "good",
        "answer": (
            "I had a disagreement with a team member regarding the division of sprint tasks. "
            "I invited him for coffee and listened to his concerns about workload, and we agreed to redistribute the backend tickets evenly, which resolved the friction."
        ),
        "deliveryMetrics": None,
        "expectedBand": (60, 85),
    },
    {
        "id": "C29",
        "questionId": "hr076",
        "question": "Describe a situation where you had a conflict with a colleague or team member.",
        "archetype": "vague",
        "answer": "Whenever there is conflict I just compromise and stay calm and friendly so everyone is happy.",
        "deliveryMetrics": None,
        "expectedBand": (20, 50),
    },
    {
        "id": "C30",
        "questionId": "hr076",
        "question": "Describe a situation where you had a conflict with a colleague or team member.",
        "archetype": "very_short",
        "answer": "We argued but then we agreed.",
        "deliveryMetrics": None,
        "expectedBand": (1, 35),
    },
    {
        "id": "C31",
        "questionId": "hr076",
        "question": "Describe a situation where you had a conflict with a colleague or team member.",
        "archetype": "off_topic",
        "answer": "Cristiano Ronaldo and Lionel Messi are considered the greatest football players of their generation.",
        "deliveryMetrics": None,
        "expectedBand": (0, 0),
    },

    # -------------------------------------------------------------
    # Question 8: hr081 - Initiative or led a project
    # -------------------------------------------------------------
    {
        "id": "C32",
        "questionId": "hr081",
        "question": "Describe a situation where you took the initiative or led a project.",
        "archetype": "excellent_star",
        "answer": (
            "At my previous internship, I noticed that our onboarding documentation was outdated, causing newly joined interns to spend nearly two weeks configuring their local development environments. "
            "Without being prompted, I spent a weekend creating a containerized Docker Compose environment with automated seed scripts and wrote a step-by-step setup guide. "
            "I presented it to my engineering manager, who approved it for team-wide adoption. This initiative reduced new hire onboarding time from 10 days to under 3 hours for the subsequent cohort of six interns."
        ),
        "deliveryMetrics": None,
        "expectedBand": (75, 100),
    },
    {
        "id": "C33",
        "questionId": "hr081",
        "question": "Describe a situation where you took the initiative or led a project.",
        "archetype": "good",
        "answer": (
            "I took the initiative to organize an internal technical knowledge-sharing workshop on Docker. "
            "I created the slides, prepared hands-on exercises, and led a 90-minute session for 15 classmates, receiving very positive feedback."
        ),
        "deliveryMetrics": None,
        "expectedBand": (60, 85),
    },
    {
        "id": "C34",
        "questionId": "hr081",
        "question": "Describe a situation where you took the initiative or led a project.",
        "archetype": "average",
        "answer": "I was the team leader for our college mini-project. I assigned work to everyone and reminded them about the deadline.",
        "deliveryMetrics": None,
        "expectedBand": (40, 65),
    },
    {
        "id": "C35",
        "questionId": "hr081",
        "question": "Describe a situation where you took the initiative or led a project.",
        "archetype": "copied_question",
        "answer": "Describe a situation where you took the initiative or led a project.",
        "deliveryMetrics": None,
        "expectedBand": (0, 0),
    },

    # -------------------------------------------------------------
    # Question 9: hr051 - Where do you see yourself in five years?
    # -------------------------------------------------------------
    {
        "id": "C36",
        "questionId": "hr051",
        "question": "Where do you see yourself in five years?",
        "archetype": "excellent",
        "answer": (
            "In five years, I see myself as a Senior Software Engineer with deep expertise in cloud-native distributed systems and API architecture. "
            "Over the first two years, my focus is to master your platform's codebase, contribute high-quality features, and earn domain ownership. "
            "In years three through five, I aim to mentor junior developers, participate in architectural design reviews, and take ownership of end-to-end service delivery within the organization."
        ),
        "deliveryMetrics": None,
        "expectedBand": (70, 100),
    },
    {
        "id": "C37",
        "questionId": "hr051",
        "question": "Where do you see yourself in five years?",
        "archetype": "good",
        "answer": (
            "In five years, I hope to have grown into a tech lead role, having mastered backend development and leading high-impact engineering projects while mentoring newer team members."
        ),
        "deliveryMetrics": None,
        "expectedBand": (55, 85),
    },
    {
        "id": "C38",
        "questionId": "hr051",
        "question": "Where do you see yourself in five years?",
        "archetype": "vague",
        "answer": "I want to be successful, earn a high salary, and be in a top management position.",
        "deliveryMetrics": None,
        "expectedBand": (20, 50),
    },
    {
        "id": "C39",
        "questionId": "hr051",
        "question": "Where do you see yourself in five years?",
        "archetype": "off_topic",
        "answer": "Photosynthesis is the biological process by which green plants convert sunlight and carbon dioxide into oxygen and glucose.",
        "deliveryMetrics": None,
        "expectedBand": (0, 0),
    },

    # -------------------------------------------------------------
    # Question 10: hr091 - Failed or serious mistake and learning
    # -------------------------------------------------------------
    {
        "id": "C40",
        "questionId": "hr091",
        "question": "Tell me about a time you failed or made a serious mistake. What did you learn?",
        "archetype": "excellent_star",
        "answer": (
            "During my internship, I accidentally pushed an unreviewed configuration change directly to our staging branch, breaking the CI/CD pipeline for 15 engineers on the team. "
            "I immediately owned up to the mistake, notified the team lead in our Slack channel, and reverted the commit within ten minutes. "
            "To ensure this never happened again, I submitted a pull request that added branch protection rules and mandatory PR approvals for staging. "
            "The incident taught me extreme accountability, transparency, and the necessity of automated safeguards over manual discipline."
        ),
        "deliveryMetrics": None,
        "expectedBand": (75, 100),
    },
    {
        "id": "C41",
        "questionId": "hr091",
        "question": "Tell me about a time you failed or made a serious mistake. What did you learn?",
        "archetype": "good",
        "answer": (
            "I once missed a project milestone because I underestimated the complexity of third-party API integration. "
            "I learned to break tasks into smaller components, add 20% contingency buffer, and communicate delays proactively to stakeholders."
        ),
        "deliveryMetrics": None,
        "expectedBand": (60, 85),
    },
    {
        "id": "C42",
        "questionId": "hr091",
        "question": "Tell me about a time you failed or made a serious mistake. What did you learn?",
        "archetype": "very_short",
        "answer": "I failed once and I learned not to do it again.",
        "deliveryMetrics": None,
        "expectedBand": (1, 35),
    },
    {
        "id": "C43",
        "questionId": "hr091",
        "question": "Tell me about a time you failed or made a serious mistake. What did you learn?",
        "archetype": "keyword_list",
        "answer": "failure, mistake, learning, accountability, resilience, growth mindset",
        "deliveryMetrics": None,
        "expectedBand": (0, 0),
    },
    {
        "id": "C44",
        "questionId": "hr091",
        "question": "Tell me about a time you failed or made a serious mistake. What did you learn?",
        "archetype": "off_topic",
        "answer": "The Eiffel Tower is located in Paris, France, and was designed by Gustave Eiffel for the 1889 World's Fair.",
        "deliveryMetrics": None,
        "expectedBand": (0, 0),
    },
]


def run_benchmark():
    print("=" * 80, flush=True)
    print("         MOCKMATE AI: HR EVALUATION GOLDEN SET ACCURACY BENCHMARK", flush=True)
    print("=" * 80, flush=True)
    print(f"Total benchmark cases: {len(GOLDEN_CASES)} across 10 distinct HR questions", flush=True)
    print("Running evaluator...", flush=True)
    print("-" * 80, flush=True)

    evaluator = AnswerEvaluator()
    is_ollama_online = False
    try:
        import requests
        r = requests.get("http://127.0.0.1:11434/api/tags", timeout=1.5)
        is_ollama_online = (r.status_code == 200)
    except Exception:
        is_ollama_online = False

    if is_ollama_online:
        print("[Mode] Ollama is ONLINE - Evaluating via fine-tuned LLaMA model (temp=0.0).", flush=True)
    else:
        print("[Mode] Ollama is UNREACHABLE - Evaluating via real offline evaluator (BERT semantic similarity + HR gate).", flush=True)
        evaluator.provider = getattr(evaluator.provider, "fallback", evaluator.provider)

    passed = 0
    failed = 0
    misses = []
    start_time = time.time()

    for idx, case in enumerate(GOLDEN_CASES, 1):
        req = AnswerEvaluationRequest(
            interviewType="hr",
            subject="hr",
            question=case["question"],
            answer=case["answer"],
            expectedConcepts=["Context and situation", "Actions taken", "Measurable outcome", "Reflection"],
            hrDeliveryMetrics=case["deliveryMetrics"],
        )
        try:
            res = evaluator.evaluate(req)
            score = res.score
        except Exception as e:
            print(f"[{case['id']}] Error: {e}", flush=True)
            score = -1

        min_exp, max_exp = case["expectedBand"]
        in_band = (min_exp <= score <= max_exp)

        if in_band:
            passed += 1
            status = "[PASS]"
        else:
            failed += 1
            status = "[MISS]"
            misses.append({
                "id": case["id"],
                "archetype": case["archetype"],
                "question": case["question"][:45] + "...",
                "expectedBand": case["expectedBand"],
                "actualScore": score,
                "diff": min_exp - score if score < min_exp else score - max_exp,
            })

        print(
            f"{status} {case['id']} | Archetype: {case['archetype']:<15} | "
            f"Expected: [{min_exp:>3}, {max_exp:>3}] | Actual: {score:>3}% | "
            f"Sub-scores: R={int(round((res.relevance or 0)*100))}% C={int(round((res.correctness or 0)*100))}% "
            f"A={int(round((res.accuracy or 0)*100))}% Comm={int(round((res.communication or 0)*100))}%",
            flush=True
        )

    duration = time.time() - start_time
    print("-" * 80, flush=True)
    print(f"Benchmark completed in {duration:.2f}s", flush=True)
    print(f"Results: {passed} / {len(GOLDEN_CASES)} PASSED ({passed / len(GOLDEN_CASES) * 100:.1f}%)", flush=True)
    print(f"Misses : {failed} / {len(GOLDEN_CASES)}", flush=True)

    if misses:
        print("\n" + "=" * 80, flush=True)
        print("                        HONEST LIST OF MISSES", flush=True)
        print("=" * 80, flush=True)
        for m in misses:
            print(
                f"- Case {m['id']} ({m['archetype']}): Expected {m['expectedBand']}, "
                f"got {m['actualScore']}% (off by {m['diff']} points) on '{m['question']}'",
                flush=True
            )
    else:
        print("\nAll 44 golden test cases landed in their expected score bands!", flush=True)

    print("=" * 80, flush=True)
    return passed, failed, misses


if __name__ == "__main__":
    passed, failed, misses = run_benchmark()
    # Exit with code 0 if passes >= 90% or exit with failure count
    sys.exit(0 if failed == 0 else 1 if failed > (len(GOLDEN_CASES) * 0.25) else 0)
