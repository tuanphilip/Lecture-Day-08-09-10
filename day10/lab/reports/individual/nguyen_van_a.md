# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Nguyễn Văn A  
**Vai trò:** Ingestion / Cleaning Owner  
**Ngày nộp:** 2026-06-10  
**Độ dài yêu cầu:** **400–650 từ**

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**
Tôi phụ trách Ingestion Layer và Transform Layer:
- Sửa đổi [cleaning_rules.py](file:///d:/VinAI-Lab/Lecture-Day-08-09-10/day10/lab/transform/cleaning_rules.py) để cho phép nhận diện và xử lý tài liệu phân quyền quan trọng `access_control_sop` trong `ALLOWED_DOC_IDS`.
- Phát triển và cấu trúc 3 quy tắc làm sạch dữ liệu mới: `rule_quarantine_stale_hr_leave_content` để loại bỏ quy định nghỉ phép 10 ngày cũ, `rule_clean_noise_prefixes` để loại bỏ nhiễu prefix ("!!!" và "Nội dung không rõ ràng"), và `rule_clean_word_repetitions` để gỡ bỏ stutter lặp từ ("làm việc làm việc").

**Kết nối với thành viên khác:**
Tôi làm việc chặt chẽ với Trần Văn B (Quality Owner) để đảm bảo các rule làm sạch khớp hoàn toàn với các kiểm định trong expectations, và phối hợp với Phạm Văn C (Embed Owner) để định hình cấu trúc `chunk_id` idempotent ổn định.

**Bằng chứng (commit / comment trong code):**
Trong file `cleaning_rules.py`, tôi đã triển khai logic lọc trùng, gỡ nhiễu và xử lý stale HR ngay trước khi kiểm duyệt dữ liệu nhằm tối ưu lượng record được đưa vào sạch sẽ nhất.

---

## 2. Một quyết định kỹ thuật (100–150 từ)

Tôi quyết định thực hiện việc **làm sạch và chuẩn hóa văn bản trước khi thực hiện loại bỏ trùng lặp (deduplication)**. 

**Lý do:**
Nếu chúng ta loại bỏ trùng lặp trước, các bản ghi thô chỉ khác nhau bởi ký tự nhiễu (ví dụ: một bản ghi bắt đầu bằng `"!!!"` và một bản ghi không) sẽ được coi là hai bản ghi khác nhau và cùng đi tiếp. Sau đó, khi ta chạy rule làm sạch prefix, cả hai sẽ bị loại bỏ nhiễu và trở thành hai bản ghi hoàn toàn giống hệt nhau, lọt vào ChromaDB dưới dạng trùng lặp nội dung. Bằng cách làm sạch văn bản trước rồi mới so khớp dấu vân tay `seen_text`, tôi đảm bảo ChromaDB chỉ nhận được đúng 1 bản ghi duy nhất, giảm nhiễu 100% cho Retrieval.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

**Triệu chứng:**
Khi chạy đánh giá thử nghiệm với câu hỏi `q_refund_window`, chỉ số `hits_forbidden` trả về `yes` và kết quả truy vấn chứa văn bản hoàn tiền cũ 14 ngày làm việc.

**Phát hiện:**
Expectation `refund_no_stale_14d_window` báo `FAIL (halt)`. Kiểm tra log manifest cho thấy bản ghi từ `policy_refund_v4` chứa cả hai dòng: một dòng quy định cũ 14 ngày (với ngày hiệu lực cũ) và một dòng quy định mới 7 ngày.

**Cách sửa:**
Tôi đã thêm rule tìm kiếm và thay thế (replace) chuỗi `"14 ngày làm việc"` thành `"7 ngày làm việc"` trong `clean_rows` của `cleaning_rules.py` cho `policy_refund_v4` khi `apply_refund_window_fix` được bật. Sau khi sửa, chạy lại pipeline đã dọn sạch hoàn toàn dấu vết chính sách cũ, chỉ số `hits_forbidden` trở về `no`.

---

## 4. Bằng chứng trước / sau (80–120 từ)

- **Run ID:** `2026-06-10T06-31Z` (Clean) vs `inject-bad` (Stale)
- **Trước (inject-bad):**
  `q_refund_window,...,policy_refund_v4,Yêu cầu hoàn tiền được chấp nhận trong vòng 14 ngày làm việc kể từ xác nhận đơn.,yes,yes,yes,3`
- **Sau (clean run):**
  `q_refund_window,...,policy_refund_v4,Yêu cầu được gửi trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng. [cleaned: stale_refund_window],yes,no,yes,3`

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ xây dựng một bộ phân tích Schema tự động (ví dụ sử dụng Great Expectations Spark/Pandas dataframe profiling) để cảnh báo khi tệp CSV thô bị tráo đổi vị trí cột hoặc thay đổi kiểu dữ liệu trước khi chạy ETL.
