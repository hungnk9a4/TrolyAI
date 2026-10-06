import flet as ft
from google import genai
from google.genai import types
import os

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# 1. TẢI TÀI LIỆU LÊN GEMINI TỪ THƯ MỤC LƯU TRỮ
doc_dir = "tai_lieu"
uploaded_pdf_parts = []

if os.path.exists(doc_dir):
    for filename in os.listdir(doc_dir):
        if filename.lower().endswith(".pdf"):
            file_path = os.path.join(doc_dir, filename)
            try:
                g_file = client.files.upload(file=file_path)
                uploaded_pdf_parts.append(g_file)
            except Exception as e:
                print(f"Lỗi tải file {filename}: {e}")

# 2. HƯỚNG DẪN ĐỊNH HƯỚNG SUY LUẬN CHO AI
system_instruction = """
Bạn là một Chuyên gia chẩn đoán kỹ thuật ô tô cấp cao.
Nhiệm vụ của bạn là hướng dẫn sinh viên đo kiểm, chẩn đoán lỗi hệ thống điều hòa (A/C) dựa trên bộ Cẩm nang sửa chữa được cung cấp.

Quy tắc bắt buộc:
1. LUÔN LUÔN giao tiếp từng bước. Không đưa ra toàn bộ quy trình đo kiểm trong 1 tin nhắn.
2. Nếu sinh viên hỏi về một dòng xe cụ thể, hãy TÌM TÀI LIỆU của dòng xe đó trong bộ nhớ để trả lời. 
3. Nếu dòng xe sinh viên hỏi KHÔNG CÓ trong tài liệu, hãy báo rõ là "Thư viện hiện tại chưa có tài liệu của xe này". Tuyệt đối không bịa thông số điện áp.
4. Trích dẫn số liệu điện áp, màu dây, vị trí chân cắm CHÍNH XÁC Y HỆT từ Cẩm nang sửa chữa.
5. QUAN TRỌNG VỀ HÌNH ẢNH: Khi sinh viên hỏi sơ đồ mạch điện hoặc vị trí hộp điều khiển, BẮT BUỘC chèn đoạn mã Markdown chứa link ảnh (nếu bạn đã được cấu hình link trước đó).
"""

config = types.GenerateContentConfig(
    system_instruction=system_instruction,
    temperature=0.2 
)

def main(page: ft.Page):
    page.title = "Trợ Lý AI Chẩn Đoán Ô Tô"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 450
    page.window_height = 750
    page.padding = 20

    # Khởi tạo phiên chat trống (Tránh lỗi Validation Error)
    chat_session = client.chats.create(
        model="gemini-3.8-flash",
        config=config
    )

    chat_view = ft.ListView(expand=True, spacing=10, auto_scroll=True)

    def add_message(sender: str, text: str):
        is_user = sender == "Bạn"
        msg_margin = ft.margin.Margin(left=50, top=0, right=0, bottom=0) if is_user else ft.margin.Margin(left=0, top=0, right=50, bottom=0)
        
        content_control = ft.Text(text, color=ft.Colors.WHITE, size=15) if is_user else ft.Markdown(text, selectable=True, extension_set=ft.MarkdownExtensionSet.GITHUB_WEB)
        
        msg_container = ft.Container(
            content=content_control,
            bgcolor=ft.Colors.BLUE if is_user else ft.Colors.BLUE_GREY_50,
            padding=15,
            border_radius=10,
            margin=msg_margin
        )
        chat_view.controls.append(msg_container)
        page.update()

    def on_send_click(e):
        if not txt_input.value:
            return
        
        user_text = txt_input.value
        add_message("Bạn", user_text)
        txt_input.value = "" 
        
        loading_text = ft.Text("AI đang tra cứu Cẩm nang sửa chữa...", italic=True, color=ft.Colors.GREY)
        chat_view.controls.append(loading_text)
        page.update()

        try:
            response_stream = chat_session.send_message_stream(user_text)
            chat_view.controls.remove(loading_text)
            
            ai_text_control = ft.Markdown("", selectable=True, extension_set=ft.MarkdownExtensionSet.GITHUB_WEB)
            ai_msg_container = ft.Container(
                content=ai_text_control,
                bgcolor=ft.Colors.BLUE_GREY_50,
                padding=15,
                border_radius=10,
                margin=ft.margin.Margin(left=0, top=0, right=50, bottom=0)
            )
            chat_view.controls.append(ai_msg_container)
            page.update()

            for chunk in response_stream:
                ai_text_control.value += chunk.text
                page.update()
        
        except Exception as ex:
            if loading_text in chat_view.controls:
                chat_view.controls.remove(loading_text)
            add_message("Hệ thống", f"Lỗi kết nối API: {ex}")
            page.update()

    txt_input = ft.TextField(
        hint_text="Nhập tình trạng xe và DÒNG XE cụ thể...",
        expand=True,
        on_submit=on_send_click
    )
    btn_send = ft.IconButton(
        icon=ft.Icons.SEND_ROUNDED, 
        icon_color=ft.Colors.BLUE,  
        on_click=on_send_click
    )
    input_row = ft.Row([txt_input, btn_send])

    page.add(
        ft.Text("TRỢ LÝ AI CHẨN ĐOÁN (ĐA DÒNG XE)", size=18, weight=ft.FontWeight.BOLD),
        ft.Divider(),
        chat_view,
        input_row
    )

    # GỬI TIN NHẮN CHÀO HỎI KÈM THEO FILE PDF ĐỂ AI ĐỌC
    try:
        if uploaded_pdf_parts:
            # Gộp câu lệnh mồi và danh sách file PDF vào cùng 1 tin nhắn
            initial_prompt = ["Hãy đọc kỹ các Cẩm nang sửa chữa sau. Gửi một lời chào ngắn gọn và yêu cầu tôi cung cấp tình trạng xe kèm DÒNG XE để tra cứu."] + uploaded_pdf_parts
            response = chat_session.send_message(initial_prompt)
        else:
            response = chat_session.send_message("Hãy gửi lời chào và yêu cầu tôi cung cấp tình trạng xe kèm DÒNG XE cụ thể để bắt đầu.")
        add_message("AI", response.text)
    except Exception as ex:
        add_message("AI", f"Xin chào! Vui lòng làm mới trang web. Lỗi: {ex}")

port = int(os.environ.get("PORT", 8080))
ft.run(main, view=ft.AppView.WEB_BROWSER, host="0.0.0.0", port=port)
