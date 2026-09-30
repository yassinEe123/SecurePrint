import os
import numpy as np
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image

from modules.preprocessor import FingerprintProcessor
from modules.minutiae import MinutiaeExtractor
from modules.template import TemplateGenerator
from modules.encryption import EncryptionManager
from modules.storage import StorageManager
from modules.matcher import Authenticator


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class SecurePrintGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self._setup_window()

        self.processor = FingerprintProcessor()
        self.extractor = MinutiaeExtractor(border_margin=20)
        self.generator = TemplateGenerator()
        self.encryptor = EncryptionManager()
        self.storage = StorageManager()
        self.authenticator = Authenticator(threshold=0.70, duplicate_threshold=0.55)  # cosine distance

        self.storage.create_tables()

        self.selected_image_path = None
        self.preview_images = {}

        self.current_template = None
        self.current_minutiae_count = 0
        self.current_template_length = 0

        self.logo_path = "assets/tek_up_logo_clean.png"
        self.logo_image_ref = None

        self.data_key = None

        self._build_ui()
        self._ask_master_password()
        self.refresh_user_selectors()
        self.show_default_action_panel()

    def _setup_window(self):
        self.title("SecurePrint - Modern Biometric Interface")

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        margin_x = 12
        margin_y = 12

        window_width = screen_width - (2 * margin_x)
        window_height = screen_height - (2 * margin_y) - 40

        self.geometry(f"{window_width}x{window_height}+{margin_x}+{margin_y}")
        self.minsize(1200, 700)

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def _build_ui(self):
        self._build_header()
        self._build_center()
        self._build_footer()

    def _build_header(self):
        header = ctk.CTkFrame(self, height=86, corner_radius=16)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        header.grid_columnconfigure(2, weight=1)
        header.grid_propagate(False)

        self.logo_label = ctk.CTkLabel(header, text="")
        self.logo_label.grid(row=0, column=0, padx=(14, 8), pady=10, sticky="w")

        self._load_header_logo()

        title_block = ctk.CTkFrame(header, fg_color="transparent")
        title_block.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="w")

        self.title_label = ctk.CTkLabel(
            title_block,
            text="SecurePrint",
            font=ctk.CTkFont(size=26, weight="bold")
        )
        self.title_label.pack(anchor="w")

        self.subtitle_label = ctk.CTkLabel(
            title_block,
            text="Encrypted Biometric Authentication",
            font=ctk.CTkFont(size=12)
        )
        self.subtitle_label.pack(anchor="w")

        self.path_var = ctk.StringVar(value="No image selected")
        self.path_entry = ctk.CTkEntry(header, textvariable=self.path_var, height=38)
        self.path_entry.grid(row=0, column=2, padx=10, pady=12, sticky="ew")

        self.status_var = ctk.StringVar(value="Ready")
        self.status_box = ctk.CTkLabel(
            header,
            textvariable=self.status_var,
            width=220,
            height=38,
            corner_radius=10,
            fg_color="#1f2a44",
            font=ctk.CTkFont(size=15, weight="bold")
        )
        self.status_box.grid(row=0, column=3, padx=16, pady=12)

    def _load_header_logo(self):
        if not os.path.exists(self.logo_path):
            self.logo_label.configure(text="TEK-UP", font=ctk.CTkFont(size=18, weight="bold"))
            return

        try:
            pil_logo = Image.open(self.logo_path)
            self.logo_image_ref = ctk.CTkImage(
                light_image=pil_logo,
                dark_image=pil_logo,
                size=(170, 58)
            )
            self.logo_label.configure(image=self.logo_image_ref, text="")
        except Exception:
            self.logo_label.configure(text="TEK-UP", font=ctk.CTkFont(size=18, weight="bold"))

    def _build_center(self):
        center = ctk.CTkFrame(self, corner_radius=16)
        center.grid(row=1, column=0, sticky="nsew", padx=10, pady=6)
        center.grid_columnconfigure(0, weight=3)
        center.grid_columnconfigure(1, weight=4)
        center.grid_columnconfigure(2, weight=3)
        center.grid_rowconfigure(0, weight=1)

        self._build_left_panel(center)
        self._build_middle_panel(center)
        self._build_right_panel(center)

    def _build_left_panel(self, parent):
        left = ctk.CTkFrame(parent, corner_radius=16)
        left.grid(row=0, column=0, sticky="nsew", padx=(8, 5), pady=8)
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            left,
            text="Selected Fingerprint",
            font=ctk.CTkFont(size=20, weight="bold")
        ).grid(row=0, column=0, padx=12, pady=(12, 6), sticky="w")

        self.main_image_label = ctk.CTkLabel(left, text="No image selected")
        self.main_image_label.grid(row=1, column=0, padx=12, pady=8, sticky="nsew")

        self.image_info_box = ctk.CTkTextbox(left, height=130)
        self.image_info_box.grid(row=2, column=0, padx=12, pady=(0, 12), sticky="ew")
        self.image_info_box.insert(
            "1.0",
            "Image info will appear here:\n\n"
            "- selected file\n"
            "- minutiae count\n"
            "- template length\n"
            "- biometric decision"
        )
        self.image_info_box.configure(state="disabled")

    def _build_middle_panel(self, parent):
        middle = ctk.CTkFrame(parent, corner_radius=16)
        middle.grid(row=0, column=1, sticky="nsew", padx=5, pady=8)
        middle.grid_columnconfigure((0, 1), weight=1)
        middle.grid_rowconfigure((1, 2, 3), weight=1)

        ctk.CTkLabel(
            middle,
            text="Processing Stages",
            font=ctk.CTkFont(size=20, weight="bold")
        ).grid(row=0, column=0, columnspan=2, padx=12, pady=(12, 6), sticky="w")

        self.stage_labels = {}
        stages = [
            ("Enhanced", "02_enhanced.png", 1, 0),
            ("Segmented", "03_segmented.png", 1, 1),
            ("Binary", "04_binary.png", 2, 0),
            ("Skeleton", "05_skeleton.png", 2, 1),
            ("Minutiae", "06_minutiae.png", 3, 0),
        ]

        for title, filename, row, col in stages:
            box = ctk.CTkFrame(middle, corner_radius=12)
            box.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            box.grid_rowconfigure(1, weight=1)
            box.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                box,
                text=title,
                font=ctk.CTkFont(size=15, weight="bold")
            ).grid(row=0, column=0, padx=8, pady=(8, 4))

            img_label = ctk.CTkLabel(box, text="No image")
            img_label.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="nsew")

            self.stage_labels[filename] = img_label

        empty_box = ctk.CTkFrame(middle, corner_radius=12, fg_color="transparent")
        empty_box.grid(row=3, column=1, padx=8, pady=8, sticky="nsew")

    def _build_right_panel(self, parent):
        right = ctk.CTkFrame(parent, corner_radius=16)
        right.grid(row=0, column=2, sticky="nsew", padx=(5, 8), pady=8)
        right.grid_rowconfigure(4, weight=1)
        right.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            right,
            text="Biometric Result",
            font=ctk.CTkFont(size=20, weight="bold")
        ).grid(row=0, column=0, padx=12, pady=(12, 6), sticky="w")

        self.result_box = ctk.CTkFrame(right, corner_radius=12, fg_color="#1d273d")
        self.result_box.grid(row=1, column=0, padx=12, pady=8, sticky="ew")
        self.result_box.grid_columnconfigure(0, weight=1)

        self.result_label = ctk.CTkLabel(
            self.result_box,
            text="No action performed yet",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.result_label.grid(row=0, column=0, padx=10, pady=(14, 8))

        self.result_details = ctk.CTkLabel(
            self.result_box,
            text="Distance: -\nTemplate: -\nMinutiae: -",
            justify="left",
            font=ctk.CTkFont(size=14)
        )
        self.result_details.grid(row=1, column=0, padx=10, pady=(0, 14))

        self.action_title = ctk.CTkLabel(
            right,
            text="Action Panel",
            font=ctk.CTkFont(size=17, weight="bold")
        )
        self.action_title.grid(row=2, column=0, padx=12, pady=(8, 4), sticky="w")

        self.dynamic_panel = ctk.CTkFrame(right, corner_radius=12, fg_color="#222831")
        self.dynamic_panel.grid(row=3, column=0, padx=12, pady=(0, 8), sticky="ew")
        self.dynamic_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            right,
            text="Activity Log",
            font=ctk.CTkFont(size=17, weight="bold")
        ).grid(row=4, column=0, padx=12, pady=(8, 4), sticky="w")

        self.log_box = ctk.CTkTextbox(right, wrap="word")
        self.log_box.grid(row=5, column=0, padx=12, pady=(0, 12), sticky="nsew")

    def _build_footer(self):
        footer = ctk.CTkFrame(self, height=72, corner_radius=16)
        footer.grid(row=2, column=0, sticky="ew", padx=10, pady=(6, 10))
        footer.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)
        footer.grid_propagate(False)

        buttons = [
            ("Select Image", self.select_image, None),
            ("Enroll", self.show_enroll_panel, None),
            ("Authenticate", self.show_auth_panel, None),
            ("Delete User", self.show_delete_panel, "#B22222"),
            ("Show Users", self.show_users, None),
            ("Show Logs", self.show_logs, None),
        ]

        for i, (text, cmd, color) in enumerate(buttons):
            kwargs = {"text": text, "command": cmd, "height": 40}
            if color:
                kwargs["fg_color"] = color
                kwargs["hover_color"] = "#8B1A1A"

            btn = ctk.CTkButton(footer, **kwargs)
            btn.grid(row=0, column=i, padx=8, pady=14, sticky="ew")

    def _ask_master_password(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Master Password")
        dialog.geometry("420x220")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        x = self.winfo_x() + (self.winfo_width() - 420) // 2
        y = self.winfo_y() + (self.winfo_height() - 220) // 2
        dialog.geometry(f"420x220+{x}+{y}")

        dialog.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            dialog,
            text="Enter master password",
            font=ctk.CTkFont(size=20, weight="bold")
        ).grid(row=0, column=0, padx=20, pady=(25, 10), sticky="w")

        password_var = ctk.StringVar()
        entry = ctk.CTkEntry(dialog, textvariable=password_var, show="*")
        entry.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        entry.focus()

        ctk.CTkLabel(
            dialog,
            text="This password unlocks secret.key.enc",
            font=ctk.CTkFont(size=12)
        ).grid(row=2, column=0, padx=20, pady=(0, 10), sticky="w")

        def validate_password():
            password = password_var.get().strip()
            if not password:
                messagebox.showwarning("Warning", "Master password is required.", parent=dialog)
                return

            try:
                self.data_key = self.encryptor.ensure_data_key(password)
                self.set_status("Key unlocked")
                self.log("[INFO] Master key unlocked successfully")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=dialog)

        ctk.CTkButton(
            dialog,
            text="Unlock",
            command=validate_password,
            height=38
        ).grid(row=3, column=0, padx=20, pady=(5, 20), sticky="ew")

        self.wait_window(dialog)

        if self.data_key is None:
            self.destroy()

    def clear_dynamic_panel(self):
        for widget in self.dynamic_panel.winfo_children():
            widget.destroy()

    def show_default_action_panel(self):
        self.clear_dynamic_panel()

        ctk.CTkLabel(
            self.dynamic_panel,
            text="Choose an action from the bottom bar",
            font=ctk.CTkFont(size=15, weight="bold")
        ).grid(row=0, column=0, padx=10, pady=(16, 8), sticky="w")

        ctk.CTkLabel(
            self.dynamic_panel,
            text="Available actions:\n- Enroll\n- Authenticate\n- Delete User",
            justify="left",
            font=ctk.CTkFont(size=13)
        ).grid(row=1, column=0, padx=10, pady=(0, 16), sticky="w")

    def show_enroll_panel(self):
        self.clear_dynamic_panel()

        ctk.CTkLabel(
            self.dynamic_panel,
            text="Enroll User",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, padx=10, pady=(10, 6), sticky="w")

        self.enroll_username_var = ctk.StringVar()
        enroll_entry = ctk.CTkEntry(
            self.dynamic_panel,
            textvariable=self.enroll_username_var,
            placeholder_text="Enter username"
        )
        enroll_entry.grid(row=1, column=0, padx=10, pady=6, sticky="ew")

        ctk.CTkButton(
            self.dynamic_panel,
            text="Confirm Enroll",
            command=self.enroll_user_inline,
            height=36
        ).grid(row=2, column=0, padx=10, pady=(6, 10), sticky="ew")

    def show_auth_panel(self):
        self.clear_dynamic_panel()
        self.refresh_user_selectors()

        ctk.CTkLabel(
            self.dynamic_panel,
            text="Authenticate User",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, padx=10, pady=(10, 6), sticky="w")

        self.auth_user_var = ctk.StringVar(value=self.auth_names[0])
        ctk.CTkOptionMenu(
            self.dynamic_panel,
            values=self.auth_names,
            variable=self.auth_user_var
        ).grid(row=1, column=0, padx=10, pady=6, sticky="ew")

        ctk.CTkButton(
            self.dynamic_panel,
            text="Confirm Authentication",
            command=self.authenticate_user_inline,
            height=36
        ).grid(row=2, column=0, padx=10, pady=(6, 10), sticky="ew")

    def show_delete_panel(self):
        self.clear_dynamic_panel()
        self.refresh_user_selectors()

        ctk.CTkLabel(
            self.dynamic_panel,
            text="Delete User",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, padx=10, pady=(10, 6), sticky="w")

        self.delete_user_var = ctk.StringVar(value=self.auth_names[0])
        ctk.CTkOptionMenu(
            self.dynamic_panel,
            values=self.auth_names,
            variable=self.delete_user_var
        ).grid(row=1, column=0, padx=10, pady=6, sticky="ew")

        ctk.CTkButton(
            self.dynamic_panel,
            text="Confirm Delete",
            command=self.confirm_delete_selected_user,
            fg_color="#B22222",
            hover_color="#8B1A1A",
            height=36
        ).grid(row=2, column=0, padx=10, pady=(6, 10), sticky="ew")

    def log(self, text):
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")

    def set_status(self, text):
        self.status_var.set(text)

    def set_result(self, title, details):
        self.result_label.configure(text=title)
        self.result_details.configure(text=details)

    def set_info_text(self, text):
        self.image_info_box.configure(state="normal")
        self.image_info_box.delete("1.0", "end")
        self.image_info_box.insert("1.0", text)
        self.image_info_box.configure(state="disabled")

    def refresh_user_selectors(self):
        users = self.storage.list_users(self.data_key)
        names = [user[1] for user in users]
        if not names:
            names = ["No users"]
        self.auth_names = names

    def select_image(self):
        file_path = filedialog.askopenfilename(
            title="Select fingerprint image",
            filetypes=[
                ("Image files", "*.bmp *.BMP *.png *.PNG *.jpg *.jpeg *.tif *.tiff"),
                ("All files", "*.*")
            ]
        )

        if file_path:
            self.selected_image_path = file_path
            self.path_var.set(file_path)
            self.set_status("Image selected")
            self.log(f"[INFO] Image selected: {file_path}")

            self.show_main_selected_image(file_path)
            self.process_selected_image_automatically()

    def show_main_selected_image(self, path):
        try:
            pil_image = Image.open(path)
            ctk_img = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(340, 380))
            self.main_image_label.configure(image=ctk_img, text="")
            self.preview_images["main"] = ctk_img
        except Exception:
            self.main_image_label.configure(text="Preview error", image=None)

    def process_selected_image_automatically(self):
        if not self.selected_image_path:
            return

        try:
            template, minutiae_count = self.process_image(self.selected_image_path)
            self.current_template = template
            self.current_minutiae_count = minutiae_count
            self.current_template_length = len(template)

            self.set_info_text(
                f"Selected file:\n{self.selected_image_path}\n\n"
                f"Minutiae detected: {minutiae_count}\n"
                f"Template length: {len(template)}\n"
                f"Derived processing images updated automatically."
            )

            self.log("[INFO] Image processed automatically")
            self.set_status("Image processed")

        except Exception as e:
            self.log(f"[ERROR] Automatic processing failed: {e}")
            self.set_status("Processing failed")
            messagebox.showerror("Processing Error", str(e))

    def display_processing_images(self, images_dict):
        for filename, img_array in images_dict.items():
            label = self.stage_labels.get(filename)

            if label is not None:
                try:
                    pil_image = Image.fromarray(img_array)
                    ctk_img = ctk.CTkImage(
                        light_image=pil_image,
                        dark_image=pil_image,
                        size=(210, 130)
                    )
                    label.configure(image=ctk_img, text="")
                    self.preview_images[filename] = ctk_img
                except Exception:
                    label.configure(text="Preview error", image=None)

    def process_image(self, image_path):
        image = self.processor.load_image(image_path)
        enhanced = self.processor.normalize_contrast(image)
        segmented = self.processor.segment_fingerprint(enhanced)
        binary = self.processor.binarize(segmented)
        skeleton = self.processor.skeletonize(binary)
        minutiae = self.extractor.extract_features(skeleton)
        minutiae = self.extractor.filter_false_minutiae(minutiae)
        marked = self.extractor.draw_minutiae(skeleton, minutiae)

        template = self.generator.generate_template(minutiae, image=segmented)

        self.display_processing_images({
            "02_enhanced.png": enhanced,
            "03_segmented.png": segmented,
            "04_binary.png": binary,
            "05_skeleton.png": skeleton,
            "06_minutiae.png": marked,
        })

        return template, len(minutiae)

    def ensure_image_processed(self):
        if self.selected_image_path is None:
            messagebox.showwarning("Warning", "Please select a fingerprint image first.")
            return False

        if self.current_template is None:
            self.process_selected_image_automatically()

        return True

    def enroll_user_inline(self):
        if not self.ensure_image_processed():
            return

        username = self.enroll_username_var.get().strip()
        if not username:
            messagebox.showwarning("Warning", "Please enter a username.")
            return

        try:
            self.set_status("Enrollment running")
            self.log(f"[ENROLL] Username: {username}")

            template = self.current_template
            minutiae_count = self.current_minutiae_count
            template_len = self.current_template_length

            candidates = {}
            all_templates = self.storage.get_all_templates(self.data_key)
            for existing_username, encrypted_blob in all_templates:
                stored_template = self.encryptor.decrypt_template(encrypted_blob, self.data_key)
                candidates[existing_username] = stored_template

            is_duplicate, matched_user, distance = self.authenticator.is_duplicate_fingerprint(
                template,
                candidates
            )

            if is_duplicate:
                self.storage.log_event(
                    event_type="enrollment",
                    data_key=self.data_key,
                    user_id=None,
                    success=False,
                    details=f"Échec: empreinte déjà utilisée, distance={distance:.6f}"
                )

                self.set_status("Duplicate fingerprint")
                self.set_result(
                    "Enrollment Refused",
                    f"Duplicate owner: {matched_user}\nDistance: {distance:.6f}\nMinutiae: {minutiae_count}"
                )
                self.set_info_text(
                    f"Selected file:\n{self.selected_image_path}\n\n"
                    f"Minutiae detected: {minutiae_count}\n"
                    f"Template length: {template_len}\n"
                    f"Duplicate fingerprint detected.\n"
                    f"Existing owner: {matched_user}\n"
                    f"Distance: {distance:.6f}"
                )
                self.log(f"[ENROLL] Duplicate fingerprint detected -> owner: {matched_user}")
                messagebox.showerror("Duplicate Fingerprint", f"This fingerprint already belongs to '{matched_user}'.")
                self.show_default_action_panel()
                return

            encrypted_template = self.encryptor.encrypt_template(template, self.data_key)
            user_id = self.storage.enroll_user(username, encrypted_template, self.data_key)

            self.refresh_user_selectors()
            self.set_status("Enrollment successful")
            self.set_result(
                "Enrollment Success",
                f"User ID: {user_id}\nTemplate: {template_len}\nMinutiae: {minutiae_count}"
            )
            self.set_info_text(
                f"Selected file:\n{self.selected_image_path}\n\n"
                f"Username: {username}\n"
                f"Minutiae detected: {minutiae_count}\n"
                f"Template length: {template_len}\n"
                f"Enrollment successful."
            )
            self.log(f"[ENROLL] Success -> user '{username}' enrolled with id {user_id}")
            messagebox.showinfo("Success", f"User '{username}' enrolled successfully.")
            self.show_default_action_panel()

        except ValueError as e:
            self.set_status("Enrollment failed")
            self.log(f"[ENROLL] Error: {e}")
            messagebox.showerror("Enrollment Error", str(e))
            self.show_default_action_panel()
        except Exception as e:
            self.set_status("Enrollment failed")
            self.log(f"[ENROLL] Unexpected error: {e}")
            messagebox.showerror("Enrollment Error", str(e))
            self.show_default_action_panel()

    def authenticate_user_inline(self):
        if not self.ensure_image_processed():
            return

        username = self.auth_user_var.get().strip()
        if not username or username == "No users":
            messagebox.showwarning("Warning", "Please select a valid user.")
            return

        try:
            self.set_status("Authentication running")
            self.log(f"[AUTH] Username: {username}")

            query_template = self.current_template
            minutiae_count = self.current_minutiae_count
            template_len = self.current_template_length

            stored_blob = self.storage.get_template_by_username(username)
            if stored_blob is None:
                self.set_status("User not found")
                self.set_result("Authentication Failed", "User not found in database")
                self.set_info_text(
                    f"Selected file:\n{self.selected_image_path}\n\n"
                    f"Username: {username}\n"
                    f"User not found in database."
                )
                self.log(f"[AUTH] No template found for '{username}'")
                messagebox.showerror("Authentication Error", f"User '{username}' not found.")
                self.show_default_action_panel()
                return

            stored_template = self.encryptor.decrypt_template(stored_blob, self.data_key)
            success, distance = self.authenticator.authenticate(query_template, stored_template)

            user_info = self.storage.get_user_by_username(username)
            uid = user_info[0] if user_info else None

            if success:
                if uid is not None:
                    self.storage.update_last_authenticated(uid, self.data_key)
                self.storage.log_event(
                    event_type="authentication",
                    data_key=self.data_key,
                    user_id=uid,
                    success=True,
                    details="Authentification réussie"
                )

                self.set_status("Authentication success")
                self.set_result(
                    "Authentication Success",
                    f"Username: {username}\nDistance: {distance:.6f}\nThreshold: {self.authenticator.threshold}"
                )
                self.set_info_text(
                    f"Selected file:\n{self.selected_image_path}\n\n"
                    f"Username: {username}\n"
                    f"Minutiae detected: {minutiae_count}\n"
                    f"Template length: {template_len}\n"
                    f"Distance: {distance:.6f}\n"
                    f"Decision: ACCEPTED"
                )
                self.log(f"[AUTH] Success -> distance {distance:.6f}")
                messagebox.showinfo("Authentication", f"Authentication successful for '{username}'.")
            else:
                self.storage.log_event(
                    event_type="authentication",
                    data_key=self.data_key,
                    user_id=uid,
                    success=False,
                    details="Authentification échouée"
                )

                self.set_status("Authentication failed")
                self.set_result(
                    "Authentication Failed",
                    f"Username: {username}\nDistance: {distance:.6f}\nThreshold: {self.authenticator.threshold}"
                )
                self.set_info_text(
                    f"Selected file:\n{self.selected_image_path}\n\n"
                    f"Username: {username}\n"
                    f"Minutiae detected: {minutiae_count}\n"
                    f"Template length: {template_len}\n"
                    f"Distance: {distance:.6f}\n"
                    f"Decision: REJECTED"
                )
                self.log(f"[AUTH] Failed -> distance {distance:.6f}")
                messagebox.showwarning("Authentication", f"Authentication failed for '{username}'.")

            self.show_default_action_panel()

        except Exception as e:
            self.set_status("Authentication failed")
            self.log(f"[AUTH] Error: {e}")
            messagebox.showerror("Authentication Error", str(e))
            self.show_default_action_panel()

    def confirm_delete_selected_user(self):
        username = self.delete_user_var.get().strip()
        if not username or username == "No users":
            messagebox.showwarning("Delete User", "Please select a valid user.")
            return

        confirm = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to delete '{username}'?"
        )
        if not confirm:
            self.show_default_action_panel()
            return

        try:
            deleted = self.storage.delete_user(username, self.data_key)
            if deleted:
                self.set_status("User deleted")
                self.set_result("Deletion Success", f"User '{username}' deleted successfully")
                self.log(f"[DELETE] User '{username}' deleted")
                messagebox.showinfo("Delete User", f"User '{username}' deleted successfully.")
            else:
                self.set_status("User not found")
                self.set_result("Deletion Failed", f"User '{username}' not found")
                self.log(f"[DELETE] User '{username}' not found")
                messagebox.showwarning("Delete User", f"User '{username}' not found.")

            self.refresh_user_selectors()
            self.show_default_action_panel()

        except Exception as e:
            self.set_status("Delete failed")
            self.log(f"[DELETE] Error: {e}")
            messagebox.showerror("Delete Error", str(e))
            self.show_default_action_panel()

    def show_users(self):
        users = self.storage.list_users(self.data_key)
        names = [user[1] for user in users]

        self.log("[USERS] Registered users:")
        if not names:
            self.log("No users found.")
            self.set_result("Users", "No users found")
            return

        text = "\n".join(names)
        for name in names:
            self.log(name)

        self.set_result("Users List", text)

    def show_logs(self):
        logs = self.storage.list_audit_logs(self.data_key)
        self.log("[LOGS] Audit log:")
        if not logs:
            self.log("No logs found.")
            self.set_result("Logs", "No logs found")
            return

        preview = ""
        for entry in logs[-8:]:
            self.log(str(entry))
            preview += f"{entry}\n"

        self.set_result("Latest Logs", preview.strip())
