# MODULES/qualite.py

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import sys
import os
import pickle
import importlib

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
except ImportError:
    # Si reportlab n'est pas installé, le code d'export PDF signalera une erreur lors de l'export.
    pass


def get_frame(parent_frame, controller):
    bg_color = '#2B2B2B'
    if hasattr(controller, 'colors') and 'bg' in controller.colors:
        bg_color = controller.colors['bg']

    frame = tk.Frame(parent_frame, bg=bg_color)
    app = QualiteModule(frame, controller)
    return frame


class QualiteModule:
    def __init__(self, parent, controller):
        self.parent = parent
        self.controller = controller
        self.colors = getattr(controller, 'colors', self.default_colors())

        # Variables pour les informations générales
        self.date_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        self.heure_var = tk.StringVar(value=datetime.now().strftime('%H:%M'))
        self.poste_var = tk.StringVar(value="Matin")
        self.chef_equipe_var = tk.StringVar()

        # Variables OUI/NON
        self.floconneuse_var = tk.StringVar(value="OUI")
        self.descentes_var = tk.StringVar(value="OUI")
        self.mateau_var = tk.StringVar(value="OUI")
        self.urshell_var = tk.StringVar(value="OUI")
        self.microniseur_var = tk.StringVar(value="OUI")

        # Test séparateur magnétique
        self.test_sep_magnetique_hours = [tk.StringVar() for _ in range(3)]
        self.test_sep_magnetique_results = [tk.StringVar(value="OUI") for _ in range(3)]

        # Test DPM
        self.test_dpm_debut_var = tk.StringVar(value="OUI")
        self.test_dpm_fin_var = tk.StringVar(value="OUI")

        # Inventaire matériel
        self.materiel_debut_var = tk.StringVar(value="OUI")
        self.materiel_fin_var = tk.StringVar(value="OUI")
        self.materiel_manquant_var = tk.StringVar()

        # Contrôle bris de verre
        self.bris_de_verre_var = tk.StringVar(value="OUI")
        self.bris_de_verre_defaut_var = tk.StringVar()

        # Numéros de lot (Sacs)
        self.lot_bleus_var = tk.StringVar()
        self.lot_rouges_var = tk.StringVar()
        self.lot_verts_var = tk.StringVar()

        # Non-conformités (global)
        self.all_non_conformities = self.load_non_conformities()

        # Non-conformités associées à l'enregistrement actuel
        self.non_conformities = []

        # Variables non-conformité temporaire
        self.nc_detectee_par_var = tk.StringVar()
        self.nc_datetime_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d %H:%M'))
        self.nc_lot_var = tk.StringVar()
        self.nc_description_var = tk.StringVar()
        self.nc_action_corrective_prise_var = tk.StringVar(value="NON")
        self.nc_action_corrective_var = tk.StringVar()
        self.nc_necessite_qualite_var = tk.StringVar(value="NON")

        # Liste des enregistrements qualité
        self.enregistrements = self.load_enregistrements()

        # Pour le clignotement du bouton Valider
        self.blink_colors = ["red", "blue", "green", "yellow", "orange", "purple", "pink", "cyan"]
        self.blink_index = 0

        self.setup_ui()

    def default_colors(self):
        return {
            'bg': '#2B2B2B',
            'fg': 'white',
            'button_bg': '#4CAF50',
            'button_fg': 'white',
            'entry_bg': 'white',
            'entry_fg': 'black',
            'label_fg': 'white',
            'tree_bg': '#D3D3D3',
            'tree_fg': 'black',
            'tree_field_bg': '#D3D3D3',
            'tree_selected_bg': '#347083',
        }

    def setup_ui(self):
        main_frame = tk.Frame(self.parent, bg=self.colors['bg'])
        main_frame.pack(fill='both', expand=True)

        # Canvas + scrollbar
        self.canvas = tk.Canvas(main_frame, bg=self.colors['bg'], highlightthickness=0)
        self.scrollbar = tk.Scrollbar(main_frame, orient="vertical", command=self.canvas.yview)
        scrollable_frame = tk.Frame(self.canvas, bg=self.colors['bg'])

        scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.config(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Ajout du binding pour la molette de la souris (tous systèmes)
        scrollable_frame.bind("<Enter>", self._bind_mousewheel)
        scrollable_frame.bind("<Leave>", self._unbind_mousewheel)

        # Titre
        title_label = tk.Label(scrollable_frame, text="QUALITE ROCHIAS", bg=self.colors['bg'],
                               fg=self.colors['fg'], font=('Arial', 14, 'bold'))
        title_label.pack(pady=10)

        # Informations générales
        info_frame = tk.LabelFrame(scrollable_frame, text="Informations Générales", bg=self.colors['bg'],
                                   fg=self.colors['fg'], font=('Arial', 12, 'bold'))
        info_frame.pack(fill='x', padx=10, pady=5)

        # Date
        row = 0
        tk.Label(info_frame, text="Date :", bg=self.colors['bg'], fg=self.colors['fg']).grid(row=row, column=0,
                                                                                             sticky='e', padx=5, pady=5)
        tk.Entry(info_frame, textvariable=self.date_var, bg=self.colors['entry_bg'],
                 fg=self.colors['entry_fg']).grid(row=row, column=1, padx=5, pady=5)

        # Heure
        row += 1
        tk.Label(info_frame, text="Heure :", bg=self.colors['bg'], fg=self.colors['fg']).grid(row=row, column=0,
                                                                                              sticky='e', padx=5,
                                                                                              pady=5)
        tk.Entry(info_frame, textvariable=self.heure_var, bg=self.colors['entry_bg'],
                 fg=self.colors['entry_fg']).grid(row=row, column=1, padx=5, pady=5)

        # Poste
        row += 1
        tk.Label(info_frame, text="Poste :", bg=self.colors['bg'], fg=self.colors['fg']).grid(row=row, column=0,
                                                                                              sticky='e', padx=5,
                                                                                              pady=5)
        poste_frame = tk.Frame(info_frame, bg=self.colors['bg'])
        poste_frame.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        for poste in ["Matin", "Après-midi", "Nuit", "Journée"]:
            tk.Radiobutton(poste_frame, text=poste, variable=self.poste_var, value=poste,
                           bg=self.colors['bg'], fg=self.colors['fg'], selectcolor=self.colors['bg'],
                           activebackground=self.colors['bg'], activeforeground=self.colors['fg']).pack(side='left',
                                                                                                        padx=5)

        # Chef d'équipe
        row += 1
        tk.Label(info_frame, text="Chef d'équipe :", bg=self.colors['bg'], fg=self.colors['fg']).grid(row=row, column=0,
                                                                                                      sticky='e',
                                                                                                      padx=5, pady=5)
        tk.Entry(info_frame, textvariable=self.chef_equipe_var, bg=self.colors['entry_bg'],
                 fg=self.colors['entry_fg']).grid(row=row, column=1, padx=5, pady=5)

        # Numéros de lot des sacs
        lot_frame = tk.LabelFrame(scrollable_frame, text="Numéros de lot des sacs", bg=self.colors['bg'],
                                  fg=self.colors['fg'], font=('Arial', 12, 'bold'))
        lot_frame.pack(fill='x', padx=10, pady=5)

        tk.Label(lot_frame, text="Numéro de lot des sacs bleus :", bg=self.colors['bg'], fg=self.colors['fg']).grid(
            row=0, column=0, sticky='e', padx=5, pady=5)
        tk.Entry(lot_frame, textvariable=self.lot_bleus_var, bg=self.colors['entry_bg'],
                 fg=self.colors['entry_fg']).grid(row=0, column=1, padx=5, pady=5)

        tk.Label(lot_frame, text="Numéro de lot des sacs rouges :", bg=self.colors['bg'], fg=self.colors['fg']).grid(
            row=1, column=0, sticky='e', padx=5, pady=5)
        tk.Entry(lot_frame, textvariable=self.lot_rouges_var, bg=self.colors['entry_bg'],
                 fg=self.colors['entry_fg']).grid(row=1, column=1, padx=5, pady=5)

        tk.Label(lot_frame, text="Numéro de lot des sacs verts :", bg=self.colors['bg'], fg=self.colors['fg']).grid(
            row=2, column=0, sticky='e', padx=5, pady=5)
        tk.Entry(lot_frame, textvariable=self.lot_verts_var, bg=self.colors['entry_bg'],
                 fg=self.colors['entry_fg']).grid(row=2, column=1, padx=5, pady=5)

        # Contrôle des aimants
        aimants_frame = tk.LabelFrame(scrollable_frame, text="Contrôle des aimants", bg=self.colors['bg'],
                                      fg=self.colors['fg'], font=('Arial', 12, 'bold'))
        aimants_frame.pack(fill='x', padx=10, pady=5)
        self.create_oui_non_field(aimants_frame, "FLoconneuse :", self.floconneuse_var)
        self.create_oui_non_field(aimants_frame, "Descentes :", self.descentes_var)
        self.create_oui_non_field(aimants_frame, "Mateau (broyeur) :", self.mateau_var)
        self.create_oui_non_field(aimants_frame, "Urshell (Broyeur) :", self.urshell_var)
        self.create_oui_non_field(aimants_frame, "Microniseur (Broyeur) :", self.microniseur_var)

        # Test Séparateur Magnétique
        sep_frame = tk.LabelFrame(scrollable_frame, text="Test Séparateur Magnétique (3 fois par poste)",
                                  bg=self.colors['bg'], fg=self.colors['fg'], font=('Arial', 12, 'bold'))
        sep_frame.pack(fill='x', padx=10, pady=5)
        for i in range(3):
            test_row = tk.Frame(sep_frame, bg=self.colors['bg'])
            test_row.pack(fill='x', pady=5)
            tk.Label(test_row, text=f"Heure du test n°{i + 1} :", bg=self.colors['bg'], fg=self.colors['fg']).pack(
                side='left', padx=5)
            tk.Entry(test_row, textvariable=self.test_sep_magnetique_hours[i], bg=self.colors['entry_bg'],
                     fg=self.colors['entry_fg']).pack(side='left', padx=5)
            tk.Label(test_row, text="Trappe fonctionne correctement ? ", bg=self.colors['bg'],
                     fg=self.colors['fg']).pack(side='left', padx=5)
            self.create_oui_non_radiobuttons(test_row, self.test_sep_magnetique_results[i])

        # Test DPM
        dpm_frame = tk.LabelFrame(scrollable_frame, text="Test Détecteur de Particules Métalliques (DPM)",
                                  bg=self.colors['bg'], fg=self.colors['fg'], font=('Arial', 12, 'bold'))
        dpm_frame.pack(fill='x', padx=10, pady=5)
        self.create_oui_non_field(dpm_frame, "TEST DPM Début de poste réussi ?", self.test_dpm_debut_var)
        self.create_oui_non_field(dpm_frame, "TEST DPM Fin de poste réussi ?", self.test_dpm_fin_var)

        # Inventaire matériel
        inv_frame = tk.LabelFrame(scrollable_frame, text="Inventaire du matériel", bg=self.colors['bg'],
                                  fg=self.colors['fg'], font=('Arial', 12, 'bold'))
        inv_frame.pack(fill='x', padx=10, pady=5)
        self.create_oui_non_field(inv_frame, "Tout le matériel est présent en début de poste ?", self.materiel_debut_var)
        self.create_oui_non_field(inv_frame, "Tout le matériel est présent en fin de poste ?", self.materiel_fin_var)
        inv_missing_frame = tk.Frame(inv_frame, bg=self.colors['bg'])
        inv_missing_frame.pack(fill='x', pady=5)
        tk.Label(inv_missing_frame, text="Si non, que manque-t-il ?", bg=self.colors['bg'], fg=self.colors['fg']).pack(
            side='left', padx=5)
        tk.Entry(inv_missing_frame, textvariable=self.materiel_manquant_var, bg=self.colors['entry_bg'],
                 fg=self.colors['entry_fg']).pack(side='left', padx=5, fill='x', expand=True)

        # Contrôle bris de verre
        bris_frame = tk.LabelFrame(scrollable_frame, text="Contrôle bris de verre", bg=self.colors['bg'],
                                   fg=self.colors['fg'], font=('Arial', 12, 'bold'))
        bris_frame.pack(fill='x', padx=10, pady=5)
        self.create_oui_non_field(bris_frame, "Tout le matériel de la liste bris de verre est conforme ?",
                                  self.bris_de_verre_var)
        defaut_frame = tk.Frame(bris_frame, bg=self.colors['bg'])
        defaut_frame.pack(fill='x', pady=5)
        tk.Label(defaut_frame, text="Si non, quel élément est défaillant ?", bg=self.colors['bg'],
                 fg=self.colors['fg']).pack(side='left', padx=5)
        tk.Entry(defaut_frame, textvariable=self.bris_de_verre_defaut_var, bg=self.colors['entry_bg'],
                 fg=self.colors['entry_fg']).pack(side='left', padx=5, fill='x', expand=True)

        # Boutons de validation et autres
        button_frame = tk.Frame(scrollable_frame, bg=self.colors['bg'])
        button_frame.pack(fill='x', pady=10)

        # Bouton non-conformité
        nc_button = tk.Button(button_frame, text="SIGNALER NON CONFORMITE", bg='red', fg='white',
                              command=self.open_nc_window)
        nc_button.pack(side='left', padx=5)

        # Bouton valider (clignotant)
        self.valider_button = tk.Button(button_frame, text="Valider", bg=self.colors['button_bg'],
                                        fg=self.colors['button_fg'], command=self.save_enregistrement)
        self.valider_button.pack(side='left', padx=5)
        self.blink_button()  # Lancer le clignotement du bouton

        # Bouton liste enregistrements
        liste_button = tk.Button(button_frame, text="Liste enregistrements qualité", bg=self.colors['button_bg'],
                                 fg=self.colors['button_fg'], command=self.show_all_enregistrements)
        liste_button.pack(side='left', padx=5)

        # Bouton liste non-conformités
        liste_nc_button = tk.Button(button_frame, text="Liste des non conformitées", bg=self.colors['button_bg'],
                                    fg=self.colors['button_fg'], command=self.show_all_non_conformities)
        liste_nc_button.pack(side='left', padx=5)

    def blink_button(self):
        # Changer la couleur du bouton Valider périodiquement
        self.valider_button.config(bg=self.blink_colors[self.blink_index])
        self.blink_index = (self.blink_index + 1) % len(self.blink_colors)
        self.parent.after(500, self.blink_button)  # Change toutes les 500 ms

    def _bind_mousewheel(self, event):
        # Sur Windows
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)
        # Sur Linux
        self.canvas.bind_all("<Button-4>", self.on_mousewheel_linux)
        self.canvas.bind_all("<Button-5>", self.on_mousewheel_linux)

    def _unbind_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_mousewheel_linux(self, event):
        if event.num == 4:  # Molette vers le haut
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:  # Molette vers le bas
            self.canvas.yview_scroll(1, "units")

    def create_oui_non_field(self, parent, label_text, var):
        frame = tk.Frame(parent, bg=self.colors['bg'])
        frame.pack(fill='x', pady=5)
        tk.Label(frame, text=label_text, bg=self.colors['bg'], fg=self.colors['fg']).pack(side='left', padx=5)
        self.create_oui_non_radiobuttons(frame, var)

    def create_oui_non_radiobuttons(self, parent, var):
        tk.Radiobutton(parent, text="OUI", variable=var, value="OUI",
                       bg=self.colors['bg'], fg='green', selectcolor=self.colors['bg'],
                       activebackground=self.colors['bg'], activeforeground='green').pack(side='left', padx=5)
        tk.Radiobutton(parent, text="NON", variable=var, value="NON",
                       bg=self.colors['bg'], fg='red', selectcolor=self.colors['bg'],
                       activebackground=self.colors['bg'], activeforeground='red').pack(side='left', padx=5)

    def open_nc_window(self):
        nc_win = tk.Toplevel(self.parent)
        nc_win.title("Signaler une non-conformité")
        nc_win.configure(bg=self.colors['bg'])

        tk.Label(nc_win, text="Non conformité détectée par :", bg=self.colors['bg'], fg=self.colors['fg']).grid(row=0,
                                                                                                                column=0,
                                                                                                                sticky='e',
                                                                                                                padx=5,
                                                                                                                pady=5)
        tk.Entry(nc_win, textvariable=self.nc_detectee_par_var, bg=self.colors['entry_bg'],
                 fg=self.colors['entry_fg']).grid(row=0, column=1, padx=5, pady=5)

        tk.Label(nc_win, text="Heure / date de la non conformité :", bg=self.colors['bg'],
                 fg=self.colors['fg']).grid(row=1, column=0, sticky='e', padx=5, pady=5)
        tk.Entry(nc_win, textvariable=self.nc_datetime_var, bg=self.colors['entry_bg'],
                 fg=self.colors['entry_fg']).grid(row=1, column=1, padx=5, pady=5)

        tk.Label(nc_win, text="Numéro de lot :", bg=self.colors['bg'], fg=self.colors['fg']).grid(row=2, column=0,
                                                                                                  sticky='e', padx=5,
                                                                                                  pady=5)
        tk.Entry(nc_win, textvariable=self.nc_lot_var, bg=self.colors['entry_bg'],
                 fg=self.colors['entry_fg']).grid(row=2, column=1, padx=5, pady=5)

        tk.Label(nc_win, text="Description détaillée :", bg=self.colors['bg'], fg=self.colors['fg']).grid(row=3,
                                                                                                          column=0,
                                                                                                          sticky='ne',
                                                                                                          padx=5,
                                                                                                          pady=5)
        desc_text = tk.Text(nc_win, width=40, height=5, bg=self.colors['entry_bg'], fg=self.colors['entry_fg'])
        desc_text.grid(row=3, column=1, padx=5, pady=5)

        def save_description(*args):
            self.nc_description_var.set(desc_text.get("1.0", tk.END).strip())

        desc_text.bind("<FocusOut>", save_description)

        tk.Label(nc_win, text="Une action corrective a-t-elle été prise ?", bg=self.colors['bg'],
                 fg=self.colors['fg']).grid(row=4, column=0, sticky='e', padx=5, pady=5)
        action_frame = tk.Frame(nc_win, bg=self.colors['bg'])
        action_frame.grid(row=4, column=1, padx=5, pady=5, sticky='w')
        self.create_oui_non_radiobuttons(action_frame, self.nc_action_corrective_prise_var)

        tk.Label(nc_win, text="Si oui, laquelle ?", bg=self.colors['bg'], fg=self.colors['fg']).grid(row=5, column=0,
                                                                                                     sticky='e', padx=5,
                                                                                                     pady=5)
        tk.Entry(nc_win, textvariable=self.nc_action_corrective_var, bg=self.colors['entry_bg'],
                 fg=self.colors['entry_fg']).grid(row=5, column=1, padx=5, pady=5)

        tk.Label(nc_win, text="Nécessite intervention du service qualité ?", bg=self.colors['bg'],
                 fg=self.colors['fg']).grid(row=6, column=0, sticky='e', padx=5, pady=5)
        qual_frame = tk.Frame(nc_win, bg=self.colors['bg'])
        qual_frame.grid(row=6, column=1, padx=5, pady=5, sticky='w')
        self.nc_necessite_qualite_var.set("NON")
        self.create_oui_non_radiobuttons(qual_frame, self.nc_necessite_qualite_var)

        btn_frame = tk.Frame(nc_win, bg=self.colors['bg'])
        btn_frame.grid(row=7, column=0, columnspan=2, pady=10)

        tk.Button(btn_frame, text="Valider", bg=self.colors['button_bg'], fg=self.colors['button_fg'],
                  command=lambda: self.save_nc(nc_win, desc_text)).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Annuler", bg=self.colors['button_bg'], fg=self.colors['button_fg'],
                  command=nc_win.destroy).pack(side='left', padx=5)

    def save_nc(self, nc_win, desc_text):
        self.nc_description_var.set(desc_text.get("1.0", tk.END).strip())

        nc_data = {
            'detectee_par': self.nc_detectee_par_var.get(),
            'datetime': self.nc_datetime_var.get(),
            'lot': self.nc_lot_var.get(),
            'description': self.nc_description_var.get(),
            'action_corrective_prise': self.nc_action_corrective_prise_var.get(),
            'action_corrective_detail': self.nc_action_corrective_var.get(),
            'necessite_qualite': self.nc_necessite_qualite_var.get(),
            'cloturee': "NON" if self.nc_necessite_qualite_var.get() == "OUI" else "OUI"
        }

        self.non_conformities.append(nc_data)
        self.all_non_conformities.append(nc_data)
        self.save_non_conformities()

        messagebox.showinfo("Non-conformité", "Non-conformité enregistrée avec succès.")

        self.nc_detectee_par_var.set("")
        self.nc_datetime_var.set(datetime.now().strftime('%Y-%m-%d %H:%M'))
        self.nc_lot_var.set("")
        self.nc_description_var.set("")
        self.nc_action_corrective_var.set("")
        self.nc_action_corrective_prise_var.set("NON")
        self.nc_necessite_qualite_var.set("NON")

        nc_win.destroy()

    def save_enregistrement(self):
        data = {
            'date': self.date_var.get(),
            'heure': self.heure_var.get(),
            'poste': self.poste_var.get(),
            'chef_equipe': self.chef_equipe_var.get(),
            'aimants': {
                'floconneuse': self.floconneuse_var.get(),
                'descentes': self.descentes_var.get(),
                'mateau': self.mateau_var.get(),
                'urshell': self.urshell_var.get(),
                'microniseur': self.microniseur_var.get()
            },
            'sep_magnetique': [
                {
                    'heure_test': self.test_sep_magnetique_hours[i].get(),
                    'result': self.test_sep_magnetique_results[i].get()
                } for i in range(3)
            ],
            'dpm_debut': self.test_dpm_debut_var.get(),
            'dpm_fin': self.test_dpm_fin_var.get(),
            'materiel_debut': self.materiel_debut_var.get(),
            'materiel_fin': self.materiel_fin_var.get(),
            'materiel_manquant': self.materiel_manquant_var.get(),
            'bris_de_verre': self.bris_de_verre_var.get(),
            'bris_de_verre_defaut': self.bris_de_verre_defaut_var.get(),
            'lot_bleus': self.lot_bleus_var.get(),
            'lot_rouges': self.lot_rouges_var.get(),
            'lot_verts': self.lot_verts_var.get(),
            'non_conformites': self.non_conformities.copy()
        }

        self.enregistrements.append(data)
        self.save_enregistrements()
        messagebox.showinfo("Enregistrement", "Enregistrement qualité sauvegardé avec succès.")
        self.non_conformities.clear()

    def show_all_enregistrements(self):
        all_win = tk.Toplevel(self.parent)
        all_win.title("Tous les enregistrements qualité")
        all_win.configure(bg=self.colors['bg'])

        columns = ("date", "heure", "poste", "chef_equipe")
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview",
                        background=self.colors['tree_bg'],
                        foreground=self.colors['tree_fg'],
                        rowheight=25,
                        fieldbackground=self.colors['tree_field_bg'])
        style.map('Treeview', background=[('selected', self.colors['tree_selected_bg'])])

        tree = ttk.Treeview(all_win, columns=columns, show='headings', style="Treeview")
        tree.heading('date', text='Date')
        tree.heading('heure', text='Heure')
        tree.heading('poste', text='Poste')
        tree.heading('chef_equipe', text='Chef d\'équipe')
        tree.column('date', width=100)
        tree.column('heure', width=100)
        tree.column('poste', width=120)
        tree.column('chef_equipe', width=150)

        for enreg in self.enregistrements:
            tree.insert('', 'end', values=(
                enreg['date'],
                enreg['heure'],
                enreg['poste'],
                enreg['chef_equipe']
            ))

        tree.pack(fill='both', expand=True, padx=10, pady=10)

        export_frame = tk.Frame(all_win, bg=self.colors['bg'])
        export_frame.pack(pady=10)
        export_button = tk.Button(export_frame, text="Exporter en PDF", bg=self.colors['button_bg'],
                                  fg=self.colors['button_fg'], command=self.export_pdf)
        export_button.pack(side='left', padx=5)

    def show_all_non_conformities(self):
        all_nc_win = tk.Toplevel(self.parent)
        all_nc_win.title("Tous les non-conformités")
        all_nc_win.configure(bg=self.colors['bg'])

        columns = ("detectee_par", "datetime", "lot", "description", "action_corrective_prise",
                   "action_corrective_detail", "necessite_qualite", "cloturee")
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview",
                        background=self.colors['tree_bg'],
                        foreground=self.colors['tree_fg'],
                        rowheight=25,
                        fieldbackground=self.colors['tree_field_bg'])
        style.map('Treeview', background=[('selected', self.colors['tree_selected_bg'])])

        tree = ttk.Treeview(all_nc_win, columns=columns, show='headings', style="Treeview")
        tree.heading('detectee_par', text='Détectée par')
        tree.heading('datetime', text='Date/Heure')
        tree.heading('lot', text='Numéro de Lot')
        tree.heading('description', text='Description')
        tree.heading('action_corrective_prise', text='Action Corrective Prise')
        tree.heading('action_corrective_detail', text='Détail Action Corrective')
        tree.heading('necessite_qualite', text='Nécessite Service Qualité')
        tree.heading('cloturee', text='Clôturée')

        tree.column('detectee_par', width=100)
        tree.column('datetime', width=120)
        tree.column('lot', width=100)
        tree.column('description', width=200)
        tree.column('action_corrective_prise', width=150)
        tree.column('action_corrective_detail', width=200)
        tree.column('necessite_qualite', width=180)
        tree.column('cloturee', width=80)

        for nc in self.all_non_conformities:
            tree.insert('', 'end', values=(
                nc['detectee_par'],
                nc['datetime'],
                nc['lot'],
                nc['description'],
                nc['action_corrective_prise'],
                nc['action_corrective_detail'],
                nc['necessite_qualite'],
                nc['cloturee']
            ))

        tree.pack(fill='both', expand=True, padx=10, pady=10)

        action_frame = tk.Frame(all_nc_win, bg=self.colors['bg'])
        action_frame.pack(pady=10)

        export_button = tk.Button(action_frame, text="Exporter en PDF", bg=self.colors['button_bg'],
                                  fg=self.colors['button_fg'], command=self.export_non_conformities_pdf)
        export_button.pack(side='left', padx=5)

        cloturer_button = tk.Button(action_frame, text="Clôturer Non-Conformité", bg='orange', fg='white',
                                    command=lambda: self.cloturer_non_conformite(tree))
        cloturer_button.pack(side='left', padx=5)

    def cloturer_non_conformite(self, tree):
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showwarning("Aucune sélection", "Veuillez sélectionner une non-conformité à clôturer.")
            return
        item = selected_item[0]
        values = list(tree.item(item, 'values'))
        cloturee = values[7]
        if cloturee == "OUI":
            messagebox.showinfo("Déjà clôturée", "Cette non-conformité est déjà clôturée.")
            return

        for nc in self.all_non_conformities:
            if (nc['detectee_par'] == values[0] and
                    nc['datetime'] == values[1] and
                    nc['lot'] == values[2] and
                    nc['description'] == values[3]):
                nc['cloturee'] = "OUI"
                break

        self.save_non_conformities()

        tree.item(item, values=(
            values[0],
            values[1],
            values[2],
            values[3],
            values[4],
            values[5],
            values[6],
            "OUI"
        ))

        messagebox.showinfo("Clôturée", "Non-conformité clôturée avec succès.")

    def export_pdf(self):
        if not self.enregistrements:
            messagebox.showwarning("Export PDF", "Aucun enregistrement disponible pour l'export.")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if not file_path:
            return

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
        except ImportError:
            messagebox.showerror("Erreur",
                                 "La bibliothèque 'reportlab' n'est pas installée. Impossible d'exporter en PDF.")
            return

        c = canvas.Canvas(file_path, pagesize=A4)
        width, height = A4

        self.y = height - 50
        self.x = 50
        c.setFont("Helvetica", 12)

        def write_line(text):
            line_height = 15
            if self.y < 100:
                c.showPage()
                c.setFont("Helvetica", 12)
                self.y = height - 50
            c.drawString(self.x, self.y, text)
            self.y -= line_height

        write_line("Liste des enregistrements Qualité")

        for enreg in self.enregistrements:
            write_line("")
            write_line(
                f"Date: {enreg['date']}, Heure: {enreg['heure']}, Poste: {enreg['poste']}, Chef: {enreg['chef_equipe']}")
            write_line(f"Lot sacs bleus: {enreg['lot_bleus']}")
            write_line(f"Lot sacs rouges: {enreg['lot_rouges']}")
            write_line(f"Lot sacs verts: {enreg['lot_verts']}")

            write_line("---- Contrôle des aimants ----")
            for k, v in enreg['aimants'].items():
                write_line(f"{k.capitalize()} : {v}")

            write_line("---- Test Séparateur Magnétique ----")
            for i, test in enumerate(enreg['sep_magnetique'], start=1):
                write_line(f"Test {i}: Heure: {test['heure_test']}, Résultat: {test['result']}")

            write_line("---- Test DPM ----")
            write_line(f"DPM Début de poste: {enreg['dpm_debut']}")
            write_line(f"DPM Fin de poste: {enreg['dpm_fin']}")

            write_line("---- Inventaire du matériel ----")
            write_line(f"Matériel début: {enreg['materiel_debut']}")
            write_line(f"Matériel fin: {enreg['materiel_fin']}")
            if enreg['materiel_manquant']:
                write_line(f"Matériel manquant: {enreg['materiel_manquant']}")

            write_line("---- Contrôle bris de verre ----")
            write_line(f"Matériel conforme: {enreg['bris_de_verre']}")
            if enreg['bris_de_verre_defaut']:
                write_line(f"Élément défaillant: {enreg['bris_de_verre_defaut']}")

            if enreg['non_conformites']:
                write_line("---- Non-Conformités ----")
                for nc in enreg['non_conformites']:
                    write_line(f"Non-conformité détectée par: {nc['detectee_par']}")
                    write_line(f"Heure/Date: {nc['datetime']}")
                    write_line(f"Lot: {nc['lot']}")
                    write_line(f"Description: {nc['description']}")
                    write_line(f"Action corrective prise: {nc['action_corrective_prise']}")
                    if nc['action_corrective_detail']:
                        write_line(f"Détail action corrective: {nc['action_corrective_detail']}")
                    write_line(f"Nécessite service qualité: {nc['necessite_qualite']}")
                    write_line(f"Clôturée: {nc['cloturee']}")
                    write_line("")

        c.save()
        messagebox.showinfo("Export PDF", f"Enregistrements exportés avec succès vers {file_path}")

    def export_non_conformities_pdf(self):
        if not self.all_non_conformities:
            messagebox.showwarning("Export PDF", "Aucune non-conformité disponible pour l'export.")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if not file_path:
            return

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
        except ImportError:
            messagebox.showerror("Erreur",
                                 "La bibliothèque 'reportlab' n'est pas installée. Impossible d'exporter en PDF.")
            return

        c = canvas.Canvas(file_path, pagesize=A4)
        width, height = A4

        y = height - 50
        x = 50
        c.setFont("Helvetica", 12)

        def write_line(text):
            nonlocal y
            line_height = 15
            if y < 100:
                c.showPage()
                c.setFont("Helvetica", 12)
                y = height - 50
            c.drawString(x, y, text)
            y -= line_height

        write_line("Liste des Non-Conformités")

        for nc in self.all_non_conformities:
            write_line("")
            write_line(f"Détectée par: {nc['detectee_par']}")
            write_line(f"Heure/Date: {nc['datetime']}")
            write_line(f"Numéro de Lot: {nc['lot']}")
            write_line(f"Description: {nc['description']}")
            write_line(f"Action corrective prise: {nc['action_corrective_prise']}")
            if nc['action_corrective_detail']:
                write_line(f"Détail action corrective: {nc['action_corrective_detail']}")
            write_line(f"Nécessite service qualité: {nc['necessite_qualite']}")
            write_line(f"Clôturée: {nc['cloturee']}")
            write_line("")

        c.save()
        messagebox.showinfo("Export PDF", f"Non-conformités exportées avec succès vers {file_path}")

    def load_enregistrements(self):
        filename = self.get_enregistrements_filename()
        if os.path.exists(filename):
            try:
                with open(filename, 'rb') as f:
                    data = pickle.load(f)
                return data
            except:
                return []
        else:
            return []

    def save_enregistrements(self):
        filename = self.get_enregistrements_filename()
        with open(filename, 'wb') as f:
            pickle.dump(self.enregistrements, f)

    def load_non_conformities(self):
        filename = self.get_non_conformities_filename()
        if os.path.exists(filename):
            try:
                with open(filename, 'rb') as f:
                    data = pickle.load(f)
                return data
            except:
                return []
        else:
            return []

    def save_non_conformities(self):
        filename = self.get_non_conformities_filename()
        with open(filename, 'wb') as f:
            pickle.dump(self.all_non_conformities, f)

    def get_enregistrements_filename(self):
        module_dir = os.path.dirname(__file__)
        return os.path.join(module_dir, 'qualite_enregistrements.pkl')

    def get_non_conformities_filename(self):
        module_dir = os.path.dirname(__file__)
        return os.path.join(module_dir, 'non_conformites.pkl')
