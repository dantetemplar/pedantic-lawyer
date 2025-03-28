# Pedantic Lawyer - Анализатор документов ЯНАО

Инструмент для выявления проблемных мест в нормативных правовых актах Ямало-Ненецкого автономного округа. Приложение
анализирует документы и выявляет потенциальные проблемы, такие как двусмысленность формулировок, нечеткое описание
требований, отсутствие ссылок на нормативные акты и другие юридические недостатки.

## Установка и запуск

1. Установить [Python 3.12+](https://www.python.org/downloads/), Установить [uv](https://github.com/astral-sh/uv)
2. Установить зависимости:
   ```bash
   uv sync
   ```
3. Скопировать файл `settings.example.yaml` в `settings.yaml` и настроить его под свои нужды.
   ```bash
   cp settings.example.yaml settings.yaml
   ```
4. Отредактируйте файл `settings.yaml` и добавьте ваш API ключ [OpenRouter](https://openrouter.ai/):
    ```yaml
    $schema: "./settings.schema.yaml"
    ai:
      openai_base_url: https://openrouter.ai/api/v1
      openai_api_key: "ваш-api-ключ"  # Замените на ваш API ключ
    ```
5. Запустите приложение с помощью streamlit:
    ```bash
    streamlit run streamlit_app.py
    ```

После запуска приложение будет доступно в браузере по адресу http://localhost:8501

## Использование

1. Загрузите документ для анализа (поддерживаются форматы DOCX, PDF, RTF, TXT) или выберите один из примеров
2. Нажмите кнопку "Анализировать документ"
3. Просмотрите результаты анализа с выявленными проблемами, объяснениями и рекомендациями по исправлению
