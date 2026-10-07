import flet as ft
from google import genai
from google.genai import types
import os

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# 1. TẢI TÀI LIỆU LÊN GEMINI
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

# 2. HƯỚNG DẪN ĐỊNH HƯỚNG SUY LUẬN
system_instruction = """
Bạn là một Chuyên gia chẩn đoán kỹ thuật ô tô cấp cao, vui tính và thân thiện với sinh viên.
Nhiệm vụ của bạn là hướng dẫn sinh viên đo kiểm, chẩn đoán lỗi hệ thống điều hòa (A/C) dựa trên bộ Cẩm nang sửa chữa.

Quy tắc bắt buộc:
1. LUÔN LUÔN giao tiếp từng bước. Không đưa ra toàn bộ quy trình đo kiểm trong 1 tin nhắn.
2. Nếu sinh viên hỏi về một dòng xe cụ thể, hãy TÌM TÀI LIỆU của dòng xe đó để trả lời. 
3. Nếu dòng xe sinh viên hỏi KHÔNG CÓ trong tài liệu, hãy báo rõ là "Thầy/Cô chưa cập nhật tài liệu xe này vào hệ thống".
4. Trích dẫn số liệu CHÍNH XÁC Y HỆT từ Cẩm nang sửa chữa.
5. QUAN TRỌNG VỀ HÌNH ẢNH: BẮT BUỘC chèn đoạn mã Markdown chứa link ảnh khi được hỏi về sơ đồ.
"""

config = types.GenerateContentConfig(
    system_instruction=system_instruction,
    temperature=0.2 
)

def main(page: ft.Page):
    # CẤU HÌNH GIAO DIỆN TỔNG THỂ
    page.title = "Trợ Lý AI Chẩn Đoán Ô Tô"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = "#F4F6F9" # Màu nền xám nhạt dịu mắt
    page.window_width = 450
    page.window_height = 750
    page.padding = 10

    # THANH TIÊU ĐỀ (APP BAR) HIỆN ĐẠI
    page.appbar = ft.AppBar(
        leading=ft.Icon(ft.Icons.DIRECTIONS_CAR_ROUNDED, color=ft.Colors.WHITE, size=28),
        leading_width=50,
        title=ft.Text("Trợ Lý Chuyên Gia A/C", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD, size=20),
        center_title=False,
        bgcolor=ft.Colors.BLUE_ACCENT_700,
        actions=[
            ft.IconButton(ft.Icons.INFO_OUTLINE_ROUNDED, icon_color=ft.Colors.WHITE)
        ]
    )

    chat_session = client.chats.create(
        model="gemini-3.8-flash",
        config=config
    )

    # KHUNG CHAT
    chat_view = ft.ListView(expand=True, spacing=15, auto_scroll=True, padding=10)

    # HÀM HIỂN THỊ TIN NHẮN VỚI AVATAR
    def add_message(sender: str, text: str):
        is_user = sender == "Bạn"
        
        # Thiết kế Avatar
        avatar = ft.CircleAvatar(
            content=ft.Icon(ft.Icons.PERSON_ROUNDED if is_user else ft.Icons.SMART_TOY_ROUNDED, color=ft.Colors.WHITE),
            bgcolor=ft.Colors.BLUE_400 if is_user else ft.Colors.ORANGE_400,
            radius=18
        )
        
        # Thiết kế Bong bóng chat
        content_control = ft.Text(text, color=ft.Colors.WHITE, size=15) if is_user else ft.Markdown(text, selectable=True, extension_set=ft.MarkdownExtensionSet.GITHUB_WEB)
        
        msg_bubble = ft.Container(
            content=content_control,
            bgcolor=ft.Colors.BLUE_ACCENT_700 if is_user else ft.Colors.WHITE,
            padding=ft.padding.all(12),
            border_radius=ft.border_radius.only(
                top_left=15, top_right=15,
                bottom_left=15 if is_user else 5,
                bottom_right=5 if is_user else 15
            ),
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=3, color=ft.Colors.BLACK12, offset=ft.Offset(0, 1)),
            width=280 # Giới hạn chiều rộng để bong bóng trông đẹp hơn
        )

        # Sắp xếp hàng (Row) tùy theo người gửi
        msg_row = ft.Row(
            controls=[msg_bubble, avatar] if is_user else [avatar, msg_bubble],
            alignment=ft.MainAxisAlignment.END if is_user else ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.END
        )
        
        chat_view.controls.append(msg_row)
        page.update()

    def on_send_click(e):
        if not txt_input.value:
            return
        
        user_text = txt_input.value
        add_message("Bạn", user_text)
        txt_input.value = "" 
        
        # Hiệu ứng đang gõ chữ
        loading_row = ft.Row([
            ft.CircleAvatar(content=ft.Icon(ft.Icons.SMART_TOY_ROUNDED, color=ft.Colors.WHITE), bgcolor=ft.Colors.ORANGE_400, radius=18),
            ft.Text("AI đang lật Cẩm nang sửa chữa...", italic=True, color=ft.Colors.GREY, size=13)
        ], alignment=ft.MainAxisAlignment.START)
        
        chat_view.controls.append(loading_row)
        page.update()

        try:
            response_stream = chat_session.send_message_stream(user_text)
            chat_view.controls.remove(loading_row)
            
            # Cấu trúc bong bóng chat cho AI khi Streaming
            ai_text_control = ft.Markdown("", selectable=True, extension_set=ft.MarkdownExtensionSet.GITHUB_WEB)
            ai_msg_bubble = ft.Container(
                content=ai_text_control,
                bgcolor=ft.Colors.WHITE,
                padding=ft.padding.all(12),
                border_radius=ft.border_radius.only(top_left=15, top_right=15, bottom_left=5, bottom_right=15),
                shadow=ft.BoxShadow(spread_radius=1, blur_radius=3, color=ft.Colors.BLACK12, offset=ft.Offset(0, 1)),
                width=280
            )
            
            ai_avatar = ft.CircleAvatar(content=ft.Icon(ft.Icons.SMART_TOY_ROUNDED, color=ft.Colors.WHITE), bgcolor=ft.Colors.ORANGE_400, radius=18)
            ai_msg_row = ft.Row([ai_avatar, ai_msg_bubble], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.END)
            
            chat_view.controls.append(ai_msg_row)
            page.update()

            for chunk in response_stream:
                ai_text_control.value += chunk.text
                page.update()
        
        except Exception as ex:
            if loading_row in chat_view.controls:
                chat_view.controls.remove(loading_row)
            add_message("Hệ thống", f"Lỗi kết nối API: {ex}")
            page.update()

    # KHU VỰC NHẬP LIỆU HIỆN ĐẠI
    txt_input = ft.TextField(
        hint_text="Hỏi thông số, sơ đồ, pan bệnh...",
        expand=True,
        border_radius=25,
        filled=True,
        fill_color=ft.Colors.WHITE,
        border_color=ft.Colors.TRANSPARENT,
        content_padding=ft.padding.only(left=20, top=15, bottom=15, right=20),
        on_submit=on_send_click
    )
    
    btn_send = ft.FloatingActionButton(
        icon=ft.Icons.SEND_ROUNDED,
        bgcolor=ft.Colors.BLUE_ACCENT_700,
        mini=True,
        on_click=on_send_click
    )
    
    input_row = ft.Row(
        [txt_input, btn_send],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER
    )

    page.add(chat_view, input_row)

    # GỬI TIN NHẮN CHÀO HỎI
    try:
        if uploaded_pdf_parts:
            initial_prompt = ["Hãy đọc kỹ các Cẩm nang sửa chữa sau. Gửi một lời chào vui vẻ tới các bạn sinh viên và yêu cầu cung cấp tình trạng xe kèm DÒNG XE để tra cứu."] + uploaded_pdf_parts
            response = chat_session.send_message(initial_prompt)
        else:
            response = chat_session.send_message("Hãy gửi một lời chào vui vẻ tới sinh viên và yêu cầu cung cấp tình trạng xe kèm DÒNG XE cụ thể để bắt đầu.")
        add_message("AI", response.text)
    except Exception as ex:
        add_message("AI", f"Xin chào! Vui lòng làm mới trang web. Lỗi: {ex}")

port = int(os.environ.get("PORT", 8080))
ft.run(main, view=ft.AppView.WEB_BROWSER, host="0.0.0.0", port=port)
