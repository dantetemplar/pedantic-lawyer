import re

import yaml

with open("from_google_sheets.yaml") as f:
    data = yaml.safe_load(f)

result = {}

for row in data:
    gt_issue_type = row["Критерий"]
    cases = []

    for positive_key, negative_key in [
        ("Краткий пример (с ошибкой)", "Краткий пример (корректный вариант)"),
        ("1 полный пример (с ошибкой)", "1 полный пример (корректный вариант)"),
        ("2 полный пример (с ошибкой)", "2 полный пример (корректный вариант)"),
        ("3 полный пример (с ошибкой)", "3 полный пример (корректный вариант)"),
    ]:
        input_text = row[positive_key]
        negative = row[negative_key]

        if input_text:
            # «Подрядчик должен обеспечить своевременную доставку материалов.» (Не указаны сроки и условия)

            pattern = re.compile(r"\(.*?\)$")
            explanation = pattern.search(input_text)  # (Не указаны сроки и условия)
            input_text = pattern.sub("", input_text)
            cases.append(
                {
                    "input_text": input_text.strip().strip("«»"),
                    "explanation": explanation.group(0).strip("()") if explanation else "",
                    "negative": negative.strip().strip("«»"),
                }
            )

    if gt_issue_type in result:
        result[gt_issue_type].extend(cases)
    else:
        result[gt_issue_type] = cases

with open("test_cases.yaml", "w") as f:
    yaml.dump(result, f, allow_unicode=True, indent=2, sort_keys=False)
