# Stack Decision

This project will use **Python** as the primary implementation language.

## Core Stack:
- **Language**: Python 3.12+
- **Browser Automation**: Playwright Python
- **Backend/API**: FastAPI
- **Data Validation & Schemas**: Pydantic
- **Testing**: Pytest
- **Reporting**: Jinja2
- **Analytics (Phase 3)**: Snowflake

## Reasoning:
- **Better testing ecosystem**: Pytest offers superior fixtures and parameterization compared to Node.js alternatives.
- **Stronger fuzzing/property-based testing**: Python has excellent libraries (like Hypothesis) for generating edge-case test data.
- **Better data handling**: Pydantic provides robust, typed data validation right out of the box.
- **Easier future AI/ML integration**: If we choose to move beyond deterministic logic in Phase 3 or later, the Python ecosystem natively supports AI and data science libraries.
- **Faster experimentation**: Fast REPL loops, Jupyter notebooks for prototyping generation logic.
- **Cleaner validation pipelines**: Strong typing with Python 3.12 and Pydantic makes validation layers incredibly rigid.