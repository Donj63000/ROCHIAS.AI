# MODULES/Effectif.py

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import sqlite3
import json
import os

class Operator:
    def __init__(self, id, name, statut, service, start_time, end_time, absent, duration_seconds):
        self.id = id
        self.name = name
        self.statut = statut
        self.service = service
        self.start_time = datetime.strptime(start_time, '%H:%M').time() if start_time else None
        self.end_time = datetime.strptime(end_time, '%H:%M').time() if end_time else None
        self.absent = bool(absent)
        self.duration = timedelta(seconds=duration_seconds) if duration_seconds else timedelta(0)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'statut': self.statut,
            'service': self.service,
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else '',
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else '',
            'absent': self.absent,
            'duration_seconds': self.duration.total_seconds()
        }

class DatabaseManager:
    def __init__(self, db_path='effectif.db'):
        self.conn = sqlite3.connect(db_path)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        # Table Operators
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Operators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                statut TEXT NOT NULL DEFAULT 'Opérateur',
                service TEXT NOT NULL DEFAULT 'Cassage',
                start_time TEXT,
                end_time TEXT,
                absent INTEGER,
                duration_seconds REAL
            )
        ''')

        # Table OperatorNames
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS OperatorNames (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        ''')

        self.conn.commit()

        # Vérification et ajout des nouvelles colonnes si elles n'existent pas
        cursor.execute("PRAGMA table_info(Operators)")
        columns = [info[1] for info in cursor.fetchall()]
        if 'statut' not in columns:
            cursor.execute("ALTER TABLE Operators ADD COLUMN statut TEXT NOT NULL DEFAULT 'Opérateur'")
        if 'service' not in columns:
            cursor.execute("ALTER TABLE Operators ADD COLUMN service TEXT NOT NULL DEFAULT 'Cassage'")

        self.conn.commit()

    # Operators CRUD
    def add_operator(self, name, statut, service, start_time, end_time, absent, duration_seconds):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO Operators (name, statut, service, start_time, end_time, absent, duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, statut, service, start_time, end_time, int(absent), duration_seconds))
        self.conn.commit()
        return cursor.lastrowid

    def get_all_operators(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, name, statut, service, start_time, end_time, absent, duration_seconds
            FROM Operators
            ORDER BY name ASC
        ''')
        return cursor.fetchall()

    def update_operator(self, operator_id, name, statut, service, start_time, end_time, absent, duration_seconds):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE Operators
            SET name = ?, statut = ?, service = ?, start_time = ?, end_time = ?, absent = ?, duration_seconds = ?
            WHERE id = ?
        ''', (name, statut, service, start_time, end_time, int(absent), duration_seconds, operator_id))
        self.conn.commit()
        return True

    def delete_operator(self, operator_id):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM Operators WHERE id = ?', (operator_id,))
        self.conn.commit()

    # OperatorNames CRUD
    def add_operator_name(self, name):
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO OperatorNames (name)
                VALUES (?)
            ''', (name,))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            messagebox.showerror("Erreur", f"Le nom '{name}' existe déjà.")
            return None

    def get_all_operator_names(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT name FROM OperatorNames
            ORDER BY name ASC
        ''')
        return [row[0] for row in cursor.fetchall()]

    def delete_operator_name(self, name):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM OperatorNames WHERE name = ?', (name,))
        self.conn.commit()

    def close(self):
        self.conn.close()

    # Fonction pour obtenir toutes les informations des opérateurs sous forme de texte
    def get_all_operators_as_text(self):
        operators = self.get_all_operators()
        operators_text = "\n--- Liste des Opérateurs ---\n"
        for op in operators:
            name, statut, service, start_time, end_time, absent, duration_seconds = op[1], op[2], op[3], op[4], op[5], op[6], op[7]
            duration_str = str(timedelta(seconds=duration_seconds)).split('.')[0]  # Format HH:MM:SS
            absent_str = "Oui" if absent else "Non"

            operators_text += (f"Nom: {name}\n"
                               f"Statut: {statut}\n"
                               f"Service: {service}\n"
                               f"Heure début: {start_time}\n"
                               f"Heure fin: {end_time}\n"
                               f"Absent: {absent_str}\n"
                               f"Durée: {duration_str}\n"
                               "-"*40 + "\n")

        return operators_text

def get_frame(parent_frame, controller):
    colors = controller.colors  # Utilisation du dictionnaire de couleurs du contrôleur
    frame = tk.Frame(parent_frame, bg=colors['bg'])

    db = DatabaseManager()

    # Liste pour stocker les popups ouverts pour mise à jour des combobox
    if not hasattr(controller, 'effectif_popups'):
        controller.effectif_popups = []

    # Frame principale divisée en deux : Tableau des opérateurs et Consignes de Production
    main_content = tk.Frame(frame, bg=colors['bg'])
    main_content.pack(fill='both', expand=True, padx=10, pady=10)

    # Frame pour le tableau des opérateurs
    operators_frame = tk.Frame(main_content, bg=colors['bg'])
    operators_frame.pack(side='left', fill='both', expand=True)

    # Frame pour les consignes de production (si nécessaire)
    # Vous pouvez adapter cette partie selon vos besoins spécifiques
    consignes_frame = tk.Frame(main_content, bg=colors['bg'], width=300)
    consignes_frame.pack(side='right', fill='y', padx=(10, 0))

    # Fonctions auxiliaires pour créer des widgets avec le thème appliqué
    def create_label(parent, text, row, column, sticky='e', **kwargs):
        label = tk.Label(parent, text=text, bg=colors['bg'], fg=colors['fg'], **kwargs)
        label.grid(row=row, column=column, padx=10, pady=5, sticky=sticky)
        return label

    def create_entry(parent, textvariable, row, column, width=30, **kwargs):
        entry = tk.Entry(parent, textvariable=textvariable, bg=colors['entry_bg'], fg=colors['entry_fg'], width=width, **kwargs)
        entry.grid(row=row, column=column, padx=10, pady=5)
        return entry

    def create_text(parent, row, column, width=40, height=5, **kwargs):
        text_widget = tk.Text(parent, bg=colors['entry_bg'], fg=colors['entry_fg'], width=width, height=height, wrap='word', **kwargs)
        text_widget.grid(row=row, column=column, padx=10, pady=5)
        return text_widget

    def create_button(parent, text, command, row, column, width=20, bg_color=None, fg_color=None, **kwargs):
        button = tk.Button(parent, text=text, command=command, 
                           bg=bg_color if bg_color else colors['button_bg'], 
                           fg=fg_color if fg_color else colors['button_fg'], 
                           width=width, **kwargs)
        button.grid(row=row, column=column, pady=10)
        return button

    # Fonction pour rafraîchir le tableau des opérateurs
    def refresh_table():
        for item in tree.get_children():
            tree.delete(item)
        operators = db.get_all_operators()
        for op in operators:
            op_id, name, statut, service, start_time, end_time, absent, duration_seconds = op
            duration_str = str(timedelta(seconds=duration_seconds)).split('.')[0]  # Format HH:MM:SS
            tree.insert('', 'end', values=(
                name,
                statut,
                service,
                start_time if start_time else '',
                end_time if end_time else '',
                "Oui" if absent else "Non",
                duration_str
            ))

    # Fonction pour gérer la liste des noms d'opérateurs
    def manage_operator_names():
        popup = tk.Toplevel(frame)
        popup.title("Gérer la liste des opérateurs")
        popup.grab_set()
        popup.configure(bg=colors['bg'])

        # Liste des noms d'opérateurs
        names_frame = tk.Frame(popup, bg=colors['bg'])
        names_frame.pack(fill='both', expand=True, padx=10, pady=10)

        operator_names = db.get_all_operator_names()
        names_var = tk.StringVar(value=operator_names)

        names_listbox = tk.Listbox(names_frame, listvariable=names_var, height=15, width=30)
        names_listbox.pack(side='left', fill='both', expand=True)

        scrollbar = tk.Scrollbar(names_frame, orient="vertical")
        scrollbar.config(command=names_listbox.yview)
        scrollbar.pack(side='left', fill='y')

        names_listbox.config(yscrollcommand=scrollbar.set)

        # Frame pour les boutons
        buttons_frame = tk.Frame(popup, bg=colors['bg'])
        buttons_frame.pack(fill='x', padx=10, pady=10)

        def add_name():
            def save_name():
                new_name = name_var.get().strip()
                if new_name:
                    db.add_operator_name(new_name)
                    operator_names = db.get_all_operator_names()
                    names_var.set(operator_names)
                    add_popup.destroy()
                else:
                    messagebox.showwarning("Attention", "Le nom ne peut pas être vide.", parent=add_popup)

            add_popup = tk.Toplevel(popup)
            add_popup.title("Ajouter un nom")
            add_popup.grab_set()
            add_popup.configure(bg=colors['bg'])

            create_label(add_popup, "Nom:", row=0, column=0)
            name_var = tk.StringVar()
            create_entry(add_popup, name_var, row=0, column=1)

            save_button = tk.Button(add_popup, text="Ajouter", command=save_name, bg=colors['button_bg'], fg=colors['button_fg'])
            save_button.grid(row=1, column=0, columnspan=2, pady=10)

        def delete_name():
            selected_indices = names_listbox.curselection()
            if selected_indices:
                selected_name = names_listbox.get(selected_indices[0])
                confirm = messagebox.askyesno("Confirmer", f"Êtes-vous sûr de vouloir supprimer '{selected_name}' ?", parent=popup)
                if confirm:
                    db.delete_operator_name(selected_name)
                    operator_names = db.get_all_operator_names()
                    names_var.set(operator_names)
            else:
                messagebox.showwarning("Attention", "Veuillez sélectionner un nom à supprimer.", parent=popup)

        add_button = tk.Button(buttons_frame, text="Ajouter un nom", command=add_name, bg=colors['button_bg'], fg=colors['button_fg'])
        add_button.pack(side='left', padx=5)

        delete_button = tk.Button(buttons_frame, text="Supprimer le nom sélectionné", command=delete_name, bg=colors['button_bg'], fg=colors['button_fg'])
        delete_button.pack(side='left', padx=5)

    # Fonction pour ajouter un opérateur
    def add_operator():
        popup = tk.Toplevel(frame)
        popup.title("Ajouter Opérateur")
        popup.grab_set()
        popup.configure(bg=colors['bg'])

        # Ajout du popup à la liste pour mise à jour future
        controller.effectif_popups.append(popup)

        # Labels et Entrées
        create_label(popup, "Nom Opérateur:", row=0, column=0)
        name_var = tk.StringVar()
        name_entry = create_entry(popup, textvariable=name_var, row=0, column=1)

        create_label(popup, "Liste Opérateurs:", row=1, column=0)
        existing_operator_names = db.get_all_operator_names()
        operator_list_var = tk.StringVar()
        operator_combobox = ttk.Combobox(
            popup,
            textvariable=operator_list_var,
            values=existing_operator_names,
            state='readonly',
            width=28
        )
        operator_combobox.grid(row=1, column=1, padx=10, pady=5)
        operator_combobox.bind("<<ComboboxSelected>>", lambda event: name_var.set(operator_list_var.get()))

        # Bouton pour gérer la liste des opérateurs
        manage_names_button = tk.Button(popup, text="Gérer la liste des opérateurs", command=manage_operator_names, bg=colors['button_bg'], fg=colors['button_fg'])
        manage_names_button.grid(row=1, column=2, padx=5)

        # Radiobuttons pour Statut
        create_label(popup, "Statut:", row=2, column=0, sticky='ne')
        statut_frame = tk.Frame(popup, bg=colors['bg'])
        statut_frame.grid(row=2, column=1, padx=10, pady=5, sticky='w')
        statut_var = tk.StringVar(value="Opérateur")
        statut_options = ["Chef d'équipe", "Opérateur", "Intérimaire"]
        for option in statut_options:
            rb = tk.Radiobutton(statut_frame, text=option, variable=statut_var, value=option, bg=colors['bg'], fg=colors['fg'])
            rb.pack(side='left', padx=5)

        # Radiobuttons pour Service
        create_label(popup, "Service:", row=3, column=0, sticky='ne')
        service_frame = tk.Frame(popup, bg=colors['bg'])
        service_frame.grid(row=3, column=1, padx=10, pady=5, sticky='w')
        service_var = tk.StringVar(value="Cassage")
        service_options = ["Cassage", "Broyage", "Déshy"]
        for option in service_options:
            rb = tk.Radiobutton(service_frame, text=option, variable=service_var, value=option, bg=colors['bg'], fg=colors['fg'])
            rb.pack(side='left', padx=5)

        create_label(popup, "Heure de début (HH:MM):", row=4, column=0)
        start_time_var = tk.StringVar()
        start_time_entry = create_entry(popup, textvariable=start_time_var, row=4, column=1)

        create_label(popup, "Heure de fin (HH:MM):", row=5, column=0)
        end_time_var = tk.StringVar()
        end_time_entry = create_entry(popup, textvariable=end_time_var, row=5, column=1)

        absent_var = tk.BooleanVar()
        absent_check = tk.Checkbutton(
            popup,
            text="Absent ?",
            variable=absent_var,
            bg=colors['bg'],
            fg=colors['fg'],
            selectcolor=colors['bg']
        )
        absent_check.grid(row=6, column=1, padx=10, pady=5, sticky='w')

        def save_operator_func():
            name = name_var.get().strip()
            statut = statut_var.get()
            service = service_var.get()
            start_time_str = start_time_var.get().strip()
            end_time_str = end_time_var.get().strip()
            absent = absent_var.get()

            if not name:
                messagebox.showerror("Erreur", "Le nom de l'opérateur est requis.", parent=popup)
                return

            if not absent:
                try:
                    if start_time_str:
                        datetime.strptime(start_time_str, '%H:%M')
                    if end_time_str:
                        datetime.strptime(end_time_str, '%H:%M')
                except ValueError:
                    messagebox.showerror("Erreur", "Heure de début ou de fin invalide.", parent=popup)
                    return
            else:
                start_time_str = ''
                end_time_str = ''

            # Calculer la durée
            if not absent and start_time_str and end_time_str:
                start_dt = datetime.strptime(start_time_str, '%H:%M')
                end_dt = datetime.strptime(end_time_str, '%H:%M')
                if end_dt <= start_dt:
                    end_dt += timedelta(days=1)  # Gestion des shifts de nuit
                duration = end_dt - start_dt
                duration_seconds = duration.total_seconds()
            else:
                duration_seconds = 0

            # Ajouter l'opérateur à la base de données
            db.add_operator(name, statut, service, start_time_str, end_time_str, absent, duration_seconds)
            refresh_table()
            update_all_operator_dropdowns()

            popup.destroy()

        save_button = tk.Button(popup, text="Sauvegarder", command=save_operator_func, bg=colors['button_bg'], fg=colors['button_fg'], width=15)
        save_button.grid(row=7, column=0, columnspan=2, pady=10)

        # Fermer le popup proprement
        def on_popup_close():
            if popup in controller.effectif_popups:
                controller.effectif_popups.remove(popup)
            popup.destroy()

        # Correction de l'erreur AttributeError en utilisant winfo_toplevel()
        popup.winfo_toplevel().protocol("WM_DELETE_WINDOW", on_popup_close)

    # Fonction pour modifier un opérateur
    def modify_operator():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Sélectionner", "Veuillez sélectionner un opérateur à modifier.", parent=frame)
            return
        item = tree.item(selected)
        values = item['values']
        index = tree.index(selected)
        operators = db.get_all_operators()
        if index >= len(operators):
            messagebox.showerror("Erreur", "Opérateur sélectionné invalide.", parent=frame)
            return
        operator = operators[index]
        op_id, name, statut, service, start_time, end_time, absent, duration_seconds = operator

        popup = tk.Toplevel(frame)
        popup.title("Modifier Opérateur")
        popup.grab_set()
        popup.configure(bg=colors['bg'])

        # Ajout du popup à la liste pour mise à jour future
        controller.effectif_popups.append(popup)

        # Labels et Entrées
        create_label(popup, "Nom Opérateur:", row=0, column=0)
        name_var = tk.StringVar(value=name)
        name_entry = create_entry(popup, textvariable=name_var, row=0, column=1)

        create_label(popup, "Liste Opérateurs:", row=1, column=0)
        existing_operator_names = db.get_all_operator_names()
        operator_list_var = tk.StringVar(value=name)
        operator_combobox = ttk.Combobox(
            popup,
            textvariable=operator_list_var,
            values=existing_operator_names,
            state='readonly',
            width=28
        )
        operator_combobox.grid(row=1, column=1, padx=10, pady=5)
        operator_combobox.set(name)  # Sélectionner l'opérateur actuel
        operator_combobox.bind("<<ComboboxSelected>>", lambda event: name_var.set(operator_list_var.get()))

        # Bouton pour gérer la liste des opérateurs
        manage_names_button = tk.Button(popup, text="Gérer la liste des opérateurs", command=manage_operator_names, bg=colors['button_bg'], fg=colors['button_fg'])
        manage_names_button.grid(row=1, column=2, padx=5)

        # Radiobuttons pour Statut
        create_label(popup, "Statut:", row=2, column=0, sticky='ne')
        statut_frame = tk.Frame(popup, bg=colors['bg'])
        statut_frame.grid(row=2, column=1, padx=10, pady=5, sticky='w')
        statut_var = tk.StringVar(value=statut)
        statut_options = ["Chef d'équipe", "Opérateur", "Intérimaire"]
        for option in statut_options:
            rb = tk.Radiobutton(statut_frame, text=option, variable=statut_var, value=option, bg=colors['bg'], fg=colors['fg'])
            rb.pack(side='left', padx=5)

        # Radiobuttons pour Service
        create_label(popup, "Service:", row=3, column=0, sticky='ne')
        service_frame = tk.Frame(popup, bg=colors['bg'])
        service_frame.grid(row=3, column=1, padx=10, pady=5, sticky='w')
        service_var = tk.StringVar(value=service)
        service_options = ["Cassage", "Broyage", "Déshy"]
        for option in service_options:
            rb = tk.Radiobutton(service_frame, text=option, variable=service_var, value=option, bg=colors['bg'], fg=colors['fg'])
            rb.pack(side='left', padx=5)

        create_label(popup, "Heure de début (HH:MM):", row=4, column=0)
        start_time_var = tk.StringVar(value=start_time)
        start_time_entry = create_entry(popup, textvariable=start_time_var, row=4, column=1)

        create_label(popup, "Heure de fin (HH:MM):", row=5, column=0)
        end_time_var = tk.StringVar(value=end_time)
        end_time_entry = create_entry(popup, textvariable=end_time_var, row=5, column=1)

        absent_var = tk.BooleanVar(value=absent)
        absent_check = tk.Checkbutton(
            popup,
            text="Absent ?",
            variable=absent_var,
            bg=colors['bg'],
            fg=colors['fg'],
            selectcolor=colors['bg']
        )
        absent_check.grid(row=6, column=1, padx=10, pady=5, sticky='w')

        def save_modified_operator_func():
            new_name = name_var.get().strip()
            statut = statut_var.get()
            service = service_var.get()
            start_time_str = start_time_var.get().strip()
            end_time_str = end_time_var.get().strip()
            absent = absent_var.get()

            if not new_name:
                messagebox.showerror("Erreur", "Le nom de l'opérateur est requis.", parent=popup)
                return

            if not absent:
                try:
                    if start_time_str:
                        datetime.strptime(start_time_str, '%H:%M')
                    if end_time_str:
                        datetime.strptime(end_time_str, '%H:%M')
                except ValueError:
                    messagebox.showerror("Erreur", "Heure de début ou de fin invalide.", parent=popup)
                    return
            else:
                start_time_str = ''
                end_time_str = ''

            # Calculer la durée
            if not absent and start_time_str and end_time_str:
                start_dt = datetime.strptime(start_time_str, '%H:%M')
                end_dt = datetime.strptime(end_time_str, '%H:%M')
                if end_dt <= start_dt:
                    end_dt += timedelta(days=1)  # Gestion des shifts de nuit
                duration = end_dt - start_dt
                duration_seconds = duration.total_seconds()
            else:
                duration_seconds = 0

            # Mettre à jour l'opérateur dans la base de données
            db.update_operator(op_id, new_name, statut, service, start_time_str, end_time_str, absent, duration_seconds)
            refresh_table()
            update_all_operator_dropdowns()

            popup.destroy()

        save_button = tk.Button(popup, text="Sauvegarder", command=save_modified_operator_func, bg=colors['button_bg'], fg=colors['button_fg'], width=15)
        save_button.grid(row=7, column=0, columnspan=2, pady=10)

        # Fermer le popup proprement
        def on_popup_close():
            if popup in controller.effectif_popups:
                controller.effectif_popups.remove(popup)
            popup.destroy()

        # Correction de l'erreur AttributeError en utilisant winfo_toplevel()
        popup.winfo_toplevel().protocol("WM_DELETE_WINDOW", on_popup_close)

    # Fonction pour supprimer un opérateur
    def delete_operator():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Sélectionner", "Veuillez sélectionner un opérateur à supprimer.", parent=frame)
            return
        confirm = messagebox.askyesno("Confirmer", "Êtes-vous sûr de vouloir supprimer cet opérateur ?", parent=frame)
        if confirm:
            index = tree.index(selected)
            operators = db.get_all_operators()
            if index >= len(operators):
                messagebox.showerror("Erreur", "Opérateur sélectionné invalide.", parent=frame)
                return
            operator = operators[index]
            op_id = operator[0]
            db.delete_operator(op_id)
            refresh_table()
            update_all_operator_dropdowns()

    # Fonction pour gérer les doubles clics sur le Treeview
    def on_double_click(event):
        item = tree.identify_row(event.y)
        if item:
            tree.selection_set(item)
            modify_operator()

    tree = ttk.Treeview(operators_frame, columns=(
        "Nom Opérateur", "Statut", "Service", "Heure Début", "Heure Fin", "Absent ?", "Durée"), show='headings', selectmode='browse')
    for col in ["Nom Opérateur", "Statut", "Service", "Heure Début", "Heure Fin", "Absent ?", "Durée"]:
        tree.heading(col, text=col)
        if col == "Nom Opérateur":
            tree.column(col, width=150, anchor='center')
        elif col in ["Statut", "Service"]:
            tree.column(col, width=100, anchor='center')
        elif col in ["Heure Début", "Heure Fin", "Durée"]:
            tree.column(col, width=100, anchor='center')
        elif col == "Absent ?":
            tree.column(col, width=80, anchor='center')
    tree.pack(side='left', fill='both', expand=True, padx=(10, 0), pady=10)

    # Scrollbar pour le Treeview
    scrollbar = ttk.Scrollbar(operators_frame, orient="vertical", command=tree.yview)
    tree.configure(yscroll=scrollbar.set)
    scrollbar.pack(side='left', fill='y', pady=10)

    # Boutons d'action
    action_frame = tk.Frame(operators_frame, bg=colors['bg'], width=200)
    action_frame.pack(side='left', padx=10, pady=10, fill='y')

    add_button = tk.Button(action_frame, text="Ajouter Opérateur", command=add_operator, width=20, bg=colors['button_bg'], fg=colors['button_fg'])
    add_button.pack(pady=5)

    modify_button = tk.Button(action_frame, text="Modifier Opérateur", command=modify_operator, width=20, bg=colors['button_bg'], fg=colors['button_fg'])
    modify_button.pack(pady=5)

    delete_button = tk.Button(action_frame, text="Supprimer Opérateur", command=delete_operator, width=20, bg=colors['button_bg'], fg=colors['button_fg'])
    delete_button.pack(pady=5)

    manage_names_button_main = tk.Button(action_frame, text="Liste des opérateurs", command=manage_operator_names, width=20, bg=colors['button_bg'], fg=colors['button_fg'])
    manage_names_button_main.pack(pady=5)

    # Bouton "Sauvegarder" en orange pour sauvegarder les données au format JSON
    def save_operators_to_json():
        operators = db.get_all_operators()
        operators_list = []
        for op in operators:
            operator = Operator(*op)
            operators_list.append(operator.to_dict())

        # Définir le chemin de sauvegarde (effectif_data.json dans le répertoire principal)
        # On part du répertoire du fichier main.py, qui est un niveau au-dessus de MODULES
        main_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        json_file = os.path.join(main_dir, 'effectif_data.json')

        try:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(operators_list, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("Sauvegarde réussie", f"Les données ont été sauvegardées avec succès dans '{json_file}'.")
        except Exception as e:
            messagebox.showerror("Erreur de sauvegarde", f"Une erreur est survenue lors de la sauvegarde des données.\n\n{e}")

    save_button = tk.Button(
        action_frame,
        text="Sauvegarder",
        command=save_operators_to_json,
        width=20,
        bg='#FFA500',  # Orange
        fg='white'
    )
    save_button.pack(pady=5)

    # Suppression de la fonctionnalité "Exporter les opérateurs"
    # La ligne suivante est supprimée :
    # export_button = tk.Button(action_frame, text="Exporter les opérateurs", command=export_operators, width=20, bg=colors['button_bg'], fg=colors['button_fg'])
    # export_button.pack(pady=5)

    # Bind double-clic
    tree.bind("<Double-1>", on_double_click)

    # Rafraîchir le tableau au démarrage
    refresh_table()

    # Fonction pour mettre à jour toutes les combobox des opérateurs
    def update_all_operator_dropdowns():
        # Fermer et réouvrir tous les popups pour mettre à jour les combobox
        for popup in controller.effectif_popups:
            for widget in popup.winfo_children():
                if isinstance(widget, ttk.Combobox):
                    current_values = db.get_all_operator_names()
                    widget['values'] = current_values

    # Nettoyage lors de la fermeture de l'application
    def on_closing(event):
        db.close()

    # Correction de l'erreur AttributeError en utilisant winfo_toplevel()
    parent_frame.winfo_toplevel().protocol("WM_DELETE_WINDOW", on_closing)

    return frame
