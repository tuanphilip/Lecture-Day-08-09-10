# Quality report — Lab Day 10 (nhóm)

**run_id:** `2026-06-10T06-31Z`  
**Ngày:** 2026-06-10

---

## 1. Tóm tắt số liệu

| Chỉ số | Trước (Inject Bad) | Sau (Clean Run) | Ghi chú |
|--------|-------|-----|---------|
| raw_records | 247 | 247 | Tổng số dòng trong policy_export_dirty.csv |
| cleaned_records | 35 | 35 | Số lượng chunk sau khi loại bỏ nhiễu và trùng lặp |
| quarantine_records | 212 | 212 | Các dòng bị cách ly do doc_id lạ, format ngày sai hoặc stale |
| Expectation halt? | FAIL (halted but skipped) | PASS (exit 0) | Halt ở rule `refund_no_stale_14d_window` |

---

## 2. Before / after retrieval (bắt buộc)

> Link dẫn tới file kết quả:
> - Tốt: [eval_after_fix.csv](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/artifacts/eval/eval_after_fix.csv)
> - Xấu (inject): [eval_inject_bad.csv](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/artifacts/eval/eval_inject_bad.csv)

**Câu hỏi then chốt:** refund window (`q_refund_window`)  
- **Trước (Inject Bad):**
  `q_refund_window,Khách hàng có bao nhiêu ngày để yêu cầu hoàn tiền kể từ khi đơn được xác nhận?,policy_refund_v4,Yêu cầu hoàn tiền được chấp nhận trong vòng 14 ngày làm việc kể từ xác nhận đơn.,yes,yes,yes,3`
  *Nhận xét: Trả về câu trả lời chứa thông tin stale "14 ngày làm việc" (bị flag hits_forbidden=yes).*
- **Sau (Clean Run):**
  `q_refund_window,Khách hàng có bao nhiêu ngày để yêu cầu hoàn tiền kể từ khi đơn được xác nhận?,policy_refund_v4,Yêu cầu được gửi trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng. [cleaned: stale_refund_window],yes,no,yes,3`
  *Nhận xét: Text đã được clean chính xác thành 7 ngày, chỉ số hits_forbidden trở về "no".*

**Merit (khuyến nghị):** versioning HR — `q_hr_annual_leave_under3` (kiểm thử so khớp ngày phép 12 ngày vs phép cũ 10 ngày)
- **Trước (Inject Bad & Clean Run):**  
  `q_hr_annual_leave_under3,Nhân viên dưới 3 năm kinh nghiệm được bao nhiêu ngày phép năm?,hr_leave_policy,Nhân viên dưới 3 năm kinh nghiệm được 12 ngày phép năm theo chính sách 2026.,yes,no,yes,3`
  *Nhận xét: Do quy tắc quarantine stale HR text "10 ngày phép phép năm" hoạt động ổn định ở cả 2 chế độ, kết quả truy vấn đều trả về chính sách 12 ngày phép năm chuẩn 2026.*

---

## 3. Freshness & monitor

- **Kết quả freshness_check:** `FAIL`
- **Chi tiết log:** `{"latest_exported_at": "2026-04-11T00:00:00", "age_hours": 1446.535, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}`
- **Giải thích SLA:** 
  - Nhóm quy định SLA là **24 giờ** kể từ thời điểm dữ liệu được export từ hệ thống nguồn (`latest_exported_at`). 
  - Dữ liệu hiện tại trong file export mẫu có timestamp là `2026-04-11`, dẫn đến việc bị quá hạn (~1446 giờ). Trong môi trường sản xuất thực tế, điều này sẽ kích hoạt alert kênh `#data-alerts-day10` để yêu cầu data provider đẩy lại bản export mới nhất.

---

## 4. Corruption inject (Sprint 3)

- **Mô tả kịch bản làm hỏng:**
  - Chạy pipeline với cờ `--no-refund-fix --skip-validate`.
  - Cờ này bỏ qua việc chuẩn hóa từ `14 ngày` về `7 ngày` đối với `policy_refund_v4` đồng thời cho phép tiếp tục embed vào ChromaDB dù expectation `refund_no_stale_14d_window` bị vi phạm.
- **Cách phát hiện:**
  - Lớp Validation suite lập tức phát hiện thông qua hàm `run_expectations` và đánh dấu `refund_no_stale_14d_window` là `FAIL (halt)`.
  - Chạy script đánh giá `eval_retrieval.py` phát hiện `hits_forbidden=yes` ở câu hỏi `q_refund_window`.

---

## 5. Hạn chế & việc chưa làm

- Chưa tích hợp kiểm tra Schema thô (Raw schema validation) để phòng ngừa việc file CSV bị đổi tên cột hoặc cấu trúc đầu vào thay đổi đột ngột.
- Freshness SLA check hiện tại đang so sánh trực tiếp với giờ hệ thống nội bộ, cần hỗ trợ việc xử lý múi giờ UTC/GMT động để tránh báo động giả khi chạy ở các khu vực địa lý khác nhau.
