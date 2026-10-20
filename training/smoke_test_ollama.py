import argparse, requests, sys

def main():
    p=argparse.ArgumentParser(); p.add_argument('--model',default='mockmate-llama-ft'); p.add_argument('--endpoint',default='http://localhost:11434/api/generate'); a=p.parse_args()
    prompts=[
      'Return only valid JSON with keys question, expectedConcepts, difficulty, questionFormat. Generate one intermediate Java interview question about generics and type erasure.',
      'Return only valid JSON with keys question, expectedConcepts, difficulty, questionFormat. Previous question: What is normalization? Student answer: It reduces duplicate data. Generate one relevant follow-up about update anomalies.',
      'Return only valid JSON with keys score, correctness, conceptCoverage, relevance, communication, isIrrelevant, feedback, strengths, weaknesses, missingConcepts, improvementSuggestion, scoreReason. Question: What is normalization in DBMS? Reference answer: It reduces redundancy and anomalies through normal forms. Student answer: It reduces duplicate data.'
    ]
    failed=False
    for i,prompt in enumerate(prompts,1):
        try:
            r=requests.post(a.endpoint,json={'model':a.model,'prompt':prompt,'stream':False,'options':{'temperature':0.1,'num_predict':500}},timeout=300)
            r.raise_for_status(); result=r.json().get('response','').strip()
            print(f'\n--- test {i} ---\n{result[:2500]}')
            if not result: failed=True; print('FAIL: empty response')
        except Exception as e: failed=True; print(f'FAIL test {i}: {e}')
    sys.exit(1 if failed else 0)
if __name__=='__main__': main()
