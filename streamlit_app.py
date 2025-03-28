import json
import os
from pathlib import Path

import streamlit as st
from humanfriendly.text import dedent
from openai import OpenAI

from src.config import prompts, settings
from src.logging_ import logger
from src.parse_markitdown import parse

# Configure logging
logger.info("Starting Pedantic Lawyer application")

# Set page configuration
st.set_page_config(
    page_title="Pedantic Lawyer - Анализатор документов ЯНАО",
    page_icon="⚖️",
    layout="wide",
)

# Custom CSS
st.markdown(
    """
<style>
    .main .block-container {
        padding-top: 2rem;
    }
    h1 {
        color: #1E3A8A;
        margin-bottom: 1rem;
    }
    h2 {
        color: #2563EB;
        margin-top: 2rem;
    }
    h3 {
        margin-top: 0;
        color: #1F2937;
    }
    .stButton > button {
        background-color: #2563EB;
        color: white;
        font-weight: bold;
        padding: 0.5rem 1.5rem;
        border-radius: 0.5rem;
        border: none;
    }
    .stButton > button:hover {
        background-color: #1D4ED8;
    }
    /* Стили для блоков с проблемами */
    div:has(> div > div > div > span.issue-box) {
        background-color: white;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
        border-left: 6px solid #EF4444;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        color: #1F2937;
    }
    .issue-title {
        font-size: 1.25rem;
        font-weight: bold;
        margin-bottom: 1rem;
        color: #1F2937;
    }
    .citation-box {
        background-color: #FEF3C7;
        border-radius: 6px;
        padding: 15px;
        margin: 15px 0;
        font-family: 'Courier New', monospace;
        border-left: 4px solid #F59E0B;
        color: #92400E;
    }
    .recommendation-box {
        background-color: #D1FAE5;
        border-radius: 6px;
        padding: 15px;
        margin: 15px 0;
        border-left: 4px solid #10B981;
        color: #065F46;
    }
    .corrected-text-box {
        background-color: #F8FAFC;
        border-radius: 6px;
        padding: 15px;
        margin: 15px 0;
        font-family: 'Courier New', monospace;
        border-left: 4px solid #0EA5E9;
        color: #0C4A6E;
    }
    /* Стили для сайдбара */
    .sidebar .sidebar-content {
        background-color: #F3F4F6;
    }
    /* Стили для экспандера */
    .streamlit-expanderHeader {
        font-weight: bold;
        color: #4B5563;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Title
st.title("Pedantic Lawyer - Анализатор документов ЯНАО")
st.markdown("Инструмент для выявления проблемных мест в нормативных правовых актах Ямало-Ненецкого автономного округа")


# Initialize OpenAI client
@st.cache_resource
def get_openai_client():
    logger.info("Initializing OpenAI client")
    return OpenAI(
        base_url=settings.ai.openai_base_url,
        api_key=settings.ai.openai_api_key.get_secret_value(),
    )


client = get_openai_client()


# Function to highlight differences between two texts at character level using diff-match-patch
def highlight_differences(original, corrected):
    """
    Highlights differences between original and corrected text at character level.
    Returns the corrected text with HTML highlighting for changed parts.
    Uses the diff-match-patch library for more accurate character-level diffs.
    """
    import html

    from diff_match_patch import diff_match_patch

    # Create a diff_match_patch object
    dmp = diff_match_patch()

    # Get the diff between the two texts
    diffs = dmp.diff_main(original, corrected)

    # Apply semantic cleanup to make the diff more meaningful
    dmp.diff_cleanupSemantic(diffs)

    # Process the diff to create HTML with highlights
    result = []
    for op, text in diffs:
        if op == 0:  # Equal
            result.append(html.escape(text))
        elif op == 1:  # Inserted
            result.append(
                f"<span style='background-color: #DCFCE7; color: #166534; font-weight: bold;'>{html.escape(text)}</span>"
            )
        elif op == -1:  # Deleted
            result.append(
                f"<span style='background-color: #FEE2E2; color: #991B1B; text-decoration: line-through;'>{html.escape(text)}</span>"
            )

    # Join the result and replace newlines with <br> for HTML display
    return "".join(result).replace("\n", "<br>")


# Function to analyze document
def analyze_document(document_text):
    logger.info(f"Analyzing document with model: {settings.ai.openai_model}")
    logger.info(f"Document length: {len(document_text)} characters")

    system_prompt = prompts.get("system", "")
    user_prompt = prompts.get("user", "").format(document_text=document_text)

    try:
        logger.info("Sending request to OpenAI API")
        response = client.chat.completions.create(
            model=settings.ai.openai_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        logger.info(response.usage)

        result = json.loads(response.choices[0].message.content)
        logger.info(f"Analysis complete. Found {len(result.get('issues', []))} issues")
        return result
    except Exception as e:
        logger.error(f"Error analyzing document: {str(e)}", exc_info=True)
        st.error(f"Ошибка при анализе документа: {str(e)}")
        return None


# Sidebar
with st.sidebar:
    st.header("Настройки")

    # File uploader
    uploaded_file = st.file_uploader("Загрузите документ для анализа", type=["docx", "pdf", "rtf", "txt"])

    # Example documents
    st.markdown("### Примеры документов")
    example_dir = Path("examples")
    if example_dir.exists():
        example_files = list(example_dir.glob("**/*.*"))
        if example_files:
            selected_example = st.selectbox(
                "Выберите пример документа",
                options=[""] + [f.name for f in example_files],
                format_func=lambda x: "Выберите пример..." if x == "" else x,
            )

            if selected_example:
                example_path = next((f for f in example_files if f.name == selected_example), None)
                logger.info(f"Selected example: {selected_example}, path: {example_path}")
        else:
            st.info("Примеры документов не найдены")
            logger.info("No example documents found in examples directory")
    else:
        st.info("Директория с примерами не найдена")
        logger.info("Examples directory not found")

# Main content
document_text = None

# Process uploaded file
if uploaded_file is not None:
    with st.spinner("Обработка загруженного документа..."):
        logger.info(f"Processing uploaded file: {uploaded_file.name}")
        # Save uploaded file temporarily
        temp_path = Path(f"temp_{uploaded_file.name}")
        with open(temp_path, "wb") as f:
            file_content = uploaded_file.getvalue()
            logger.info(f"File size: {len(file_content)} bytes")
            f.write(file_content)

        try:
            # Parse document
            logger.info(f"Parsing document: {temp_path}")
            document_text = parse(temp_path)
            logger.info(f"Document parsed successfully: {len(document_text)} characters")
            st.success("Документ успешно загружен и обработан")
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}", exc_info=True)
            st.error(f"Ошибка при обработке документа: {str(e)}")
        finally:
            # Clean up temporary file
            if temp_path.exists():
                logger.info(f"Removing temporary file: {temp_path}")
                os.remove(temp_path)

# Process example file if selected
elif "selected_example" in locals() and selected_example and example_path is not None:
    with st.spinner(f"Обработка примера: {selected_example}"):
        logger.info(f"Processing example file: {selected_example}")
        try:
            logger.info(f"Parsing example document: {example_path}")
            document_text = parse(example_path)
            logger.info(f"Example document parsed successfully: {len(document_text)} characters")
            st.success(f"Пример документа '{selected_example}' успешно загружен")
        except Exception as e:
            logger.error(f"Error processing example: {str(e)}", exc_info=True)
            st.error(f"Ошибка при обработке примера: {str(e)}")

# Display document preview if available
if document_text:
    logger.info("Document loaded, displaying preview")
    with st.expander("Предпросмотр документа", expanded=False):
        # allow to download original document
        if uploaded_file:
            st.download_button(
                "Скачать оригинал документа",
                data=uploaded_file.getvalue(),
                file_name=uploaded_file.name,
                mime="application/octet-stream",
            )
            logger.info("Download button added for original document (uploaded file)")
        elif example_path is not None and isinstance(example_path, Path):
            st.download_button(
                "Скачать оригинал документа",
                data=example_path.read_bytes(),
                file_name=example_path.name,
                mime="application/octet-stream",
            )
            logger.info("Download button added for original document (example file)")
        st.text_area("Содержимое документа", document_text, height=300, disabled=True)

    # Analyze button
    if st.button("Анализировать документ", type="primary"):
        logger.info("Analyze button clicked")
        with st.spinner("Анализ документа..."):
            result = analyze_document(document_text)

            if result and "issues" in result:
                issues = result["issues"]

                if not issues:
                    logger.info("No issues found in document")
                    st.success("Проблемных мест в документе не обнаружено!")
                else:
                    logger.info(f"Found {len(issues)} issues in document")
                    st.subheader(f"Обнаружено проблемных мест: {len(issues)}")

                    for i, issue in enumerate(issues, 1):
                        logger.info(f"Issue {i}: {issue.get('criterion', 'Unknown')}")
                        with st.container():
                            # Generate highlighted text on the fly if needed
                            corrected_html = ""
                            if "corrected_text" in issue and "citation" in issue:
                                # Generate highlighted text
                                highlighted_text = highlight_differences(issue["citation"], issue["corrected_text"])

                                # Create the corrected text HTML
                                corrected_html = dedent(f"""
                                <div class="corrected-text-box">
                                    <strong>Исправленный текст:</strong><br>{highlighted_text}
                                </div>
                                """)

                            markdown_x_html = (
                                dedent(f"""
                                <span class="issue-box"/>
                                <div class="issue-title">Проблема {i}: {issue.get("criterion", "Неизвестная проблема")}</div>
                                <p><strong>Объяснение:</strong> {issue.get("explanation", "")}</p>
                                <div class="citation-box">
                                    <strong>Цитата:</strong><br>{issue.get("citation", "")}
                                </div>
                                <div class="recommendation-box">
                                    <strong>Рекомендация:</strong><br>{issue.get("recommendation", "")}
                                </div>
                                """)
                                + corrected_html
                            )

                            # Render everything in one markdown call
                            st.markdown(
                                markdown_x_html,
                                unsafe_allow_html=True,
                            )

            elif result:
                logger.warning(f"Unexpected API response format: {result}")
                st.warning("Неожиданный формат ответа от API")
                st.json(result)
else:
    logger.info("No document loaded, displaying info message")
    st.info("Загрузите документ или выберите пример для анализа")

# Footer
st.markdown("---")
st.markdown("© 2025 Pedantic Lawyer - Инструмент для анализа нормативных правовых актов ЯНАО")
