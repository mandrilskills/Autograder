# 🎓 C Autograder Pro

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini_2.5_Flash-8E75B2?style=for-the-badge&logo=google&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-Cloud-black?style=for-the-badge)

A university-grade, AI-powered autograder for C programming assignments. Moving beyond simple output-matching, this system acts as a virtual teaching assistant, evaluating code correctness, design, performance, and memory management through a multi-agent AI architecture.

## ✨ Key Innovations

* 📸 **Multimodal OCR Submission:** Take a photo or upload a PDF of handwritten exam code. Powered by Gemini Vision, the system transcribes the handwriting directly into the editor for review.
* 🧠 **AST-Driven Deterministic Testing:** Eliminates LLM hallucination. The system mathematically parses the C code's Abstract Syntax Tree (`pycparser`) to understand expected input types and automatically generates strict boundary test cases.
* ⚖️ **Self-Oracle Execution:** The compiled binary is run against generated inputs to produce ground-truth expected outputs, ensuring the program is evaluated fairly against its own logical constraints.
* 🤖 **Agentic Evaluation Swarm:** The code is scored out of 100 marks across 5 distinct axes: 
    * **Functional Testing (30%)**
    * **Optimization Quality (20%)**
    * **Static Analysis (20%)**
    * **Design Quality (15%)**
    * **Performance (15%)**
* 📄 **Academic PDF Reports:** Generates polished, downloadable PDF evaluations using `ReportLab`, complete with Gemini-authored plain-language summaries and compiler error hints.

---

## 🏗️ Architecture Workflow

1.  **Input:** Paste code, upload `.c`, or scan handwritten documents.
2.  **Compilation:** Real `gcc` compilation. Errors trigger an AI explanation sequence (no auto-corrections, maintaining academic integrity).
3.  **Analysis:** `cppcheck` runs static security and style analysis.
4.  **Testing:** AST mathematically generates boundary inputs (with an LLM fallback). The Self-Oracle tests for logic and stability.
5.  **Reporting:** Interactive Streamlit dashboard and downloadable PDF.

---

## 🚀 Installation & Setup

### 1. System Requirements
You must have `gcc` and `cppcheck` installed on your host system.
* **Ubuntu/Debian:** `sudo apt install gcc cppcheck`
* **macOS:** `brew install gcc cppcheck`

### 2. Clone the Repository
```bash
git clone [https://github.com/mandrilskills/autograder.git](https://github.com/mandrilskills/autograder.git)
cd autograder
