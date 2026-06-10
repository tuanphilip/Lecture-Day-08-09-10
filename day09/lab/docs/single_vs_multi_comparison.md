# Single Agent vs Multi-Agent Comparison — Lab Day 09

**Nhóm:** VinAI Lab Team  
**Ngày:** 2026-06-10

---

## 1. Metrics Comparison

| Metric | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Delta | Ghi chú |
|--------|----------------------|---------------------|-------|---------|
| Avg confidence | 0.85 (Est) | 0.617 | -0.233 | Tự đánh giá nghiêm khắc hơn ở Day 09 |
| Avg latency (ms) | ~6,500 ms | 2,741 ms | -3,759 ms | Day 09 tối ưu nhờ caching model |
| Abstain rate (%) | 10% (1/10) | 6.6% (1/15) | -3.4% | Cả hai đều từ chối trả lời câu ERR-403 |
| Multi-hop accuracy | N/A | 100% | N/A | Day 08 không test các case multi-hop phức tạp |
| Routing visibility | ✗ Không có | ✓ Có route_reason | N/A | Hiển thị rõ vết rẽ nhánh |
| Debug time (estimate) | 15 phút | 2 phút | -13 phút | Xem trace log tìm được ngay node lỗi |

---

## 2. Phân tích theo loại câu hỏi

### 2.1 Câu hỏi đơn giản (single-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | 100% | 100% |
| Latency | ~6,500 ms | ~40 ms (warm queries) |
| Observation | Chạy tuần tự và chậm do gọi LLM trực tiếp | Phản hồi siêu tốc nhờ cache embedding và logic tối ưu |

**Kết luận:** Multi-agent cải thiện vượt bậc về tốc độ phản hồi đối với câu hỏi đơn giản nhờ cơ chế caching và định tuyến nhanh (route thẳng sang retrieval và synthesis).

---

## 2.2 Câu hỏi multi-hop (cross-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | N/A | 100% |
| Routing visible? | ✗ | ✓ |
| Observation | Dễ bị hallucinate hoặc thiếu sót context khi gom dữ liệu | Supervisor định tuyến sang policy_tool, gọi thêm MCP tool để gom đủ context |

**Kết luận:** Multi-agent vượt trội ở các câu hỏi phối hợp thông tin từ nhiều nguồn khác nhau (như ticket + SLA policy), đảm bảo tính toàn vẹn của context trước khi Synthesis tạo câu trả lời.

---

## 2.3 Câu hỏi cần abstain

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Abstain rate | 10% | 6.6% |
| Hallucination cases | 0 | 0 |
| Observation | Trả về thông báo từ chối khi không tìm thấy chunk | Route vào human_review và trả về câu trả lời an toàn |

**Kết luận:** Cả hai hệ thống đều giữ được độ an toàn cao (không chém gió khi thiếu thông tin). Multi-agent bổ sung thêm tầng Human Review để đảm bảo các lỗi hệ thống nghiêm trọng được thông báo cho con người.

---

## 3. Debuggability Analysis

### Day 08 — Debug workflow
```
Khi answer sai → phải đọc toàn bộ RAG pipeline code → tìm lỗi ở indexing/retrieval/generation
Không có trace → không biết lỗi do retrieved chunks sai hay do prompt generation.
Thời gian ước tính: 15 phút
```

### Day 09 — Debug workflow
```
Khi answer sai → đọc trace JSON → xem supervisor_route + route_reason
  → Nếu route sai → sửa supervisor routing logic trong graph.py
  → Nếu retrieval sai → test retrieval_worker độc lập
  → Nếu synthesis sai → test synthesis_worker độc lập
Thời gian ước tính: 2 phút
```

**Câu cụ thể nhóm đã debug:**
Lỗi trùng từ khóa và cross-contamination: Khi Synthesis Worker chạy thử nghiệm, từ khóa "thử việc" trong context của access-control-sop đã khiến mock logic nhận diện sai câu hỏi `q15` (sự cố P1 lúc 2am) thành câu hỏi thử việc từ xa. Bằng việc đọc trace log JSON và kiểm tra vết chạy của `synthesis_worker` với input/output cụ thể, nhóm đã phát hiện ra lỗi so khớp từ khóa trên toàn bộ prompt (bao gồm cả context) và nhanh chóng sửa lại bằng cách trích xuất chỉ riêng câu hỏi của người dùng để so khớp.

---

## 4. Extensibility Analysis

| Scenario | Day 08 | Day 09 |
|---------|--------|--------|
| Thêm 1 tool/API mới | Phải sửa toàn bộ prompt chính của agent | Thêm MCP tool schema + route rule trong server |
| Thêm 1 domain mới | Phải viết lại prompt lớn | Thêm 1 worker node độc lập vào StateGraph |
| Thay đổi retrieval strategy | Sửa trực tiếp trong pipeline lớn | Sửa hàm retrieve trong retrieval_worker |
| A/B test một phần | Khó — phải clone toàn bộ pipeline | Dễ — chỉ cần swap worker node |

**Nhận xét:**
Hệ thống Multi-Agent của Day 09 cực kỳ dễ mở rộng. Ví dụ, việc tích hợp thêm tool `get_ticket_info` từ Jira chỉ mất vài dòng code khai báo schema trong `mcp_server.py` và gọi nó từ `policy_tool.py`, hoàn toàn độc lập với phần retrieval hay synthesis.

---

## 5. Cost & Latency Trade-off

| Scenario | Day 08 calls | Day 09 calls |
|---------|-------------|-------------|
| Simple query | 1 LLM call | 1 LLM call (Supervisor dùng keyword, Synthesis dùng LLM) |
| Complex query | 1 LLM call | 1-2 LLM calls (Supervisor + Synthesis) |
| MCP tool call | N/A | Gọi API nội bộ qua Dispatch (0 LLM call nếu dùng mock/rule-based) |

**Nhận xét về cost-benefit:**
Mặc dù Multi-Agent phân rã thành nhiều bước, trong lab này chúng ta đã tối ưu hóa chi phí bằng cách sử dụng các bộ lọc keyword và rule-based cho Supervisor và Policy check, chỉ gọi LLM ở Synthesis Worker. Điều này giúp cân bằng hoàn hảo giữa chi phí và tính chính xác, giữ latency ở mức tối thiểu.

---

## 6. Kết luận

**Multi-agent tốt hơn single agent ở điểm nào?**
1. **Khả năng quan sát (Observability):** Trace log JSON của từng run giúp hiểu rõ luồng suy nghĩ và ra quyết định rẽ nhánh của hệ thống.
2. **Khả năng bảo trì và mở rộng:** Dễ dàng phát triển, kiểm thử và thay thế các worker độc lập mà không lo ảnh hưởng đến các phần khác.

**Multi-agent kém hơn hoặc không khác biệt ở điểm nào?**
1. **Độ phức tạp ban đầu:** Cần thiết lập đồ thị (graph state), định nghĩa các worker contracts và giao thức kết nối (MCP) phức tạp hơn nhiều so với viết một script RAG monolith.

**Khi nào KHÔNG nên dùng multi-agent?**
Không nên dùng Multi-Agent cho các tác vụ đơn giản, một chiều (như dịch thuật, tóm tắt văn bản đơn thuần, hoặc tra cứu FAQ cơ bản) vì nó sẽ gây overhead về mặt latency và độ phức tạp mã nguồn không cần thiết.

**Nếu tiếp tục phát triển hệ thống này, nhóm sẽ thêm gì?**
1. Nâng cấp Supervisor lên một LLM classifier nhỏ (như Llama-3-8B hoặc Gemini-flash) để phân loại câu hỏi thông minh hơn.
2. Tích hợp thêm các MCP tool kết nối thật với Jira API và Slack API để tự động hóa hoàn toàn quy trình xử lý sự cố IT Helpdesk.
