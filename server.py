import sys
from mcp.server.fastmcp import FastMCP

# 1. Khởi tạo MCP Server tên là "demo-service"
mcp = FastMCP("demo-service")

# 2. Định nghĩa một Tool đơn giản tính tổng 2 số
@mcp.tool()
async def add_numbers(a: float, b: float) -> float:
    """Cộng hai số a và b lại với nhau."""
    # Lưu ý: Với STDIO Server, dùng sys.stderr để log nếu cần (KHÔNG dùng print chuẩn)
    print(f"[Server Log] Đang tính tổng: {a} + {b}", file=sys.stderr)
    return a + b

# 3. Định nghĩa một Tool mô phỏng tra cứu thông tin
@mcp.tool()
async def get_system_status() -> str:
    """Lấy trạng thái hệ thống hiện tại."""
    return "Hệ thống mcp-a2a-demo đang hoạt động bình thường (Status: OK)."

# Tùy chỉnh 1: Thêm Resource cho AI đọc file/dữ liệu
@mcp.resource("config://app-settings")
async def get_config() -> str:
    """Cung cấp cấu hình mặc định của hệ thống."""
    return '{"env": "development", "max_connections": 10}'

# Tùy chỉnh 2: Thêm Prompt mẫu đóng gói sẵn
@mcp.prompt()
def system_audit_prompt() -> str:
    """Tạo câu lệnh mẫu để kiểm tra toàn bộ hệ thống."""
    return "Hãy gọi tool get_system_status và phân tích xem hệ thống có sẵn sàng cho vận hành không."

if __name__ == "__main__":
    # Khởi chạy server qua giao thức STDIO
    mcp.run(transport="stdio")
    # mcp.run(transport="sse") # HTTP Server với Server-Sent 