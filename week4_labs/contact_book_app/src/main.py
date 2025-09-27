import flet as ft
from database import init_db
from app_logic import display_contacts, add_contact

def main(page: ft.Page):
    page.title = "Contact Book"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.window_width = 420
    page.window_height = 700
    page.padding = 16

    # Initialize DB
    db_conn = init_db()

    # Top row: Title + Theme toggle
    title = ft.Text("Contact Book", size=22, weight=ft.FontWeight.BOLD)

    theme_switch = ft.Switch(label="Switch Theme", value=False)

    def toggle_theme(e):
        page.theme_mode = ft.ThemeMode.LIGHT if theme_switch.value else ft.ThemeMode.DARK
        
        page.update()

    theme_switch.on_change = toggle_theme

    top_row = ft.Row([title, ft.Container(expand=True), theme_switch], vertical_alignment=ft.CrossAxisAlignment.CENTER)

    # Input fields
    name_input = ft.TextField(label="Name", width=360)
    phone_input = ft.TextField(label="Phone", width=360)
    email_input = ft.TextField(label="Email", width=360)

    inputs = (name_input, phone_input, email_input)

    # Search field
    search_input = ft.TextField(label="Search by name", hint_text="Type to filter contacts", width=360)

    # Contacts list
    contacts_list_view = ft.ListView(expand=1, spacing=10, auto_scroll=True )

    # Add button
    add_button = ft.ElevatedButton("Add Contact", on_click=lambda e: add_contact(page, inputs, contacts_list_view, db_conn))

    # Clear search button (optional)
    clear_search_btn = ft.IconButton(ft.Icons.CLEAR, tooltip="Clear search", on_click=lambda e: clear_search(page, search_input, contacts_list_view, db_conn))

    # Search on change: refresh displayed list
    def on_search_change(e):
        display_contacts(page, contacts_list_view, db_conn, search_input.value)

    search_input.on_change = on_search_change

    # Layout
    form = ft.Column(
        [
            ft.Text("Enter Contact Details:", size=16, weight=ft.FontWeight.BOLD),
            name_input,
            phone_input,
            email_input,
            ft.Row([add_button]),
            ft.Divider(),
            ft.Row([ft.Text("Contacts:", size=16, weight=ft.FontWeight.BOLD), ft.Container(expand=True), clear_search_btn]),
            ft.Row([search_input]),
            ft.Container(height=8),
            ft.Container(
                content=ft.Column([contacts_list_view]),
                expand=True,
                padding=0,
            ),
        ],
        spacing=8,
    )

    page.add(top_row, ft.Divider(), form)

    # Initial display
    display_contacts(page, contacts_list_view, db_conn)

def clear_search(page: ft.Page, search_input: ft.TextField, contacts_container: ft.Column, db_conn):
    search_input.value = ""
    page.update()
    display_contacts(page, contacts_container, db_conn)

if __name__ == "__main__":
    ft.app(target=main)