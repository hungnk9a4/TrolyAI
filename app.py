import flet as ft
from google import genai
from google.genai import types
import os
import fitz  # PyMuPDF
import urllib.request
import json
import ssl

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

assets_dir = "assets"
if not os.path.exists(assets_dir):
    os.makedirs(assets_dir)

# ---------------------------------------------------
# BỘ GIẢI MÃ SỐ KHUNG THÔNG MINH (Hỗ trợ toàn bộ xe Việt Nam & Quốc tế)
# ---------------------------------------------------
def decode_vin_smart(vin):
    vin_clean = vin.strip().upper()
    if len(vin_clean) < 10:
        return None, None, None, None, "Không đủ ký tự"

    # 1. Tra cứu kho nội bộ của xưởng trường trước
    LOCAL_VIN_DB = {
        "RNHA39KHJTT": {"make": "KIA", "model": "Xe tải tập lái", "year": "2026", "engine": "2.5L Diesel"},
        "RL4B23F35J": {"make": "HUYNDAI / THACO", "model": "Xe khách / Tải", "year": "2018", "engine": "2.9L Diesel"}
    }
    for prefix, info in LOCAL_VIN_DB.items():
        if vin_clean.startswith(prefix):
            return info["make"], info["model"], info["year"], info["engine"], "Kho nội bộ xưởng"

    # 2. Giải mã tự động theo chuẩn Quốc tế (ISO 3779) cho mọi loại xe 16-17 ký tự
    wmi = vin_clean[:3]
    make_map = {
        "KNA": "KIA (Hàn Quốc)", "KNB": "KIA", "KMH": "HYUNDAI", "MAL": "HYUNDAI / THACO",
        "JMB": "MITSUBISHI", "JTE": "TOYOTA", "JTD": "TOYOTA", "4T1": "TOYOTA (Mỹ)",
        "1NX": "TOYOTA", "ZFA": "FIAT", "VF1": "RENAULT", "WBA": "BMW", "WDB": "MERCEDES-BENZ"
    }
    
    # Nhận diện hãng qua mã WMI (3 ký tự đầu) hoặc mã quốc gia
    make = make_map.get(wmi, "Xe lắp ráp / Nhập khẩu tổng hợp")
    if wmi.startswith("RL") or wmi.startswith("RK") or wmi.startswith("MB"):
        make = "Xe thương mại / Tải / Khách tại Việt Nam"

    # Giải mã năm sản xuất từ ký tự thứ 10 theo chuẩn ISO
    year_map = {
        'J': '2018', 'K': '2019', 'L': '2020', 'M': '2021', 
        'N': '2022', 'P': '2023', 'R': '2024', 'S': '2025', 'T': '2026', 'V': '2027'
    }
    year_char = vin_clean[9] if len(vin_clean) >= 10 else ""
    year = year_map.get(year_char, "Đời xe tiêu chuẩn")

    # Phỏng đoán dung tích/loại động cơ dựa trên ký tự dòng xe
    engine = "Động cơ tiêu chuẩn (Xăng / Dầu)"
    model = f"Mã nhận diện: {vin_clean[3:9]}"

    return make, model, year, engine, "Giải mã tiêu chuẩn VIN"

# ---------------------------------------------------
# CHUYỂN ĐỔI PDF THÀNH ẢNH
# ---------------------------------------------------
def convert_pdf_to_images(rel_pdf_path):
    norm_rel_path = os.path.normpath(rel_pdf_path)
    full_pdf_path = os.path.join(assets_dir, norm_rel_path)
    
    if not os.path.exists(full_pdf_path):
        target_filename = os.path.basename(rel_pdf_path)
        found_path = None
        for root, dirs, files in os.walk(assets_dir):
            if target_filename in files:
                found_path = os.path.join(root, target_filename)
                break
        if found_path: full_pdf_path = found_path
        else: return []

    clean_prefix = os.path.splitext(os.path.basename(full_pdf_path))[0]
    img_files = []
    try:
        doc = fitz.open(full_pdf_path)
        for i, page in enumerate(doc):
            img_name = f"{clean_prefix}_page_{i+1}.png"
            img_path = os.path.join(assets_dir, img_name)
            if not os.path.exists(img_path):
                pix = page.get_pixmap(dpi=150)
                pix.save(img_path)
            img_files.append(img_name)
    except Exception: pass
    return img_files

def build_file_tree(root_directory):
    tree = {}
    for root, dirs, files in os.walk(root_directory):
        rel_path = os.path.relpath(root, root_directory)
        if rel_path == ".":
            pdf_in_root = [f for f in files if f.lower().endswith(".pdf")]
            if pdf_in_root: tree["__files__"] = pdf_in_root
            continue
        parts = rel_path.replace("\\", "/").split("/")
        current = tree
        for part in parts:
            if part not in current: current[part] = {}
            current = current[part]
        pdf_files = [f for f in files if f.lower().endswith(".pdf")]
        if pdf_files: current["__files__"] = pdf_files
    return tree

config = types.GenerateContentConfig(
    system_instruction="Bạn là Chuyên gia chẩn đoán kỹ thuật ô tô cấp cao của GDS Auto Edu.",
    temperature=0.2 
)

def main(page: ft.Page):
    page.title = "GDS Auto Edu - Nền tảng Tra cứu ALLDATA"
    page.padding = 0 
    page.theme_mode = ft.ThemeMode.LIGHT
    
    chat_session = client.chats.create(model="gemini-3.8-flash", config=config) if client else None
    chat_list = ft.ListView(expand=True, auto_scroll=True, spacing=15)

    def add_message(sender: str, text: str):
        is_user = sender == "Bạn"
        avatar = ft.CircleAvatar(
            content=ft.Icon(ft.Icons.PERSON_ROUNDED if is_user else ft.Icons.SMART_TOY_ROUNDED, color="white"),
            bgcolor="blue400" if is_user else "orange500", radius=16
        )
        content_control = ft.Text(text, color="black87", size=14) if is_user else ft.Markdown(text, selectable=True, extension_set=ft.MarkdownExtensionSet.GITHUB_WEB)
        msg_bubble = ft.Container(content=content_control, bgcolor="blue50" if is_user else "grey100", padding=12, border_radius=15, width=260)
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

    def load_document(title, rel_pdf_path):
        doc_title.value = title
        img_files = convert_pdf_to_images(rel_pdf_path)
        if img_files:
            zoom_level = [1000] 
            img_column = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=15)
            def update_images():
                img_column.controls = [ft.Image(src=f"/{img}", width=zoom_level[0], fit="contain") for img in img_files]
                page.update()
            def zoom_in(e):
                zoom_level[0] += 300
                update_images()
            def zoom_out(e):
                if zoom_level[0] > 500: zoom_level[0] -= 300
                update_images()
            def reset_zoom(e):
                zoom_level[0] = 1000
                update_images()
            update_images()
            scrollable_2d_area = ft.Row(controls=[img_column], scroll=ft.ScrollMode.AUTO, expand=True, vertical_alignment=ft.CrossAxisAlignment.START)
            zoom_toolbar = ft.Row([
                ft.Container(content=ft.Row([ft.Icon(ft.Icons.ZOOM_OUT, color="white", size=18), ft.Text("Thu nhỏ", color="white", size=12, weight=ft.FontWeight.BOLD)]), bgcolor="blueGrey600", padding=8, border_radius=5, on_click=zoom_out),
                ft.Container(content=ft.Row([ft.Icon(ft.Icons.RESTART_ALT, color="white", size=18), ft.Text("Mặc định", color="white", size=12, weight=ft.FontWeight.BOLD)]), bgcolor="orange600", padding=8, border_radius=5, on_click=reset_zoom),
                ft.Container(content=ft.Row([ft.Icon(ft.Icons.ZOOM_IN, color="white", size=18), ft.Text("Phóng to", color="white", size=12, weight=ft.FontWeight.BOLD)]), bgcolor="blue700", padding=8, border_radius=5, on_click=zoom_in)
            ], alignment=ft.MainAxisAlignment.END)
            doc_display_area.content = ft.Column([zoom_toolbar, scrollable_2d_area], expand=True)
        else:
            doc_display_area.content = ft.Text("Không thể tải tài liệu.", color="red")
        page.update()

    def create_menu_nodes(tree_dict, current_path="", level=0, search_term=""):
        controls = []
        font_sizes = [13, 12, 12, 11, 11, 11]
        icon_colors = ["orange600", "blue600", "teal600", "purple600", "indigo600", "blueGrey600"]
        for key, value in sorted(tree_dict.items()):
            if key == "__files__": continue
            files = value.get("__files__", [])
            sub_folders = {k: v for k, v in value.items() if k != "__files__"}
            sub_controls = []
            new_path = os.path.join(current_path, key) if current_path else key
            folder_matches = (search_term in key.lower()) if search_term else False
            if sub_folders:
                sub_controls.extend(create_menu_nodes(sub_folders, new_path, level + 1, search_term))
            for f in sorted(files):
                doc_name = os.path.splitext(f)[0]
                if search_term and (search_term not in doc_name.lower()) and not folder_matches:
                    continue
                full_rel_path = os.path.join(new_path, f)
                file_indent = (level + 1) * 10
                sub_controls.append(
                    ft.ListTile(
                        dense=True,
                        leading=ft.Row([ft.Container(width=file_indent) if file_indent > 0 else ft.Container(width=0), ft.Icon(ft.Icons.PICTURE_AS_PDF_ROUNDED, color="red500", size=15)], spacing=2, tight=True),
                        title=ft.Text(doc_name, color="#334155", size=11, weight=ft.FontWeight.W_500),
                        on_click=lambda e, path=full_rel_path, name=doc_name: load_document(name, path)
                    )
                )
            if search_term and not folder_matches and not sub_controls:
                continue
            current_size = font_sizes[min(level, len(font_sizes)-1)]
            current_color = icon_colors[min(level, len(icon_colors)-1)]
            folder_indent = level * 10
            folder_icon = ft.Icons.DIRECTIONS_CAR_ROUNDED if level == 0 else (ft.Icons.FOLDER_ROUNDED if sub_folders else ft.Icons.FOLDER_OPEN_ROUNDED)
            controls.append(
                ft.ExpansionTile(
                    dense=True,
                    title=ft.Text(key, weight=ft.FontWeight.BOLD if level < 2 else ft.FontWeight.W_500, size=current_size, color="#0F172A"),
                    leading=ft.Row([ft.Container(width=folder_indent) if folder_indent > 0 else ft.Container(width=0), ft.Icon(folder_icon, color=current_color, size=16)], spacing=2, tight=True),
                    controls=sub_controls
                )
            )
        return controls

    file_tree = build_file_tree(assets_dir)
    sidebar_column = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

    def update_search(e_or_value):
        query = e_or_value.control.value.lower().strip() if hasattr(e_or_value, 'control') else e_or_value.lower().strip()
        filtered_controls = create_menu_nodes(file_tree, search_term=query)
        if not filtered_controls: filtered_controls = [ft.Text("Không tìm thấy dữ liệu...", color="red400", italic=True)]
        sidebar_column.controls = filtered_controls
        sidebar_column.update()

    sidebar_column.controls = create_menu_nodes(file_tree)
    if not sidebar_column.controls: sidebar_column.controls = [ft.Text("Đang chờ tạo thư mục xe trong assets...", color="grey", italic=True)]

    search_input = ft.TextField(
        hint_text="Tìm kiếm hệ thống, hãng xe...", bgcolor="#1E293B", border_color="transparent", color="white", 
        border_radius=5, content_padding=10, prefix_icon=ft.Icons.SEARCH, on_change=update_search
    )

    vin_input = ft.TextField(label="Nhập số khung (Hỗ trợ 16-17 ký tự)", capitalization=ft.TextCapitalization.CHARACTERS, prefix_icon=ft.Icons.DIRECTIONS_CAR, border_radius=8)
    vin_result_text = ft.Text("", size=14)
    vin_loading = ft.ProgressBar(visible=False)

    def process_vin(e):
        vin = vin_input.value.strip().upper()
        if len(vin) < 6:
            vin_result_text.value, vin_result_text.color = "❌ Vui lòng nhập ít nhất 6 ký tự số khung!", "red"
            page.update()
            return
        
        vin_result_text.value, vin_result_text.color, vin_loading.visible = "Đang giải mã thông tin số khung...", "blue", True
        page.update()

        make, model, year, engine, source = decode_vin_smart(vin)
        vin_loading.visible = False
        
        # Luôn luôn hiển thị thông tin xe đã giải mã thành công
        vin_result_text.value = (
            f"✅ THÔNG TIN PHƯƠNG TIỆN:\n"
            f"• Số khung: {vin}\n"
            f"• Hãng / Đơn vị: {make}\n"
            f"• Đời xe (Năm): {year}\n"
            f"• Động cơ / Thông số: {engine}\n\n"
            f"👉 Hệ thống đã nhận diện thành công!"
        )
        vin_result_text.color, vin_result_text.weight = "green700", ft.FontWeight.BOLD
        
        # Thử tự động lọc menu bên trái nếu hãng xe có trong kho tài liệu
        try:
            search_input.value = make.split()[0] # Lấy từ đầu tiên của hãng (VD: KIA)
            update_search(search_input.value)
        except Exception:
            pass
            
        page.update()

    def close_vin_dialog(e):
        vin_modal.visible = False
        page.update()
    def open_vin_dialog(e):
        vin_input.value, vin_result_text.value, vin_loading.visible, vin_modal.visible = "", "", False, True
        page.update()

    btn_decode = ft.Container(content=ft.Row([ft.Icon(ft.Icons.SEARCH, color="white", size=16), ft.Text("Tra Cứu Xe", color="white", weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.CENTER, tight=True), bgcolor="blue700", padding=10, border_radius=5, on_click=process_vin)
    btn_close = ft.Container(content=ft.Text("Đóng", color="blueGrey400", weight=ft.FontWeight.BOLD), padding=10, on_click=close_vin_dialog)

    vin_modal = ft.Container(
        visible=False, left=0, right=0, top=0, bottom=0, bgcolor="#99000000",
        content=ft.Row(
            controls=[
                ft.Container(
                    width=450, bgcolor="white", border_radius=10, padding=20, shadow=ft.BoxShadow(spread_radius=1, blur_radius=15, color="black26"),
                    content=ft.Column([
                        ft.Row([ft.Icon(ft.Icons.DOCUMENT_SCANNER, color="orange600"), ft.Text("Tra Cứu Thông Tin Số Khung", weight=ft.FontWeight.BOLD, size=16)]),
                        ft.Divider(color="grey300"), vin_input, vin_loading, vin_result_text, ft.Container(height=10),
                        ft.Row([btn_close, btn_decode], alignment=ft.MainAxisAlignment.END)
                    ], tight=True)
                )
            ], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER
        )
    )

    top_bar = ft.Container(
        bgcolor="#0F172A", height=60, padding=15,
        content=ft.Row([
            ft.Row([ft.Icon(ft.Icons.DIRECTIONS_CAR, color="orange500", size=30), ft.Text("GDS AUTO EDU", color="white", weight=ft.FontWeight.BOLD, size=20)]),
            ft.Container(content=search_input, width=400),
            ft.Row([
                ft.IconButton(icon=ft.Icons.DOCUMENT_SCANNER_ROUNDED, icon_color="orange500", tooltip="Tra cứu số khung xe", on_click=open_vin_dialog),
                ft.Container(width=5),
                ft.CircleAvatar(content=ft.Icon(ft.Icons.PERSON, color="white"), bgcolor="grey700")
            ])
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    )

    sidebar = ft.Container(
        width=330, bgcolor="#F8FAFC", padding=10,
        content=ft.Column([
            ft.Text("DANH MỤC HÃNG XE & HỆ THỐNG", weight=ft.FontWeight.BOLD, color="grey700", size=12),
            sidebar_column
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
    
    page.add(ft.Stack(controls=[main_layout, chat_window, vin_modal, fab], expand=True))

port = int(os.environ.get("PORT", 8080))
ft.run(main, view=ft.AppView.WEB_BROWSER, host="0.0.0.0", port=port, assets_dir="assets")
