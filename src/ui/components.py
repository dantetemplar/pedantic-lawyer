import streamlit as st
from humanfriendly.text import dedent


def apply_custom_styles():
    """Apply custom CSS styles to the Streamlit app."""
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


def render_issue(issue, index, highlight_differences_func):
    """Render a single issue with all its components."""
    corrected_html = ""
    if "corrected_text" in issue and "citation" in issue:
        highlighted_text = highlight_differences_func(issue["citation"], issue["corrected_text"])
        corrected_html = dedent(f"""
        <div class="corrected-text-box">
            <strong>Исправленный текст:</strong><br>{highlighted_text}
        </div>
        """)

    markdown_html = (
        dedent(f"""
        <span class="issue-box"/>
        <div class="issue-title">Проблема {index}: {issue.get("criterion", "Неизвестная проблема")}</div>
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

    st.markdown(markdown_html, unsafe_allow_html=True)
