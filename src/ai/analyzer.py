import json
import re
from re import Pattern
from typing import Any

from natasha import (  # type: ignore
    Doc,
    MorphVocab,
    NewsEmbedding,
    NewsMorphTagger,
    NewsNERTagger,
    NewsSyntaxParser,
    Segmenter,
)

from src.ai.client import async_client
from src.config import prompts, settings
from src.logging_ import logger

# Initialize Natasha components for org name detection
segmenter = Segmenter()
morph_vocab = MorphVocab()
emb = NewsEmbedding()
morph_tagger = NewsMorphTagger(emb)
syntax_parser = NewsSyntaxParser(emb)
ner_tagger = NewsNERTagger(emb)

# Legal document patterns
LEGAL_PATTERNS: list[tuple[Pattern[str], str, str]] = [
    # Competency patterns
    (re.compile(r"\b[Рр]аспоряжение\b.*\b[Пп]равительства\b"), "распоряжение Правительства", "competency"),
    (re.compile(r"\b[Пп]риказ\b.*\b[Дд]епартамента\b"), "приказ Департамента", "competency"),
    (re.compile(r"\b[Пп]остановление\b.*\b[Аа]дминистрации\b"), "постановление Администрации", "competency"),
    # Date patterns
    (re.compile(r"(\d{2})\.(\d{2})\.(\d{4})\s*г\.?"), "DD.MM.YYYY г.", "date"),
    (re.compile(r"(\d{2})\.(\d{2})\.(\d{4})"), "DD.MM.YYYY", "date"),
    (re.compile(r"(\d{4})-(\d{2})-(\d{2})"), "YYYY-MM-DD", "date"),
    (re.compile(r"(\d{2})/(\d{2})/(\d{4})"), "DD/MM/YYYY", "date"),
    (re.compile(r"(\d{2})\s+(\d{2})\s+(\d{4})"), "DD MM YYYY", "date"),
    # Legal term patterns
    (re.compile(r"\b[Вв]праве\b.*\b[Нн]е\b"), "negative_right", "legal_term"),
    (re.compile(r"\b[Оо]бязан\b.*\b[Нн]е\b"), "negative_obligation", "legal_term"),
    (re.compile(r"\b[Дд]олжен\b.*\b[Нн]е\b"), "negative_must", "legal_term"),
    # Document reference patterns
    (re.compile(r"\b[Пп]ункт\b\s+\d+\.\d+"), "point_reference", "reference"),
    (re.compile(r"\b[Сс]татья\b\s+\d+"), "article_reference", "reference"),
    (re.compile(r"\b[Пп]одпункт\b\s+\d+\.\d+\.\d+"), "subpoint_reference", "reference"),
]

# Legal terminology dictionary
LEGAL_TERMS: dict[str, dict[str, list[Pattern[str]] | list[str]]] = {
    "competency": {
        "patterns": [
            re.compile(r"\b[Рр]аспоряжение\b"),
            re.compile(r"\b[Пп]риказ\b"),
            re.compile(r"\b[Пп]остановление\b"),
            re.compile(r"\b[Уу]каз\b"),
        ],
        "context": ["Правительства", "Департамента", "Администрации", "Министерства"],
    },
    "rights": {
        "patterns": [
            re.compile(r"\b[Вв]праве\b"),
            re.compile(r"\b[Ии]меет право\b"),
            re.compile(r"\b[Мм]ожет\b"),
        ],
        "context": ["не", "обязан", "должен"],
    },
    "obligations": {
        "patterns": [
            re.compile(r"\b[Оо]бязан\b"),
            re.compile(r"\b[Дд]олжен\b"),
            re.compile(r"\b[Нн]еобходимо\b"),
        ],
        "context": ["не", "может", "вправе"],
    },
}


def generate_manual_check_hints(document_text: str) -> list[str]:
    """Generate hints from manual checks to help LLM analysis."""
    hints = []

    # Process document with Natasha
    doc = Doc(document_text)
    doc.segment(segmenter)
    doc.tag_morph(morph_tagger)
    doc.parse_syntax(syntax_parser)
    doc.tag_ner(ner_tagger)

    # Check for organization names with improved formatting
    for span in doc.spans:
        if span.type == "ORG":
            org_name = span.text
            formatted_name = format_org_name(org_name)
            if org_name != formatted_name:
                hints.append(
                    f"Обнаружено потенциально неправильное написание организации: '{org_name}' -> '{formatted_name}'"
                )

    # Check for legal patterns
    for pattern, format_name, pattern_type in LEGAL_PATTERNS:
        for match in pattern.finditer(document_text):
            if pattern_type == "date":
                hints.append(f"Обнаружена дата в формате {format_name}, что может требовать корректировки")
            elif pattern_type == "competency":
                hints.append(f"Обнаружен документ типа '{format_name}' - проверьте соответствие компетенции")
            elif pattern_type == "legal_term":
                hints.append(f"Обнаружено потенциально проблемное сочетание терминов: '{match.group()}'")
            elif pattern_type == "reference":
                hints.append(f"Обнаружена ссылка на {format_name}: '{match.group()}'")

    # Check for legal terminology consistency
    for term_type, term_data in LEGAL_TERMS.items():
        patterns = term_data["patterns"]
        contexts = term_data["context"]
        for pattern in patterns:  # type: Pattern[str]
            for match in pattern.finditer(document_text):
                context = document_text[max(0, match.start() - 50) : min(len(document_text), match.end() + 50)]
                for ctx in contexts:  # type: str
                    if ctx in context:
                        hints.append(
                            f"Обнаружено потенциально противоречивое сочетание терминов ({term_type}): "
                            f"'{match.group()}' с '{ctx}' в контексте: '{context}'"
                        )

    # Check for potential email addresses with improved detection
    email_pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
    for match in email_pattern.finditer(document_text):
        email = match.group()
        if not email.startswith(("http://", "https://", "www.")):
            hints.append(f"Обнаружен адрес электронной почты: '{email}'")

    # Check for URLs with improved protocol detection
    url_pattern = re.compile(r'(?:https?://)?(?:www\.)?[^\s<>"]+\.[a-zA-Z]{2,}(?:/[^\s<>"]*)?')
    for match in url_pattern.finditer(document_text):
        url = match.group()
        if is_url(url) and not url.startswith(("http://", "https://")):
            hints.append(f"Обнаружен URL без указания протокола: '{url}'")

    # Check for abbreviations with context
    abbreviation_pattern = re.compile(r"\b([А-Я]{2,})\b")
    for abbr in abbreviation_pattern.finditer(document_text):
        if len(abbr.group()) > 2:
            context = document_text[max(0, abbr.start() - 50) : min(len(document_text), abbr.end() + 50)]
            hints.append(f"Обнаружена аббревиатура без расшифровки: '{abbr.group()}' в контексте: '{context}'")

    return hints


async def self_judge_issues(document_text: str, issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Self-judge detected issues to improve their quality."""
    if not issues:
        return issues

    system_prompt = prompts["judge_system"]
    user_prompt = prompts["judge_user"].format(
        document_text=document_text, issues_json=json.dumps(issues, ensure_ascii=False, indent=2)
    )

    try:
        logger.info("Self-judging issues")
        response = await async_client.chat.completions.create(
            model=settings.ai.openai_model,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "judge_response",
                    "schema": {
                        "type": "object",
                        "required": ["issues"],
                        "additionalProperties": False,
                        "properties": {
                            "issues": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": [
                                        "criterion",
                                        "citation",
                                        "explanation",
                                        "recommendation",
                                        "corrected_text",
                                    ],
                                    "additionalProperties": False,
                                    "properties": {
                                        "criterion": {
                                            "type": "string",
                                            "description": "Название критерия из списка проблем",
                                        },
                                        "citation": {
                                            "type": "string",
                                            "description": "Цитата из текста, содержащая проблему",
                                        },
                                        "explanation": {
                                            "type": "string",
                                            "description": "Объяснение, почему это является проблемой",
                                        },
                                        "recommendation": {
                                            "type": "string",
                                            "description": "Рекомендация по исправлению",
                                        },
                                        "corrected_text": {
                                            "type": "string",
                                            "description": "Исправленный вариант текста",
                                        },
                                    },
                                },
                            }
                        },
                    },
                    "strict": True,
                },
            },
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,  # Balanced temperature for consistent improvements
        )
        logger.debug(response)
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("Received empty response from OpenAI API")

        improved_issues = json.loads(content)
        logger.info(f"Self-judging complete. Improved {len(issues)} issues")
        return improved_issues.get("issues", [])
    except Exception as e:
        logger.error(f"Error in self-judging: {str(e)}", exc_info=True)
        return issues  # Return original issues if self-judging fails


async def analyze_document(document_text: str) -> dict[str, Any]:
    """Analyze document using OpenAI API asynchronously."""
    logger.info(f"Analyzing document with model: {settings.ai.openai_model}")
    logger.info(f"Document length: {len(document_text)} characters")

    # Generate hints from manual checks
    hints = generate_manual_check_hints(document_text)
    hints_text = "\n".join(hints) if hints else "No additional hints."

    system_prompt = prompts["system"]
    user_prompt = prompts["user"].format(
        document_text=document_text, manual_check_hints=f"\nРезультаты автоматических проверок:\n{hints_text}"
    )

    try:
        logger.info("Sending request to OpenAI API")
        response = await async_client.chat.completions.create(
            model=settings.ai.openai_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=settings.ai.temperature,
        )
        logger.info(response.usage)

        content = response.choices[0].message.content
        if content is None:
            raise ValueError("Received empty response from OpenAI API")

        result = json.loads(content)
        initial_issues = result.get("issues", [])
        logger.info(f"Initial analysis complete. Found {len(initial_issues)} issues")

        # Self-judge the issues to improve their quality if enabled
        if settings.ai.use_judge:
            improved_issues = await self_judge_issues(document_text, initial_issues)
            result["issues"] = improved_issues
            logger.info(f"Self-judging complete. Final issues count: {len(improved_issues)}")
        else:
            logger.info("Self-judging stage skipped as per configuration")
            result["issues"] = initial_issues

        result["manual_check_hints"] = hints
        return result
    except Exception as e:
        logger.error(f"Error analyzing document: {str(e)}", exc_info=True)
        raise


def is_email(text: str) -> bool:
    """Check if text is meant to be an email address."""
    # Check for domain patterns that suggest this should be an email
    domain_patterns = [".ru", ".com", ".org", ".net"]
    has_domain = any(text.endswith(pattern) for pattern in domain_patterns)
    has_dot = "." in text
    no_protocol = not text.startswith(("http://", "https://", "www."))
    return has_domain and has_dot and no_protocol


def is_url(text: str) -> bool:
    """Check if text is meant to be a URL."""
    # Check for patterns that suggest this should be a URL
    url_indicators = ["www.", "http://", "https://", ".ru/", ".com/", ".org/", ".net/"]
    return any(indicator in text for indicator in url_indicators)


def format_org_name(name: str) -> str:
    """Format organization name according to rules."""
    # Split into words and capitalize each significant word
    words = name.split()
    formatted_words = []
    skip_words = {"и", "в", "на", "с", "по", "для", "при", "за", "от", "до"}

    for i, word in enumerate(words):
        if i == 0 or word.lower() not in skip_words:
            formatted_words.append(word.capitalize())
        else:
            formatted_words.append(word.lower())

    return " ".join(formatted_words)
