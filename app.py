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
4. QUAN TRỌNG NHẤT VỀ HÌNH ẢNH: BẤT CỨ KHI NÀO sinh viên hỏi về sơ đồ mạch điện hoặc vị trí hộp điều khiển, bạn BẮT BUỘC phải chèn nguyên vẹn đoạn mã Markdown tương ứng dưới đây vào ngay sau câu giới thiệu. Không được phép bỏ sót hoặc tự ý sửa đổi link.
Kho dữ liệu ảnh (Chỉ sử dụng copy-paste nguyên khối cú pháp này):
- Ảnh sơ đồ mạch cảm biến 5V: ![Sơ đồ mạch cảm biến](https://github.com/hungnk9a4/TrolyAI/blob/main/cambien.jpg?raw=true).
- Khi cần vị trí hộp A/C Amplifier: ![Vị trí hộp A/C](https://github.com/hungnk9a4/TrolyAI/blob/main/vitri.jpg?raw=true).
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
        model="gemini-3.8-flash",
        config=config
    )

    chat_view = ft.ListView(expand=True, spacing=10, auto_scroll=True)

    def add_message(sender: str, text: str):
        is_user = sender == "Bạn"
        msg_margin = ft.margin.Margin(left=50, top=0, right=0, bottom=0) if is_user else ft.margin.Margin(left=0, top=0, right=50, bottom=0)
        
        # Nếu là người dùng gửi, hiển thị dạng Text. Nếu AI gửi, hiển thị dạng Markdown để load được ảnh
        content_control = ft.Text(text, color=ft.Colors.WHITE, size=15) if is_user else ft.Markdown(text, selectable=True)
        
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
            ai_text_control = ft.Markdown("", selectable=True)
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
