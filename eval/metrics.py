import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class TestResult:
    """Represents a single test result with metrics."""

    gt_issue_type: str
    gt_text: str
    gt_explanation: str
    gt_without_problem: str

    pipeline_prediction: dict[str, Any]

    judge_is_correct: bool
    judge_score: float
    judge_feedback: str


class MetricsCollector:
    """Collects and manages test metrics across different tests."""

    def __init__(self, log_file: str = "test_metrics.json"):
        self.results: list[TestResult] = []
        self.log_file = Path(log_file)

    def add_result(
        self,
        text: str,
        issue_type: str,
        negative: str,
        explanation: str,
        evaluation: dict[str, Any],
        pipeline_answer: dict[str, Any],
    ):
        """Add a new test result to the collector."""
        result = TestResult(
            gt_issue_type=issue_type,
            gt_text=text,
            gt_explanation=explanation,
            gt_without_problem=negative,
            pipeline_prediction=pipeline_answer,
            judge_is_correct=evaluation["is_correct"],
            judge_score=evaluation["score"],
            judge_feedback=evaluation["feedback"],
        )
        self.results.append(result)

    def get_summary(self) -> dict[str, Any]:
        """Generate a summary of all collected metrics."""
        if not self.results:
            return {"total_tests": 0, "average_score": 0.0, "correct_ratio": 0.0, "issue_type_breakdown": {}}

        total_tests = len(self.results)
        avg_score = sum(r.judge_score for r in self.results) / total_tests
        correct_count = sum(1 for r in self.results if r.judge_is_correct)

        # Calculate breakdown by issue type
        issue_type_breakdown = {}
        for result in self.results:
            if result.gt_issue_type not in issue_type_breakdown:
                issue_type_breakdown[result.gt_issue_type] = {"count": 0, "correct": 0, "avg_score": 0.0}
            breakdown = issue_type_breakdown[result.gt_issue_type]
            breakdown["count"] += 1
            breakdown["correct"] += 1 if result.judge_is_correct else 0
            breakdown["avg_score"] += result.judge_score

        # Calculate averages for each issue type
        for breakdown in issue_type_breakdown.values():
            if breakdown["count"] > 0:
                breakdown["avg_score"] /= breakdown["count"]
                breakdown["correct_ratio"] = breakdown["correct"] / breakdown["count"]

        return {
            "total_tests": total_tests,
            "average_score": avg_score,
            "correct_ratio": correct_count / total_tests,
            "issue_type_breakdown": issue_type_breakdown,
        }

    def save_results(self):
        """Save all results and summary to a JSON file."""
        data = {"results": [asdict(r) for r in self.results], "summary": self.get_summary()}

        with open(self.log_file, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_results(self) -> dict[str, Any]:
        """Load previously saved results from the JSON file."""
        if not self.log_file.exists():
            return {}

        with open(self.log_file) as f:
            return json.load(f)
