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

# 2. HƯỚNG DẪN ĐỊNH HƯỚNG AI
system_instruction = """
Bạn là một Chuyên gia chẩn đoán kỹ thuật ô tô cấp cao, được tích hợp trong phần mềm GDS Auto Edu.
Nhiệm vụ của bạn là hướng dẫn sinh viên đo kiểm, chẩn đoán lỗi dựa trên bộ Cẩm nang sửa chữa.
1. LUÔN LUÔN giao tiếp từng bước. 
2. Trích dẫn số liệu CHÍNH XÁC từ Cẩm nang sửa chữa.
"""

config = types.GenerateContentConfig(
    system_instruction=system_instruction,
    temperature=0.2 
)

def main(page: ft.Page):
    page.title = "Nền tảng Tra cứu Kỹ thuật Ô tô - GDS Auto Edu"
    page.padding = 0 
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 1200
    page.window_height = 800

    chat_session = client.chats.create(model="gemini-3.8-flash", config=config)

    # ---------------------------------------------------
    # HỆ THỐNG XỬ LÝ CHAT AI
    # ---------------------------------------------------
    chat_list = ft.ListView(expand=True, auto_scroll=True, spacing=15)

    def add_message(sender: str, text: str):
        is_user = sender == "Bạn"
        avatar = ft.CircleAvatar(
            content=ft.Icon(ft.Icons.PERSON_ROUNDED if is_user else ft.Icons.SMART_TOY_ROUNDED, color="white"),
            bgcolor="blue400" if is_user else "orange500",
            radius=16
        )
        content_control = ft.Text(text, color="black87", size=14) if is_user else ft.Markdown(text, selectable=True, extension_set=ft.MarkdownExtensionSet.GITHUB_WEB)
        
        msg_bubble = ft.Container(
            content=content_control,
            bgcolor="blue50" if is_user else "grey100",
            padding=12,
            border_radius=15,
            width=260
        )
        
        row = ft.Row(
            controls=[msg_bubble, avatar] if is_user else [avatar, msg_bubble],
            alignment=ft.MainAxisAlignment.END if is_user else ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.START
        )
        chat_list.controls.append(row)
        page.update()

    def send_msg(e=None):
        if not chat_input.value:
            return
        
        user_text = chat_input.value
        add_message("Bạn", user_text)
        chat_input.value = "" 
        
        loading = ft.Row([
            ft.CircleAvatar(content=ft.Icon(ft.Icons.SMART_TOY_ROUNDED, color="white"), bgcolor="orange500", radius=16),
            ft.Text("AI đang tra cứu dữ liệu...", italic=True, color="grey", size=13)
        ], alignment=ft.MainAxisAlignment.START)
        chat_list.controls.append(loading)
        page.update()

        try:
            response_stream = chat_session.send_message_stream(user_text)
            chat_list.controls.remove(loading)
            
            ai_text = ft.Markdown("", selectable=True, extension_set=ft.MarkdownExtensionSet.GITHUB_WEB)
            ai_bubble = ft.Container(content=ai_text, bgcolor="grey100", padding=12, border_radius=15, width=260)
            ai_avatar = ft.CircleAvatar(content=ft.Icon(ft.Icons.SMART_TOY_ROUNDED, color="white"), bgcolor="orange500", radius=16)
            ai_row = ft.Row([ai_avatar, ai_bubble], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START)
            
            chat_list.controls.append(ai_row)
            page.update()

            for chunk in response_stream:
                ai_text.value += chunk.text
                page.update()
        except Exception as ex:
            if loading in chat_list.controls: chat_list.controls.remove(loading)
            add_message("Hệ thống", f"Lỗi: {ex}")

    chat_input = ft.TextField(
        hint_text="Hỏi AI về pan bệnh này...",
        border_radius=25,
        content_padding=15,
        filled=True,
        fill_color="blueGrey50",
        border_color="transparent",
        expand=True,
        on_submit=send_msg
    )
    send_btn = ft.IconButton(icon=ft.Icons.SEND_ROUNDED, icon_color="blueAccent700", on_click=send_msg)

    chat_window = ft.Container(
        visible=False, 
        width=380,
        height=550,
        bgcolor="white",
        border_radius=15,
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=15, color="black26", offset=ft.Offset(0, 5)),
        right=20,
        bottom=80, 
        padding=15,
        content=ft.Column([
            ft.Row([
                ft.CircleAvatar(content=ft.Icon(ft.Icons.SMART_TOY_ROUNDED, color="white"), bgcolor="orange500", radius=16),
                ft.Text("Trợ lý AI - Vios", weight=ft.FontWeight.BOLD, color="blueAccent700", size=16),
                ft.Container(expand=True),
                ft.IconButton(ft.Icons.CLOSE_ROUNDED, on_click=lambda e: toggle_chat(False))
            ]),
            ft.Divider(color="grey300"),
            chat_list,  
            ft.Row([chat_input, send_btn]) 
        ])
    )

    def toggle_chat(show: bool):
        chat_window.visible = show
        page.update()

    fab = ft.FloatingActionButton(
        icon=ft.Icons.FORUM_ROUNDED,
        bgcolor="orange500",
        right=20,
        bottom=20,
        on_click=lambda e: toggle_chat(not chat_window.visible)
    )

    # ---------------------------------------------------
    # KHU VỰC HIỂN THỊ CHÍNH (BIẾN ĐỘNG)
    # ---------------------------------------------------
    # Tiêu đề mặc định
    doc_title = ft.Text("Trang chủ - Xin mời chọn tài liệu", size=22, weight=ft.FontWeight.BOLD, color="blueGrey900")
    
    # Màn hình chào mừng mặc định
    welcome_view = ft.Column([
        ft.Icon(ft.Icons.DIRECTIONS_CAR_ROUNDED, size=80, color="blueGrey200"),
        ft.Text("GDS AUTO EDU", weight=ft.FontWeight.BOLD, color="blueGrey400", size=24),
        ft.Text("Hãy chọn dòng xe và tài liệu từ menu bên trái", color="blueGrey300")
    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    # Biến chứa hình ảnh (ẩn lúc đầu)
    doc_image = ft.Image(src="", fit="contain", visible=False, expand=True)

    # Container trung tâm chứa nội dung
    doc_display_area = ft.Container(
        expand=True,
        bgcolor="white",
        border_radius=10,
        content=welcome_view,
        alignment=ft.alignment.center
    )

    # ---------------------------------------------------
    # HÀM ĐỔI NỘI DUNG KHI CLICK MENU
    # ---------------------------------------------------
    def load_document(title, image_url):
        doc_title.value = title
        if image_url:
            doc_image.src = image_url
            doc_image.visible = True
            doc_display_area.content = doc_image
        else:
            doc_image.visible = False
            doc_display_area.content = ft.Text("Dữ liệu đang được cập nhật...", color="grey")
        
        # Tự động gửi thông báo ngầm cho AI biết sinh viên đang xem gì
        try:
            chat_session.send_message(f"Sinh viên vừa mở tài liệu: {title}. Hãy chuẩn bị sẵn sàng trả lời nếu họ hỏi.")
        except:
            pass

        page.update()

    # ---------------------------------------------------
    # THANH ĐIỀU HƯỚNG BÊN TRÁI (SIDEBAR)
    # ---------------------------------------------------
    sidebar = ft.Container(
        width=280,
        bgcolor="#1E293B", 
        padding=15,
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.AUTO_AWESOME_MOTION_ROUNDED, color="blue400", size=30),
                ft.Text("GDS AUTO EDU", color="white", weight=ft.FontWeight.BOLD, size=20),
            ], alignment=ft.MainAxisAlignment.START),
            ft.Divider(color="white24", height=30),
            
            ft.ExpansionTile(
                title=ft.Text("TOYOTA", color="white", weight=ft.FontWeight.BOLD),
                controls=[
                    ft.ExpansionTile(
                        title=ft.Text("Vios (2019-2020)", color="white70"),
                        controls=[
                            # GẮN SỰ KIỆN CLICK VÀO ĐÂY VỚI LINK ẢNH GIẢ LẬP
                            ft.ListTile(
                                title=ft.Text("Sơ đồ mạch điện A/C", color="white"), 
                                leading=ft.Icon(ft.Icons.ACCOUNT_TREE_ROUNDED, color="blue400"),
                                on_click=lambda e: load_document("Sơ đồ mạch điện A/C - Toyota Vios 2019", "https://placehold.co/1000x700/E2E8F0/1E293B?text=SO+DO+MACH+DIEN+DIEU+HOA+VIOS")
                            ),
                            ft.ListTile(
                                title=ft.Text("Vị trí giắc cắm hộp A/C", color="white"), 
                                leading=ft.Icon(ft.Icons.LOCATION_ON_ROUNDED, color="blue400"),
                                on_click=lambda e: load_document("Vị trí giắc cắm hộp điều khiển A/C - Toyota Vios 2019", "https://placehold.co/1000x700/E2E8F0/1E293B?text=VI+TRI+GIAC+CAM+TREN+XE")
                            ),
                            ft.ListTile(
                                title=ft.Text("Lực siết ốc lốc lạnh", color="white"), 
                                leading=ft.Icon(ft.Icons.BUILD_ROUNDED, color="blue400"),
                                on_click=lambda e: load_document("Bảng lực siết ốc hệ thống A/C - Toyota Vios 2019", "https://placehold.co/1000x700/E2E8F0/1E293B?text=BANG+LUC+SIET+OC+TIEU+CHUAN")
                            ),
                        ]
                    )
                ]
            )
        ])
    )

    # ---------------------------------------------------
    # KHÔNG GIAN LÀM VIỆC CHÍNH
    # ---------------------------------------------------
    main_workspace = ft.Container(
        expand=True,
        bgcolor="#F1F5F9", 
        padding=20,
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.ACCOUNT_TREE_ROUNDED, color="blueGrey700"),
                doc_title # Tiêu đề tự động thay đổi
            ]),
            ft.Divider(color="grey300"),
            doc_display_area # Nội dung tự động thay đổi
        ])
    )

    main_layout = ft.Row([sidebar, main_workspace], expand=True, spacing=0)

    page.add(
        ft.Stack(
            controls=[main_layout, chat_window, fab],
            expand=True
        )
    )

    try:
        if uploaded_pdf_parts:
            initial_prompt = ["Đọc các Cẩm nang sau. Chào sinh viên ngắn gọn và chờ câu hỏi."] + uploaded_pdf_parts
            response = chat_session.send_message(initial_prompt)
        else:
            response = chat_session.send_message("Hãy gửi một lời chào ngắn gọn tới sinh viên và yêu cầu câu hỏi.")
        add_message("AI", response.text)
    except Exception:
        pass

port = int(os.environ.get("PORT", 8080))
ft.run(main, view=ft.AppView.WEB_BROWSER, host="0.0.0.0", port=port)
