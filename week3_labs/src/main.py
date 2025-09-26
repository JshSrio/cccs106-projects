import flet as ft
import mysql.connector
from db_connection import connect_db
import asyncio

def _check_credentials_sync(username: str, password: str) -> bool:
    """Blocking DB check (runs in separate thread)."""
    conn = None
    cur = None
    try:
        conn = connect_db()
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE username = %s AND password = %s", (username, password))
        row = cur.fetchone()
        return bool(row)
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def main(page: ft.Page):
    # --- Page setup ---
    page.title = "User Login"
    try:
        page.window.width = 1200
        page.window.height = 800
    except Exception:
        pass
    try:
        page.window_center()
    except Exception:
        pass
    try:
        page.window_frameless = True
    except Exception:
        pass

    # --- UI controls ---
    title = ft.Text(
        "User Login",
        size=20,
        weight=ft.FontWeight.BOLD,
        font_family="Arial",
        text_align=ft.TextAlign.CENTER,
        color=ft.Colors.BLACK,
    )

    username_field = ft.TextField(
        label="User name",
        hint_text="Enter your user name",
        helper_text="This is your unique identifier",
        width=300,
        autofocus=True,
        prefix_icon=ft.Icons.PERSON,
        color=ft.Colors.BLACK,  # <-- Input value color
        hint_style=ft.TextStyle(color=ft.Colors.BLACK),
        label_style=ft.TextStyle(color=ft.Colors.BLACK),
        helper_style=ft.TextStyle(color=ft.Colors.BLACK),
    
    )
    username_wrapper = ft.Container(
        content=username_field,
        padding=ft.padding.symmetric(vertical=6, horizontal=8),
        border_radius=8,
        bgcolor=ft.Colors.WHITE,
    )

    password_field = ft.TextField(
        label="Password",
        hint_text="Enter your password",
        helper_text="This is your secret key",
        width=300,
        password=True,
        can_reveal_password=True,
        prefix_icon=ft.Icons.LOCK,
        color=ft.Colors.BLACK,  # <-- Input value color
        hint_style=ft.TextStyle(color=ft.Colors.BLACK),
        label_style=ft.TextStyle(color=ft.Colors.BLACK),
        helper_style=ft.TextStyle(color=ft.Colors.BLACK),
    )
    password_wrapper = ft.Container(
        content=password_field,
        padding=ft.padding.symmetric(vertical=6, horizontal=8),
        border_radius=8,
        bgcolor=ft.Colors.WHITE,
    )

    status_text = ft.Text("", size=12, color=ft.Colors.RED)

    async def login_click(e):
        uname = username_field.value.strip()
        pwd = password_field.value

        def close_dialog(d: ft.AlertDialog):
            d.open = False
            page.update()

        # Success dialog
        success_dialog = ft.AlertDialog(
            modal=True,
            shape=ft.RoundedRectangleBorder(radius=12),
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN, size=30),
                    ft.Text("Login Successful", size=18, weight=ft.FontWeight.BOLD),
                ],
            ),
            content=ft.Container(  # <-- Wrap content in Container
                content=ft.Text(f"Welcome, {uname}!", size=18, text_align=ft.TextAlign.CENTER),
                width=320,
                padding=20,
            ),
            actions_alignment=ft.MainAxisAlignment.END,
            actions=[ft.TextButton("OK", on_click=lambda ev: close_dialog(success_dialog))],
        )

        # Failure dialog
        failure_dialog = ft.AlertDialog(
            modal=True,
            shape=ft.RoundedRectangleBorder(radius=12),
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.ERROR, color=ft.Colors.RED, size=30),
                    ft.Text("Login Failed", size=18, weight=ft.FontWeight.BOLD),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            content=ft.Container(
                content=ft.Text("Invalid username or password", size=18, text_align=ft.TextAlign.CENTER),
                width=320,
                padding=20,
            ),
            actions_alignment=ft.MainAxisAlignment.END,
            actions=[ft.TextButton("OK", on_click=lambda ev: close_dialog(failure_dialog))],
        )

        # Input error dialog
        invalid_input_dialog = ft.AlertDialog(
            modal=True,
            shape=ft.RoundedRectangleBorder(radius=12),
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.INFO, color=ft.Colors.BLUE, size=30),
                    ft.Text("Input Error", size=18, weight=ft.FontWeight.BOLD),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            content=ft.Container(
                content=ft.Text("Please enter username and password", size=18, text_align=ft.TextAlign.CENTER),
                width=320,
                padding=20,
            ),
            actions_alignment=ft.MainAxisAlignment.END,
            actions=[ft.TextButton("OK", on_click=lambda ev: close_dialog(invalid_input_dialog))],
        )

        # Database error dialog
        database_error_dialog = ft.AlertDialog(
            modal=True,
            shape=ft.RoundedRectangleBorder(radius=12),
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.WARNING, color=ft.Colors.AMBER, size=30),
                    ft.Text("Database Error", size=18, weight=ft.FontWeight.BOLD),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            content=ft.Container(
                content=ft.Text(
                    "An error occurred while connecting to the database",
                    size=18,
                    text_align=ft.TextAlign.CENTER,
                ),
                width=320,
                padding=20,
            ),
            actions_alignment=ft.MainAxisAlignment.END,
            actions=[ft.TextButton("OK", on_click=lambda ev: close_dialog(database_error_dialog))],
        )

        # --- Input validation ---
        if not uname or not pwd:
              page.dialog = invalid_input_dialog
              page.add(invalid_input_dialog)
              invalid_input_dialog.open = True
              page.update()
              return

        try:
            ok = await asyncio.to_thread(_check_credentials_sync, uname, pwd)
            if ok:
                page.dialog = success_dialog
                page.add(success_dialog)
                success_dialog.open = True
                username_field.value = ""
                password_field.value = ""
            else:
                page.dialog = failure_dialog
                page.add(failure_dialog)
                failure_dialog.open = True

            page.update()

        except mysql.connector.Error as db_err:
              page.dialog = database_error_dialog
              page.add(database_error_dialog)
              database_error_dialog.open = True
              status_text.value = f"DB error: {db_err}"
              page.update()
        except Exception as ex:
              page.dialog = database_error_dialog
              page.add(database_error_dialog)
              database_error_dialog.open = True
              status_text.value = f"Error: {ex}"
              page.update()

    login_btn = ft.ElevatedButton(
        "Login",
        icon=ft.Icons.LOGIN,
        on_click=login_click,
        width=100,
        style=ft.ButtonStyle(
        bgcolor=ft.Colors.BLUE_400,   
        color=ft.Colors.WHITE,    
        ),
    )

    inputs_column = ft.Column([username_wrapper, password_wrapper], spacing=20)
    button_container = ft.Container(
        content=ft.Row([login_btn], alignment=ft.MainAxisAlignment.END),
        margin=ft.margin.only(left=0, top=20, right=40, bottom=0),
    )

    content_column = ft.Column(
        [title, inputs_column, button_container, status_text],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=8,
    )

    root_container = ft.Container(expand=True, bgcolor=ft.Colors.YELLOW, content=content_column)

    page.add(root_container)
    page.update()


if __name__ == "__main__":
    ft.app(target=main)


