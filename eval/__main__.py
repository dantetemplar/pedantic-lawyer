import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import yaml
from tabulate import tabulate
from tqdm.asyncio import tqdm_asyncio

from eval.metrics import MetricsCollector
from src.ai.analyzer import analyze_document
from src.ai.client import async_client

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

# Configuration
JUDGE_MODEL = "openai/gpt-4o-mini"
SYSTEM_PROMPT = "Вы являетесь экспертом по анализу и оценке юридических документов."

# Message templates
JUDGE_PROMPT_TEMPLATE = """
Оцените качество анализа юридического документа:

Исходный текст с проблемой:
```plain
{input_text}
```
Ожидаемый тип проблемы: {gt_issue_type}
Объяснение: {explanation}
Пример, в котором проблема исправлена:
```plain
{negative}
```

Результаты анализа (именно его вы должны оценить):
```json
{pipeline_answer}
```

Пожалуйста, оцените качество анализа по следующим критериям:
1. Правильность определения типа проблемы
2. Точность определения наличия/отсутствия проблемы
3. Качество предложенного исправления (если проблема)
4. Полнота и точность объяснения проблемы
5. Соответствие рекомендаций по исправлению

Предоставьте вашу оценку в формате JSON со следующими полями:
- is_correct: boolean (true, если анализ соответствует ожиданиям)
- score: число от 1 до 10
- feedback: строка с объяснением вашей оценки, будьте краткими и конкретными
"""

# Create a metrics collector instance
metrics = MetricsCollector()

# Load test cases from YAML file
with (Path(__file__).parent / "test_cases.yaml").open() as f:
    test_cases = yaml.safe_load(f)


async def evaluate_analysis(
    gt_issue_type: str,
    input_text: str,
    explanation: str,
    negative: str,
    pipeline_answer: dict,
) -> dict:
    judge_prompt = JUDGE_PROMPT_TEMPLATE.format(
        input_text=input_text,
        gt_issue_type=gt_issue_type,
        explanation=explanation,
        negative=negative,
        pipeline_answer=json.dumps(pipeline_answer["issues"], ensure_ascii=False, indent=2),
    )

    judge_response = await async_client.chat.completions.create(
        model=JUDGE_MODEL,
        response_format={"type": "json_object"},
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": judge_prompt}],
        temperature=0,
        top_p=1,
        max_tokens=1000,
        seed=4564128811,
    )

    content = judge_response.choices[0].message.content
    if content is None:
        raise ValueError("Received empty response from LLM")

    evaluation = json.loads(content)
    metrics.add_result(
        issue_type=gt_issue_type,
        text=input_text,
        explanation=explanation,
        negative=negative,
        pipeline_answer=pipeline_answer,
        evaluation=evaluation,
    )
    return evaluation


async def process_single_case(gt_issue_type: str, case: dict[str, Any]) -> tuple[str, dict, dict, dict]:
    """Process a single test case and return the output and evaluation."""
    pipeline_answer = await analyze_document(case["input_text"])
    evaluation = await evaluate_analysis(**case, gt_issue_type=gt_issue_type, pipeline_answer=pipeline_answer)
    return gt_issue_type, case, pipeline_answer, evaluation


async def run_analysis():
    """Run analysis for all test cases in parallel."""
    tasks = []

    for gt_issue_type, cases in test_cases.items():
        for case in cases:
            task = process_single_case(gt_issue_type, case)
            tasks.append(task)

    # Run all tasks in parallel and collect results
    results = await tqdm_asyncio.gather(*tasks, desc="Processing test cases")

    for gt_issue_type, case, pipeline_answer, evaluation in results:
        bad = not evaluation["is_correct"] or evaluation["score"] < 7
        print(f"Issue Type: {gt_issue_type} {'❌' if bad else '✅'}")
        if bad:
            print(f"Input Text: {case['input_text']}")
            print(f"Evaluation: {evaluation}")
            print(f"Pipeline Answer: {pipeline_answer}")
            print(f"Example without issues: {case['negative']}")
        else:
            print(
                f"Input Text: {case['input_text'][:50] + '...' if len(case['input_text']) > 50 else case['input_text']}"
            )
            to_print = {"is_correct": evaluation["is_correct"], "score": evaluation["score"]}
            print(f"Evaluation: {to_print}")

        print("-" * 40)

    # Save and display metrics
    metrics.save_results()
    # Show metrics in a human-readable format
    summary = metrics.get_summary()

    # Print issue type breakdown as Markdown table
    issue_breakdown = summary["issue_type_breakdown"]
    table_data = []
    for issue_type, stats in issue_breakdown.items():
        table_data.append([issue_type, stats["count"], f"{stats['correct_ratio']:.2%}", f"{stats['avg_score']:.2f}"])

    headers = ["Issue Type", "Count", "Correct Ratio", "Average Score"]
    print("\nIssue Type Breakdown:\n")
    print(tabulate(table_data, headers=headers, tablefmt="github"))

    # Print overall metrics
    print("\nOverall Metrics:")
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Average Score: {summary['average_score']:.2f}")
    print(f"Correct Ratio: {summary['correct_ratio']:.2%}")


if __name__ == "__main__":
    asyncio.run(run_analysis())
