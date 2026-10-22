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
# 1. HỆ THỐNG GIẢI MÃ SỐ KHUNG (VIN DECODER API)
# ---------------------------------------------------
def decode_vin_api(vin):
    url = f"https://vpic.nhtsa.dot.gov/api/vehicles/decodevin/{vin}?format=json"
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            make, model, year, engine = "Không rõ", "Không rõ", "Không rõ", "Không rõ"
            
            for item in data.get("Results", []):
                val = item["Value"]
                if not val or val == "Not Applicable": continue
                
                if item["Variable"] == "Make": make = val
                elif item["Variable"] == "Model": model = val
                elif item["Variable"] == "Model Year": year = val
                elif item["Variable"] == "Displacement (L)": engine = f"{val}L"
                
            return make, model, year, engine
    except Exception as e:
        print("Lỗi giải mã VIN:", e)
        return None, None, None, None

# ---------------------------------------------------
# 2. CHUYỂN ĐỔI PDF THÀNH ẢNH
# ---------------------------------------------------
def convert_pdf_to_images(rel_pdf_path):
    norm_rel_path = os.path.normpath(rel_pdf_path)
    full_pdf_path = os.path.join(assets_dir, norm_rel_path)
    if not os.path.exists(full_pdf_path): return []

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
            img_files.append(img_name)
    except Exception: pass
    return img_files

# ---------------------------------------------------
# 3. XÂY DỰNG CÂY THƯ MỤC TỰ ĐỘNG
# ---------------------------------------------------
def build_file_tree(root_directory):
    tree = {}
    for root, dirs, files in os.walk(root_directory):
        rel_path = os.path.relpath(root, root_directory)
        if rel_path == ".":
            pdf_in_root = [f for f in files if f.lower().endswith(".pdf")]
            if pdf_in_root: tree["__files__"] = pdf_in_root
            continue
        
        parts = rel_path.split(os.sep)
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
            image_controls = [ft.Image(src=f"/{img}", fit="contain", expand=True) for img in img_files]
            doc_display_area.content = ft.ListView(controls=image_controls, expand=True, spacing=15)
        else:
            doc_display_area.content = ft.Text("Không thể tải tài liệu.", color="red")
        page.update()

    # ---------------------------------------------------
    # DIALOG TRA CỨU SỐ KHUNG (VIN)
    # ---------------------------------------------------
    vin_input = ft.TextField(label="Nhập số khung (VIN) - 17 ký tự", capitalization=ft.TextCapitalization.CHARACTERS, prefix_icon=ft.Icons.DIRECTIONS_CAR, border_radius=8)
    vin_result_text = ft.Text("", size=14)
    vin_loading = ft.ProgressBar(visible=False)

    def process_vin(e):
        vin = vin_input.value.strip().upper()
        if len(vin) != 17:
            vin_result_text.value, vin_result_text.color = "❌ Số VIN phải có đúng 17 ký tự!", "red"
            page.update()
            return
        
        vin_result_text.value, vin_result_text.color, vin_loading.visible = "Đang kết nối cơ sở dữ liệu quốc tế...", "blue", True
        page.update()

        make, model, year, engine = decode_vin_api(vin)
        vin_loading.visible = False
        
        if make and make != "Không rõ":
            vin_result_text.value = f"✅ KẾT QUẢ GIẢI MÃ:\n• Hãng xe: {make}\n• Dòng xe: {model}\n• Đời xe: {year}\n• Động cơ: {engine}\n\n👉 Bạn có thể tìm theo hãng {make} ở menu."
            vin_result_text.color, vin_result_text.weight = "green700", ft.FontWeight.BOLD
            # Tự động điền hãng xe vào ô tìm kiếm
            search_input.value = make
            update_search(make)
        else:
            vin_result_text.value, vin_result_text.color, vin_result_text.weight = "❌ Không tìm thấy dữ liệu cho số khung này.", "red", ft.FontWeight.NORMAL
        page.update()

    def close_vin_dialog(e):
        vin_modal.visible = False
        page.update()
    def open_vin_dialog(e):
        vin_input.value, vin_result_text.value, vin_loading.visible, vin_modal.visible = "", "", False, True
        page.update()

    btn_decode = ft.Container(content=ft.Row([ft.Icon(ft.Icons.SEARCH, color="white", size=16), ft.Text("Giải Mã", color="white", weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.CENTER, tight=True), bgcolor="blue700", padding=10, border_radius=5, on_click=process_vin)
    btn_close = ft.Container(content=ft.Text("Đóng", color="blueGrey400", weight=ft.FontWeight.BOLD), padding=10, on_click=close_vin_dialog)

    vin_modal = ft.Container(
        visible=False, left=0, right=0, top=0, bottom=0, bgcolor="#99000000",
        content=ft.Row(
            controls=[
                ft.Container(
                    width=450, bgcolor="white", border_radius=10, padding=20, shadow=ft.BoxShadow(spread_radius=1, blur_radius=15, color="black26"),
                    content=ft.Column([
                        ft.Row([ft.Icon(ft.Icons.DOCUMENT_SCANNER, color="orange600"), ft.Text("Tra Cứu Số Khung (VIN)", weight=ft.FontWeight.BOLD, size=18)]),
                        ft.Divider(color="grey300"), vin_input, vin_loading, vin_result_text, ft.Container(height=10),
                        ft.Row([btn_close, btn_decode], alignment=ft.MainAxisAlignment.END)
                    ], tight=True)
                )
            ], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER
        )
    )

    # ---------------------------------------------------
    # TÍNH NĂNG TÌM KIẾM THỜI GIAN THỰC (REAL-TIME SEARCH)
    # ---------------------------------------------------
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
            
            # Kiểm tra xem từ khóa có nằm trong tên thư mục này không
            folder_matches = (search_term in key.lower()) if search_term else False
            
            if sub_folders:
                # Chuyển từ khóa tìm kiếm xuống các thư mục con
                sub_controls.extend(create_menu_nodes(sub_folders, new_path, level + 1, search_term))
            
            for f in sorted(files):
                doc_name = os.path.splitext(f)[0]
                # Lọc file: Giữ lại nếu tên file khớp, hoặc thư mục cha đã khớp
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
            
            # Ẩn thư mục nếu đang tìm kiếm mà thư mục này (và các con của nó) không khớp
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
                    controls=sub_controls,
                    # Tự động bung mở thư mục nếu đang ở chế độ tìm kiếm
                    initially_expanded=True if search_term else False 
                )
            )
        return controls

    file_tree = build_file_tree(assets_dir)
    sidebar_column = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

    def update_search(e_or_value):
        # Lấy giá trị từ sự kiện gõ phím hoặc chuỗi trực tiếp
        query = e_or_value.control.value.lower().strip() if hasattr(e_or_value, 'control') else e_or_value.lower().strip()
        filtered_controls = create_menu_nodes(file_tree, search_term=query)
        
        if not filtered_controls:
            filtered_controls = [ft.Text("Không tìm thấy dữ liệu...", color="red400", italic=True)]
        
        sidebar_column.controls = filtered_controls
        sidebar_column.update()

    # Load menu lần đầu tiên
    sidebar_column.controls = create_menu_nodes(file_tree)
    if not sidebar_column.controls:
        sidebar_column.controls = [ft.Text("Đang chờ tạo thư mục xe trong assets...", color="grey", italic=True)]

    # Gắn sự kiện on_change vào ô tìm kiếm
    search_input = ft.TextField(
        hint_text="Tìm kiếm hệ thống, xe...", 
        bgcolor="#1E293B", border_color="transparent", color="white", 
        border_radius=5, content_padding=10, prefix_icon=ft.Icons.SEARCH,
        on_change=update_search
    )

    top_bar = ft.Container(
        bgcolor="#0F172A", height=60, padding=15,
        content=ft.Row([
            ft.Row([ft.Icon(ft.Icons.DIRECTIONS_CAR, color="orange500", size=30), ft.Text("GDS AUTO EDU", color="white", weight=ft.FontWeight.BOLD, size=20)]),
            ft.Container(content=search_input, width=400),
            ft.Row([
                ft.IconButton(icon=ft.Icons.DOCUMENT_SCANNER_ROUNDED, icon_color="orange500", tooltip="Tra cứu VIN", on_click=open_vin_dialog),
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
