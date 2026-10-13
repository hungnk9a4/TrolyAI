import flet as ft
from google import genai
from google.genai import types
import os
import fitz  # PyMuPDF

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

assets_dir = "assets"
if not os.path.exists(assets_dir):
    os.makedirs(assets_dir)

# ---------------------------------------------------
# 1. CHUYỂN ĐỔI PDF THÀNH ẢNH (ĐÃ CHUẨN HÓA ĐƯỜNG DẪN)
# ---------------------------------------------------
def convert_pdf_to_images(rel_pdf_path):
    # Chuẩn hóa đường dẫn cho phù hợp với hệ điều hành Linux/Windows
    norm_rel_path = os.path.normpath(rel_pdf_path)
    full_pdf_path = os.path.join(assets_dir, norm_rel_path)
    
    if not os.path.exists(full_pdf_path):
        print(f"Không tìm thấy file: {full_pdf_path}")
        return []

    # Tạo tên ảnh duy nhất
    clean_prefix = norm_rel_path.replace(os.sep, "_").replace("/", "_").replace("\\", "_")
    clean_prefix = os.path.splitext(clean_prefix)[0]
    
    img_files = []
    try:
        doc = fitz.open(full_pdf_path)
        for i, page in enumerate(doc):
            img_name = f"{clean_prefix}_page_{i+1}.png"
            img_path = os.path.join(assets_dir, img_name)
            if not os.path.exists(img_path):
                pix = page.get_pixmap(dpi=150)
                pix.save(img_path)
            
            # Đường dẫn phục vụ hiển thị web (luôn dùng dấu /)
            web_img_path = img_name
            img_files.append(web_img_path)
    except Exception as ex:
        print(f"Lỗi chuyển đổi PDF {full_pdf_path}: {ex}")
    return img_files

# ---------------------------------------------------
# 2. XÂY DỰNG CÂY THƯ MỤC TỰ ĐỘNG
# ---------------------------------------------------
def build_file_tree(root_directory):
    tree = {}
    for root, dirs, files in os.walk(root_directory):
        rel_path = os.path.relpath(root, root_directory)
        if rel_path == ".":
            pdf_in_root = [f for f in files if f.lower().endswith(".pdf")]
            if pdf_in_root:
                tree["__files__"] = pdf_in_root
            continue
        
        parts = rel_path.split(os.sep)
        current = tree
        for part in parts:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        pdf_files = [f for f in files if f.lower().endswith(".pdf")]
        if pdf_files:
            current["__files__"] = pdf_files
    return tree

system_instruction = """
Bạn là một Chuyên gia chẩn đoán kỹ thuật ô tô cấp cao, được tích hợp trong phần mềm GDS Auto Edu.
Nhiệm vụ của bạn là hướng dẫn sinh viên đo kiểm, chẩn đoán lỗi dựa trên bộ Cẩm nang sửa chữa.
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

    chat_session = client.chats.create(model="gemini-3.8-flash", config=config) if client else None
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
        if not chat_input.value or not chat_session: return
        user_text = chat_input.value
        add_message("Bạn", user_text)
        chat_input.value = "" 
        
        loading = ft.Row([
            ft.CircleAvatar(content=ft.Icon(ft.Icons.SMART_TOY_ROUNDED, color="white"), bgcolor="orange500", radius=16),
            ft.Text("AI đang phân tích sơ đồ...", italic=True, color="grey", size=13)
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

    chat_input = ft.TextField(hint_text="Hỏi AI...", border_radius=25, content_padding=15, filled=True, fill_color="blueGrey50", border_color="transparent", expand=True, on_submit=send_msg)
    send_btn = ft.IconButton(icon=ft.Icons.SEND_ROUNDED, icon_color="blueAccent700", on_click=send_msg)

    chat_window = ft.Container(
        visible=False, width=380, height=550, bgcolor="white", border_radius=15,
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=15, color="black26", offset=ft.Offset(0, 5)),
        right=20, bottom=80, padding=15,
        content=ft.Column([
            ft.Row([
                ft.CircleAvatar(content=ft.Icon(ft.Icons.SMART_TOY_ROUNDED, color="white"), bgcolor="orange500", radius=16),
                ft.Text("Trợ lý AI ALLDATA", weight=ft.FontWeight.BOLD, color="blueAccent700", size=16),
                ft.Container(expand=True),
                ft.IconButton(ft.Icons.CLOSE_ROUNDED, on_click=lambda e: toggle_chat(False))
            ]),
            ft.Divider(color="grey300"),
            chat_list, ft.Row([chat_input, send_btn]) 
        ])
    )

    def toggle_chat(show: bool):
        chat_window.visible = show
        page.update()

    fab = ft.FloatingActionButton(icon=ft.Icons.FORUM_ROUNDED, bgcolor="orange500", right=20, bottom=20, on_click=lambda e: toggle_chat(not chat_window.visible))
    doc_title = ft.Text("Trang chủ", size=22, weight=ft.FontWeight.BOLD, color="#1E293B")
    
    doc_display_area = ft.Container(
        expand=True, bgcolor="white", border_radius=10,
        content=ft.Column([
            ft.Icon(ft.Icons.DIRECTIONS_CAR_ROUNDED, size=80, color="blueGrey200"),
            ft.Text("HỆ THỐNG TRA CỨU ALLDATA EDU", weight=ft.FontWeight.BOLD, color="blueGrey400", size=24),
            ft.Text("Hãy chọn hãng xe và hệ thống từ cây thư mục bên trái", color="blueGrey300")
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )

    # ---------------------------------------------------
    # HÀM MỞ FILE VỚI GIAO DIỆN MỞ RỘNG TOÀN MÀN HÌNH
    # ---------------------------------------------------
    def load_document(title, rel_pdf_path):
        doc_title.value = title
        img_files = convert_pdf_to_images(rel_pdf_path)
        if img_files:
            image_controls = [ft.Image(src=f"/{img}", fit="contain", expand=True) for img in img_files]
            doc_display_area.content = ft.ListView(
                controls=image_controls,
                expand=True,
                spacing=15
            )
        else:
            doc_display_area.content = ft.Column([
                ft.Icon(ft.Icons.ERROR_OUTLINE_ROUNDED, color="red400", size=50),
                ft.Text("Không thể tải tài liệu này. Hãy kiểm tra tên file PDF trong thư mục assets.", color="red400", weight=ft.FontWeight.BOLD)
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        page.update()

    top_bar = ft.Container(
        bgcolor="#0F172A", height=60, padding=15,
        content=ft.Row([
            ft.Row([ft.Icon(ft.Icons.DIRECTIONS_CAR, color="orange500", size=30), ft.Text("GDS AUTO EDU", color="white", weight=ft.FontWeight.BOLD, size=20)]),
            ft.Container(content=ft.TextField(hint_text="Tìm kiếm linh kiện...", bgcolor="#1E293B", border_color="transparent", color="white", border_radius=5, content_padding=10, prefix_icon=ft.Icons.SEARCH), width=400),
            ft.Row([ft.Icon(ft.Icons.NOTIFICATIONS, color="white"), ft.Container(width=10), ft.CircleAvatar(content=ft.Icon(ft.Icons.PERSON, color="white"), bgcolor="grey700")])
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    )

    # ---------------------------------------------------
    # HÀM TẠO MENU LỒNG NHAU ĐA TẦNG DỰA TRÊN THƯ MỤC
    # ---------------------------------------------------
    def create_menu_nodes(tree_dict, current_path=""):
        controls = []
        for key, value in sorted(tree_dict.items()):
            if key == "__files__":
                continue
            
            files = value.get("__files__", [])
            sub_folders = {k: v for k, v in value.items() if k != "__files__"}
            
            sub_controls = []
            new_path = os.path.join(current_path, key) if current_path else key
            
            if sub_folders:
                sub_controls.extend(create_menu_nodes(sub_folders, new_path))
            
            for f in sorted(files):
                doc_name = os.path.splitext(f)[0]
                full_rel_path = os.path.join(new_path, f)
                sub_controls.append(
                    ft.ListTile(
                        title=ft.Text(doc_name, color="#334155", weight=ft.FontWeight.BOLD),
                        leading=ft.Icon(ft.Icons.PICTURE_AS_PDF_ROUNDED, color="red400"),
                        on_click=lambda e, path=full_rel_path, name=doc_name: load_document(name, path)
                    )
                )
            
            controls.append(
                ft.ExpansionTile(
                    title=ft.Text(key, weight=ft.FontWeight.BOLD, color="#1E293B"),
                    controls=sub_controls
                )
            )
        return controls

    file_tree = build_file_tree(assets_dir)
    menu_controls = create_menu_nodes(file_tree)
    if not menu_controls:
        menu_controls = [ft.Text("Đang chờ tạo thư mục xe trong assets...", color="grey", italic=True)]

    sidebar = ft.Container(
        width=320, bgcolor="#F8FAFC", padding=15,
        content=ft.Column([
            ft.Text("DANH MỤC HÃNG XE & HỆ THỐNG", weight=ft.FontWeight.BOLD, color="grey700", size=13),
            ft.Column(controls=menu_controls, scroll=ft.ScrollMode.AUTO, expand=True)
        ])
    )

    main_workspace = ft.Container(
        expand=True, bgcolor="#E2E8F0", padding=20,
        content=ft.Column([
            ft.Row([ft.Icon(ft.Icons.FOLDER_OPEN_ROUNDED, color="blueGrey700"), doc_title]),
            ft.Divider(color="grey400"),
            doc_display_area 
        ])
    )

    body_layout = ft.Row([sidebar, main_workspace], expand=True, spacing=0)
    main_layout = ft.Column([top_bar, body_layout], expand=True, spacing=0)
    page.add(ft.Stack(controls=[main_layout, chat_window, fab], expand=True))

    add_message("AI", "Xin chào! Trợ lý AI đã sẵn sàng hỗ trợ bạn tra cứu mạch điện.")

port = int(os.environ.get("PORT", 8080))
ft.run(main, view=ft.AppView.WEB_BROWSER, host="0.0.0.0", port=port, assets_dir="assets")
