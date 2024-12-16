# MODULES/visa.py

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import json
import pickle
from datetime import datetime
import shutil
import sqlite3

try:
    from PIL import Image, ImageTk
except ImportError:
    messagebox.showerror("Erreur", "La bibliothèque Pillow (PIL) n'est pas installée.")


def init_database(db_path):
    """Initialise la base de données SQLite et crée la table 'productions' si elle n'existe pas."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS productions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT,
        date TEXT,
        poste TEXT,
        contenu TEXT,
        timestamp TEXT
    )
    """)
    conn.commit()
    conn.close()


def load_all_data(main_dir):
    """Charge toutes les données nécessaires depuis les fichiers JSON / pickle, incluant désormais le broyage."""
    cassage_file = os.path.join(main_dir, 'cassage_data.json')
    sechoir_file = os.path.join(main_dir, 'sechoir_data.json')
    effectif_file = os.path.join(main_dir, 'effectif_data.json')

    # Chargement cassage
    cassage_data = []
    if os.path.exists(cassage_file):
        with open(cassage_file, 'r', encoding='utf-8') as f:
            cassage_data = json.load(f)

    # Chargement sechoir
    sechoir_data = []
    if os.path.exists(sechoir_file):
        with open(sechoir_file, 'r', encoding='utf-8') as f:
            sechoir_data = json.load(f)

    # Chargement effectif
    effectif_data = []
    if os.path.exists(effectif_file):
        with open(effectif_file, 'r', encoding='utf-8') as f:
            effectif_data = json.load(f)

    current_dir = os.path.dirname(__file__)
    qualite_enregistrements_file = os.path.join(current_dir, 'qualite_enregistrements.pkl')
    non_conformites_file = os.path.join(current_dir, 'non_conformites.pkl')
    maintenance_requests_file = os.path.join(current_dir, 'maintenance_requests.pkl')
    maintenance_ops_file = os.path.join(current_dir, 'maintenance_ops.pkl')

    qualite_enregistrements = []
    if os.path.exists(qualite_enregistrements_file):
        with open(qualite_enregistrements_file, 'rb') as f:
            qualite_enregistrements = pickle.load(f)

    all_non_conformities = []
    if os.path.exists(non_conformites_file):
        with open(non_conformites_file, 'rb') as f:
            all_non_conformities = pickle.load(f)

    maintenance_requests = []
    if os.path.exists(maintenance_requests_file):
        with open(maintenance_requests_file, 'rb') as f:
            maintenance_requests = pickle.load(f)

    maintenance_ops = []
    if os.path.exists(maintenance_ops_file):
        with open(maintenance_ops_file, 'rb') as f:
            maintenance_ops = pickle.load(f)

    production_state_file = os.path.join(main_dir, 'rochias_pod_calculator_state.pkl')
    production_state = {}
    if os.path.exists(production_state_file):
        with open(production_state_file, 'rb') as f:
            production_state = pickle.load(f)

    # Chargement des données de broyage
    broyage_data_file = os.path.join(current_dir, 'broyage_data.json')
    if os.path.exists(broyage_data_file):
        with open(broyage_data_file, 'r', encoding='utf-8') as f:
            broyage_list = json.load(f)
        if broyage_list:
            broyage_lines = ["--- Données de Broyage ---"]
            for prod in broyage_list:
                broyage_lines.append(
                    f"ID: {prod.get('ID','')}, Type: {prod.get('Type de Broyage','')}, Date: {prod.get('Date','')}, "
                    f"Poste: {prod.get('Poste','')}, Lot: {prod.get('Lot','')}, Produit: {prod.get('Produit','')}, "
                    f"Q. Rentrée: {prod.get('Quantité Rentrée','')}, Q. Fini: {prod.get('Quantité Fini','')}, Perte: {prod.get('Perte','')}"
                )
            broyage_data = "\n".join(broyage_lines)
        else:
            broyage_data = "Aucune production de broyage enregistrée."
    else:
        broyage_data = "Données de broyage non disponibles (fichier introuvable)."

    return (cassage_data, sechoir_data, qualite_enregistrements, all_non_conformities,
            effectif_data, production_state, broyage_data, maintenance_requests, maintenance_ops)


def write_fiche_production(write_func, nom, date_str, poste, production_state,
                           qualite_enregistrements, all_non_conformities, cassage_data,
                           sechoir_data, effectif_data, broyage_data,
                           maintenance_requests, maintenance_ops):
    """Écrit la fiche de production complète dans le rapport texte."""
    write_func("VISA PRODUCTION")
    write_func(f"Nom: {nom}")
    write_func(f"Date: {date_str}")
    write_func(f"Poste: {poste}")
    write_func("-" * 40)

    write_func("PRODUCTION (JEU) - État complet :")
    if production_state:
        for k, v in production_state.items():
            write_func(f"{k}: {v}")
    else:
        write_func("Aucune donnée de production disponible.")
    write_func("-" * 40)

    write_func("QUALITE :")
    if qualite_enregistrements:
        write_func("Enregistrements Qualité :")
        for enreg in qualite_enregistrements:
            write_func(f"Date: {enreg.get('date', '')}, Heure: {enreg.get('heure', '')}, Poste: {enreg.get('poste', '')}, Chef: {enreg.get('chef_equipe', '')}")
            write_func(f"Lot bleus: {enreg.get('lot_bleus', '')}, rouges: {enreg.get('lot_rouges', '')}, verts: {enreg.get('lot_verts', '')}")
            write_func("----")
    else:
        write_func("Aucun enregistrement qualité.")

    write_func("Non Conformités :")
    if all_non_conformities:
        for nc in all_non_conformities:
            write_func(f"Détectée par: {nc.get('detectee_par', '')}, Date/Heure: {nc.get('datetime', '')}, Lot: {nc.get('lot', '')}")
            write_func(f"Description: {nc.get('description', '')}")
            write_func(f"Action corrective: {nc.get('action_corrective_prise', '')}, Détail: {nc.get('action_corrective_detail', '')}")
            write_func(f"Nécessite Qualité: {nc.get('necessite_qualite', '')}, Clôturée: {nc.get('cloturee', '')}")
            write_func("----")
    else:
        write_func("Aucune non-conformité.")
    write_func("-" * 40)

    write_func("CASSAGE :")
    if cassage_data:
        write_func("Dernières entrées Cassage (jusqu'à 5 dernières) :")
        for entry in cassage_data[-5:]:
            write_func(f"Lot: {entry.get('lot_num', '')}, Ail Entree: {entry.get('ail_entree', '')}, Ail Sortie: {entry.get('ail_sortie', '')}, Perte: {entry.get('perte', '')}")
            write_func(f"Production: {entry.get('temps_production_display', '')}, Nettoyage: {entry.get('temps_nettoyage_display', '')}, Poste: {entry.get('poste', '')}")
            write_func(f"Panne: {entry.get('panne', '')}, Temps Panne: {entry.get('temps_panne', '')}")
            write_func(f"Observation: {entry.get('observation', '')}, Date: {entry.get('date', '')}, Heure: {entry.get('heure', '')}")
            write_func("----")
    else:
        write_func("Aucune donnée de cassage.")
    write_func("-" * 40)

    write_func("SECHOIR :")
    if sechoir_data:
        write_func("Entrées du Séchoir :")
        for idx, entry in enumerate(sechoir_data, start=1):
            write_func(f"--- Entrée Séchoir n°{idx} ---")
            timestamp = entry.get('timestamp', '')
            four_data = entry.get('four_data', {})
            produit = four_data.get('produit', {})
            tapis = four_data.get('tapis', [])
            temps_consignes = four_data.get('temperatures_consignes', [])
            temps_reelles = four_data.get('temperatures_reelles', [])

            write_func(f"Horodatage: {timestamp}")
            write_func("Produit :")
            write_func(f"  Type de produit: {produit.get('type_produit', '')}")
            write_func(f"  Humide: {produit.get('humide', '')}")
            write_func(f"  Observations: {produit.get('observations', '')}")

            write_func("Tapis (Vitesses) :")
            if tapis:
                for t in tapis:
                    write_func(f"  Heure: {t.get('heure','')}, Vitesse Stockeur: {t.get('vit_stockeur','')} Hz, "
                               f"Tapis1: {t.get('tapis1','')} Hz, Tapis2: {t.get('tapis2','')} Hz, Tapis3: {t.get('tapis3','')} Hz")
            else:
                write_func("  Aucune donnée de tapis.")

            write_func("Températures Consigne :")
            if temps_consignes:
                for tc in temps_consignes:
                    write_func(f"  Heure: {tc.get('heure','')}, CELs: {tc.get('cels','')}, Air Neuf: {tc.get('air_neuf','')}")

            else:
                write_func("  Aucune donnée de température consigne.")

            write_func("Températures Réelles :")
            if temps_reelles:
                for tr in temps_reelles:
                    write_func(f"  Heure: {tr.get('heure','')}, CELs: {tr.get('cels','')}, Air Neuf: {tr.get('air_neuf','')}")
            else:
                write_func("  Aucune donnée de température réelle.")

            write_func("--------------------------------")
    else:
        write_func("Aucune donnée de séchoir.")
    write_func("-" * 40)

    write_func("EFFECTIF :")
    if effectif_data:
        write_func("Liste des opérateurs :")
        for op in effectif_data:
            write_func(f"Nom: {op.get('name', '')}, Statut: {op.get('statut', '')}, Service: {op.get('service', '')}")
            write_func(f"Absent: {'Oui' if op.get('absent', False) else 'Non'}, Start: {op.get('start_time', '')}, End: {op.get('end_time', '')}")
            write_func("----")
    else:
        write_func("Aucune donnée d'effectif.")
    write_func("-" * 40)

    write_func("BROYAGE :")
    write_func(broyage_data)
    write_func("-" * 40)

    write_func("MAINTENANCE (Demandes) :")
    if maintenance_requests:
        order = ["Critique", "Important", "Modéré", "Faible"]
        maintenance_requests_sorted = sorted(maintenance_requests, key=lambda r: order.index(r.get('gravite', 'Faible')))
        for req in maintenance_requests_sorted:
            write_func(f"Gravité: {req.get('gravite', '')}, Equipement: {req.get('equipement', '')} - {req.get('description', '')}")
            write_func(f"Nom: {req.get('nom', '')}, Heure: {req.get('heure', '')}, Production stoppée: {req.get('production_stop', '')}, Temps arrêt: {req.get('temps_stop', '')}")
            write_func(f"Actions: {req.get('actions', '')}, Date Demande: {req.get('datetime', '')}")
            write_func("----")
    else:
        write_func("Aucune demande de maintenance.")
    write_func("-" * 40)

    write_func("MAINTENANCE (Opérations) :")
    if maintenance_ops:
        for op in maintenance_ops:
            write_func(f"Equipement: {op.get('equipement', '')}, Maintenance: {op.get('maintenance', '')}")
            write_func(f"Changements: {op.get('changements', '')}, Provisoire: {op.get('provisoire', '')}")
            write_func(f"Nom Tech: {op.get('nom', '')}, Date: {op.get('date', '')}, Heure: {op.get('heure', '')}, Durée(min): {op.get('duree', '')}")
            write_func(f"Enregistré le: {op.get('datetime', '')}")
            write_func("----")
    else:
        write_func("Aucune opération de maintenance.")


def save_to_database(db_path, nom, date_str, poste, contenu):
    """Enregistre le rapport dans la base de données SQLite."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO productions (nom, date, poste, contenu, timestamp) VALUES (?, ?, ?, ?, ?)",
                   (nom, date_str, poste, contenu, timestamp))
    conn.commit()
    conn.close()


def archive_files(txt_path, main_dir):
    """Archive le fichier texte généré et les fichiers de données dans le répertoire 'Archive-Prod'."""
    archive_dir = os.path.join(main_dir, "Archive-Prod")
    if not os.path.exists(archive_dir):
        os.makedirs(archive_dir)

    cassage_file = os.path.join(main_dir, 'cassage_data.json')
    sechoir_file = os.path.join(main_dir, 'sechoir_data.json')
    effectif_file = os.path.join(main_dir, 'effectif_data.json')

    current_dir = os.path.dirname(__file__)
    qualite_enregistrements_file = os.path.join(current_dir, 'qualite_enregistrements.pkl')
    non_conformites_file = os.path.join(current_dir, 'non_conformites.pkl')
    maintenance_requests_file = os.path.join(current_dir, 'maintenance_requests.pkl')
    maintenance_ops_file = os.path.join(current_dir, 'maintenance_ops.pkl')

    files_to_move = [
        cassage_file,
        sechoir_file,
        effectif_file,
        qualite_enregistrements_file,
        non_conformites_file,
        maintenance_requests_file,
        maintenance_ops_file
    ]

    base_name = os.path.basename(txt_path)
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_txt_name = f"{os.path.splitext(base_name)[0]}_{now_str}.txt"
    txt_archive_path = os.path.join(archive_dir, new_txt_name)
    shutil.copy(txt_path, txt_archive_path)

    for f in files_to_move:
        if os.path.exists(f):
            dest = os.path.join(archive_dir, os.path.basename(f))
            shutil.move(f, dest)


def generate_txt(nom, date_str, poste, main_dir):
    """Génère le fichier texte du rapport et le renvoie avec son contenu."""
    (cassage_data, sechoir_data, qualite_enregistrements, all_non_conformities,
     effectif_data, production_state, broyage_data, maintenance_requests, maintenance_ops) = load_all_data(main_dir)

    file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
    if not file_path:
        raise Exception("Aucun fichier texte n'a été sélectionné pour la sauvegarde.")

    lines = []
    def mem_write_line(text):
        lines.append(text)

    write_fiche_production(mem_write_line, nom, date_str, poste, production_state,
                           qualite_enregistrements, all_non_conformities, cassage_data,
                           sechoir_data, effectif_data, broyage_data, maintenance_requests, maintenance_ops)

    contenu = "\n".join(lines)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(contenu)

    return file_path, contenu


def get_frame(parent_frame, controller):
    """Crée et retourne le frame principal pour le module VISA, avec un style plus professionnel."""
    # Couleurs et style
    bg_color = '#2B2B2B'      # Fond général anthracite
    text_bg_color = '#ECECEC' # Fond du texte (gris clair)
    button_color = '#009688'  # Vert/bleu doux pour les boutons
    font_family = 'Helvetica'

    frame = tk.Frame(parent_frame, bg=bg_color)

    main_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    db_path = os.path.join(main_dir, "visa.db")
    init_database(db_path)

    # Chargement de l'image VISA
    image_path = os.path.join(os.path.dirname(__file__), 'visa.png')
    if os.path.exists(image_path):
        from PIL import Image, ImageTk
        img = Image.open(image_path)
        img = img.resize((100, 100), Image.LANCZOS)
        visa_image = ImageTk.PhotoImage(img)
    else:
        visa_image = None

    # Définition d'un style ttk
    style = ttk.Style()
    style.theme_use('clam')

    # Style des boutons
    style.configure("TButton",
                    background=button_color,
                    foreground='white',
                    font=(font_family, 12, 'bold'),
                    padding=6)
    style.map("TButton",
              background=[('active', '#00796B'), ('pressed', '#004D40')])  # nuances plus sombres au survol/clique

    # Style des labels
    style.configure("TLabel",
                    background=bg_color,
                    foreground='white',
                    font=(font_family, 12))

    # Style du séparateur
    style.configure("TSeparator", background='#444444')

    def open_visa_form():
        popup = tk.Toplevel(frame)
        popup.title("Formulaire VISA")
        popup.configure(bg=bg_color)

        # Label et entry nom
        ttk.Label(popup, text="Nom :").grid(row=0, column=0, padx=10, pady=5, sticky='e')
        nom_var = tk.StringVar()
        tk.Entry(popup, textvariable=nom_var, bg='white', fg='black', font=(font_family, 11)).grid(row=0, column=1, padx=10, pady=5, sticky='w')

        # Label et entry date
        ttk.Label(popup, text="Date (YYYY-MM-DD):").grid(row=1, column=0, padx=10, pady=5, sticky='e')
        date_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        tk.Entry(popup, textvariable=date_var, bg='white', fg='black', font=(font_family, 11)).grid(row=1, column=1, padx=10, pady=5, sticky='w')

        # Label et combobox poste
        ttk.Label(popup, text="Poste :").grid(row=2, column=0, padx=10, pady=5, sticky='e')
        poste_var = tk.StringVar(value="Journée")
        poste_options = ["Journée", "Matin", "Après-midi", "Nuit"]
        poste_cb = ttk.Combobox(popup, textvariable=poste_var, values=poste_options, state="readonly", font=(font_family, 11))
        poste_cb.grid(row=2, column=1, padx=10, pady=5, sticky='w')
        poste_cb.current(0)

        def validate_form():
            nom = nom_var.get().strip()
            date_str = date_var.get().strip()
            poste = poste_var.get().strip()

            if not nom or not date_str or not poste:
                messagebox.showerror("Erreur", "Veuillez remplir tous les champs.")
                return

            confirm = messagebox.askyesno("Confirmation", "Valider le visa enregistrera la production. Continuer ?")
            if confirm:
                try:
                    txt_path, contenu = generate_txt(nom, date_str, poste, main_dir)
                    archive_files(txt_path, main_dir)
                    save_to_database(db_path, nom, date_str, poste, contenu)
                    messagebox.showinfo("Succès", "Les données ont été archivées avec succès.")
                    popup.destroy()
                except Exception as e:
                    messagebox.showerror("Erreur", f"Erreur lors de la génération/archivage : {e}")

        ttk.Button(popup, text="Valider", command=validate_form).grid(row=3, column=0, columnspan=2, pady=10)

    def show_history():
        hist_popup = tk.Toplevel(frame)
        hist_popup.title("Historique des VISAs")
        hist_popup.configure(bg=bg_color)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, nom, date, poste, timestamp FROM productions ORDER BY id DESC")
        rows = cursor.fetchall()
        conn.close()

        columns = ("id", "nom", "date", "poste", "timestamp")
        tree = ttk.Treeview(hist_popup, columns=columns, show="headings", height=10)
        tree.heading("id", text="ID")
        tree.heading("nom", text="Nom")
        tree.heading("date", text="Date")
        tree.heading("poste", text="Poste")
        tree.heading("timestamp", text="Enregistré le")

        for col in columns:
            tree.column(col, anchor='center')

        for r in rows:
            tree.insert("", tk.END, values=r)

        tree.pack(fill='both', expand=True, padx=10, pady=10)

        def show_details():
            selected = tree.selection()
            if not selected:
                return
            item = tree.item(selected)
            prod_id = item['values'][0]

            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("SELECT contenu FROM productions WHERE id=?", (prod_id,))
            result = c.fetchone()
            conn.close()

            if result:
                contenu = result[0]
                detail_popup = tk.Toplevel(hist_popup)
                detail_popup.title(f"Détails de la production ID {prod_id}")
                detail_popup.configure(bg=bg_color)

                text_frame = tk.Frame(detail_popup, bg=bg_color)
                text_frame.pack(fill='both', expand=True, padx=10, pady=10)

                scrollbar = ttk.Scrollbar(text_frame)
                scrollbar.pack(side='right', fill='y')

                text_widget = tk.Text(text_frame, wrap='word', bg='white', fg='black', yscrollcommand=scrollbar.set, font=(font_family, 11))
                text_widget.pack(fill='both', expand=True)
                scrollbar.config(command=text_widget.yview)

                text_widget.insert('end', contenu)
                text_widget.config(state='disabled')

        btn_frame = tk.Frame(hist_popup, bg=bg_color)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Voir Détails", command=show_details).pack()

    def refresh_display():
        (cassage_data, sechoir_data, qualite_enregistrements, all_non_conformities,
         effectif_data, production_state, broyage_data, maintenance_requests, maintenance_ops) = load_all_data(main_dir)

        text_widget.config(state='normal')
        text_widget.delete('1.0', 'end')
        write_fiche_production(write_text_line, "NOM NON DEFINI", "DATE NON DEFINIE", "POSTE NON DEFINI",
                               production_state, qualite_enregistrements, all_non_conformities,
                               cassage_data, sechoir_data, effectif_data, broyage_data,
                               maintenance_requests, maintenance_ops)
        text_widget.config(state='disabled')

    # En-tête (logo + titre)
    header_frame = tk.Frame(frame, bg=bg_color)
    header_frame.pack(pady=10)

    if visa_image:
        img_label = tk.Label(header_frame, image=visa_image, bg=bg_color)
        img_label.pack(side='left', padx=10)
        frame.visa_image = visa_image

    tk.Label(header_frame, text="Module VISA", bg=bg_color, fg='white', font=(font_family, 18, "bold")).pack(side='left', padx=10)

    # Frame des boutons (Valider VISA, Historique, Rafraîchir)
    button_frame = tk.Frame(frame, bg=bg_color)
    button_frame.pack(pady=10)

    ttk.Button(button_frame, text="Valider le VISA", command=open_visa_form).pack(side='left', padx=10)
    ttk.Button(button_frame, text="Historique", command=show_history).pack(side='left', padx=10)
    ttk.Button(button_frame, text="Rafraîchir", command=refresh_display).pack(side='left', padx=10)

    # Séparateur horizontal
    sep = ttk.Separator(frame, orient='horizontal')
    sep.pack(fill='x', pady=10)

    # Chargement initial des données pour l'affichage du texte
    (cassage_data, sechoir_data, qualite_enregistrements, all_non_conformities,
     effectif_data, production_state, broyage_data, maintenance_requests, maintenance_ops) = load_all_data(main_dir)

    # Zone de texte (rapport)
    text_frame = tk.Frame(frame, bg=bg_color)
    text_frame.pack(fill='both', expand=True, padx=10, pady=10)

    scrollbar = ttk.Scrollbar(text_frame)
    scrollbar.pack(side='right', fill='y')

    text_widget = tk.Text(text_frame, wrap='word', bg=text_bg_color, fg='black', yscrollcommand=scrollbar.set, font=(font_family, 11))
    text_widget.pack(fill='both', expand=True)
    scrollbar.config(command=text_widget.yview)

    def write_text_line(text):
        text_widget.insert('end', text + '\n')

    # Écrire une version par défaut (sans nom/date/poste définis)
    write_fiche_production(write_text_line, "NOM NON DEFINI", "DATE NON DEFINIE", "POSTE NON DEFINI",
                           production_state, qualite_enregistrements, all_non_conformities, cassage_data,
                           sechoir_data, effectif_data, broyage_data, maintenance_requests, maintenance_ops)
    text_widget.config(state='disabled')

    return frame
