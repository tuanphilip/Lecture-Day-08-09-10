# Data contract — Lab Day 10

> Được đồng bộ và mở rộng từ cấu hình khai báo trong [data_contract.yaml](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/contracts/data_contract.yaml) để xác định các ràng buộc chất lượng cho bộ dữ liệu tri thức CS & IT Helpdesk.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Tài liệu Canonical | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|-------------------|----------------|
| `policy_refund_v4` | [policy_refund_v4.txt](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/data/docs/policy_refund_v4.txt) | CSV Export | Chứa thông tin hoàn tiền cũ 14 ngày làm việc thay vì 7 ngày. | `refund_no_stale_14d_window` (HALT) |
| `sla_p1_2026` | [sla_p1_2026.txt](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/data/docs/sla_p1_2026.txt) | CSV Export | Thiếu tài liệu hoặc thông tin SLA bị thay đổi sai lệch. | `expected_doc_ids_present` (HALT) |
| `it_helpdesk_faq` | [it_helpdesk_faq.txt](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/data/docs/it_helpdesk_faq.txt) | CSV Export | Các câu hỏi trùng lặp hoặc văn bản rỗng, nhiễu prefix. | `no_duplicate_chunk_text` (WARN) |
| `hr_leave_policy` | [hr_leave_policy.txt](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/data/docs/hr_leave_policy.txt) | CSV Export | Xung đột phiên bản chính sách cũ 2025 (10 ngày phép) thay vì 2026 (12 ngày phép). | `hr_leave_no_stale_10d_annual` (HALT) |
| `access_control_sop` | [access_control_sop.txt](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/data/docs/access_control_sop.txt) | CSV Export | Không nạp tài liệu phân quyền truy cập quan trọng này. | `expected_doc_ids_present` (HALT) |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| `chunk_id` | string | Có | Khóa định danh duy nhất ổn định được tạo từ hàm sinh hash `_stable_chunk_id` giúp đảm bảo tính idempotent. |
| `doc_id` | string | Có | Mã logic định dạng tài liệu nguồn nằm trong allowlist khai báo ở [data_contract.yaml](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/contracts/data_contract.yaml). |
| `chunk_text` | string | Có | Nội dung văn bản tri thức đã được chuẩn hóa, loại bỏ khoảng trắng dư thừa, làm sạch prefix và lặp từ. |
| `effective_date` | date | Có | Ngày hiệu lực của tài liệu ở định dạng chuẩn hóa `YYYY-MM-DD`. |
| `exported_at` | datetime | Có | Thời điểm trích xuất dữ liệu từ hệ thống nguồn. |

---

## 3. Quy tắc quarantine vs drop

- **Không drop dữ liệu âm thầm:** Tất cả các record không vượt qua kiểm tra định danh hoặc định dạng ngày sẽ được cách ly vào thư mục `artifacts/quarantine/quarantine_<run_id>.csv` thay vì bị xóa bỏ không dấu vết.
- **Merge & Approve:**
  - Ingestion / Quality Owner sẽ định kỳ rà soát các record bị cách ly.
  - Sau khi sửa chữa lỗi dữ liệu từ hệ thống nguồn, dữ liệu sẽ được kích hoạt nạp lại (replay) qua ETL pipeline. Dữ liệu sửa đổi cần có chữ ký phê duyệt (chạy lại pipeline thành công exit 0) trước khi được merge vào vector database chính thức.

---

## 4. Phiên bản & canonical

- **Refund Policy:**
  - **Source of truth:** [policy_refund_v4.txt](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/data/docs/policy_refund_v4.txt).
  - **Version rule:** Chỉ chấp nhận hoàn tiền trong vòng 7 ngày làm việc. Bất kỳ chunk nào chứa thông tin 14 ngày làm việc đều là dữ liệu cũ và phải được tự động làm sạch sang 7 ngày hoặc quarantine.
- **HR Leave Policy:**
  - **Source of truth:** [hr_leave_policy.txt](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/data/docs/hr_leave_policy.txt).
  - **Version rule:** Kể từ 2026-01-01 trở đi, số ngày nghỉ phép tối thiểu là 12 ngày (dưới 3 năm). Các văn bản có hiệu lực trước năm 2026 chứa quy định cũ "10 ngày phép phép năm" sẽ bị quarantine.
