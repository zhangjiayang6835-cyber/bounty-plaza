# Contributing to Bounty Plaza

First off, thank you for considering contributing! To maintain the integrity of the bounty system, we enforce strict quality and security standards.

## 🛠 Submission Process

1.  **Claiming**: Find an open issue and comment `/claim`.
2.  **Development**: Create a branch for your fix.
3.  **Testing**: Ensure all `pytest` cases pass locally.
4.  **PR Submission**: Your Pull Request must include:
    - The working code fix.
    - A clear description of the changes.
    - New test cases (if applicable).

## 📊 Scoring Criteria

Every PR is automatically graded on a 100-point scale. You must score **≥ 90 points** to be eligible for rewards.

| Dimension | Weight | Method |
|-----------|:------:|--------|
| **Correctness** | 40% | `pytest` execution. Any failure = 0 total score. |
| **Security** | 35% | AST analysis + Bandit scan. |
| **Code Quality** | 15% | `pylint` score and cyclomatic complexity. |
| **Performance** | 10% | Execution time vs. baseline. |

## 🚫 Prohibited Actions (Instant Ban)

To prevent "gaming" the system, the following will result in an immediate 0 score and potential blacklist:
- **Hardcoding**: Returning the expected output directly instead of implementing logic.
- **Test Tampering**: Deleting or emptying test files.
- **Dangerous Modules**: Using `pickle`, `marshal`, `ctypes`, `eval`, or `exec`.
- **System Calls**: Using `os.system` or `subprocess` without explicit permission.

## 📝 Code Style Guidelines

- Follow **PEP 8** for Python code.
- Include docstrings for all new functions.
- Keep functions small and focused (low cyclomatic complexity).

## 🏆 Winner Determination

1. Only submissions with **Score ≥ 90** are considered.
2. Submissions are ranked by **Quality Score**.
3. In case of a tie, the **earliest submission** wins.
