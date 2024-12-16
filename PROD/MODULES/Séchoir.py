# MODULES/Séchoir.py

import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import StringVar
import re
import json
import os
from datetime import datetime
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

def get_frame(parent_frame, controller):
    # Cadre principal
    frame = tk.Frame(parent_frame, bg='#2B2B2B')
    frame.grid_rowconfigure(0, weight=1)
    frame.grid_columnconfigure(1, weight=1)

    # Frame des boutons (à gauche)
    button_frame = tk.Frame(frame, bg='#2B2B2B')
    button_frame.grid(row=0, column=0, sticky='nw', padx=10, pady=10)

    # Partie scrollable (à droite)
    canvas = tk.Canvas(frame, bg='#2B2B2B', highlightthickness=0)
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg='#2B2B2B')

    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.grid(row=0, column=1, sticky='nsew')
    scrollbar.grid(row=0, column=2, sticky='ns')

    # ---------------------------
    # Fonctions de validation et utilitaires
    # ---------------------------
    def format_time(event, entry):
        """Formate le contenu d'une entrée heure pour qu'il corresponde au format HH:MM."""
        value = entry.get()
        # Enlever les caractères non numériques
        value = re.sub(r'[^\d]', '', value)
        if len(value) > 2:
            value = value[:2] + ':' + value[2:4]
        elif len(value) == 2 and not value.endswith(':'):
            value += ':'
        entry.delete(0, tk.END)
        entry.insert(0, value)

    def validate_time(P):
        """Valide l'entrée partielle d'une heure au format HH:MM."""
        if P == "":
            return True
        match = re.match(r'^([01]?\d|2[0-3])?(:[0-5]?\d?)?$', P)
        return match is not None

    def validate_numeric(P):
        """Valide qu'un champ est vide ou contient un nombre entre 0.0 et 10000.0."""
        if P == "":
            return True
        try:
            value = float(P)
            return 0.0 <= value <= 10000.0
        except ValueError:
            return False

    vcmd_time = (frame.register(validate_time), '%P')
    vcmd_numeric = (frame.register(validate_numeric), '%P')

    def create_heure_entry(parent, row, column=0):
        """Crée une entrée pour une heure (HH:MM) avec validation et formattage automatique."""
        heure_var = StringVar()
        heure_entry = tk.Entry(parent, textvariable=heure_var, validate="key", validatecommand=vcmd_time,
                               bg='#3C3F41', fg='white', insertbackground='white', width=8)
        heure_entry.grid(row=row, column=column, padx=2, pady=5)
        heure_entry.bind('<KeyRelease>', lambda event, entry=heure_entry: format_time(event, entry))
        return heure_var, heure_entry

    def create_temperature_row(parent, row, entry_list):
        """Crée une ligne pour saisir les températures (consignes ou réelles)."""
        # Heure
        heure_var, _ = create_heure_entry(parent, row, column=0)
        entry = {'heure': heure_var}

        # Colonnes pour CEL 1 à CEL 7/8, puis AIR NEUF
        cellules = ["CEL 1", "CEL 2", "CEL 3", "CEL 4", "CEL 5/6", "CEL 7/8", "AIR NEUF"]
        temp_vars = []
        for idx, cellule in enumerate(cellules):
            temp_var = StringVar()
            temp_entry = tk.Entry(parent, textvariable=temp_var, validate="key",
                                  validatecommand=vcmd_numeric, bg='#3C3F41', fg='white',
                                  insertbackground='white', width=10)
            temp_entry.grid(row=row, column=idx+1, padx=2, pady=5)
            temp_vars.append(temp_var)

        entry['cels'] = temp_vars[:-1]  # De CEL 1 à CEL 7/8
        entry['air_neuf'] = temp_vars[-1]  # AIR NEUF

        entry_list.append(entry)

    # ---------------------------
    # Fonctions de sauvegarde et affichage du graphique
    # ---------------------------
    def save_data():
        """Sauvegarde toutes les données saisies dans sechoir_data.json."""
        # Récupérer les données du produit
        produit_data = {
            'type_produit': type_var.get(),
            'humide': humide_var.get(),
            'observations': observations_text.get("1.0", tk.END).strip()
        }

        # Récupérer les données des tapis
        tapis_data = []
        for entry in tapis_entries:
            tapis_data.append({
                'heure': entry['heure'].get(),
                'vit_stockeur': entry['vit_stockeur'].get(),
                'tapis1': entry['tapis1'].get(),
                'tapis2': entry['tapis2'].get(),
                'tapis3': entry['tapis3'].get(),
            })

        # Récupérer les données de températures de consigne
        consignes_data = []
        for entry in temp_consignes_entries:
            consignes_data.append({
                'heure': entry['heure'].get(),
                'cels': [cel.get() for cel in entry['cels']],
                'air_neuf': entry['air_neuf'].get(),
            })

        # Récupérer les données de températures réelles
        reelles_data = []
        for entry in temp_reelles_entries:
            reelles_data.append({
                'heure': entry['heure'].get(),
                'cels': [cel.get() for cel in entry['cels']],
                'air_neuf': entry['air_neuf'].get(),
            })

        # Construction du dictionnaire final
        four_data = {
            'produit': produit_data,
            'tapis': tapis_data,
            'temperatures_consignes': consignes_data,
            'temperatures_reelles': reelles_data
        }

        # Chemin du fichier de données
        main_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        data_file = os.path.join(main_dir, 'sechoir_data.json')

        # Charger les données existantes
        if os.path.exists(data_file):
            try:
                with open(data_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            except json.JSONDecodeError:
                existing_data = []
        else:
            existing_data = []

        # Nouvelle entrée
        save_entry = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'four_data': four_data
        }

        existing_data.append(save_entry)

        # Sauvegarde dans le fichier
        try:
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("Sauvegarde réussie", f"Données sauvegardées dans '{data_file}'.")
        except Exception as e:
            messagebox.showerror("Erreur de sauvegarde", f"Erreur lors de la sauvegarde.\n\n{e}")

    def open_graph_window():
        """Ouvre une nouvelle fenêtre affichant le graphique des températures."""
        main_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        data_file = os.path.join(main_dir, 'sechoir_data.json')

        if not os.path.exists(data_file):
            messagebox.showwarning("Aucune donnée", "Pas de données disponibles pour le graphique.")
            return

        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        except json.JSONDecodeError:
            messagebox.showerror("Erreur", "Erreur lors de la lecture des données.")
            return

        if not existing_data:
            messagebox.showwarning("Aucune donnée", "Aucune donnée disponible pour le graphique.")
            return

        last_entry = existing_data[-1]

        # Créer la fenêtre du graphique
        graph_window = tk.Toplevel()
        graph_window.title("Graphique des Températures")
        graph_window.configure(bg='#2B2B2B')
        graph_window.geometry("800x600")

        plot_temperatures(last_entry, graph_window)

    def plot_temperatures(entry, graph_container):
        """Affiche le graphique des températures à partir de la dernière entrée."""
        # Extraire les données du last_entry
        four_data = entry.get('four_data', {})
        consignes = four_data.get('temperatures_consignes', [])
        reelles = four_data.get('temperatures_reelles', [])

        cellules = ["CEL 1", "CEL 2", "CEL 3", "CEL 4", "CEL 5/6", "CEL 7/8", "AIR NEUF"]

        def extract_last_temperatures(temp_list):
            """Extrait la dernière entrée de température valide."""
            for temp_entry in reversed(temp_list):
                if 'cels' in temp_entry and 'air_neuf' in temp_entry:
                    return temp_entry
            return None

        last_consignes = extract_last_temperatures(consignes)
        last_reelles = extract_last_temperatures(reelles)

        if last_consignes is None or last_reelles is None:
            # Pas de données valides
            msg = "Pas de données de température valide pour tracer le graphique."
            label = tk.Label(graph_container, text=msg, bg='#2B2B2B', fg='white', font=("Helvetica", 12))
            label.pack(pady=20)
            return

        # Convertir les données en float, avec gestion d'erreurs
        temp_con = []
        temp_re = []
        for idx, cel_name in enumerate(cellules):
            if idx < len(cellules)-1:
                # Une cellule classique
                val_con_str = last_consignes['cels'][idx] if idx < len(last_consignes['cels']) else "0"
                val_re_str = last_reelles['cels'][idx] if idx < len(last_reelles['cels']) else "0"
            else:
                # AIR NEUF
                val_con_str = last_consignes.get('air_neuf', "0")
                val_re_str = last_reelles.get('air_neuf', "0")

            # Conversion sécurisée en float
            try:
                val_con = float(val_con_str)
            except:
                val_con = 0.0
            try:
                val_re = float(val_re_str)
            except:
                val_re = 0.0

            temp_con.append(val_con)
            temp_re.append(val_re)

        # Création de la figure matplotlib
        fig, ax = plt.subplots(figsize=(10, 6), facecolor='#2B2B2B')
        fig.patch.set_facecolor('#2B2B2B')
        ax.set_facecolor('#2B2B2B')
        ax.tick_params(colors='white')
        for spine in ax.spines.values():
            spine.set_color('white')

        x = range(len(cellules))
        width = 0.35

        bars_con = ax.bar([p - width/2 for p in x], temp_con, width=width, label='Consigne', color='#FFA500')
        bars_re = ax.bar([p + width/2 for p in x], temp_re, width=width, label='Réelle', color='#007ACC')

        ax.set_xlabel("Cellules", color='white', fontsize=12)
        ax.set_ylabel("Température (°C)", color='white', fontsize=12)
        ax.set_title("Températures Consignes vs Réelles", color='white', fontsize=14)
        ax.set_xticks(x)
        ax.set_xticklabels(cellules, color='white', fontsize=10)
        ax.legend(loc='upper right', fontsize='small')
        ax.grid(True, color='gray', linestyle='dotted', linewidth=0.5)

        def add_labels(bars):
            for bar in bars:
                height = bar.get_height()
                if height != 0:
                    ax.annotate(f'{height:.1f}',
                                xy=(bar.get_x() + bar.get_width() / 2, height),
                                xytext=(0, 3),
                                textcoords="offset points",
                                ha='center', va='bottom', color='white', fontsize=8)

        add_labels(bars_con)
        add_labels(bars_re)

        canvas = FigureCanvasTkAgg(fig, master=graph_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)

    # ---------------------------
    # Création de l'interface (Produits, Tapis, Températures)
    # ---------------------------

    # Section "Produit"
    produit_section = tk.LabelFrame(scrollable_frame, text="Produit", bg='#2B2B2B', fg='white', font=("Helvetica", 14, "bold"))
    produit_section.pack(padx=10, pady=10, fill='x', expand=True)

    # Type de Produit
    type_label = tk.Label(produit_section, text="Type de Produit:", bg='#2B2B2B', fg='white', font=("Helvetica", 12))
    type_label.grid(row=0, column=0, padx=5, pady=5, sticky='e')
    type_options = ["Ail", "Oignon", "Échalote"]
    type_var = StringVar(value=type_options[0])
    type_menu = ttk.Combobox(produit_section, textvariable=type_var, values=type_options, state="readonly", width=12)
    type_menu.grid(row=0, column=1, padx=5, pady=5, sticky='w')

    # Humide
    humide_label = tk.Label(produit_section, text="Humide:", bg='#2B2B2B', fg='white', font=("Helvetica", 12))
    humide_label.grid(row=1, column=0, padx=5, pady=5, sticky='e')
    humide_options = ["Oui", "Non"]
    humide_var = StringVar(value="Non")
    humide_menu = ttk.Combobox(produit_section, textvariable=humide_var, values=humide_options, state="readonly", width=12)
    humide_menu.grid(row=1, column=1, padx=5, pady=5, sticky='w')

    # Observations
    observations_label = tk.Label(produit_section, text="Observations:", bg='#2B2B2B', fg='white', font=("Helvetica", 12))
    observations_label.grid(row=2, column=0, padx=5, pady=5, sticky='ne')
    observations_text = tk.Text(produit_section, width=28, height=4, bg='#3C3F41', fg='white', insertbackground='white', wrap='word')
    observations_text.grid(row=2, column=1, padx=5, pady=5, sticky='w')

    # Section Tapis
    tapis_section = tk.LabelFrame(scrollable_frame, text="Tapis (Vitesses)", bg='#2B2B2B', fg='white', font=("Helvetica", 14, "bold"))
    tapis_section.pack(padx=10, pady=10, fill='x', expand=True)

    tapis_headers = ["Heure", "Vitesse Stockeur (Hz)", "Tapis 1 (Hz)", "Tapis 2 (Hz)", "Tapis 3 (Hz)"]
    for idx, header in enumerate(tapis_headers):
        tk.Label(tapis_section, text=header, bg='#2B2B2B', fg='white', font=("Helvetica", 10, "bold")).grid(row=0, column=idx, padx=2, pady=5)

    tapis_entries = []
    for row in range(1, 4):
        heure_var, _ = create_heure_entry(tapis_section, row)
        tapis_entries.append({'heure': heure_var})

        vit_stockeur_var = StringVar()
        tapis1_var = StringVar()
        tapis2_var = StringVar()
        tapis3_var = StringVar()

        # Vitesse Stockeur
        vit_stockeur_entry = tk.Entry(tapis_section, textvariable=vit_stockeur_var, validate="key", validatecommand=vcmd_numeric,
                                      bg='#3C3F41', fg='white', insertbackground='white', width=12)
        vit_stockeur_entry.grid(row=row, column=1, padx=2, pady=5)
        tapis_entries[-1]['vit_stockeur'] = vit_stockeur_var

        # Tapis 1
        tapis1_entry = tk.Entry(tapis_section, textvariable=tapis1_var, validate="key", validatecommand=vcmd_numeric,
                                bg='#3C3F41', fg='white', insertbackground='white', width=12)
        tapis1_entry.grid(row=row, column=2, padx=2, pady=5)
        tapis_entries[-1]['tapis1'] = tapis1_var

        # Tapis 2
        tapis2_entry = tk.Entry(tapis_section, textvariable=tapis2_var, validate="key", validatecommand=vcmd_numeric,
                                bg='#3C3F41', fg='white', insertbackground='white', width=12)
        tapis2_entry.grid(row=row, column=3, padx=2, pady=5)
        tapis_entries[-1]['tapis2'] = tapis2_var

        # Tapis 3
        tapis3_entry = tk.Entry(tapis_section, textvariable=tapis3_var, validate="key", validatecommand=vcmd_numeric,
                                bg='#3C3F41', fg='white', insertbackground='white', width=12)
        tapis3_entry.grid(row=row, column=4, padx=2, pady=5)
        tapis_entries[-1]['tapis3'] = tapis3_var

    def add_tapis_row():
        """Ajoute une nouvelle ligne pour les tapis."""
        row = len(tapis_entries) + 1
        heure_var, _ = create_heure_entry(tapis_section, row)
        tapis_entries.append({'heure': heure_var})

        vit_stockeur_var = StringVar()
        tapis1_var = StringVar()
        tapis2_var = StringVar()
        tapis3_var = StringVar()

        # Vitesse Stockeur
        vit_stockeur_entry = tk.Entry(tapis_section, textvariable=vit_stockeur_var, validate="key", validatecommand=vcmd_numeric,
                                      bg='#3C3F41', fg='white', insertbackground='white', width=12)
        vit_stockeur_entry.grid(row=row, column=1, padx=2, pady=5)
        tapis_entries[-1]['vit_stockeur'] = vit_stockeur_var

        # Tapis 1
        tapis1_entry = tk.Entry(tapis_section, textvariable=tapis1_var, validate="key", validatecommand=vcmd_numeric,
                                bg='#3C3F41', fg='white', insertbackground='white', width=12)
        tapis1_entry.grid(row=row, column=2, padx=2, pady=5)
        tapis_entries[-1]['tapis1'] = tapis1_var

        # Tapis 2
        tapis2_entry = tk.Entry(tapis_section, textvariable=tapis2_var, validate="key", validatecommand=vcmd_numeric,
                                bg='#3C3F41', fg='white', insertbackground='white', width=12)
        tapis2_entry.grid(row=row, column=3, padx=2, pady=5)
        tapis_entries[-1]['tapis2'] = tapis2_var

        # Tapis 3
        tapis3_entry = tk.Entry(tapis_section, textvariable=tapis3_var, validate="key", validatecommand=vcmd_numeric,
                                bg='#3C3F41', fg='white', insertbackground='white', width=12)
        tapis3_entry.grid(row=row, column=4, padx=2, pady=5)
        tapis_entries[-1]['tapis3'] = tapis3_var

    add_tapis_button = tk.Button(
        tapis_section, text="Ajouter une ligne", command=add_tapis_row,
        bg='#6e6e6e', fg='white', font=("Helvetica", 10, "bold"),
        relief="flat", padx=5, pady=2
    )
    add_tapis_button.grid(row=1000, column=0, columnspan=5, pady=10)

    # Section Température Consigne
    temp_consignes_section = tk.LabelFrame(scrollable_frame, text="Température Consigne", bg='#2B2B2B', fg='white', font=("Helvetica", 14, "bold"))
    temp_consignes_section.pack(padx=10, pady=10, fill='x', expand=True)

    temp_headers = ["Heure", "CEL 1", "CEL 2", "CEL 3", "CEL 4", "CEL 5/6", "CEL 7/8", "AIR NEUF"]
    for idx, header in enumerate(temp_headers):
        tk.Label(temp_consignes_section, text=header, bg='#2B2B2B', fg='white', font=("Helvetica", 10, "bold")).grid(row=0, column=idx, padx=2, pady=5)

    temp_consignes_entries = []
    for row in range(1, 3):
        create_temperature_row(temp_consignes_section, row, temp_consignes_entries)

    def add_temp_consignes_row():
        row = len(temp_consignes_entries) + 1
        create_temperature_row(temp_consignes_section, row, temp_consignes_entries)

    add_temp_consignes_button = tk.Button(
        temp_consignes_section, text="Ajouter une ligne", command=add_temp_consignes_row,
        bg='#6e6e6e', fg='white', font=("Helvetica", 10, "bold"),
        relief="flat", padx=5, pady=2
    )
    add_temp_consignes_button.grid(row=1000, column=0, columnspan=8, pady=10)

    # Section Température Réelle
    temp_reelles_section = tk.LabelFrame(scrollable_frame, text="Température Réelle", bg='#2B2B2B', fg='white', font=("Helvetica", 14, "bold"))
    temp_reelles_section.pack(padx=10, pady=10, fill='x', expand=True)

    for idx, header in enumerate(temp_headers):
        tk.Label(temp_reelles_section, text=header, bg='#2B2B2B', fg='white', font=("Helvetica", 10, "bold")).grid(row=0, column=idx, padx=2, pady=5)

    temp_reelles_entries = []
    for row in range(1, 3):
        create_temperature_row(temp_reelles_section, row, temp_reelles_entries)

    def add_temp_reelles_row():
        row = len(temp_reelles_entries) + 1
        create_temperature_row(temp_reelles_section, row, temp_reelles_entries)

    add_temp_reelles_button = tk.Button(
        temp_reelles_section, text="Ajouter une ligne", command=add_temp_reelles_row,
        bg='#6e6e6e', fg='white', font=("Helvetica", 10, "bold"),
        relief="flat", padx=5, pady=2
    )
    add_temp_reelles_button.grid(row=1000, column=0, columnspan=8, pady=10)

    # Boutons Sauvegarder et Graphique dans button_frame (à gauche)
    save_button = tk.Button(
        button_frame,
        text="Sauvegarder les données",
        command=save_data,
        bg='#FFA500',
        fg='white',
        font=("Helvetica", 12, "bold"),
        relief="flat",
        padx=20,
        pady=10
    )
    save_button.pack(pady=10, fill='x')

    graph_button = tk.Button(
        button_frame,
        text="Afficher le Graphique",
        command=open_graph_window,
        bg='#007ACC',
        fg='white',
        font=("Helvetica", 12, "bold"),
        relief="flat",
        padx=20,
        pady=10
    )
    graph_button.pack(pady=10, fill='x')

    return frame
