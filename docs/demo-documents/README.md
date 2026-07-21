# Demo Documents

Fictional sample documents used to seed the DocuMindAI demo (screenshots and the product video). **All content is synthetic** — a made-up company (Meridian Labs), fictional people (`*@example.com`), and invented figures. Nothing here is real data.

| File | Workspace | Purpose |
|---|---|---|
| `meridian_employee_handbook.pdf` | General | Grounded policy Q&A (leave, expenses, security) |
| `meridian_gridwatch_spec.pdf` | General | Product-spec Q&A |
| `scanned_site_inspection_memo.pdf` | General | **Image-only PDF** — exercises the OCR pipeline (PaddleOCR/Docling) |
| `photosynthesis_lesson_notes.pdf` | Teacher | Source material for grounded exam generation |
| `os_process_scheduling_chapter.pdf` | Student | Flashcards, quiz, and tutor grounding |
| `paper_attention_cnn_retina.pdf` | Research | Paper A — reports attention *helps* (large dataset) |
| `paper_cnn_attention_null_result.pdf` | Research | Paper B — reports attention *does not help* (small datasets); deliberately contradicts Paper A for synthesis/contradiction demos |
| `resume_priya_sharma.pdf`, `resume_arjun_mehta.pdf`, `resume_sara_iyer.pdf` | HR | Candidate ranking against a backend-engineer JD |
| `meridian_vendor_msa.pdf` | Legal | Contract with an uncapped-liability clause for risk-report escalation |
| `meridian_annual_report_fy2025.pdf`, `meridian_financials_fy2025_clean.pdf` | Finance | Statements for ratio extraction and proactive insights |

These files are provided so anyone can reproduce the demo locally: create a chat in the matching workspace, upload the file, and run the workflow.
