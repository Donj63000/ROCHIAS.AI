import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

THEME = {
    'bg_main': '#2B2B2B',
    'bg_section': '#2B2B2B',
    'fg_text': 'white',
    'highlight': '#6e6e6e',
    'button_bg': '#6e6e6e',
    'button_fg': 'white',
    'accent': '#FFA500',
    'accent2': '#007ACC',
    'title_font': ("Helvetica", 14, "bold"),
    'label_font': ("Helvetica", 10),
    'entry_font': ("Helvetica", 10),
    'text_bg': '#3C3F41'
}

def create_thematic_frame(parent, title=None, theme=THEME):
    if title:
        frame = tk.LabelFrame(parent, text=title, bg=theme['bg_section'], fg='white', font=theme['title_font'])
    else:
        frame = tk.Frame(parent, bg=theme['bg_section'])
    return frame

class IAMenuFrame(tk.Frame):
    """
    Ce frame représente le menu IA.
    Il permet de choisir entre "Utiliser l'IA" et "Entraîner l'IA".
    """
    def __init__(self, parent, main_app):
        super().__init__(parent, bg=THEME['bg_main'])
        self.main_app = main_app
        self.setup_ui()

    def setup_ui(self):
        # Cadre principal
        menu_frame = create_thematic_frame(self, "Menu IA")
        menu_frame.pack(padx=10, pady=10, fill='both', expand=True)

        tk.Label(menu_frame, text="Que souhaitez-vous faire ?", bg=THEME['bg_section'], fg='white').pack(pady=10)

        # Bouton pour utiliser l'IA (chargera use_ia)
        tk.Button(menu_frame, text="Utiliser l'IA", bg=THEME['accent'], fg='white',
                  command=lambda: self.main_app.switch_module("use_ia")).pack(pady=10, fill='x', padx=20)

        # Bouton pour entraîner l'IA (chargera train_ia)
        tk.Button(menu_frame, text="Entraîner/Evaluer l'IA", bg=THEME['accent2'], fg='white',
                  command=lambda: self.main_app.switch_module("train_ia")).pack(pady=10, fill='x', padx=20)

        # Vous pouvez ajouter d'autres boutons ou infos si nécessaire

def get_frame(parent, main_app):
    """
    Fonction appelée par main.py pour charger le module 'ia'.
    Elle doit retourner un Frame prêt à être affiché dans content_frame.
    """
    return IAMenuFrame(parent, main_app)
