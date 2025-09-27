import flet as ft
from database import add_contact_db, get_all_contacts_db, update_contact_db, delete_contact_db


def display_contacts(page: ft.Page, contacts_list_view, db_conn, search_text: str = ""):
    """
    Fetches and displays all contacts in the provided container (ft.Column).
    Uses ft.Card for each contact and provides Edit/Delete in a PopupMenuButton.
    """
    contacts_list_view.controls.clear()
    contacts = get_all_contacts_db(db_conn, search_text)

    for contact in contacts:
        contact_id, name, phone, email = contact

        # Build contact row inside a card
        contact_row = ft.Row(
            [
                ft.Column(
                    [
                        ft.Text(name, weight=ft.FontWeight.BOLD, size=14),
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.PHONE, size=16),
                                ft.Text(phone or "-", size=12),
                                ft.Container(width=12),  # small spacer
                                ft.Icon(ft.Icons.EMAIL, size=16),
                                ft.Text(email or "-", size=12),
                            ],
                            tight=True,
                        ),
                    ],
                    spacing=6,
                    expand=True,
                ),
                ft.PopupMenuButton(
                    icon=ft.Icons.MORE_VERT,
                    items=[
                        ft.PopupMenuItem(
                            text="Edit",
                            icon=ft.Icons.EDIT,
                            # FIXED: bind current contact with default arg
                            on_click=lambda e, c=(contact_id, name, phone, email): open_edit_dialog(
                                page, c, db_conn, contacts_list_view
                            ),
                        ),
                        ft.PopupMenuItem(
                            text="Delete",
                            icon=ft.Icons.DELETE,
                            # FIXED: bind current contact_id
                            on_click=lambda e, cid=contact_id: confirm_delete(
                                page, cid, db_conn, contacts_list_view
                            ),
                        ),
                    ],
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        card = ft.Card(
            content=ft.Container(content=contact_row, padding=12),
            elevation=2,
            margin=ft.margin.only(bottom=8),
        )
        contacts_list_view.controls.append(card)

    page.update()


def add_contact(page: ft.Page, inputs, contacts_list_view, db_conn):
    """
    Adds a new contact after validation and refreshes the list.
    inputs: tuple(name_input, phone_input, email_input)
    """
    name_input, phone_input, email_input = inputs

    # Input validation: name is required
    if not (name_input.value and name_input.value.strip()):
        name_input.error_text = "Name cannot be empty"
        page.update()
        return
    else:
        name_input.error_text = None

    # Input validation: phone is required
    if not (phone_input.value and phone_input.value.strip()):
        phone_input.error_text = "Phone Number cannot be empty"
        page.update()
        return
    else:
        phone_input.error_text = None

    # Input validation: email is required
    if not (email_input.value and email_input.value.strip()):
        email_input.error_text = "Email Address cannot be empty"
        page.update()
        return
    else:
        email_input.error_text = None

    # Save new contact
    add_contact_db(
        db_conn,
        name_input.value.strip(),
        phone_input.value.strip(),
        email_input.value.strip(),
    )

    # Clear fields
    name_input.value = ""
    phone_input.value = ""
    email_input.value = ""
    page.update()

    # Always refresh full list
    display_contacts(page, contacts_list_view, db_conn)


def open_edit_dialog(page, contact, db_conn, contacts_list_view):
    """Opens a dialog to edit a contact's details."""
    contact_id, name, phone, email = contact

    edit_name = ft.TextField(label="Name", value=name)
    edit_phone = ft.TextField(label="Phone", value=phone)
    edit_email = ft.TextField(label="Email", value=email)

    def save_and_close(e):
        update_contact_db(db_conn, contact_id, edit_name.value, edit_phone.value, edit_email.value)
        dialog.open = False
        page.update()
        display_contacts(page, contacts_list_view, db_conn)

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Edit Contact"),
        content = ft.Container(
            content=ft.Column([edit_name, edit_phone, edit_email]),
            height = 200,
            width = 300,
        ),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: close_dialog(page, dialog)),
            ft.TextButton("Save", on_click=save_and_close),
        ],
    )

    page.open(dialog)

def delete_contact(page: ft.Page, contact_id, db_conn, contacts_list_view):
    """
    Opens a confirmation dialog before deletion. Only deletes if user confirms.
    """
    delete_contact_db(db_conn, contact_id)
    display_contacts(page, contacts_list_view, db_conn)

def confirm_delete(page, contact_id, db_conn, contacts_list_view):
    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Confirm Delete"),
        content=ft.Text("You are going to delete this contact. Are you sure?"),
        actions=[
            ft.TextButton("No", on_click=lambda e: close_dialog(page, dialog)),
            ft.TextButton(
                "Yes",
                on_click=lambda e: (
                    delete_contact(page, contact_id, db_conn, contacts_list_view),
                    close_dialog(page, dialog)
                ),
            ),
        ],
    )
    page.open(dialog)

    
def close_dialog(page, dialog):
    dialog.open = False
    page.update()