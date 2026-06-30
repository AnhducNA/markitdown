"""Minimal example converting a file with MarkItDown.

Usage:
  python examples/quickstart.py path/to/file.pdf
"""
import sys
from markitdown import MarkItDown


def main():
    if len(sys.argv) < 2:
        print("Usage: python examples/quickstart.py path/to/file")
        sys.exit(1)
    path = sys.argv[1]
    md = MarkItDown(enable_plugins=False,)
    result = md.convert(path)
    print(result.markdown if hasattr(result, "markdown") else result.text_content)


if __name__ == "__main__":
    main()
