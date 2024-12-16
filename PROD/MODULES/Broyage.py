# MODULES/Broyage.py

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import json
import os
import traceback


class ProductionManager:
    """
    Gère la logique métier liée aux productions.
    """

    def __init__(self):
        self.productions = []

    def generate_production_id(self):
        """Génère un ID unique basé sur la longueur de la liste des productions."""
        return len(self.productions) + 1

    def add_production(self, data):
        """
        Ajoute une production après validation.
        data : dict contenant :
            "Type de Broyage", "Date", "Poste", "Lot",
            "Produit", "Quantité Rentrée", "Quantité Fini", "Perte"
        """
        if not self.validate_data(data):
            raise ValueError("Les données de la production ne sont pas valides.")
        data["ID"] = self.generate_production_id()
        self.productions.append(data)
        return data["ID"]

    def edit_production(self, prod_id, data):
        """Modifie une production existante."""
        if not self.validate_data(data):
            raise ValueError("Les données de la production ne sont pas valides.")

        for p in self.productions:
            if p["ID"] == prod_id:
                p.update(data)
                return True
        raise ValueError("Production non trouvée.")

    def delete_production(self, prod_id):
        """Supprime une production par ID."""
        before_count = len(self.productions)
        self.productions = [p for p in self.productions if p["ID"] != prod_id]
        return len(self.productions) < before_count

    def get_production(self, prod_id):
        """Récupère une production par ID."""
        for p in self.productions:
            if p["ID"] == prod_id:
                return p
        return None

    def validate_data(self, data):
        """Valide les données d'une production."""
        if not self.validate_date(data.get("Date", "")):
            return False

        for field in ["Quantité Rentrée", "Quantité Fini", "Perte"]:
            val = data.get(field, None)
            if val is None or not isinstance(val, (int, float)) or val < 0:
                return False

        if not data.get("Lot"):
            return False

        if not data.get("Type de Broyage"):
            return False

        if not data.get("Poste"):
            return False

        return True

    @staticmethod
    def validate_date(date_str):
        """Vérifie que la date est au format YYYY-MM-DD."""
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False


class BroyageController:
    """
    Contrôleur faisant le lien entre la vue (BroyageView) et le modèle (ProductionManager).
    """

    def __init__(self):
        self.manager = ProductionManager()
        self.view = None

    def set_view(self, view):
        self.view = view

    def add_production(self, data):
        """Ajoute une production via le manager et met à jour la vue."""
        try:
            prod_id = self.manager.add_production(data)
            self.view.add_tree_item(self.manager.get_production(prod_id))
            messagebox.showinfo("Succès", "Production enregistrée avec succès.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'enregistrement : {e}")
            traceback.print_exc()

    def update_production(self, prod_id, data):
        """Met à jour une production existante."""
        try:
            self.manager.edit_production(prod_id, data)
            updated_prod = self.manager.get_production(prod_id)
            self.view.update_tree_item(updated_prod)
            messagebox.showinfo("Succès", "Production mise à jour avec succès.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la mise à jour : {e}")
            traceback.print_exc()

    def delete_production(self, prod_id):
        """Supprime une production."""
        confirm = messagebox.askyesno("Confirmation", "Voulez-vous vraiment supprimer cette production ?")
        if not confirm:
            return
        if self.manager.delete_production(prod_id):
            self.view.remove_tree_item(prod_id)
            messagebox.showinfo("Succès", "Production supprimée avec succès.")
        else:
            messagebox.showerror("Erreur", "Production introuvable.")

    def get_production_details(self, prod_id):
        """Récupère les détails d'une production."""
        return self.manager.get_production(prod_id)

    def save_productions(self):
        """Sauvegarde toutes les productions dans un fichier JSON."""
        data = self.manager.productions
        file_path = os.path.join(os.path.dirname(__file__), 'broyage_data.json')
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("Sauvegarde", f"Les données de broyage ont été sauvegardées dans {file_path}.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de sauvegarder les données: {e}")


class BroyageView:
    """
    Vue Tkinter gérant l'affichage des données, des fenêtres de création/édition et le Treeview.
    """

    def __init__(self, parent, controller, colors=None):
        self.parent = parent
        self.controller = controller
        self.controller.set_view(self)
        self.colors = self.get_colors(colors)
        self.tree = None
        # Pour le clignotement du bouton "Sauvegarder"
        self.blink_colors = ["red", "blue", "green", "yellow", "orange", "purple", "pink", "cyan"]
        self.blink_index = 0

        self.create_ui()

    def get_colors(self, user_colors):
        default_colors = {
            'bg': '#1C1C1C',
            'fg': '#F0F0F0',
            'button_bg': '#333333',
            'button_fg': '#FFFFFF',
            'entry_bg': '#2E2E2E',
            'entry_fg': '#FFFFFF',
            'label_fg': '#F0F0F0',
            'tree_bg': '#1C1C1C',
            'tree_fg': '#F0F0F0',
            'tree_field_bg': '#1C1C1C',
            'tree_selected_bg': '#1F7A3A',
            'tree_selected_fg': '#FFFFFF',
            'heading_bg': '#1F7A3A',
            'heading_fg': '#FFFFFF'
        }

        if user_colors and isinstance(user_colors, dict):
            default_colors.update(user_colors)
        return default_colors

    def create_ui(self):
        top_frame = tk.Frame(self.parent, bg=self.colors['bg'])
        top_frame.pack(pady=10)

        create_button = tk.Button(top_frame, text="Créer Production",
                                  command=self.open_create_window,
                                  bg=self.colors['button_bg'], fg=self.colors['button_fg'])
        create_button.pack(side='left', padx=5)

        # Bouton Sauvegarder (clignotant)
        self.save_button = tk.Button(top_frame, text="Sauvegarder",
                                     command=self.controller.save_productions,
                                     bg=self.colors['button_bg'], fg=self.colors['button_fg'])
        self.save_button.pack(side='left', padx=5)
        self.blink_button()  # Lancer le clignotement du bouton

        table_frame = tk.Frame(self.parent, bg=self.colors['bg'])
        table_frame.pack(fill='both', expand=True, padx=10, pady=10)

        columns = ("ID", "Type de Broyage", "Date", "Poste", "Lot", "Produit",
                   "Quantité Rentrée", "Quantité Fini", "Perte")

        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', style="Treeview")

        for col in columns:
            self.tree.heading(col, text=col, anchor='center')
            self.tree.column(col, anchor='center', width=110)

        self.configure_treeview_style()

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        self.tree.pack(fill='both', expand=True)

        button_frame = tk.Frame(self.parent, bg=self.colors['bg'])
        button_frame.pack(pady=10)

        edit_button = tk.Button(button_frame, text="Modifier Production",
                                command=self.open_edit_window,
                                bg=self.colors['button_bg'], fg=self.colors['button_fg'])
        edit_button.pack(side='left', padx=5)

        delete_button = tk.Button(button_frame, text="Supprimer Production",
                                  command=self.delete_production_action,
                                  bg=self.colors['button_bg'], fg=self.colors['button_fg'])
        delete_button.pack(side='left', padx=5)

        self.tree.bind("<Double-1>", self.show_production_details)

    def configure_treeview_style(self):
        style = ttk.Style()
        style.theme_use('clam')

        style.configure("Treeview",
                        background=self.colors['tree_bg'],
                        fieldbackground=self.colors['tree_field_bg'],
                        foreground=self.colors['tree_fg'],
                        rowheight=25,
                        bordercolor=self.colors['bg'],
                        borderwidth=0)
        style.configure("Treeview.Heading",
                        background=self.colors['heading_bg'],
                        foreground=self.colors['heading_fg'],
                        font=('Helvetica', 10, 'bold'))
        style.map('Treeview',
                  background=[('selected', self.colors['tree_selected_bg'])],
                  foreground=[('selected', self.colors['tree_selected_fg'])])

    def blink_button(self):
        """Fait clignoter le bouton Sauvegarder."""
        self.save_button.config(bg=self.blink_colors[self.blink_index])
        self.blink_index = (self.blink_index + 1) % len(self.blink_colors)
        self.parent.after(500, self.blink_button)

    def open_create_window(self):
        ProductionWindow(self.parent, self.controller, self.colors, mode="create")

    def open_edit_window(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Avertissement", "Veuillez sélectionner une production à modifier.")
            return
        item = self.tree.item(selection[0])
        prod_id = item['values'][0]
        ProductionWindow(self.parent, self.controller, self.colors, mode="edit", prod_id=prod_id)

    def delete_production_action(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Avertissement", "Veuillez sélectionner une production à supprimer.")
            return
        item = self.tree.item(selection[0])
        prod_id = item['values'][0]
        self.controller.delete_production(prod_id)

    def show_production_details(self, event):
        item_id = self.tree.focus()
        if not item_id:
            return
        values = self.tree.item(item_id, 'values')
        prod_id = values[0]
        prod = self.controller.get_production_details(prod_id)
        if prod:
            self.display_details_window(prod)

    def display_details_window(self, prod):
        detail_win = tk.Toplevel(self.parent)
        detail_win.title("Détails de la Production")
        detail_win.configure(bg=self.colors['bg'])
        detail_win.grab_set()

        row = 0
        for key, val in prod.items():
            tk.Label(detail_win, text=f"{key}:", bg=self.colors['bg'], fg=self.colors['label_fg'], anchor='e') \
                .grid(row=row, column=0, sticky='e', padx=10, pady=5)
            tk.Label(detail_win, text=str(val), bg=self.colors['bg'], fg=self.colors['fg'], anchor='w') \
                .grid(row=row, column=1, sticky='w', padx=10, pady=5)
            row += 1

        tk.Button(detail_win, text="Fermer", command=detail_win.destroy,
                  bg=self.colors['button_bg'], fg=self.colors['button_fg']).grid(row=row, column=0, columnspan=2, pady=10)

    def add_tree_item(self, production):
        self.tree.insert('', 'end', values=(
            production["ID"], production["Type de Broyage"], production["Date"],
            production["Poste"], production["Lot"], production["Produit"],
            production["Quantité Rentrée"], production["Quantité Fini"], production["Perte"]
        ))

    def update_tree_item(self, production):
        for item_id in self.tree.get_children():
            vals = self.tree.item(item_id, 'values')
            if vals and vals[0] == production["ID"]:
                self.tree.item(item_id, values=(
                    production["ID"], production["Type de Broyage"], production["Date"],
                    production["Poste"], production["Lot"], production["Produit"],
                    production["Quantité Rentrée"], production["Quantité Fini"], production["Perte"]
                ))
                break

    def remove_tree_item(self, prod_id):
        for item_id in self.tree.get_children():
            vals = self.tree.item(item_id, 'values')
            if vals and vals[0] == prod_id:
                self.tree.delete(item_id)
                break


class ProductionWindow:
    """
    Fenêtre de création/édition d'une production.
    """

    def __init__(self, parent, controller, colors, mode="create", prod_id=None):
        self.parent = parent
        self.controller = controller
        self.colors = colors
        self.mode = mode
        self.prod_id = prod_id
        self.init_vars()

        if mode == "edit" and prod_id is not None:
            prod = self.controller.get_production_details(prod_id)
            if not prod:
                messagebox.showerror("Erreur", "Production non trouvée.")
                return
            self.load_data(prod)

        self.create_window()

    def init_vars(self):
        self.broyage_type = tk.StringVar(value="Urshell")
        self.production_date = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        self.shift = tk.StringVar(value="Matin")
        self.lot_number = tk.StringVar()
        self.quantite_rentree = tk.DoubleVar(value=0.0)
        self.quantite_fini = tk.DoubleVar(value=0.0)
        self.perte = tk.DoubleVar(value=0.0)

        self.poudre_sac = tk.StringVar()
        self.poudre_poid_sac = tk.StringVar()
        self.poudre_poid_dernier_sac = tk.StringVar()

        self.semoule_2060_sac = tk.StringVar()
        self.semoule_2060_poid_sac = tk.StringVar()
        self.semoule_2060_poid_dernier_sac = tk.StringVar()

        self.semoule_14_sac = tk.StringVar()
        self.semoule_14_poid_sac = tk.StringVar()
        self.semoule_14_poid_dernier_sac = tk.StringVar()

        self.ail_var = tk.BooleanVar()
        self.oignon_var = tk.BooleanVar()
        self.echalote_var = tk.BooleanVar()

    def load_data(self, prod):
        self.broyage_type.set(prod["Type de Broyage"])
        self.production_date.set(prod["Date"])
        self.shift.set(prod["Poste"])
        self.lot_number.set(prod["Lot"])
        self.quantite_rentree.set(prod["Quantité Rentrée"])
        self.quantite_fini.set(prod["Quantité Fini"])
        self.perte.set(prod["Perte"])

        produits = prod["Produit"].split(", ")
        self.ail_var.set("Ail" in produits)
        self.oignon_var.set("Oignon" in produits)
        self.echalote_var.set("Echalote" in produits)

    def create_window(self):
        self.win = tk.Toplevel(self.parent)
        self.win.title("Créer Production" if self.mode == "create" else "Modifier Production")
        self.win.configure(bg=self.colors['bg'])
        self.win.grab_set()

        main_frame = tk.Frame(self.win, bg=self.colors['bg'])
        main_frame.pack(padx=10, pady=10, fill='both', expand=True)

        self.create_production_fields(main_frame)
        self.create_specific_frames(main_frame)
        self.create_buttons(main_frame)
        self.set_trace_for_calculation()
        self.toggle_fields()

    def create_labeled_entry(self, parent, label_text, var, row, column=0, width=17, state='normal'):
        tk.Label(parent, text=label_text, bg=self.colors['bg'],
                 fg=self.colors['label_fg']).grid(row=row, column=column, sticky='e', pady=2)
        entry = tk.Entry(parent, textvariable=var, bg=self.colors['entry_bg'],
                         fg=self.colors['entry_fg'], width=width, state=state)
        entry.grid(row=row, column=column+1, pady=2, padx=5)
        return entry

    def create_production_fields(self, main_frame):
        title_label = tk.Label(main_frame, text="Type de Broyage",
                               bg=self.colors['bg'], fg=self.colors['label_fg'], font=('Helvetica', 10, 'bold'))
        title_label.grid(row=0, column=0, padx=10, pady=(0,5), sticky='w')

        type_frame = tk.Frame(main_frame, bg=self.colors['bg'], bd=0, highlightthickness=0, relief='flat')
        type_frame.grid(row=1, column=0, padx=10, pady=5, sticky='w')
        for tb in ["Urshell", "Micro", "Marteau"]:
            ttk.Radiobutton(type_frame, text=tb, variable=self.broyage_type, value=tb).pack(side='left', padx=5, pady=5)

        datetime_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        datetime_frame.grid(row=2, column=0, padx=10, pady=5, sticky='w')
        self.create_labeled_entry(datetime_frame, "Date (YYYY-MM-DD):", self.production_date, row=0)
        tk.Label(datetime_frame, text="Poste:", bg=self.colors['bg'], fg=self.colors['label_fg']) \
            .grid(row=1, column=0, sticky='e', pady=2)
        shift_menu = ttk.Combobox(datetime_frame, textvariable=self.shift,
                                  values=["Matin", "Après-midi", "Nuit"], state="readonly", width=17)
        shift_menu.grid(row=1, column=1, pady=2, padx=5)
        shift_menu.current(0)

        lot_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        lot_frame.grid(row=3, column=0, padx=10, pady=5, sticky='w')
        self.create_labeled_entry(lot_frame, "Numéro de Lot:", self.lot_number, row=0)

        produit_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        produit_frame.grid(row=4, column=0, padx=10, pady=5, sticky='w')
        tk.Label(produit_frame, text="Produit:", bg=self.colors['bg'], fg=self.colors['label_fg']) \
            .grid(row=0, column=0, sticky='e', pady=2)
        ttk.Checkbutton(produit_frame, text="Ail", variable=self.ail_var).grid(row=0, column=1, padx=5, pady=2, sticky='w')
        ttk.Checkbutton(produit_frame, text="Oignon", variable=self.oignon_var).grid(row=0, column=2, padx=5, pady=2, sticky='w')
        ttk.Checkbutton(produit_frame, text="Echalote", variable=self.echalote_var).grid(row=0, column=3, padx=5, pady=2, sticky='w')

        quantite_rentree_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        quantite_rentree_frame.grid(row=5, column=0, padx=10, pady=5, sticky='w')
        self.create_labeled_entry(quantite_rentree_frame, "Quantité de produit rentrée (kg):", self.quantite_rentree, row=0)

        quantite_fini_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        quantite_fini_frame.grid(row=6, column=0, padx=10, pady=5, sticky='w')
        self.create_labeled_entry(quantite_fini_frame, "Quantité de produit fini (kg):",
                                  self.quantite_fini, row=0, state='readonly')

        perte_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        perte_frame.grid(row=7, column=0, padx=10, pady=5, sticky='w')
        self.create_labeled_entry(perte_frame, "Perte (kg):", self.perte, row=0, state='readonly')

    def create_specific_frames(self, main_frame):
        poudre_label = tk.Label(main_frame, text="Poudre", bg=self.colors['bg'], fg='#87CEFA', font=('Helvetica', 10, 'bold'))
        poudre_label.grid(row=8, column=0, padx=10, pady=(10,2), sticky='w')
        self.poudre_frame = tk.Frame(main_frame, bg=self.colors['bg'], bd=0, highlightthickness=0, relief='flat')
        self.poudre_frame.grid(row=9, column=0, padx=10, pady=5, sticky='w')
        self.create_labeled_entry(self.poudre_frame, "Nombre de sac:", self.poudre_sac, row=0, width=10)
        self.create_labeled_entry(self.poudre_frame, "Poids du sac (kg):", self.poudre_poid_sac, row=1, width=10)
        self.create_labeled_entry(self.poudre_frame, "Poids dernier sac si inférieur (kg):",
                                  self.poudre_poid_dernier_sac, row=2, width=10)

        sem20_label = tk.Label(main_frame, text="Semoule 20/60", bg=self.colors['bg'], fg='#90EE90', font=('Helvetica', 10, 'bold'))
        sem20_label.grid(row=10, column=0, padx=10, pady=(10,2), sticky='w')
        self.semoule_2060_frame = tk.Frame(main_frame, bg=self.colors['bg'], bd=0, highlightthickness=0, relief='flat')
        self.semoule_2060_frame.grid(row=11, column=0, padx=10, pady=5, sticky='w')
        self.create_labeled_entry(self.semoule_2060_frame, "Nombre de sac:", self.semoule_2060_sac, row=0, width=10)
        self.create_labeled_entry(self.semoule_2060_frame, "Poids du sac (kg):", self.semoule_2060_poid_sac, row=1, width=10)
        self.create_labeled_entry(self.semoule_2060_frame, "Poids dernier sac si inférieur (kg):",
                                  self.semoule_2060_poid_dernier_sac, row=2, width=10)

        sem14_label = tk.Label(main_frame, text="Semoule 1/4", bg=self.colors['bg'], fg='#90EE90', font=('Helvetica', 10, 'bold'))
        sem14_label.grid(row=12, column=0, padx=10, pady=(10,2), sticky='w')
        self.semoule_14_frame = tk.Frame(main_frame, bg=self.colors['bg'], bd=0, highlightthickness=0, relief='flat')
        self.semoule_14_frame.grid(row=13, column=0, padx=10, pady=5, sticky='w')
        self.create_labeled_entry(self.semoule_14_frame, "Nombre de sac:", self.semoule_14_sac, row=0, width=10)
        self.create_labeled_entry(self.semoule_14_frame, "Poids du sac (kg):", self.semoule_14_poid_sac, row=1, width=10)
        self.create_labeled_entry(self.semoule_14_frame, "Poids dernier sac si inférieur (kg):",
                                  self.semoule_14_poid_dernier_sac, row=2, width=10)

    def create_buttons(self, main_frame):
        button_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        button_frame.grid(row=14, column=0, padx=10, pady=10, sticky='e')

        tk.Button(button_frame, text="Annuler", command=self.win.destroy,
                  bg=self.colors['button_bg'], fg=self.colors['button_fg']).pack(side='left', padx=5)

        action_text = "Valider" if self.mode == "create" else "Mettre à jour"
        tk.Button(button_frame, text=action_text,
                  command=self.save_data,
                  bg='#4CAF50', fg='white').pack(side='left', padx=5)

    def set_trace_for_calculation(self):
        sac_vars = [
            self.poudre_sac, self.poudre_poid_sac, self.poudre_poid_dernier_sac,
            self.semoule_2060_sac, self.semoule_2060_poid_sac, self.semoule_2060_poid_dernier_sac,
            self.semoule_14_sac, self.semoule_14_poid_sac, self.semoule_14_poid_dernier_sac
        ]
        for var in sac_vars:
            var.trace_add('write', lambda *args: self.calculate_quantite_fini())
        self.quantite_rentree.trace_add('write', lambda *args: self.calculate_quantite_fini())
        self.broyage_type.trace_add('write', lambda *args: self.toggle_fields())

    def toggle_fields(self):
        # Masquer/afficher les frames semoule selon le type de broyage
        if self.broyage_type.get() in ["Urshell", "Marteau"]:
            self.semoule_2060_frame.grid()
            self.semoule_14_frame.grid()
        else:
            self.semoule_2060_frame.grid_remove()
            self.semoule_14_frame.grid_remove()
        self.calculate_quantite_fini()

    def safe_get_int(self, var):
        val = var.get().strip()
        if val == "":
            return 0
        try:
            return int(float(val))
        except ValueError:
            return 0

    def safe_get_float(self, var):
        val = var.get().strip()
        if val == "":
            return 0.0
        try:
            return float(val)
        except ValueError:
            return 0.0

    def calc_poids_total(self, sacs, poids_sac, poids_dernier):
        if sacs > 0 and poids_sac > 0:
            total = (sacs - 1) * poids_sac
            total += poids_dernier if poids_dernier > 0 else poids_sac
            return total
        return 0

    def calculate_quantite_fini(self):
        try:
            quantite_entree = self.quantite_rentree.get()

            poudre_total = self.calc_poids_total(
                self.safe_get_int(self.poudre_sac),
                self.safe_get_float(self.poudre_poid_sac),
                self.safe_get_float(self.poudre_poid_dernier_sac)
            )

            if self.broyage_type.get() in ["Urshell", "Marteau"]:
                sem_2060_total = self.calc_poids_total(
                    self.safe_get_int(self.semoule_2060_sac),
                    self.safe_get_float(self.semoule_2060_poid_sac),
                    self.safe_get_float(self.semoule_2060_poid_dernier_sac)
                )
                sem_14_total = self.calc_poids_total(
                    self.safe_get_int(self.semoule_14_sac),
                    self.safe_get_float(self.semoule_14_poid_sac),
                    self.safe_get_float(self.semoule_14_poid_dernier_sac)
                )
            else:
                sem_2060_total = 0
                sem_14_total = 0

            quantite_finie = poudre_total + sem_2060_total + sem_14_total
            perte = quantite_entree - quantite_finie
            if perte < 0:
                perte = 0

            self.quantite_fini.set(round(quantite_finie, 2))
            self.perte.set(round(perte, 2))
        except Exception:
            self.quantite_fini.set(0.0)
            self.perte.set(0.0)

    def get_selected_products(self):
        produits = []
        if self.ail_var.get():
            produits.append("Ail")
        if self.oignon_var.get():
            produits.append("Oignon")
        if self.echalote_var.get():
            produits.append("Echalote")
        return ", ".join(produits) if produits else "Inconnu"

    def save_data(self):
        confirm = messagebox.askyesno("Confirmation", "Tous les champs sont correctement remplis ?")
        if not confirm:
            return

        data = {
            "Type de Broyage": self.broyage_type.get(),
            "Date": self.production_date.get(),
            "Poste": self.shift.get(),
            "Lot": self.lot_number.get(),
            "Produit": self.get_selected_products(),
            "Quantité Rentrée": self.quantite_rentree.get(),
            "Quantité Fini": self.quantite_fini.get(),
            "Perte": self.perte.get()
        }

        if self.mode == "create":
            self.controller.add_production(data)
        else:
            self.controller.update_production(self.prod_id, data)

        self.win.destroy()


def get_frame(parent_frame, controller_colors=None):
    """
    Point d’entrée pour intégrer ce module dans une application plus large.
    Retourne un frame contenant l’interface de Broyage.
    """
    controller = BroyageController()
    frame = tk.Frame(parent_frame, bg='#1C1C1C')
    BroyageView(frame, controller, colors=controller_colors)
    return frame
