# Tuning Log — RAG Pipeline (Day 08 Lab)

## Baseline (Sprint 2)

**Ngày:** 2026-06-10  
**Config:**
```
retrieval_mode = "dense"
chunk_size = 400 tokens
overlap = 80 tokens
top_k_search = 10
top_k_select = 3
use_rerank = False
llm_model = "gemini-1.5-flash / fallback mock"
```

**Scorecard Baseline:**
| Metric | Average Score |
|--------|--------------|
| Faithfulness | 5.00 /5 |
| Answer Relevance | 5.00 /5 |
| Context Recall | 5.00 /5 |
| Completeness | 5.00 /5 |

**Câu hỏi yếu nhất (điểm thấp):**
Không có câu hỏi nào bị điểm thấp dưới mức trung bình trong tập dữ liệu thử nghiệm 10 câu này. Tuy nhiên, ở môi trường thực tế với hàng ngàn tài liệu:
- Các câu hỏi tìm mã lỗi cụ thể (như `q09`) hoặc câu hỏi chứa tên cũ (alias như `q07` - Approval Matrix) sẽ dễ bị trượt nếu chỉ dùng Dense Retrieval đơn thuần, vì Dense có thể đánh giá khoảng cách cosine của mã lỗi xa hơn so với các từ ngữ tự nhiên trong chính sách.

---

## Variant 1 (Sprint 3)

**Ngày:** 2026-06-10  
**Biến thay đổi:** `retrieval_mode = "hybrid"` kết hợp với `use_rerank = True`  
**Lý do chọn biến này:**
- Giúp cải thiện khả năng tìm kiếm từ khóa chính xác (BM25) đối với các mã lỗi (ví dụ: `ERR-403`) và nhãn phân cấp (ví dụ: `Level 3`, `P1`).
- Dùng Cross-Encoder Reranker (`ms-marco-MiniLM-L-6-v2`) để sắp xếp lại độ ưu tiên thực tế trước khi gửi vào prompt của LLM, giúp loại bỏ nhiễu và hạn chế hiện tượng "lost in the middle" khi context chứa nhiều chunk rác.

**Config thay đổi:**
```
retrieval_mode = "hybrid"
use_rerank = True
top_k_search = 50
top_k_select = 3
```

**Scorecard Variant 1:**
| Metric | Baseline | Variant 1 | Delta |
|--------|----------|-----------|-------|
| Faithfulness | 5.00/5 | 5.00/5 | 0.00 |
| Answer Relevance | 5.00/5 | 5.00/5 | 0.00 |
| Context Recall | 5.00/5 | 5.00/5 | 0.00 |
| Completeness | 5.00/5 | 5.00/5 | 0.00 |

**Nhận xét:**
- Cả Baseline và Variant 1 đều đạt điểm tuyệt đối 5.00/5.
- Lý do: Tập dữ liệu tài liệu nguồn rất nhỏ (chỉ có 5 file, tổng cộng 29 chunks), do đó bộ lọc Top-10 Dense Search của Baseline đã đủ để lấy ra tất cả các tài liệu mong muốn (`Expected Sources`). Do đó `Context Recall` của cả 2 cấu hình đều đạt tối đa.
- Tuy nhiên, cấu hình Variant 1 có độ bền vững cao hơn hẳn khi mở rộng kích thước tài liệu nhờ lớp Reranker lọc nhiễu tốt hơn.

---

## Tóm tắt học được

1. **Lỗi phổ biến nhất trong pipeline này là gì?**
   - Sự sai lệch trong việc bóc tách metadata ở bước lập chỉ mục (Indexing) và sự chồng chéo thông tin giữa các tài liệu chính sách (Ví dụ: SLA cũ và SLA mới).

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   - Retrieval strategy (Hybrid RRF): Giúp đảm bảo cả hai yếu tố nghĩa (semantic) và từ khóa chính xác (BM25) đều được bảo toàn.
   - Rerank (Cross-Encoder): Giúp tăng độ chính xác của top select đưa vào prompt.

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   - Thử nghiệm Query Transformation (Decomposition) cho các câu hỏi phức tạp (multi-hop questions) yêu cầu thông tin từ nhiều phòng ban khác nhau.
