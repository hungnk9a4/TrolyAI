import flet as ft
from google import genai
from google.genai import types
import os

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# ĐƯA SẴN TÀI LIỆU HÌNH ẢNH VÀO CHO AI TẠI ĐÂY
system_instruction = """
Bạn là một Chuyên gia chẩn đoán kỹ thuật ô tô cấp cao, chuyên sâu về mạch điện và hệ thống điều hòa (A/C) trên Toyota Vios 2019-2020.
Nhiệm vụ của bạn là hướng dẫn sinh viên đo kiểm, chẩn đoán lỗi mạch cảm biến áp suất ga (nguồn 5V, mass, tín hiệu).

Quy tắc bắt buộc:
1. LUÔN LUÔN giao tiếp từng bước. Không bao giờ đưa ra toàn bộ quy trình đo kiểm trong 1 tin nhắn.
2. Bắt đầu bằng việc yêu cầu người dùng miêu tả tình trạng xe.
3. Khi phân tích điện áp, phải giải thích nguyên nhân và yêu cầu đo kiểm bước tiếp theo.
4. QUAN TRỌNG VỀ HÌNH ẢNH: Nếu sinh viên hỏi vị trí giắc cắm, sơ đồ mạch điện hoặc hình ảnh linh kiện, hãy trả lời bằng cú pháp Markdown hình ảnh: `![Tên ảnh](Link ảnh)`. 
Sử dụng kho dữ liệu ảnh sau đây để trả lời (không tự bịa link khác):
- Ảnh sơ đồ mạch cảm biến 5V: https://github.com/hungnk9a4/TrolyAI/blob/main/cambien.jpg?raw=true
- Ảnh vị trí hộp A/C Amplifier: https://github.com/hungnk9a4/TrolyAI/blob/main/vitri.jpg?raw=true
"""

config = types.GenerateContentConfig(
    system_instruction=system_instruction,
    temperature=0.7 
)

def main(page: ft.Page):
    page.title = "Trợ Lý AI Chẩn Đoán Ô Tô"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 450
    page.window_height = 750
    page.padding = 20

    chat_session = client.chats.create(
        # Đổi về 1.5-flash để có 1500 lượt miễn phí/ngày
        model="gemini-1.5-flash",
        config=config
    )

    chat_view = ft.ListView(expand=True, spacing=10, auto_scroll=True)

    def add_message(sender: str, text: str):
        is_user = sender == "Bạn"
        msg_margin = ft.margin.Margin(left=50, top=0, right=0, bottom=0) if is_user else ft.margin.Margin(left=0, top=0, right=50, bottom=0)
        
        # Nếu là người dùng gửi, hiển thị dạng Text. Nếu AI gửi, hiển thị dạng Markdown để load được ảnh
        content_control = ft.Text(text, color=ft.Colors.WHITE, size=15) if is_user else ft.Markdown(text, selectable=True, extension_set=ft.MarkdownExtensionSet.GITHUB_WEB_FLAVOR)
        
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
        
        loading_text = ft.Text("AI đang phân tích...", italic=True, color=ft.Colors.GREY)
        chat_view.controls.append(loading_text)
        page.update()

        try:
            response_stream = chat_session.send_message_stream(user_text)
            chat_view.controls.remove(loading_text)
            
            # Sử dụng Markdown cho luồng chữ chạy ra
            ai_text_control = ft.Markdown("", selectable=True, extension_set=ft.MarkdownExtensionSet.GITHUB_WEB_FLAVOR)
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
        hint_text="Nhập thông số hoặc yêu cầu sơ đồ...",
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
        ft.Text("TRỢ LÝ CHUYÊN GIA - TOYOTA VIOS", size=18, weight=ft.FontWeight.BOLD),
        ft.Divider(),
        chat_view,
        input_row
    )

    try:
        response = chat_session.send_message("Hãy gửi lời chào.")
        add_message("AI", response.text)
    except Exception:
        add_message("AI", "Xin chào! Vui lòng làm mới trang web.")

port = int(os.environ.get("PORT", 8080))
ft.run(main, view=ft.AppView.WEB_BROWSER, host="0.0.0.0", port=port)
