import asyncio
import os
from pathlib import Path

import streamlit as st

from src.ai.analyzer import analyze_document
from src.ai.parse_markitdown import parse
from src.logging_ import logger
from src.ui.components import apply_custom_styles, render_issue
from src.ui.diff import highlight_differences

# Configure logging
logger.info("Starting Pedantic Lawyer application")

# Set page configuration
st.set_page_config(
    page_title="Pedantic Lawyer - Анализатор документов ЯНАО",
    page_icon="⚖️",
    layout="wide",
)

# Custom CSS
apply_custom_styles()

# Title
st.title("Pedantic Lawyer - Анализатор документов ЯНАО")
st.markdown("Инструмент для выявления проблемных мест в нормативных правовых актах Ямало-Ненецкого автономного округа")

# Sidebar
with st.sidebar:
    st.header("Настройки")

    # Input method selection
    input_method = st.radio(
        "Выберите способ ввода текста",
        ["Вставить текст", "Загрузить файл", "Использовать пример"],
        index=0,
    )

    if input_method == "Загрузить файл":
        # File uploader
        uploaded_file = st.file_uploader("Загрузите документ для анализа", type=["docx", "pdf", "rtf", "txt"])
    elif input_method == "Использовать пример":
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

# Handle different input methods
if input_method == "Вставить текст":
    document_text = st.text_area(
        "Введите текст для анализа",
        height=300,
        placeholder="Вставьте сюда текст нормативного правового акта...",
    )
    if document_text:
        st.success("Текст готов к анализу")
        logger.info(f"Text input received, length: {len(document_text)} characters")

elif input_method == "Загрузить файл" and uploaded_file is not None:
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

elif (
    input_method == "Использовать пример"
    and "selected_example" in locals()
    and selected_example
    and example_path is not None
):
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
        # Show download button only for file uploads
        if input_method == "Загрузить файл" and uploaded_file:
            st.download_button(
                "Скачать оригинал документа",
                data=uploaded_file.getvalue(),
                file_name=uploaded_file.name,
                mime="application/octet-stream",
            )
            logger.info("Download button added for original document (uploaded file)")
        elif input_method == "Использовать пример" and example_path is not None and isinstance(example_path, Path):
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
            try:
                # Run async function in a synchronous context
                result = asyncio.run(analyze_document(document_text))

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
                            render_issue(issue, i, highlight_differences)

                elif result:
                    logger.warning(f"Unexpected API response format: {result}")
                    st.warning("Неожиданный формат ответа от API")
                    st.json(result)
            except Exception as e:
                st.error(f"Ошибка при анализе документа: {str(e)}")
else:
    logger.info("No document loaded, displaying info message")
    st.info("Выберите способ ввода текста и загрузите документ для анализа")

# Footer
st.markdown("---")
st.markdown("© 2025 Pedantic Lawyer - Инструмент для анализа нормативных правовых актов ЯНАО")
