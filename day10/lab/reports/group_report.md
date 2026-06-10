# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** VinAI Lab Team  
**Thành viên:**
| Tên | Vai trò (Day 10) | Email |
|-----|------------------|-------|
| Nguyen Van A | Ingestion / Raw Owner | a.nv@company.internal |
| Tran Van B | Cleaning & Quality Owner | b.tv@company.internal |
| Pham Van C | Embed & Idempotency Owner | c.pv@company.internal |
| Le Thi D | Monitoring / Docs Owner | d.lt@company.internal |

**Ngày nộp:** 2026-06-10  
**Repo:** d:\VinAI-Lab\Lecture-Day-08-09-10  
**Độ dài khuyến nghị:** 600–1000 từ

---

## 1. Pipeline tổng quan (150–200 từ)

**Tóm tắt luồng:**
Pipeline chất lượng dữ liệu hoạt động theo mô hình ETL khép kín:
1. **Ingest Layer:** Tải tệp CSV xuất thô [policy_export_dirty.csv](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/data/raw/policy_export_dirty.csv) và đếm tổng số bản ghi thô (247 records).
2. **Transform Layer:** Áp dụng bộ quy tắc làm sạch văn bản và chuẩn hóa ngày hiệu lực. Các dòng không hợp lệ hoặc stale sẽ bị đưa vào khu vực cách ly [quarantine](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/artifacts/quarantine/).
3. **Quality Validation Suite:** Thực hiện kiểm tra định dạng và nội dung qua bộ luật Expectations. Nếu phát hiện vi phạm luật nghiêm trọng (Halt), pipeline sẽ lập tức dừng hoạt động và trả về exit code 2.
4. **Embed & Indexing Layer:** Nạp dữ liệu idempotent vào ChromaDB bằng cơ chế upsert dựa trên `chunk_id` ổn định và tự động prune các vector mồ côi (mồi cũ).
5. **Monitoring Layer:** Xuất tệp manifest và đo lường độ mới (Freshness SLA) so với giờ hệ thống thực tế.

**Lệnh chạy một dòng (copy từ README thực tế của nhóm):**
```bash
python etl_pipeline.py run
```
*Ghi chú: run_id được sinh tự động theo định dạng UTC timestamp (ví dụ: `2026-06-10T06-31Z`) hiển thị trực tiếp ở dòng đầu tiên của log.*

---

## 2. Cleaning & expectation (150–200 từ)

Nhóm đã bổ sung **3 rules làm sạch mới** và **3 expectations mới** ngoài bộ baseline để kiểm duyệt dữ liệu toàn diện hơn.

### 2a. Bảng metric_impact (bắt buộc — chống trivial)

| Rule / Expectation mới (tên ngắn) | Trước (số liệu) | Sau / khi inject (số liệu) | Chứng cứ (log / CSV / commit) |
|-----------------------------------|------------------|-----------------------------|-------------------------------|
| `rule_quarantine_stale_hr_leave_content` | 0 cách ly | 9 cách ly | [run_2026-06-10T06-31Z.log](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/artifacts/logs/run_2026-06-10T06-31Z.log#L12) |
| `rule_clean_noise_prefixes` | 15 lỗi prefix | 0 lỗi prefix (15 cleaned) | [run_2026-06-10T06-31Z.log](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/artifacts/logs/run_2026-06-10T06-31Z.log#L13) |
| `rule_clean_word_repetitions` | 3 lỗi stutter | 0 lỗi stutter (3 cleaned) | [run_2026-06-10T06-31Z.log](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/artifacts/logs/run_2026-06-10T06-31Z.log#L15) |
| `no_invalid_prefixes` (halt) | fail khi chưa làm sạch | OK (halt) | [run_2026-06-10T06-31Z.log](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/artifacts/logs/run_2026-06-10T06-31Z.log#L13) |
| `expected_doc_ids_present` (halt) | fail nếu thiếu doc_id | OK (halt) | [run_2026-06-10T06-31Z.log](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/artifacts/logs/run_2026-06-10T06-31Z.log#L14) |
| `no_word_repetitions` (warn) | warn khi chưa làm sạch | OK (warn) | [run_2026-06-10T06-31Z.log](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/artifacts/logs/run_2026-06-10T06-31Z.log#L15) |

**Rule chính (baseline + mở rộng):**
- **Allowlist filter:** Chỉ chấp nhận 5 `doc_id` canonical.
- **Date ISO parser:** Chuyển đổi ngày `DD/MM/YYYY` về `YYYY-MM-DD`.
- **Stale HR rules:** Loại bỏ tệp tin HR cũ trước 2026 (`eff_norm < "2026-01-01"`) và lọc văn bản chứa "10 ngày phép".
- **Stale refund window fix:** Tìm và thay thế chuỗi "14 ngày làm việc" thành "7 ngày làm việc" cho policy hoàn tiền v4.

**Ví dụ 1 lần expectation fail (nếu có) và cách xử lý:**
Khi chạy lệnh mô phỏng sự cố `python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate`, expectation `refund_no_stale_14d_window` lập tức kích hoạt trạng thái **FAIL (halt)** do phát hiện có 1 chunk chứa dữ liệu stale "14 ngày". Để xử lý, hệ thống buộc phải sử dụng tham số `--skip-validate` để tiếp tục embed (để so sánh trước/sau), nhưng trong thực tế, pipeline sẽ dừng lại (halt) không ghi đè dữ liệu lỗi vào database.

---

## 3. Before / after ảnh hưởng retrieval hoặc agent (200–250 từ)

**Kịch bản inject:**
Nhóm chạy thử nghiệm nạp dữ liệu bị lỗi cố ý (chứa chính sách hoàn tiền cũ 14 ngày) thông qua cờ `--no-refund-fix --skip-validate`, sau đó đánh giá chất lượng qua script `eval_retrieval.py` và lưu trữ tại [eval_inject_bad.csv](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/artifacts/eval/eval_inject_bad.csv). Sau đó, chạy lại pipeline sạch để chuẩn hóa chính sách về 7 ngày và xuất báo cáo chất lượng tại [eval_after_fix.csv](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/artifacts/eval/eval_after_fix.csv).

**Kết quả định lượng (từ CSV / bảng):**
Ở câu hỏi `q_refund_window` ("Khách hàng có bao nhiêu ngày để yêu cầu hoàn tiền kể từ khi đơn được xác nhận?"):
- **Trước (Inject Bad):** 
  * `top1_preview`: `"Yêu cầu hoàn tiền được chấp nhận trong vòng 14 ngày làm việc kể từ xác nhận đơn."`
  * `hits_forbidden`: `yes`
  * *Hệ quả:* Agent đọc từ context bị sai lệch và trả lời sai cho người dùng là 14 ngày.
- **Sau (Clean Run):**
  * `top1_preview`: `"Yêu cầu được gửi trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng. [cleaned: stale_refund_window]"`
  * `hits_forbidden`: `no`
  * *Hệ quả:* Agent đọc được context sạch đã cập nhật chuẩn 7 ngày và đưa ra câu trả lời chính xác.

---

## 4. Freshness & monitoring (100–150 từ)

**SLA & Monitor:**
Nhóm đã thiết lập SLA thời gian cập nhật dữ liệu là **24 giờ** tính từ thời điểm export (`latest_exported_at`). 
Do tệp xuất thô mẫu có ngày xuất bản tối đa là `2026-04-11`, nên khi so sánh với thời gian thực tế hiện tại, chênh lệch `age_hours` lên tới 1446.5 giờ, kích hoạt trạng thái **freshness_check=FAIL**. 
Cơ chế này giúp đảm bảo dữ liệu phục vụ Agent luôn mới nhất và sẽ gửi cảnh báo đến kênh `#data-alerts-day10` để IT/Ops kịp thời phản hồi khi tệp xuất bị nghẽn (data pipeline lag).

---

## 5. Liên hệ Day 09 (50–100 từ)

Dữ liệu tri thức sau khi được chuẩn hóa ở Day 10 sẽ được ghi đè vào collection `day10_kb`. 
Đồ thị multi-agent ở Day 09 hoàn toàn có thể trỏ thẳng tới collection này để trả lời câu hỏi bằng cách thiết lập biến môi trường `CHROMA_COLLECTION=day10_kb`. Sự tích hợp này đảm bảo các Worker Agents hoạt động trên nguồn dữ liệu sạch, đã qua QA nghiêm ngặt, giảm thiểu tối đa ảo giác (hallucination) do dữ liệu nguồn bẩn gây ra.

---

## 6. Rủi ro còn lại & việc chưa làm

- **Lệch ID do Quarantine:** Việc sử dụng số thứ tự `seq` để sinh `chunk_id` có thể bị thay đổi nếu danh sách các dòng bị cách ly thay đổi, gây khó khăn cho việc đối chiếu lineage dòng dữ liệu.
- **Raw Schema Validation:** Cần xây dựng lớp kiểm duyệt schema thô (như Pydantic/Pandas Schema) ở Ingest Layer trước khi thực hiện clean, tránh lỗi runtime khi file CSV thay đổi cấu trúc cột.
