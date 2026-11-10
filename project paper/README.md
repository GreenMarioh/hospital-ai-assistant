# Project Paper: AI Hospital Management Assistant

This directory contains the IEEE-formatted academic project paper for the **AI Hospital Management Assistant**, constructed in accordance with the guidelines specified in `Project paper format.docx`.

## Directory Contents
- **`paper.tex`**: The complete, self-contained LaTeX source file conforming to IEEE conference / academic formatting.
- **`figures/`**: High-resolution diagrams, architecture flowcharts, and application screenshots embedded within the paper:
  - `system_architecture.png`: Multi-tier system architecture diagram.
  - `patient-triage.png`: Patient symptom intake & AI triage web interface screenshot.
  - `doctor-briefing.png`: Doctor clinical chart & pre-visit AI briefing interface screenshot.
  - `admin-dashboard.png`: Hospital administrative analytics & metrics dashboard screenshot.
  - `triage_flow.png`: Deterministic red-flag emergency detection & output guardrail flowchart.
  - `audit_chain.png`: Cryptographic SHA-256 tamper-evident audit log hash chain diagram.
  - `loadtest_latency.png`: Distributed k6 load-testing and subsystem latency benchmark chart.
- **`Project paper format.docx`**: The original structural format specification.

---

## Authors & Institutional Affiliation
- **Ayushman Patel** (Roll No: 2305776)
- **Khushal Nirwal** (Roll No: 2305788)
- **Mohnish Kumar** (Roll No: 2305793)
- **Prahlad Jha** (Roll No: 23051846)
- **Guide:** Dr. Jayashree Piri
- **Affiliation:** School of Computer Science and Engineering, KIIT Deemed to be University, Bhubaneswar, Odisha, India.
- **Session:** Academic Year 2026–2027

---

## Compilation Instructions

### 1. In Overleaf (Recommended)
1. Zip the contents of the `Project Paper` directory (`paper.tex` and the `figures/` folder).
2. Go to [Overleaf](https://www.overleaf.com), click **New Project** $\rightarrow$ **Upload Project**, and select the zip file.
3. Select `pdfLaTeX` as the compiler and click **Recompile**.

### 2. Local TeX Live / MiKTeX / VS Code
Run the standard two-pass `pdflatex` command in this directory:
```bash
pdflatex paper.tex
pdflatex paper.tex
```

---

## Paper Sections Overview
1. **Abstract (~200 words):** Outlines the clinical motivation, system architecture, deterministic guardrails, and benchmark results.
2. **Section I (Introduction):** Outpatient friction, clinical burnout, systemic gaps in legacy EHRs, and key technical contributions.
3. **Section II (Techniques and Technologies Used):** FastAPI async architecture, Next.js 15 App Router, PostgreSQL GiST exclusion constraints & GIN full-text search, Google Gemini SDK, Manchester Triage System (MTS) & Emergency Severity Index (ESI), Argon2id, RFC 6238 TOTP, Fernet encryption, and ClamAV streaming.
4. **Section III (Designing and Software Requirements Specification):** IEEE 830 functional requirements across Patient, Doctor, Reception, and Admin roles, access control matrix, and UI screenshots.
5. **Section IV (Implementation):** Deterministic red-flag algorithm, output guardrails, booking tool confirmation gate, in-memory TF-IDF knowledge base RAG, and SHA-256 audit chaining.
6. **Section V (Testing, Results, and Comparative Analysis):** Verification test cases table (T01–T08), 60 clinical benchmark cases (100% emergency recall), k6 load test results (p95: 67 ms), and feature-wise comparative analysis against Epic, OpenEMR, and commercial chatbots.
7. **Section VI (Conclusion and Future Scope):** Outcomes, clinical safety boundaries (~200 words), and roadmap (HL7 FHIR R4, pgvector RAG, WebRTC telemedicine, multilingual voice).
8. **References:** 18 formal academic citations in IEEE format.

