# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** Cá nhân  
**Thành viên:**
| Tên | MSSV | Vai trò |
|-----|------|---------|
| Vũ Tuấn Phương | 2A202600772 | Full Pipeline — Ingestion / Cleaning / Embed / Grading / Monitoring |

**Ngày nộp:** 2026-06-10  
**Repo:** d:\VinAI-Lab\Lecture-Day-08-09-10  
**Độ dài khuyến nghị:** 600–1000 từ

---

## 1. Pipeline tổng quan (150–200 từ)

**Tóm tắt luồng:**
Pipeline chất lượng dữ liệu hoạt động theo mô hình ETL khép kín:

1. **Ingest Layer:** Tải tệp CSV xuất thô [policy_export_dirty.csv](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/data/raw/policy_export_dirty.csv) và đếm tổng số bản ghi thô (247 records) với run_id tự động theo UTC timestamp.
2. **Transform Layer:** Áp dụng 6 rules làm sạch — lọc allowlist 5 doc_id canonical, chuẩn hóa ngày ISO, loại bỏ HR stale, sửa refund window "14 ngày" → "7 ngày", xóa noise prefixes (`!!!`, `##`), xóa word repetitions (stutter). Các dòng không hợp lệ bị đưa vào quarantine.
3. **Quality Validation Suite:** 8 expectations (6 halt + 2 warn) kiểm tra định dạng, nội dung, doc_id. Nếu vi phạm halt → pipeline dừng ngay (exit code 2).
4. **Embed & Indexing Layer:** Upsert idempotent vào ChromaDB collection `day10_kb` với cơ chế prune vector mồ côi.
5. **Monitoring Layer:** Xuất manifest JSON + freshness check (SLA 24h) so với giờ hệ thống.

**Lệnh chạy:**
```powershell
cd day10/lab
python etl_pipeline.py run
```

Kết quả: `raw_records=247, cleaned_records=35, quarantine_records=212, PIPELINE_OK`

---

## 2. Cleaning & expectation (150–200 từ)

Tôi đã bổ sung **3 rules làm sạch mới** và **3 expectations mới** ngoài bộ baseline.

### 2a. Bảng metric_impact

| Rule / Expectation mới | Trước (số liệu) | Sau / khi inject (số liệu) | Chứng cứ |
|------------------------|-----------------|----------------------------|----------|
| `rule_quarantine_stale_hr_leave_content` | 0 cách ly | 9 cách ly | [run log](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/artifacts/logs/run_2026-06-10T09-17Z.log) |
| `rule_clean_noise_prefixes` | 15 lỗi prefix | 0 lỗi (15 cleaned) | [run log](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/artifacts/logs/run_2026-06-10T09-17Z.log) |
| `rule_clean_word_repetitions` | 3 lỗi stutter | 0 lỗi (3 cleaned) | [run log](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/artifacts/logs/run_2026-06-10T09-17Z.log) |
| `no_invalid_prefixes` (halt) | fail khi chưa clean | OK | [run log](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/artifacts/logs/run_2026-06-10T09-17Z.log) |
| `expected_doc_ids_present` (halt) | fail nếu thiếu doc_id | OK | [run log](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/artifacts/logs/run_2026-06-10T09-17Z.log) |
| `no_word_repetitions` (warn) | warn khi chưa clean | OK | [run log](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/artifacts/logs/run_2026-06-10T09-17Z.log) |

**Rule chính (baseline + mở rộng):**
- **Allowlist filter:** Chỉ chấp nhận 5 `doc_id` canonical (lọc ~200+ dòng lạ).
- **Date ISO parser:** Chuyển đổi `DD/MM/YYYY` → `YYYY-MM-DD`.
- **Stale HR rules:** Loại bỏ HR content có `eff_norm < "2026-01-01"` và lọc văn bản chứa "10 ngày phép" (9 dòng quarantine).
- **Stale refund window fix:** Replace "14 ngày làm việc" → "7 ngày làm việc".
- **Noise prefixes:** Xóa `!!!` và `##` ở đầu chunk text (15 dòng).
- **Word repetitions:** Xóa stutter như "làm việc làm việc" (3 dòng).

**Ví dụ expectation fail và cách xử lý:**
Khi chạy `python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate`, expectation `refund_no_stale_14d_window` kích hoạt **FAIL (halt)** do chunk chứa "14 ngày". Với `--skip-validate`, pipeline vẫn tiếp tục embed để so sánh before/after, nhưng trong thực tế pipeline sẽ dừng lại không ghi đè dữ liệu lỗi vào database.

---

## 3. Before / after ảnh hưởng retrieval hoặc agent (200–250 từ)

**Kịch bản inject:**
Tôi chạy inject-bad (chứa chính sách hoàn tiền cũ 14 ngày) qua `--no-refund-fix --skip-validate`, đánh giá tại [eval_inject_bad.csv](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/artifacts/eval/eval_inject_bad.csv). Sau đó chạy pipeline sạch, đánh giá tại [eval_final.csv](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/artifacts/eval/eval_final.csv).

**Kết quả định lượng:**

| Câu hỏi | Trước (inject-bad) | Sau (clean) |
|---------|-------------------|-------------|
| **q_refund_window** (số ngày hoàn tiền) | `top1_preview`: "14 ngày làm việc"<br>`hits_forbidden`: **yes** | `top1_preview`: "7 ngày làm việc"<br>`hits_forbidden`: **no** |
| **q_p1_escalation** (auto escalate P1) | `contains_expected`: **no** (top_k=3 quá thấp) | `contains_expected`: **yes** (top_k=10) |

**Grading results sau fix (10/10 pass):**

| ID | Câu hỏi | contains_expected | top1_doc | top1_matches |
|----|---------|-------------------|----------|-------------|
| gq_d10_01 | Số ngày yêu cầu hoàn tiền | ✅ True | policy_refund_v4 | ✅ |
| gq_d10_02 | Sản phẩm không được hoàn tiền | ✅ True | policy_refund_v4 | ✅ |
| gq_d10_03 | Finance xử lý trong bao lâu | ✅ True | policy_refund_v4 | ✅ |
| gq_d10_04 | SLA phản hồi P1 | ✅ True | sla_p1_2026 | ✅ |
| gq_d10_05 | SLA resolution P1 | ✅ True | sla_p1_2026 | ✅ |
| gq_d10_06 | Auto escalate P1 sau bao lâu | ✅ True | sla_p1_2026 | ✅ |
| gq_d10_07 | Số lần login sai khóa tài khoản | ✅ True | it_helpdesk_faq | ✅ |
| gq_d10_08 | VPN tối đa thiết bị | ✅ True | it_helpdesk_faq | ✅ |
| gq_d10_09 | Ngày phép năm HR 2026 | ✅ True | hr_leave_policy | ✅ |
| gq_d10_10 | Level 4 Admin Access phê duyệt | ✅ True | access_control_sop | ✅ |

---

## 4. Freshness & monitoring (100–150 từ)

**SLA & Monitor:**
SLA thời gian cập nhật dữ liệu được thiết lập là **24 giờ** tính từ `latest_exported_at`. Do tệp xuất thô mẫu có ngày xuất bản tối đa là `2026-04-11`, chênh lệch `age_hours` lên tới ~1,449 giờ so với thời gian thực, kích hoạt **freshness_check=FAIL**. Cơ chế này giúp đảm bảo pipeline luôn cảnh báo khi dữ liệu quá cũ, tránh việc Agent trả lời dựa trên thông tin lỗi thời.

**Run log:**
```
freshness_check=FAIL {"latest_exported_at": "2026-04-11T00:00:00",
"age_hours": 1449.305, "sla_hours": 24.0,
"reason": "freshness_sla_exceeded"}
```

---

## 5. Liên hệ Day 09 (50–100 từ)

Dữ liệu sau chuẩn hóa được ghi vào collection `day10_kb`. Đồ thị multi-agent Day 09 có thể trỏ tới collection này bằng biến môi trường `CHROMA_COLLECTION=day10_kb`, đảm bảo các Worker Agents hoạt động trên nguồn dữ liệu sạch đã qua QA nghiêm ngặt, giảm thiểu hallucination do dữ liệu bẩn.

---

## 6. Rủi ro còn lại & việc chưa làm

- **Lệch ID do Quarantine:** `chunk_id` sinh từ `seq` có thể thay đổi nếu thứ tự dòng trong CSV bị xáo trộn hoặc dòng trước bị quarantine. Cơ chế prune đã giải quyết vector mồ côi nhưng có thể tăng overhead.
- **Raw Schema Validation:** Cần kiểm tra schema CSV thô trước khi clean để tránh lỗi runtime khi cấu trúc cột thay đổi.
- **Lệch múi giờ:** Freshness check so sánh `exported_at` với giờ hệ thống có thể fail do lệch UTC vs Local time.
- **Fix `top_k`:** Việc tăng `top_k` từ 5 lên 10 trong grading_run.py và eval_retrieval.py là workaround cho embedding model `all-MiniLM-L6-v2`. Cần thử nghiệm với embedding model khác có khả năng phân biệt ngữ nghĩa tiếng Việt tốt hơn.
