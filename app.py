import flet as ft
import os

def main(page: ft.Page):
    # CẤU HÌNH TRANG TOÀN MÀN HÌNH
    page.title = "Nền tảng Tra cứu Kỹ thuật Ô tô - GDS Auto Edu"
    page.padding = 0 
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 1200
    page.window_height = 800

    # ---------------------------------------------------
    # 1. CỬA SỔ AI CHAT (NỔI LƠ LỬNG)
    # ---------------------------------------------------
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
            # Thanh tiêu đề AI
            ft.Row([
                ft.CircleAvatar(content=ft.Icon(ft.Icons.SMART_TOY_ROUNDED, color="white"), bgcolor="orange500", radius=16),
                ft.Text("Trợ lý AI - Vios 2019", weight=ft.FontWeight.BOLD, color="blueAccent700", size=16),
                ft.Container(expand=True),
                ft.IconButton(ft.Icons.CLOSE_ROUNDED, on_click=lambda e: toggle_chat(False))
            ]),
            ft.Divider(color="grey300"),
            
            # Khu vực tin nhắn 
            ft.ListView(expand=True, auto_scroll=True, controls=[
                ft.Container(
                    content=ft.Text("Xin chào! Tôi thấy bạn đang xem Sơ đồ mạch điện A/C. Bạn cần tôi hướng dẫn đo kiểm chân cắm nào?", color="white"),
                    bgcolor="blueAccent700", padding=12, border_radius=12
                )
            ]),
            
            # Ô nhập liệu
            ft.TextField(
                hint_text="Nhập thông số hoặc câu hỏi...",
                border_radius=20,
                content_padding=15,
                filled=True,
                fill_color="blueGrey50",
                border_color="transparent"
            )
        ])
    )

    # Hàm bật/tắt cửa sổ AI
    def toggle_chat(show: bool):
        chat_window.visible = show
        page.update()

    # Nút bấm bong bóng nổi (Floating Action Button)
    fab = ft.FloatingActionButton(
        icon=ft.Icons.FORUM_ROUNDED,
        bgcolor="orange500",
        right=20,
        bottom=20,
        on_click=lambda e: toggle_chat(not chat_window.visible)
    )

    # ---------------------------------------------------
    # 2. THANH ĐIỀU HƯỚNG BÊN TRÁI (SIDEBAR)
    # ---------------------------------------------------
    sidebar = ft.Container(
        width=280,
        bgcolor="#1E293B", 
        padding=15,
        content=ft.Column([
            # Logo phần mềm
            ft.Row([
                ft.Icon(ft.Icons.AUTO_AWESOME_MOTION_ROUNDED, color="blue400", size=30),
                ft.Text("GDS AUTO EDU", color="white", weight=ft.FontWeight.BOLD, size=20),
            ], alignment=ft.MainAxisAlignment.START),
            ft.Divider(color="white24", height=30),
            
            # Cây thư mục (Tree View) chọn dòng xe 
            ft.ExpansionTile(
                title=ft.Text("TOYOTA", color="white", weight=ft.FontWeight.BOLD),
                controls=[
                    ft.ExpansionTile(
                        title=ft.Text("Vios (2019-2020)", color="white70"),
                        controls=[
                            ft.ListTile(title=ft.Text("Sơ đồ mạch điện A/C", color="blue400"), leading=ft.Icon(ft.Icons.ACCOUNT_TREE_ROUNDED, color="blue400")),
                            ft.ListTile(title=ft.Text("Vị trí giắc cắm hộp điều khiển", color="white54"), leading=ft.Icon(ft.Icons.LOCATION_ON_ROUNDED, color="white54")),
                            ft.ListTile(title=ft.Text("Bảng thông số lực siết", color="white54"), leading=ft.Icon(ft.Icons.BUILD_ROUNDED, color="white54")),
                        ]
                    ),
                    ft.ExpansionTile(
                        title=ft.Text("Camry (2018-2021)", color="white70"),
                        controls=[
                            ft.ListTile(title=ft.Text("Sơ đồ mạch điện A/C", color="white54"), leading=ft.Icon(ft.Icons.ACCOUNT_TREE_ROUNDED, color="white54")),
                        ]
                    )
                ]
            )
        ])
    )

    # ---------------------------------------------------
    # 3. KHÔNG GIAN LÀM VIỆC CHÍNH (MAIN WORKSPACE)
    # ---------------------------------------------------
    main_workspace = ft.Container(
        expand=True,
        bgcolor="#F1F5F9", 
        padding=20,
        content=ft.Column([
            # Tiêu đề tài liệu đang xem
            ft.Row([
                ft.Icon(ft.Icons.ACCOUNT_TREE_ROUNDED, color="blueGrey700"),
                ft.Text("Sơ đồ mạch điện hệ thống điều hòa (A/C) - Toyota Vios 2019", size=22, weight=ft.FontWeight.BOLD, color="blueGrey900")
            ]),
            ft.Divider(color="grey300"),
            
            # Khu vực hiển thị bản vẽ / Hình ảnh (Đã gỡ bỏ alignment)
            ft.Container(
                expand=True,
                bgcolor="white",
                border_radius=10,
                content=ft.Image(src="https://i.imgur.com/39hNq1b.jpeg", fit=ft.ImageFit.CONTAIN) 
            )
        ])
    )

    # ---------------------------------------------------
    # GẮP NỐI TẤT CẢ LÊN MÀN HÌNH BẰNG STACK
    # ---------------------------------------------------
    main_layout = ft.Row([sidebar, main_workspace], expand=True, spacing=0)

    page.add(
        ft.Stack(
            controls=[
                main_layout,  
                chat_window,  
                fab           
            ],
            expand=True
        )
    )

port = int(os.environ.get("PORT", 8080))
ft.run(main, view=ft.AppView.WEB_BROWSER, host="0.0.0.0", port=port)
