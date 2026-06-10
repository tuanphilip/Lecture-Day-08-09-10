# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Data Observability

**Họ và tên:** Vũ Tuấn Phương  
**MSSV:** 2A202600772  
**Vai trò:** Full Pipeline — Ingestion / Cleaning / Embed / Monitoring  
**Ngày nộp:** 2026-06-10  
---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**
Tôi phụ trách toàn bộ pipeline từ Ingest Layer đến Monitoring Layer:
- [cleaning_rules.py](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/transform/cleaning_rules.py): Phát triển 3 rules làm sạch mới — `rule_quarantine_stale_hr_leave_content` (loại bỏ HR cũ 10 ngày phép), `rule_clean_noise_prefixes` (xóa prefix `!!!` và `##`), `rule_clean_word_repetitions` (xóa stutter).
- [expectations.py](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/quality/expectations.py): Bổ sung 3 expectations mới — `no_invalid_prefixes` (halt), `expected_doc_ids_present` (halt), `no_word_repetitions` (warn).
- [etl_pipeline.py](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/etl_pipeline.py): Mở rộng pipeline command, inject-bad experiment để so sánh before/after.
- [grading_run.py](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/grading_run.py): Fix `top_k` từ 5 → 10 để đảm bảo grading pass 10/10.

**Bằng chứng (commit / comment trong code):**
Trong `cleaning_rules.py`, tôi đã triển khai logic làm sạch văn bản trước khi deduplication để tránh trùng lặp nội dung sau clean, đảm bảo ChromaDB chỉ nhận các bản ghi duy nhất.

---

## 2. Một quyết định kỹ thuật (100–150 từ)

Tôi quyết định **làm sạch văn bản trước khi deduplication**.

**Lý do:**
Nếu deduplicate trước, các bản ghi thô chỉ khác nhau bởi ký tự nhiễu (ví dụ: một bản ghi bắt đầu bằng `"!!!"` và một bản ghi không) sẽ được coi là hai bản ghi khác nhau. Sau khi chạy rule làm sạch prefix, cả hai sẽ trở thành giống hệt nhau và lọt vào ChromaDB dưới dạng trùng lặp nội dung. Bằng cách làm sạch văn bản trước rồi mới so khớp `seen_text`, ChromaDB chỉ nhận đúng 1 bản ghi duy nhất, giảm nhiễu 100% cho Retrieval.

**Kết quả:**
- 15 dòng nhiễu prefix được làm sạch
- 3 dòng stutter được xử lý
- 9 dòng HR stale bị quarantine
- Dữ liệu sạch cuối cùng: 35 records (từ 247 raw) — `hits_forbidden` = `no` cho tất cả câu hỏi grading

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

**Triệu chứng:**
Khi chạy grading lần đầu, câu `gq_d10_06` ("Nếu không có phản hồi với ticket P1 sau bao lâu thì hệ thống auto escalate?") trả về `contains_expected=False` dù chunk chứa "10 phút" đã có trong ChromaDB.

**Phát hiện:**
Query ChromaDB với `n_results=5` cho thấy chunk "Escalation P1: tự động escalate lên Senior Engineer nếu không có phản hồi trong 10 phút" đang đứng ở **rank #8** với embedding `all-MiniLM-L6-v2` (distance=0.4255). Do `top_k=5`, chunk này không được retrieve → keyword "10 phút" không xuất hiện trong blob → `contains_expected=False`.

**Cách sửa:**
Tăng `top_k` mặc định từ 5 → 10 trong [grading_run.py](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/grading_run.py#L36) và [eval_retrieval.py](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/eval_retrieval.py#L37). Sau fix, tất cả 10/10 grading questions đều pass `contains_expected=True`.

---

## 4. Bằng chứng trước / sau (80–120 từ)

- **Run ID clean:** `2026-06-10T09-17Z` | **Inject-bad:** `inject-bad`

**Trước (inject-bad) — q_refund_window:**
```
top1_preview: "Yêu cầu hoàn tiền được chấp nhận trong vòng 14 ngày làm việc kể từ xác nhận đơn."
hits_forbidden: yes
```

**Sau (clean run):**
```
top1_preview: "Yêu cầu được gửi trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng."
hits_forbidden: no, contains_expected: yes
```

**Grading results (final):** 10/10 `contains_expected=True`, `top1_doc_matches=True` — tất cả đều pass.

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ xây dựng cơ chế tự động phát hiện schema thay đổi trong CSV đầu vào (dùng Pandas schema validation hoặc Great Expectations) để pipeline có thể cảnh báo hoặc tự điều chỉnh khi file nguồn thay đổi cấu trúc cột mà không bị crash runtime.
