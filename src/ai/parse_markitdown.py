from pathlib import Path

from markitdown import MarkItDown

md = MarkItDown(enable_plugins=True)


def parse(path: Path) -> str:
    """
    Parse a document and return the text content.
    """
    result = md.convert(path)
    return result.markdown


if __name__ == "__main__":
    example_path = Path("Нормативные акты/Закон ЯНАО от 04.06.2024 N 30-ЗАО  О внесении изменений в За.rtf")
    print(parse(example_path))
