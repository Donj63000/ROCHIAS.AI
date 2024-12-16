import tkinter as tk
from tkinter import messagebox
import importlib
import sys
import os
from PIL import Image, ImageTk

class MainApplication(tk.Tk):
    """
    Application principale du logiciel ROCHIAS Pod Calculator.
    Gère la navigation entre les différents modules.
    """
    def __init__(self):
        super().__init__()
        self.title("Logiciel ROCHIAS Pod Calculator")
        self.geometry("1200x800")
        self.configure(bg="#2B2B2B")  # Couleur de fond sombre

        # Ajout d'un attribut pour gérer le plein écran
        self.fullscreen = False

        # Préparer le chemin du dossier MODULES
        self.setup_modules_path()

        # Configuration de la grille principale
        self.setup_main_layout()

        # Configuration du logo
        self.setup_logo()

        # Liste des modules disponibles :
        # Le bouton "STOCK" lance "production"
        # Le bouton "PRODUCTION" lance "jeu"
        self.module_buttons = [
            ("VISA", "visa", "#FFD700"),
            ("STOCK", "production", "#4e4e4e"),
            ("PRODUCTION", "jeu", "#FF69B4"),
            ("MAINTENANCE", "maintenance", "#1E90FF"),
            ("IA", "ia", "#32CD32")  # Ancien module IA
        ]

        # Créer les boutons de navigation
        self.create_nav_buttons()

        # Cadre de contenu
        self.content_frame = tk.Frame(self, bg="#2B2B2B")
        self.content_frame.grid(row=1, column=1, sticky="nsew")

        # Dictionnaire pour stocker les frames des modules
        self.modules_frames = {}

        # Binding pour le plein écran (Alt+Entrée)
        self.bind("<Alt-Return>", self.toggle_fullscreen)

    def setup_modules_path(self):
        """
        Configure le chemin du répertoire MODULES et s'assure qu'il est reconnu comme un package Python.
        """
        modules_path = os.path.join(os.path.dirname(__file__), 'MODULES')
        if modules_path not in sys.path:
            sys.path.append(modules_path)

        # Assurer que MODULES est un package
        init_file = os.path.join(modules_path, '__init__.py')
        if not os.path.exists(init_file):
            open(init_file, 'a').close()

    def setup_main_layout(self):
        """
        Met en place la grille principale et le cadre de navigation.
        """
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        self.nav_frame = tk.Frame(self, bg="#2B2B2B", width=200)
        self.nav_frame.grid(row=1, column=0, sticky="ns")
        self.nav_frame.grid_propagate(False)

    def setup_logo(self):
        """
        Charge et affiche le logo dans la barre de navigation.
        """
        try:
            logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
            if not os.path.exists(logo_path):
                raise FileNotFoundError(f"Logo introuvable : {logo_path}")

            logo_image = Image.open(logo_path)
            logo_image = logo_image.resize((80, 80), Image.LANCZOS)
            self.logo_photo = ImageTk.PhotoImage(logo_image)

            logo_label = tk.Label(self.nav_frame, image=self.logo_photo, bg="#2B2B2B")
            logo_label.pack(pady=20)
        except Exception as e:
            messagebox.showerror("Erreur de logo", f"Impossible de charger le logo.\n\n{e}")

    def create_nav_buttons(self):
        """
        Crée les boutons de navigation pour accéder aux différents modules.
        """
        button_font = ("Helvetica", 10, "bold")
        button_fg = "white"
        button_active_bg = "#6e6e6e"

        for label, module_name, bg_color in self.module_buttons:
            self.create_nav_button(label, module_name, bg_color, button_font, button_fg, button_active_bg)

    def create_nav_button(self, label, module_name, bg_color, font, fg, active_bg):
        """
        Crée un bouton de navigation et applique les effets de survol.
        """
        button = tk.Button(
            self.nav_frame,
            text=label,
            command=lambda name=module_name: self.switch_module(name),
            bg=bg_color,
            fg=fg,
            activebackground=active_bg,
            font=font,
            relief="flat",
            padx=10,
            pady=5,
            bd=0,
            highlightthickness=0
        )
        button.pack(fill='x', padx=20, pady=5)

        # Effets de survol (hover)
        def on_enter(e, b=button):
            b.config(bg=active_bg)

        def on_leave(e, b=button, color=bg_color):
            b.config(bg=color)

        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)

    def switch_module(self, module_name):
        """
        Affiche le module sélectionné dans la zone de contenu.
        Si le module n'est pas déjà chargé, l'importe et crée le frame.
        """
        # Cacher tous les cadres actuels
        for frame in self.content_frame.winfo_children():
            frame.pack_forget()

        if module_name in self.modules_frames:
            # Afficher le module déjà chargé
            frame = self.modules_frames[module_name]
            frame.pack(fill='both', expand=True)
        else:
            # Tenter de charger le module
            try:
                module = importlib.import_module(module_name)
                frame = module.get_frame(self.content_frame, self)

                # Stocker le frame pour ne pas recharger le module plus tard
                self.modules_frames[module_name] = frame
                frame.pack(fill='both', expand=True)
            except ImportError as e:
                messagebox.showerror("Erreur", f"Impossible de charger le module '{module_name}'.\n\n{e}")
            except AttributeError:
                messagebox.showerror("Erreur", f"Le module '{module_name}' ne contient pas de fonction 'get_frame'.")
            except Exception as e:
                messagebox.showerror("Erreur", f"Une erreur est survenue lors du chargement du module '{module_name}'.\n\n{e}")

    def toggle_fullscreen(self, event=None):
        """
        Bascule l'état du plein écran lorsque Alt+Entrée est pressé.
        """
        self.fullscreen = not self.fullscreen
        self.attributes("-fullscreen", self.fullscreen)
        # Si on sort du plein écran, on peut forcer un redimensionnement
        if not self.fullscreen:
            self.geometry("1200x800")

if __name__ == "__main__":
    app = MainApplication()
    app.mainloop()
