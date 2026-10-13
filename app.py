import flet as ft
import flet_webview as fwv  # Kéo thư viện WebView độc lập vào
from google import genai
from google.genai import types
import os

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

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
    page.title = "GDS Auto Edu - Nền tảng Tra cứu ALLDATA"
    page.padding = 0 
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 1200
    page.window_height = 800

    chat_session = client.chats.create(model="gemini-3.8-flash", config=config)

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
        hint_text="Hỏi AI về hệ thống này...",
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
                ft.Text("Trợ lý AI ALLDATA", weight=ft.FontWeight.BOLD, color="blueAccent700", size=16),
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

    doc_title = ft.Text("Trang chủ", size=22, weight=ft.FontWeight.BOLD, color="#1E293B")
    
    doc_display_area = ft.Container(
        expand=True,
        bgcolor="white",
        border_radius=10,
        content=ft.Column([
            ft.Icon(ft.Icons.DIRECTIONS_CAR_ROUNDED, size=80, color="blueGrey200"),
            ft.Text("HỆ THỐNG TRA CỨU ALLDATA EDU", weight=ft.FontWeight.BOLD, color="blueGrey400", size=24),
            ft.Text("Hãy chọn sơ đồ từ cây thư mục hệ thống bên trái", color="blueGrey300")
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )

    def load_document(title, pdf_url):
        doc_title.value = title
        if pdf_url:
            # SỬ DỤNG THƯ VIỆN CHUYÊN DỤNG ĐỂ NHÚNG PDF TRỰC TIẾP
            doc_display_area.content = fwv.WebView(
                url=pdf_url,
                expand=True
            )
        
        try:
            chat_session.send_message(f"Sinh viên vừa mở tài liệu: {title}.")
        except:
            pass
        page.update()

    top_bar = ft.Container(
        bgcolor="#0F172A",
        height=60,
        padding=15,
        content=ft.Row([
            ft.Row([
                ft.Icon(ft.Icons.DIRECTIONS_CAR, color="orange500", size=30),
                ft.Text("GDS AUTO EDU", color="white", weight=ft.FontWeight.BOLD, size=20)
            ]),
            ft.Container(
                content=ft.TextField(
                    hint_text="Tìm kiếm linh kiện, sơ đồ mạch điện...",
                    bgcolor="#1E293B",
                    border_color="transparent",
                    color="white",
                    border_radius=5,
                    content_padding=10,
                    prefix_icon=ft.Icons.SEARCH,
                ),
                width=400
            ),
            ft.Row([
                ft.Icon(ft.Icons.NOTIFICATIONS, color="white"),
                ft.Container(width=10),
                ft.CircleAvatar(content=ft.Icon(ft.Icons.PERSON, color="white"), bgcolor="grey700")
            ])
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    )

    sidebar = ft.Container(
        width=300,
        bgcolor="#F8FAFC", 
        padding=15,
        content=ft.Column([
            ft.Text("HỆ THỐNG TRÊN XE (SYSTEM)", weight=ft.FontWeight.BOLD, color="grey700", size=13),
            
            ft.ExpansionTile(
                title=ft.Text("BRAKE (Hệ thống phanh)", weight=ft.FontWeight.BOLD, color="#1E293B"),
                leading=ft.Icon(ft.Icons.SPEED_ROUNDED, color="red500"),
                controls=[
                    ft.ListTile(
                        title=ft.Text("Sơ đồ TRC-H-F", color="#334155"), 
                        leading=ft.Icon(ft.Icons.PICTURE_AS_PDF_ROUNDED, color="red400"),
                        on_click=lambda e: load_document("Sơ đồ mạch điện TRC-H-F", "https://drive.google.com/file/d/1T2sntqGfpM3mC04mSz95IsSVgaK-J51N/preview")
                    ),
                    ft.ListTile(
                        title=ft.Text("Sơ đồ TRC-S-F", color="#334155"), 
                        leading=ft.Icon(ft.Icons.PICTURE_AS_PDF_ROUNDED, color="red400"),
                        on_click=lambda e: load_document("Sơ đồ mạch điện TRC-S-F", "https://drive.google.com/file/d/1NdXgLAd7oNRYbZ4XYAjDyyrKbarf0K0f/preview")
                    ),
                    ft.ListTile(
                        title=ft.Text("Sơ đồ VSC-H-F", color="#334155"), 
                        leading=ft.Icon(ft.Icons.PICTURE_AS_PDF_ROUNDED, color="red400"),
                        on_click=lambda e: load_document("Sơ đồ mạch điện VSC-H-F", "https://drive.google.com/file/d/1pUCuG1PgDOnaMtnMTRUI55y3O1y597ue/preview")
                    ),
                    ft.ListTile(
                        title=ft.Text("Sơ đồ VSC-SD", color="#334155"), 
                        leading=ft.Icon(ft.Icons.PICTURE_AS_PDF_ROUNDED, color="red400"),
                        on_click=lambda e: load_document("Sơ đồ mạch điện VSC-SD", "https://drive.google.com/file/d/1cIiF1Bao0spW8migy-X9rHHTjfSUhqS2/preview")
                    ),
                    ft.ListTile(
                        title=ft.Text("Sơ đồ EBD SD", color="#334155"), 
                        leading=ft.Icon(ft.Icons.PICTURE_AS_PDF_ROUNDED, color="red400"),
                        on_click=lambda e: load_document("Sơ đồ mạch điện EBD SD", "https://drive.google.com/file/d/1ebXdWhJgySd5-K_i_TXMg_s3c_Hn8N_i/preview")
                    ),
                ]
            ),
            ft.ExpansionTile(
                title=ft.Text("POWER SOURCE (Nguồn điện)", weight=ft.FontWeight.BOLD, color="#1E293B"),
                leading=ft.Icon(ft.Icons.BATTERY_CHARGING_FULL_ROUNDED, color="green500")
            ),
            ft.ExpansionTile(
                title=ft.Text("STEERING (Hệ thống lái)", weight=ft.FontWeight.BOLD, color="#1E293B"),
                leading=ft.Icon(ft.Icons.COMPASS_CALIBRATION_ROUNDED, color="blue500")
            )
        ])
    )

    main_workspace = ft.Container(
        expand=True,
        bgcolor="#E2E8F0", 
        padding=20,
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.FOLDER_OPEN_ROUNDED, color="blueGrey700"),
                doc_title
            ]),
            ft.Divider(color="grey400"),
            doc_display_area 
        ])
    )

    body_layout = ft.Row([sidebar, main_workspace], expand=True, spacing=0)
    main_layout = ft.Column([top_bar, body_layout], expand=True, spacing=0)

    page.add(
        ft.Stack(
            controls=[main_layout, chat_window, fab],
            expand=True
        )
    )

    try:
        if uploaded_pdf_parts:
            initial_prompt = ["Đọc các Cẩm nang sau. Chào sinh viên ngắn gọn."] + uploaded_pdf_parts
            chat_session.send_message(initial_prompt)
        else:
            chat_session.send_message("Xin chào.")
        add_message("AI", "Xin chào! Trợ lý AI đã sẵn sàng hỗ trợ bạn tra cứu mạch điện.")
    except Exception:
        pass

port = int(os.environ.get("PORT", 8080))
ft.run(main, view=ft.AppView.WEB_BROWSER, host="0.0.0.0", port=port)
