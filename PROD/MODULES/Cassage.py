# Cassage.py

import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import StringVar, IntVar
import re
import json
import os
from datetime import datetime
import pickle
import ast
import operator

def get_frame(parent_frame, controller):
    frame = tk.Frame(parent_frame, bg='#2B2B2B')  # Thème sombre
    app = CassageApp(frame, controller)
    return frame

class CassageApp:
    def __init__(self, parent, controller):
        self.parent = parent
        self.controller = controller  # Référence au contrôleur principal (Application)
        self.colors = {
            'bg': '#2B2B2B',
            'fg': 'white',
            'button_bg': '#4CAF50',
            'button_fg': 'white',
            'entry_bg': '#3C3F41',
            'entry_fg': 'white',
            'label_fg': 'white',
            'tree_bg': '#D3D3D3',
            'tree_fg': 'black',
            'tree_field_bg': '#D3D3D3',
            'tree_selected_bg': '#347083',
            'bot_button_bg': 'red',          # Couleur rouge pour les boutons d'action importants
            'bot_button_fg': 'white',        # Texte blanc pour les boutons d'action importants
            'error_bg': '#FFCCCC'
        }

        self.parent.configure(bg=self.colors['bg'])

        # Variables
        self.lot_num = StringVar()
        self.ail_entree = StringVar()
        self.ail_sortie = StringVar()
        self.perte = StringVar()
        self.observation = StringVar()
        self.panne = IntVar()  # 1 pour Oui, 0 pour Non
        self.temps_panne = StringVar()
        self.temps_production = StringVar()
        self.temps_nettoyage = StringVar()
        self.poste = StringVar()

        self.state_filename = "cassage_state.pkl"

        self.setup_ui()
        self.load_state()

    def setup_ui(self):
        colors = self.colors

        # Cadre principal
        main_frame = tk.Frame(self.parent, bg=colors['bg'])
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Section Entrées
        entry_frame = tk.LabelFrame(main_frame, text="Atelier Cassage", bg=colors['bg'], fg=colors['fg'],
                                    font=("Helvetica", 14, "bold"))
        entry_frame.pack(fill='x', padx=5, pady=5)

        # Sous-Cadres pour une meilleure organisation
        lot_frame = tk.Frame(entry_frame, bg=colors['bg'])
        lot_frame.grid(row=0, column=0, padx=10, pady=5, sticky='w')

        # Numéro de Lot
        tk.Label(lot_frame, text="Numéro de Lot:", bg=colors['bg'], fg=colors['label_fg'],
                 font=("Helvetica", 12)).grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.lot_entry = tk.Entry(lot_frame, textvariable=self.lot_num, bg=colors['entry_bg'],
                                  fg=colors['entry_fg'], width=20)
        self.lot_entry.grid(row=0, column=1, padx=5, pady=5, sticky='w')

        # Quantité d'Ail Rentrée
        tk.Label(lot_frame, text="Ail Rentrée (kg):", bg=colors['bg'], fg=colors['label_fg'],
                 font=("Helvetica", 12)).grid(row=1, column=0, padx=5, pady=5, sticky='e')
        self.ail_entree_entry = tk.Entry(lot_frame, textvariable=self.ail_entree, bg=colors['entry_bg'],
                                        fg=colors['entry_fg'], width=20)
        self.ail_entree_entry.grid(row=1, column=1, padx=5, pady=5, sticky='w')

        # Quantité d'Ail Sortie
        tk.Label(lot_frame, text="Ail Sortie (kg):", bg=colors['bg'], fg=colors['label_fg'],
                 font=("Helvetica", 12)).grid(row=2, column=0, padx=5, pady=5, sticky='e')
        self.ail_sortie_entry = tk.Entry(lot_frame, textvariable=self.ail_sortie, bg=colors['entry_bg'],
                                        fg=colors['entry_fg'], width=20)
        self.ail_sortie_entry.grid(row=2, column=1, padx=5, pady=5, sticky='w')
        self.ail_sortie_entry.bind('<KeyRelease>', self.calculate_perte)

        # Perte/Pellures
        tk.Label(lot_frame, text="Perte/Pellures (kg):", bg=colors['bg'], fg=colors['label_fg'],
                 font=("Helvetica", 12)).grid(row=3, column=0, padx=5, pady=5, sticky='e')
        self.perte_label = tk.Label(lot_frame, textvariable=self.perte, bg=colors['bg'], fg='green',
                                    font=("Helvetica", 12, "bold"))
        self.perte_label.grid(row=3, column=1, padx=5, pady=5, sticky='w')

        # Temps de Production et Nettoyage
        temps_frame = tk.Frame(entry_frame, bg=colors['bg'])
        temps_frame.grid(row=0, column=1, padx=10, pady=5, sticky='w')

        # Temps de Production
        tk.Label(temps_frame, text="Production:", bg=colors['bg'], fg=colors['label_fg'],
                 font=("Helvetica", 12)).grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.temps_production_entry = tk.Entry(temps_frame, textvariable=self.temps_production, bg=colors['entry_bg'],
                                               fg=colors['entry_fg'], width=20)
        self.temps_production_entry.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        self.temps_production_entry.bind('<FocusOut>', self.validate_and_convert_time)
        self.temps_production_entry.bind('<KeyRelease>', self.calculate_total_time)

        # Temps de Nettoyage
        tk.Label(temps_frame, text="Nettoyage:", bg=colors['bg'], fg=colors['label_fg'],
                 font=("Helvetica", 12)).grid(row=1, column=0, padx=5, pady=5, sticky='e')
        self.temps_nettoyage_entry = tk.Entry(temps_frame, textvariable=self.temps_nettoyage, bg=colors['entry_bg'],
                                              fg=colors['entry_fg'], width=20)
        self.temps_nettoyage_entry.grid(row=1, column=1, padx=5, pady=5, sticky='w')
        self.temps_nettoyage_entry.bind('<FocusOut>', self.validate_and_convert_time)
        self.temps_nettoyage_entry.bind('<KeyRelease>', self.calculate_total_time)

        # Poste
        poste_frame = tk.Frame(entry_frame, bg=colors['bg'])
        poste_frame.grid(row=1, column=0, padx=10, pady=5, sticky='w')

        tk.Label(poste_frame, text="Poste:", bg=colors['bg'], fg=colors['label_fg'],
                 font=("Helvetica", 12)).grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.poste_combobox = ttk.Combobox(poste_frame, textvariable=self.poste, state="readonly",
                                           values=["Matin", "Après-midi", "Nuit"], width=18)
        self.poste_combobox.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        self.poste_combobox.current(0)  # Valeur par défaut

        # Observation
        observation_frame = tk.Frame(entry_frame, bg=colors['bg'])
        observation_frame.grid(row=2, column=0, padx=10, pady=5, sticky='w')

        tk.Label(observation_frame, text="Observation:", bg=colors['bg'], fg=colors['label_fg'],
                 font=("Helvetica", 12)).grid(row=0, column=0, padx=5, pady=5, sticky='ne')
        self.observation_text = tk.Text(observation_frame, width=30, height=4, bg=colors['entry_bg'],
                                        fg=colors['entry_fg'], insertbackground='white', wrap='word')
        self.observation_text.grid(row=0, column=1, padx=5, pady=5, sticky='w')

        # Panne
        panne_frame = tk.Frame(entry_frame, bg=colors['bg'])
        panne_frame.grid(row=3, column=0, padx=10, pady=5, sticky='w')

        self.panne_check = tk.Checkbutton(panne_frame, text="Panne", variable=self.panne, bg=colors['bg'],
                                         fg=colors['label_fg'], onvalue=1, offvalue=0,
                                         command=self.toggle_panne, font=("Helvetica", 12))
        self.panne_check.grid(row=0, column=0, padx=5, pady=5, sticky='e')

        # Temps de la Panne (visible uniquement si Panne est Oui)
        self.temps_panne_label = tk.Label(panne_frame, text="Temps de la Panne (min):", bg=colors['bg'],
                                          fg=colors['label_fg'], font=("Helvetica", 12))
        self.temps_panne_entry = tk.Entry(panne_frame, textvariable=self.temps_panne, bg=colors['entry_bg'],
                                         fg=colors['entry_fg'], width=20)
        self.temps_panne_entry.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        self.temps_panne_entry.bind('<FocusOut>', self.validate_panne_time)

        # Boutons
        button_frame = tk.Frame(main_frame, bg=colors['bg'])
        button_frame.pack(fill='x', padx=5, pady=5)

        # Modification : Bouton "Sauvegarder" en rouge
        self.save_button = tk.Button(button_frame, text="Sauvegarder", command=self.save_data,
                                     bg=colors['bot_button_bg'], fg=colors['bot_button_fg'], font=("Helvetica", 12, "bold"))
        self.save_button.pack(side='left', padx=5, pady=5)

        self.add_button = tk.Button(button_frame, text="Ajouter une Entrée", command=self.add_entry,
                                    bg=colors['button_bg'], fg=colors['button_fg'], font=("Helvetica", 12, "bold"))
        self.add_button.pack(side='left', padx=5, pady=5)

        self.reset_button = tk.Button(button_frame, text="Réinitialiser", command=self.reset_fields,
                                      bg=colors['button_bg'], fg=colors['button_fg'], font=("Helvetica", 12, "bold"))
        self.reset_button.pack(side='left', padx=5, pady=5)

        # Bouton Calculatrice
        self.calc_button = tk.Button(button_frame, text="Calculatrice", command=self.open_calculator,
                                     bg="#2196F3", fg="white", font=("Helvetica", 12, "bold"))
        self.calc_button.pack(side='left', padx=5, pady=5)

        # Barre de Recherche
        search_frame = tk.Frame(main_frame, bg=colors['bg'])
        search_frame.pack(fill='x', padx=5, pady=5)

        tk.Label(search_frame, text="Recherche:", bg=colors['bg'], fg=colors['fg'],
                 font=("Helvetica", 12)).pack(side='left', padx=5)
        self.search_var = StringVar()
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var, bg=colors['entry_bg'],
                                     fg=colors['entry_fg'], width=30)
        self.search_entry.pack(side='left', padx=5)
        self.search_entry.bind('<KeyRelease>', self.search_entries)

        clear_search_button = tk.Button(search_frame, text="Effacer", command=self.clear_search,
                                        bg=colors['button_bg'], fg=colors['button_fg'], font=("Helvetica", 10, "bold"))
        clear_search_button.pack(side='left', padx=5)

        # Tableau des Entrées avec Barres de Défilement
        table_frame = tk.LabelFrame(main_frame, text="Historique des Entrées", bg=colors['bg'], fg=colors['fg'],
                                    font=("Helvetica", 14, "bold"))
        table_frame.pack(fill='both', expand=True, padx=5, pady=5)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview",
                        background=colors['tree_bg'],
                        foreground=colors['tree_fg'],
                        rowheight=25,
                        fieldbackground=colors['tree_field_bg'])
        style.map('Treeview', background=[('selected', colors['tree_selected_bg'])])

        columns = ('Lot', 'Ail Rentrée', 'Ail Sortie', 'Perte/Pellures',
                   'Production', 'Nettoyage', 'Poste', 'Panne', 'Temps Panne',
                   'Observation', 'Date', 'Heure')

        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', style="Treeview")
        for col in columns:
            self.tree.heading(col, text=col, command=lambda _col=col: self.sort_treeview(_col, False))
            self.tree.column(col, width=100, anchor='center')

        # Ajustement des largeurs
        self.tree.column('Lot', width=100, anchor='center')
        self.tree.column('Ail Rentrée', width=120, anchor='center')
        self.tree.column('Ail Sortie', width=120, anchor='center')
        self.tree.column('Perte/Pellures', width=150, anchor='center')
        self.tree.column('Production', width=150, anchor='center')
        self.tree.column('Nettoyage', width=150, anchor='center')
        self.tree.column('Poste', width=100, anchor='center')
        self.tree.column('Panne', width=80, anchor='center')
        self.tree.column('Temps Panne', width=150, anchor='center')
        self.tree.column('Observation', width=200, anchor='center')
        self.tree.column('Date', width=100, anchor='center')
        self.tree.column('Heure', width=100, anchor='center')

        # Barres de défilement
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscroll=vsb.set, xscroll=hsb.set)
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

    def show_about(self):
        messagebox.showinfo("À propos", "Application de Gestion du Cassage d'Ail\nDéveloppée par [Votre Nom]")

    def toggle_panne(self):
        if self.panne.get() == 1:
            self.temps_panne_label.grid(row=0, column=2, padx=5, pady=5, sticky='e')
            self.temps_panne_entry.grid(row=0, column=3, padx=5, pady=5, sticky='w')
        else:
            self.temps_panne_label.grid_forget()
            self.temps_panne_entry.grid_forget()
            self.temps_panne.set('')

    def calculate_perte(self, event=None):
        try:
            entree = float(self.ail_entree.get())
            sortie = float(self.ail_sortie.get())
            perte = entree - sortie
            self.perte.set(round(perte, 2))
        except ValueError:
            self.perte.set("0")

    def parse_time_input(self, time_str):
        """
        Parse a time string and return total minutes.
        Acceptable formats: "7h", "7h30m", "1h", "45m", "1h15m", etc.
        """
        time_str = time_str.lower().strip()
        pattern = re.compile(r'(?:(\d+)\s*h(?:ours?)?)?\s*(?:(\d+)\s*m(?:inutes?)?)?')
        match = pattern.fullmatch(time_str)
        if not match:
            return None
        hours = int(match.group(1)) if match.group(1) else 0
        minutes = int(match.group(2)) if match.group(2) else 0
        return hours * 60 + minutes

    def convert_minutes_to_hhmm(self, total_minutes):
        hours = total_minutes // 60
        minutes = total_minutes % 60
        return f"{hours}h{minutes:02d}m"

    def validate_and_convert_time(self, event=None):
        """
        Validate the time input and convert it to minutes.
        Update the entry field to standardized format.
        """
        widget = event.widget
        time_str = widget.get()
        total_minutes = self.parse_time_input(time_str)
        if total_minutes is None:
            messagebox.showerror("Erreur", f"Format de temps invalide: '{time_str}'. Utilisez des formats comme '7h', '7h30m', '45m', etc.")
            widget.focus_set()
            widget.delete(0, tk.END)
            return
        # Convert back to standardized format
        standardized_time = self.convert_minutes_to_hhmm(total_minutes)
        widget.delete(0, tk.END)
        widget.insert(0, standardized_time)

    def validate_panne_time(self, event=None):
        """
        Validate the panne time input.
        """
        widget = event.widget
        time_str = widget.get()
        if not time_str.isdigit():
            messagebox.showerror("Erreur", f"Le temps de panne doit être un nombre entier positif.")
            widget.focus_set()
            widget.delete(0, tk.END)
            return

    def calculate_total_time(self, event=None):
        """
        Optional: Calculate total time if needed.
        Currently unused but can be implemented for additional features.
        """
        pass

    def add_entry(self):
        lot = self.lot_num.get().strip()
        ail_entree_str = self.ail_entree.get().strip()
        ail_sortie_str = self.ail_sortie.get().strip()
        perte_str = self.perte.get().strip()
        temps_production_str = self.temps_production.get().strip()
        temps_nettoyage_str = self.temps_nettoyage.get().strip()
        observation = self.observation_text.get("1.0", tk.END).strip()
        poste = self.poste.get()
        panne = "Oui" if self.panne.get() == 1 else "Non"
        temps_panne = self.temps_panne.get() if self.panne.get() == 1 else "N/A"
        date = datetime.now().strftime("%Y-%m-%d")
        heure = datetime.now().strftime("%H:%M:%S")

        # Validation des champs
        if not lot:
            messagebox.showerror("Erreur", "Le numéro de lot est requis.")
            return

        try:
            ail_entree = float(ail_entree_str)
            if ail_entree < 0:
                messagebox.showerror("Erreur", "La quantité d'ail rentrée ne peut pas être négative.")
                return
        except ValueError:
            messagebox.showerror("Erreur", "La quantité d'ail rentrée doit être un nombre valide.")
            return

        try:
            ail_sortie = float(ail_sortie_str)
            if ail_sortie < 0:
                messagebox.showerror("Erreur", "La quantité d'ail sortie ne peut pas être négative.")
                return
        except ValueError:
            messagebox.showerror("Erreur", "La quantité d'ail sortie doit être un nombre valide.")
            return

        if not poste:
            messagebox.showerror("Erreur", "Veuillez sélectionner un poste (Matin, Après-midi, Nuit).")
            return

        # Parse et valider les temps de production et de nettoyage
        temps_production_minutes = self.parse_time_input(temps_production_str)
        if temps_production_minutes is None:
            messagebox.showerror("Erreur", f"Format de Temps de Production invalide: '{temps_production_str}'. Utilisez des formats comme '7h', '7h30m', '45m', etc.")
            return
        temps_nettoyage_minutes = self.parse_time_input(temps_nettoyage_str)
        if temps_nettoyage_minutes is None:
            messagebox.showerror("Erreur", f"Format de Temps de Nettoyage invalide: '{temps_nettoyage_str}'. Utilisez des formats comme '7h', '7h30m', '45m', etc.")
            return

        if temps_production_minutes < 0:
            messagebox.showerror("Erreur", "Le temps de production ne peut pas être négatif.")
            return
        if temps_nettoyage_minutes < 0:
            messagebox.showerror("Erreur", "Le temps de nettoyage ne peut pas être négatif.")
            return

        if self.panne.get() == 1:
            if not temps_panne.isdigit() or int(temps_panne) < 0:
                messagebox.showerror("Erreur", "Le temps de panne doit être un nombre de minutes valide et positif.")
                return
            temps_panne_val = int(temps_panne)
        else:
            temps_panne_val = "N/A"

        perte = float(perte_str) if perte_str else 0

        # Calcul de la perte si non calculée
        if not perte_str:
            perte = ail_entree - ail_sortie
            self.perte.set(round(perte, 2))

        # Convertir les minutes en format affichage
        temps_production_display = self.convert_minutes_to_hhmm(temps_production_minutes)
        temps_nettoyage_display = self.convert_minutes_to_hhmm(temps_nettoyage_minutes)

        # Ajouter l'entrée au tableau avec les temps convertis en HH:MM
        self.tree.insert('', 'end', values=(lot, ail_entree, ail_sortie, perte,
                                           temps_production_display, temps_nettoyage_display,
                                           poste, panne, temps_panne_val, observation, date, heure))

        # Sauvegarder dans le fichier JSON
        data_entry = {
            'lot_num': lot,
            'ail_entree': ail_entree,
            'ail_sortie': ail_sortie,
            'perte': perte,
            'temps_production_minutes': temps_production_minutes,
            'temps_nettoyage_minutes': temps_nettoyage_minutes,
            'temps_production_display': temps_production_display,
            'temps_nettoyage_display': temps_nettoyage_display,
            'poste': poste,
            'panne': panne,
            'temps_panne': temps_panne_val,
            'observation': observation,
            'date': date,
            'heure': heure,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Définir le chemin de sauvegarde
        main_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        data_file = os.path.join(main_dir, 'cassage_data.json')

        existing_data = []
        if os.path.exists(data_file):
            try:
                with open(data_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            except json.JSONDecodeError:
                existing_data = []

        existing_data.append(data_entry)

        try:
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("Succès", "Entrée ajoutée avec succès.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la sauvegarde des données: {e}")

        # Réinitialiser les champs
        self.reset_fields()

    def sort_treeview(self, col, reverse):
        """
        Sort the treeview contents when a column header is clicked.
        """
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        try:
            # Tentative de conversion en float pour les colonnes numériques
            l.sort(key=lambda t: float(re.sub('[^0-9.]', '', t[0])), reverse=reverse)
        except ValueError:
            # Si conversion échoue, trier comme des chaînes de caractères
            l.sort(reverse=reverse)

        for index, (val, k) in enumerate(l):
            self.tree.move(k, '', index)

        # Reverse sort next time
        self.tree.heading(col, command=lambda: self.sort_treeview(col, not reverse))

    def search_entries(self, event=None):
        """
        Search and filter the treeview entries based on the search query.
        """
        query = self.search_var.get().lower()
        for item in self.tree.get_children():
            values = self.tree.item(item, 'values')
            if any(query in str(value).lower() for value in values):
                self.tree.reattach(item, '', 'end')
            else:
                self.tree.detach(item)

    def clear_search(self):
        """
        Clear the search entry and show all treeview items.
        """
        self.search_var.set('')
        for item in self.tree.get_children():
            self.tree.reattach(item, '', 'end')

    def show_about(self):
        messagebox.showinfo("À propos", "Application de Gestion du Cassage d'Ail\nDéveloppée par [Votre Nom]")

    def toggle_panne(self):
        if self.panne.get() == 1:
            self.temps_panne_label.grid(row=0, column=2, padx=5, pady=5, sticky='e')
            self.temps_panne_entry.grid(row=0, column=3, padx=5, pady=5, sticky='w')
        else:
            self.temps_panne_label.grid_forget()
            self.temps_panne_entry.grid_forget()
            self.temps_panne.set('')

    def save_data(self):
        """
        Sauvegarde de l'état actuel des champs.
        """
        state = {
            'lot_num': self.lot_num.get(),
            'ail_entree': self.ail_entree.get(),
            'ail_sortie': self.ail_sortie.get(),
            'perte': self.perte.get(),
            'temps_production': self.temps_production.get(),
            'temps_nettoyage': self.temps_nettoyage.get(),
            'poste': self.poste.get(),
            'observation': self.observation_text.get("1.0", "end"),
            'panne': self.panne.get(),
            'temps_panne': self.temps_panne.get()
        }
        try:
            with open(self.state_filename, 'wb') as f:
                pickle.dump(state, f)
            messagebox.showinfo("Succès", "État sauvegardé avec succès.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la sauvegarde de l'état: {e}")

    def reset_fields(self):
        """
        Réinitialise tous les champs d'entrée.
        """
        self.lot_num.set('')
        self.ail_entree.set('')
        self.ail_sortie.set('')
        self.perte.set('')
        self.temps_production.set('')
        self.temps_nettoyage.set('')
        self.observation_text.delete("1.0", tk.END)
        self.poste.set('')
        self.panne.set(0)
        self.temps_panne.set('')
        self.toggle_panne()

    def save_state(self):
        """
        Sauvegarde l'état actuel des champs dans un fichier.
        """
        state = {
            'lot_num': self.lot_num.get(),
            'ail_entree': self.ail_entree.get(),
            'ail_sortie': self.ail_sortie.get(),
            'perte': self.perte.get(),
            'temps_production': self.temps_production.get(),
            'temps_nettoyage': self.temps_nettoyage.get(),
            'poste': self.poste.get(),
            'observation': self.observation_text.get("1.0", "end"),
            'panne': self.panne.get(),
            'temps_panne': self.temps_panne.get()
        }
        try:
            with open(self.state_filename, 'wb') as f:
                pickle.dump(state, f)
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la sauvegarde de l'état: {e}")

    def load_state(self):
        """
        Charge l'état précédent des champs depuis un fichier.
        """
        if os.path.exists(self.state_filename):
            try:
                with open(self.state_filename, 'rb') as f:
                    state = pickle.load(f)
                self.lot_num.set(state.get('lot_num', ''))
                self.ail_entree.set(state.get('ail_entree', ''))
                self.ail_sortie.set(state.get('ail_sortie', ''))
                self.perte.set(state.get('perte', ''))
                self.temps_production.set(state.get('temps_production', ''))
                self.temps_nettoyage.set(state.get('temps_nettoyage', ''))
                self.poste.set(state.get('poste', ''))
                self.observation_text.delete("1.0", tk.END)
                self.observation_text.insert(tk.END, state.get('observation', ''))
                self.panne.set(state.get('panne', 0))
                self.temps_panne.set(state.get('temps_panne', ''))
                self.toggle_panne()
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors du chargement de l'état: {e}")

    def open_calculator(self):
        """
        Ouvre la calculatrice dans une nouvelle fenêtre.
        """
        calculator_window = tk.Toplevel(self.parent)
        Calculator(calculator_window)

class Calculator:
    def __init__(self, master):
        self.master = master
        self.master.title("Calculatrice")
        self.master.geometry("350x500")
        self.master.resizable(False, False)

        self.expression = ""
        self.input_text = tk.StringVar()

        # Cadre d'affichage
        input_frame = tk.Frame(self.master, width=312, height=50, bd=0, highlightbackground="black",
                               highlightcolor="black", highlightthickness=1)
        input_frame.pack(side=tk.TOP)

        # Champ d'affichage
        self.input_field = tk.Entry(input_frame, font=('arial', 18, 'bold'), textvariable=self.input_text,
                               width=50, bg="#eee", bd=0, justify=tk.RIGHT)
        self.input_field.grid(row=0, column=0)
        self.input_field.pack(ipady=10)  # Augmenter la hauteur de l'entrée

        # Focaliser sur le champ d'entrée pour recevoir les événements clavier
        self.input_field.focus_set()

        # Cadre des boutons
        btns_frame = tk.Frame(self.master, width=312, height=272.5, bg="grey")
        btns_frame.pack()

        # Définir les boutons
        buttons = [
            ['C', '⌫', '(', ')'],
            ['7', '8', '9', '/'],
            ['4', '5', '6', '*'],
            ['1', '2', '3', '-'],
            ['0', '.', '^', '+'],
            ['=', 'Ans', 'Clear']
        ]

        for row_index, row in enumerate(buttons):
            for col_index, button_text in enumerate(row):
                if button_text == '=':
                    btn = tk.Button(btns_frame, text=button_text, fg="black", width=10, height=3, bd=0,
                                   bg="#ffa500", cursor="hand2",
                                   command=self.btn_equals)
                elif button_text == 'C':
                    btn = tk.Button(btns_frame, text=button_text, fg="black", width=10, height=3, bd=0,
                                   bg="#ff6666", cursor="hand2",
                                   command=self.btn_clear)
                elif button_text == '⌫':
                    btn = tk.Button(btns_frame, text=button_text, fg="black", width=10, height=3, bd=0,
                                   bg="#ffcc66", cursor="hand2",
                                   command=self.btn_backspace)
                elif button_text == 'Clear':
                    btn = tk.Button(btns_frame, text=button_text, fg="black", width=10, height=3, bd=0,
                                   bg="#ff6666", cursor="hand2",
                                   command=self.btn_clear_all)
                elif button_text == 'Ans':
                    btn = tk.Button(btns_frame, text=button_text, fg="black", width=10, height=3, bd=0,
                                   bg="#66cc66", cursor="hand2",
                                   command=self.btn_ans)
                else:
                    btn = tk.Button(btns_frame, text=button_text, fg="black", width=10, height=3, bd=0,
                                   bg="#fff", cursor="hand2",
                                   command=lambda x=button_text: self.btn_click(x))
                btn.grid(row=row_index, column=col_index, padx=1, pady=1)

        # Variable pour stocker le dernier résultat
        self.last_ans = ""

        # Ajouter les raccourcis clavier
        self.master.bind('<Key>', self.key_pressed)

    def key_pressed(self, event):
        """
        Gère les entrées clavier pour que la calculatrice fonctionne aussi avec le pavé numérique et le clavier principal.
        """
        # Mapping des touches du pavé numérique
        keypad_mapping = {
            'KP_0': '0',
            'KP_1': '1',
            'KP_2': '2',
            'KP_3': '3',
            'KP_4': '4',
            'KP_5': '5',
            'KP_6': '6',
            'KP_7': '7',
            'KP_8': '8',
            'KP_9': '9',
            'KP_Add': '+',
            'KP_Subtract': '-',
            'KP_Multiply': '*',
            'KP_Divide': '/',
            'KP_Enter': '=',
            'KP_Decimal': '.',
            'KP_ParenLeft': '(',
            'KP_ParenRight': ')'
        }

        # Gestion des touches spécifiques
        keysym = event.keysym
        char = event.char

        if keysym in keypad_mapping:
            action = keypad_mapping[keysym]
            if action.isdigit() or action in '+-*/().^':
                self.btn_click(action)
            elif action == '=':
                self.btn_equals()
        elif char.isdigit() or char in '+-*/().^':
            self.btn_click(char)
        elif keysym in ['Return', 'KP_Enter']:
            self.btn_equals()
        elif keysym in ['BackSpace', 'Delete']:
            self.btn_backspace()
        elif char.lower() == 'c':
            self.btn_clear()

    def btn_click(self, item):
        self.expression += str(item)
        self.input_text.set(self.expression)

    def btn_clear(self):
        self.expression = ""
        self.input_text.set("")

    def btn_clear_all(self):
        self.expression = ""
        self.input_text.set("")
        self.last_ans = ""

    def btn_backspace(self):
        self.expression = self.expression[:-1]
        self.input_text.set(self.expression)

    def btn_equals(self):
        try:
            result = self.evaluate_expression(self.expression)
            self.input_text.set(result)
            self.last_ans = str(result)
            self.expression = str(result)
        except Exception as e:
            self.input_text.set("Erreur")
            self.expression = ""
            messagebox.showerror("Erreur", f"Erreur dans l'expression: {e}")

    def btn_ans(self):
        if self.last_ans:
            self.expression += self.last_ans
            self.input_text.set(self.expression)

    def evaluate_expression(self, expression):
        """
        Évalue une expression mathématique en toute sécurité.
        """
        try:
            # Remplacer l'opérateur '^' par '**' pour la puissance
            expression = expression.replace('^', '**')

            # Analyse de l'expression en un arbre AST
            node = ast.parse(expression, mode='eval')

            # Définir les opérateurs autorisés
            operators_allowed = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
                ast.Pow: operator.pow,
                ast.USub: operator.neg,
                ast.UAdd: operator.pos
            }

            def _eval(node):
                if isinstance(node, ast.Expression):
                    return _eval(node.body)
                elif isinstance(node, ast.Num):  # Pour Python <3.8
                    return node.n
                elif isinstance(node, ast.Constant):  # Pour Python 3.8+
                    return node.value
                elif isinstance(node, ast.BinOp):
                    if type(node.op) in operators_allowed:
                        return operators_allowed[type(node.op)](_eval(node.left), _eval(node.right))
                    else:
                        raise TypeError(f"Opérateur non autorisé: {type(node.op)}")
                elif isinstance(node, ast.UnaryOp):
                    if type(node.op) in operators_allowed:
                        return operators_allowed[type(node.op)](_eval(node.operand))
                    else:
                        raise TypeError(f"Opérateur non autorisé: {type(node.op)}")
                else:
                    raise TypeError(f"Type non autorisé: {type(node)}")

            return _eval(node)
        except Exception as e:
            raise e

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Gestion du Cassage d'Ail")
    root.geometry("800x600")  # Ajustez la taille selon vos besoins
    app_frame = get_frame(root, None)
    app_frame.pack(fill='both', expand=True)
    root.mainloop()
