# W6 Side Challenge Reflections - Group 13 (KicksShoes Project)

### Prompt 3: clean --apply blast radius — If you accidentally ran clean --tag Environment=dev --apply in an account shared with another team, what would you have wanted in place to limit damage?

**Answer:**
Lệnh `clean --apply` là lệnh nguy hiểm nhất trong bộ công cụ CLI này vì nó có khả năng càn quét diện rộng (blast radius lớn). Nếu vô tình chạy lệnh này trên một AWS account dùng chung với đội ngũ khác, Group 13 đề xuất các giải pháp phòng vệ đa tầng (Defense in Depth) sau để cô lập và hạn chế tối đa thiệt hại:

1. **Thiết lập IAM Policy dựa trên Resource Tags (Attribute-Based Access Control - ABAC):**
   - Không cấp quyền xóa (`ec2:TerminateInstances`, `ec2:DeleteVolume`) một cách đại trà. IAM Role/User chạy ứng dụng `costctl` của nhóm nào thì chỉ được phép can thiệp vào tài nguyên có chứa tag của nhóm đó (ví dụ sử dụng điều kiện `Condition` trong policy yêu cầu `aws:ResourceTag/Group == "13"`). Điều này ngăn chặn tuyệt đối việc xóa nhầm tài nguyên của đội khác dù trùng tag `Environment=dev`.

2. **Kích hoạt tính năng bảo vệ (Termination Protection):**
   - Đối với các máy chủ EC2 hoặc các tài nguyên cốt lõi dùng chung, bắt buộc phải bật thuộc tính bảo vệ để API không thể xóa trực tiếp trừ khi có sự can thiệp thủ công bằng tay trên AWS Console.

3. **Cơ chế an toàn hai tầng (Two-Factor Confirmation) trên CLI:**
   - Dù người dùng có truyền flag cứng `--apply`, CLI nên bổ sung một hàm đếm tổng số lượng tài nguyên mục tiêu. Nếu số lượng vượt quá một ngưỡng an toàn (ví dụ: > 5 tài nguyên), hệ thống bắt buộc phải hiển thị cảnh báo đỏ và yêu cầu người dùng gõ chính xác chuỗi từ khóa ngẫu nhiên hoặc tên nhãn gán để tiếp tục, thay vì tự động xóa ngay.

---

### Prompt 4: AI assistance — What fraction of code came from AI tools (Claude / Cursor / Copilot) unmodified? Which parts did you actively modify, why?

**Answer:**
Trong quá trình thực hiện thử thách cá nhân này, tỷ lệ phân bổ mã nguồn và sự can thiệp của Group 13 diễn ra như sau:

1. **Tỷ lệ code giữ nguyên từ AI (~70%):**
   - Các đoạn mã khuôn mẫu (Boilerplate code) liên quan đến việc khởi tạo `boto3.client()`, cấu trúc vòng lặp duyệt qua các dictionary lồng nhau của AWS API response (như `Reservations` -> `Instances` -> `Tags`), và cú pháp tính ngày tháng với `timedelta` được sinh ra chính xác từ AI và giữ nguyên để tăng tốc độ phát triển.

2. **Các phần chủ động chỉnh sửa và tối ưu hóa (~30%):**
   - **Xử lý bất đồng bộ thuộc tính Namespace (Lỗi CLI):** AI ban đầu sinh mã cho hàm `run(args)` của lệnh `list` sử dụng thuộc tính `args.resource`, tuy nhiên file cấu hình hệ thống gốc lại định nghĩa biến này là `args.type` ở một số khu vực. Nhóm đã chủ động sửa đổi bằng cách sử dụng hàm kiểm tra động `hasattr(args, "resource")` để giúp CLI chạy tương thích mượt mà trên mọi môi trường mà không bị crash lỗi `AttributeError`.
   - **Tối ưu hóa logic lọc trạng thái Volume:** Trong lệnh `clean`, nhóm đã sửa lại điều kiện lọc để cam kết CHỈ thu thập các EBS Volume ở trạng thái `available` (ổ đĩa trống). AI ban đầu chỉ bỏ qua trạng thái `deleting`, việc lọc chặt chẽ này giúp công cụ tránh được việc cố xóa các volume đang bận (`in-use`), giảm thiểu số lượng exception lỗi không cần thiết từ AWS ClientError.
   - **Tinh chỉnh định dạng chuỗi (String Matching):** Sửa đổi các câu lệnh `print()` để khớp chính xác từng ký tự với bộ kiểm thử nghiêm ngặt của `pytest` (ví dụ chuyển từ `"No resources found"` sang `"Nothing to clean"`).

3. **Bài học hạ tầng thực tế (ECS + Fargate):**
   - Vì dự án **KicksShoes** của nhóm sử dụng kiến trúc Serverless Container (ECS Fargate), nhóm nhận ra các lệnh kiểm tra EC2 truyền thống trả về `0 found` và `$0.00` chi phí. Đây là cơ sở quan trọng để nhóm nâng cao tư duy thiết kế, không lạm dụng máy chủ ảo và kiểm soát tốt kiến trúc FinOps của hệ thống.