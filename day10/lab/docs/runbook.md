# Runbook — Lab Day 10 (incident tối giản)

Tài liệu hướng dẫn xử lý sự cố chất lượng dữ liệu tri thức CS & IT Helpdesk.

---

## Symptom

- **Đối với User / Agent:** Khách hàng hoặc CS Agent nhận được câu trả lời sai lệch thông tin chính sách mới nhất. 
  * Ví dụ: Trả lời thời hạn hoàn tiền là “14 ngày làm việc” thay vì 7 ngày; hoặc trả lời phép năm của nhân viên mới là “10 ngày phép” thay vì 12 ngày.
- **Đối với Hệ thống RAG:** Vector search trả về các chunk bị lỗi (nhiễu prefix "!!!", lặp từ "làm việc làm việc") làm suy giảm độ chính xác của prompt generation.

---

## Detection

- **SLA Freshness Alert:** Hệ thống phát hiện độ trễ dữ liệu vượt quá ngưỡng 24 giờ. log ghi nhận `freshness_check=FAIL {"reason": "freshness_sla_exceeded"}`.
- **Pipeline HALT:** Lệnh chạy `python etl_pipeline.py run` kết thúc với **exit code 2** hoặc **3**.
- **Expectation Suite Failure:** Log hiển thị các lỗi nghiêm trọng (severity: halt) như:
  * `refund_no_stale_14d_window FAIL` (phát hiện cửa sổ hoàn tiền 14 ngày).
  * `hr_leave_no_stale_10d_annual FAIL` (phát hiện phép năm cũ 10 ngày).
  * `expected_doc_ids_present FAIL` (thiếu tài liệu quan trọng trong index).
- **Retrieval Evaluation Failure:** Chạy `python eval_retrieval.py` phát hiện chỉ số `hits_forbidden` bằng `true` hoặc `contains_expected` bằng `false`.

---

## Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Kiểm tra `artifacts/manifests/*.json` | Xác định `run_id`, `latest_exported_at` xem dữ liệu nạp vào có bị quá cũ (out-of-date) hay không. |
| 2 | Mở `artifacts/quarantine/*.csv` | Xem các cột dữ liệu bị cách ly và cột `reason` để biết nguyên nhân (ví dụ: `stale_hr_policy_text_10d`, `invalid_effective_date_format`). |
| 3 | Chạy `python eval_retrieval.py` | Kiểm tra xem các câu hỏi then chốt (như `q_refund_window`, `q_hr_sick_leave`) có trả về đúng tài liệu và chunk sạch hay không thông qua cột `contains_expected` và `hits_forbidden`. |

---

## Mitigation

1. **Khắc phục lỗi định dạng / stale:**
   * Sửa lỗi trực tiếp từ tệp xuất thô `data/raw/policy_export_dirty.csv` hoặc cập nhật rules trong [cleaning_rules.py](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/transform/cleaning_rules.py).
2. **Re-run & Repopulate:**
   * Chạy lại pipeline chuẩn: `python etl_pipeline.py run`.
   * Kiểm tra xem pipeline có kết thúc thành công với **exit 0** hay không.
3. **Index Rollback (nếu cần):**
   * Nếu dữ liệu mới bị lỗi nặng chưa thể khắc phục ngay, khôi phục lại snapshot trước đó bằng cách chạy lại pipeline với file raw backup sạch gần nhất để nạp đè và prune các chunk lỗi trên ChromaDB.

---

## Prevention

- **Đồng bộ hóa Contract:** Mọi tài liệu mới được xuất bản phải được đăng ký đầy đủ trong [data_contract.yaml](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/contracts/data_contract.yaml).
- **Halt Suite:** Giữ các quy tắc kiểm định quan trọng ở mức `severity: halt` để ngăn chặn tuyệt đối việc nạp dữ liệu bẩn vào production vector store.
- **Slack Alerting:** Tích hợp alert qua webhook Slack (`#data-alerts-day10`) khi phát hiện Freshness vượt quá 24h hoặc Expectation bị fail.
