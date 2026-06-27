# Theo Dõi Vấn Đề Kiến Trúc

Tài liệu này dùng để theo dõi các vấn đề kiến trúc và thiết kế trong review agent
để có thể sửa dần theo từng giai đoạn.

## 1. Rò rỉ abstraction giữa provider interface và Azure DevOps implementation

### Vấn đề

Luồng orchestration của review hiện chưa hoàn toàn provider-agnostic. Agent vẫn
phân nhánh theo hành vi riêng của Azure DevOps ngay trong review runner chính và
gọi trực tiếp vào các method đặc thù của implementation.

Ví dụ:

- `agent/app/services/review_runner.py` kiểm tra `AzureDevOpsProvider`
- `review_runner.py` gọi `providers.git._git_auth_args()`
- `review_runner.py` gọi `providers.git.build_diff_from_workspace()`

Điều này cho thấy lớp orchestration đang biết quá nhiều chi tiết của một provider
cụ thể.

### Tại sao vấn đề này quan trọng

- Làm yếu ranh giới abstraction của `GitProvider`
- Làm `review_runner` khó mở rộng hơn khi thêm provider mới
- Khuyến khích tăng thêm logic `if/else` đặc thù provider trong core flow
- Tăng nguy cơ regression khi hệ thống hỗ trợ nhiều provider hơn

### Hướng xử lý mong muốn

- Đưa hành vi đặc thù provider về sau protocol hoặc interface dùng chung
- Tránh để orchestration gọi trực tiếp vào private method hoặc method chỉ tồn tại ở implementation cụ thể
- Giữ `review_runner` tập trung vào workflow, không gắn với đặc điểm của từng provider

## 2. Phần parse output của OpenCode đang phụ thuộc nhiều vào heuristic

### Vấn đề

Tích hợp OpenCode hiện khá bền bỉ trước output không ổn định, nhưng đang phụ thuộc
nhiều vào heuristic khi parse NDJSON events, text payload lồng nhau, và JSON trong
code fence để lấy findings.

Hành vi hiện tại gồm:

- quét nhiều dạng event khác nhau để tìm findings
- cố gắng parse JSON nằm trong các text field
- fallback sang parse JSON trong fenced code block
- trả về danh sách findings rỗng nếu không tìm được dữ liệu parse hợp lệ

Cách làm này thực dụng cho output của model chưa ổn định, nhưng nó làm mờ ranh giới
giữa các trường hợp:

- model thực sự không tìm thấy vấn đề
- model trả về output sai định dạng
- event format thay đổi theo cách parser hiện tại không hiểu

### Tại sao vấn đề này quan trọng

- Có thể tạo ra kết quả false "không có findings"
- Làm khó chẩn đoán nguyên nhân khi có lỗi
- Làm hành vi phụ thuộc vào những output shape lỏng lẻo
- Tạo rủi ro khi nâng cấp OpenCode hoặc khi output của model thay đổi

### Hướng xử lý mong muốn

- Làm chặt hơn output contract giữa agent và OpenCode
- Phát hiện và hiển thị parse failure rõ ràng thay vì âm thầm trả về danh sách rỗng
- Bổ sung validation chặt hơn cho structured result cuối cùng
- Cân nhắc coi malformed final output là review failure hoặc degraded result

## 3. MCP tool surface chưa khớp hoàn toàn với hành vi mong muốn của agent

### Vấn đề

MCP server hiện expose cả các tool dùng để đăng remote comment, trong khi prompt của
review agent lại chỉ đạo model không được dùng các tool này.

Ví dụ:

- MCP server expose `coreview-git_post_review_comment`
- MCP server expose `coreview-git_post_inline_comments`
- OpenCode prompt nói review agent không được post remote comment thông qua MCP

Điều này có nghĩa là ranh giới hành vi hiện đang dựa vào việc model tuân thủ prompt,
thay vì được ràng buộc bởi capability thật sự.

### Tại sao vấn đề này quan trọng

- Model vẫn có thể thử thực hiện hành động mà nó chỉ được "nhắc" là không nên làm
- Giới hạn dựa trên prompt yếu hơn giới hạn dựa trên tool-level restriction
- Tool surface hiện rộng hơn vai trò thực tế của review agent
- Tăng rủi ro về safety và control cho các review run tự động

### Hướng xử lý mong muốn

- Chỉ expose các MCP tool thực sự cần cho review agent
- Bỏ các tool đăng remote comment khỏi OpenCode review path nếu lớp orchestration Python mới là nơi phụ trách việc publish comment
- Đồng bộ tool availability với đúng trách nhiệm thực tế trong kiến trúc
