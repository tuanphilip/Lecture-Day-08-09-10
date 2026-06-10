# Routing Decisions Log — Lab Day 09

**Nhóm:** VinAI Lab Team  
**Ngày:** 2026-06-10

---

## Routing Decision #1

**Task đầu vào:**
> SLA xử lý ticket P1 là bao lâu?

**Worker được chọn:** `retrieval_worker`  
**Route reason (từ trace):** `default route`  
**MCP tools được gọi:** Không có  
**Workers called sequence:** `retrieval_worker` → `synthesis_worker`

**Kết quả thực tế:**
- final_answer (ngắn): Ticket P1 có SLA phản hồi ban đầu 15 phút và thời gian xử lý (resolution) là 4 giờ.
- confidence: 0.55
- Correct routing? Yes

**Nhận xét:**
Quy trình định tuyến hoàn toàn chính xác. Đây là câu hỏi tra cứu thông tin trực tiếp về SLA của ticket kỹ thuật, không chứa từ khóa đặc biệt về chính sách (policy/refund) hay quyền hạn (access) phức tạp, do đó supervisor chọn route mặc định là `retrieval_worker` để truy vấn dense search trực tiếp trên ChromaDB.

---

## Routing Decision #2

**Task đầu vào:**
> Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `task contains policy/access keyword`  
**MCP tools được gọi:** `search_kb`  
**Workers called sequence:** `policy_tool_worker` → `synthesis_worker`

**Kết quả thực tế:**
- final_answer (ngắn): Khách hàng có thể yêu cầu hoàn tiền trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng.
- confidence: 0.66
- Correct routing? Yes

**Nhận xét:**
Vì câu hỏi chứa từ khóa "hoàn tiền" (refund), Supervisor đã định tuyến chính xác sang `policy_tool_worker` để phân tích ngoại lệ. Vì lúc bắt đầu worker chưa có chunks nào, nó đã gọi MCP tool `search_kb` để thực hiện tìm kiếm tài liệu từ xa, sau đó phân tích các điều kiện hoàn tiền và chuyển cho Synthesis Worker kết luận. Luồng chạy sạch sẽ, không gọi thừa worker.

---

## Routing Decision #3

**Task đầu vào:**
> ERR-403-AUTH là lỗi gì và cách xử lý?

**Worker được chọn:** `human_review`  
**Route reason (từ trace):** `unknown error code + risk_high → human review`  
**MCP tools được gọi:** Không có (ở bước Human Review), sau đó gọi `search_kb` ở bước Retrieval  
**Workers called sequence:** `human_review` → `retrieval_worker` → `synthesis_worker`

**Kết quả thực tế:**
- final_answer (ngắn): Không tìm thấy thông tin về mã lỗi ERR-403-AUTH trong tài liệu nội bộ hiện có. Hãy liên hệ IT Helpdesk để được hỗ trợ trực tiếp.
- confidence: 0.41
- Correct routing? Yes

**Nhận xét:**
Supervisor phát hiện từ khóa rủi ro cao "err-" đại diện cho mã lỗi không xác định, kết hợp với chính sách bảo mật nên đã gắn cờ `risk_high=True` và route sang `human_review` (HITL). Trong lab mode, node này tự động approve và chuyển sang `retrieval_worker` để tra cứu tài liệu trước khi Synthesis Worker đưa ra câu trả lời phủ định (abstain) do không có thông tin trong DB.

---

## Routing Decision #4 (tuỳ chọn — bonus)

**Task đầu vào:**
> Ticket P1 lúc 2am. Cần cấp Level 2 access tạm thời cho contractor để thực hiện emergency fix. Đồng thời cần notify stakeholders theo SLA. Nêu đủ cả hai quy trình.

**Worker được chọn:** `policy_tool_worker`  
**Route reason:** `task contains policy/access keyword | risk_high flagged`  
**Workers called sequence:** `policy_tool_worker` → `synthesis_worker` (có gọi MCP `search_kb` và `get_ticket_info` trong node policy)

**Nhận xét: Đây là trường hợp routing khó nhất trong lab. Tại sao?**
Câu hỏi này là một câu hỏi **multi-hop/cross-document** rất phức tạp. Nó kết hợp giữa:
1. Quy trình cấp quyền khẩn cấp Level 2 cho contractor (Access Control SOP).
2. Quy trình liên lạc, thông báo cho sự cố P1 và thời gian SLA (SLA P1).
Supervisor định tuyến sang `policy_tool_worker` vì chứa các từ khóa về cấp quyền ("access") và rủi ro ("2am", "P1"). Tại đây, worker đã gọi đồng thời 2 công cụ MCP là `search_kb` để lấy văn bản chính sách và `get_ticket_info` để lấy metadata của ticket P1 (Jira), giúp Synthesis tổng hợp đầy đủ và chính xác cả hai quy trình song song mà không bị sót thông tin.

---

## Tổng kết

### Routing Distribution

| Worker | Số câu được route | % tổng |
|--------|------------------|--------|
| retrieval_worker | 8 | 53% |
| policy_tool_worker | 7 | 46% |
| human_review (HITL ban đầu) | 1 | 6% |

*(Lưu ý: Có 1 câu đi qua human_review sau đó được chuyển hướng tiếp sang retrieval_worker)*

### Routing Accuracy

- Câu route đúng: 15 / 15
- Câu route sai: 0
- Câu trigger HITL: 1 (Câu hỏi mã lỗi ERR-403-AUTH)

### Lesson Learned về Routing

1. **Phân tách câu hỏi trước khi so khớp:** Việc trích xuất phần câu hỏi người dùng tách biệt khỏi context (retrieved chunks) là bài học xương máu để tránh việc supervisor hoặc synthesis worker bị nhầm lẫn bởi các từ khóa nằm trong tài liệu tham khảo (cross-contamination).
2. **Quy tắc kết hợp linh hoạt:** Việc kết hợp giữa keyword matching đơn giản cho các case tiêu chuẩn và cờ trạng thái (`risk_high`, `needs_tool`) cho phép đồ thị phản ứng nhanh nhạy với các điều kiện khẩn cấp mà không cần lạm dụng LLM call đắt đỏ ở tầng Supervisor.

### Route Reason Quality

Các `route_reason` hiện tại như `"task contains policy/access keyword | risk_high flagged"` hay `"unknown error code + risk_high → human review"` đã cung cấp rất đầy đủ ngữ cảnh tại sao Supervisor rẽ nhánh luồng đi đó. Điều này giúp cho việc kiểm tra trace log file JSON cực kỳ nhanh chóng và tường minh khi có lỗi xảy ra.
