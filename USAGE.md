# Using MarkItDown (Quick Guide)

This document provides concise, copy-pastable instructions to install and use the MarkItDown source in this repository.

**Prerequisites:** Python 3.10+ and a virtual environment are recommended.

**Create and activate a virtual environment**

```bash
python3 -m venv .venv
source venv/bin/activate
```

**Install the package (editable from source)**

From the repository root:

```bash
pip install -e 'packages/markitdown[all]'
```

This installs MarkItDown and optional dependencies. To install a subset, use e.g. `pip install 'markitdown[pdf,docx]'`.

**Command-line usage**

- Convert a file to Markdown and print to stdout:

```bash
markitdown path/to/file.pdf > document.md
```

- Specify an output file:

```bash
markitdown path/to-file.pdf -o document.md
```

- Read from stdin (pipe):

```bash
cat path/to-file.pdf | markitdown
```

**Python API (programmatic use)**

Example basic usage:

```python
from markitdown import MarkItDown

md = MarkItDown(enable_plugins=False)
result = md.convert("path/to/file.pdf")
print(result.text_content)
```

Enable cloud or LLM features by passing arguments such as `docintel_endpoint`, `cu_endpoint`, `llm_client`, and `llm_model` when constructing `MarkItDown`.

**Plugins**

- List installed plugins:

```bash
markitdown --list-plugins
```

- Enable plugins for a single run:

```bash
markitdown --use-plugins path/to-file.pdf
```

Install the OCR plugin with `pip install markitdown-ocr` and provide an LLM client (e.g. OpenAI) to enable OCR-based image text extraction. See [packages/markitdown-ocr/README.md](packages/markitdown-ocr/README.md) for details.

**Azure integrations**

- Content Understanding (CU) CLI example:

```bash
markitdown path/to-file.pdf --use-cu --cu-endpoint "<content_understanding_endpoint>"
```

- Document Intelligence CLI example:

```bash
markitdown path-to-file.pdf -o document.md -d -e "<document_intelligence_endpoint>"
```

In Python, pass `cu_endpoint` or `docintel_endpoint` to `MarkItDown(...)`.

**Run tests**

```bash
cd packages/markitdown
pip install hatch
hatch shell
hatch test
```

Run pre-commit checks before submitting changes:

```bash
pre-commit run --all-files
```

**Docker**

```bash
docker build -t markitdown:latest .
docker run --rm -i markitdown:latest < ~/your-file.pdf > output.md
```

**Examples**

See `examples/quickstart.py` for a minimal Python example that converts a file and prints the Markdown output.

**Reference files**

- Main project README: [README.md](README.md)
- Package source: [packages/markitdown](packages/markitdown)
- OCR plugin docs: [packages/markitdown-ocr/README.md](packages/markitdown-ocr/README.md)

If you'd like, I can:

- Run a quick CLI conversion using a test file from the repo.
- Run the example script and show the output.
- Expand this guide into more detailed docs (developer setup, plugin development tutorial).
