import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import os
import pickle

def get_frame(parent_frame, controller):
    bg_color = '#2B2B2B'
    if hasattr(controller, 'colors') and 'bg' in controller.colors:
        bg_color = controller.colors['bg']
    frame = tk.Frame(parent_frame, bg=bg_color)
    app = MaintenanceModule(frame, controller)
    return frame

class MaintenanceModule:
    def __init__(self, parent, controller):
        self.parent = parent
        self.controller = controller
        self.colors = getattr(controller, 'colors', self.default_colors())

        # Stockage des demandes et opérations
        self.requests = self.load_data(self.get_requests_filename())
        self.ops = self.load_data(self.get_ops_filename())

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
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        title_label = tk.Label(main_frame, text="MAINTENANCE", bg=self.colors['bg'],
                               fg=self.colors['fg'], font=('Arial', 14, 'bold'))
        title_label.pack(pady=10)

        button_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        button_frame.pack(pady=10)

        demande_button = tk.Button(button_frame, text="Demande maintenance", bg=self.colors['button_bg'],
                                   fg=self.colors['button_fg'], command=self.open_demande_maintenance_window)
        demande_button.pack(side='left', padx=5)

        historique_button = tk.Button(button_frame, text="Historique maintenance (demandes)", bg=self.colors['button_bg'],
                                      fg=self.colors['button_fg'], command=self.show_requests_history)
        historique_button.pack(side='left', padx=5)

        info_button = tk.Button(button_frame, text="Informations équipements", bg=self.colors['button_bg'],
                                fg=self.colors['button_fg'], command=self.informations_equipements)
        info_button.pack(side='left', padx=5)

        add_op_button = tk.Button(button_frame, text="Ajouter opération maintenance", bg=self.colors['button_bg'],
                                  fg=self.colors['button_fg'], command=self.open_add_op_window)
        add_op_button.pack(side='left', padx=5)

        # Historique des opérations
        ops_button = tk.Button(button_frame, text="Historique maintenance (opérations)", bg=self.colors['button_bg'],
                               fg=self.colors['button_fg'], command=self.show_ops_history)
        ops_button.pack(side='left', padx=5)

    def informations_equipements(self):
        messagebox.showinfo("Informations équipements", "Module à venir (placeholder).")

    def open_demande_maintenance_window(self):
        dm_win = tk.Toplevel(self.parent)
        dm_win.title("Demande de Maintenance")
        dm_win.configure(bg=self.colors['bg'])

        # Variables
        nom_var = tk.StringVar()
        heure_var = tk.StringVar(value=datetime.now().strftime('%H:%M'))
        equipement_var = tk.StringVar()
        desc_var = tk.StringVar()
        actions_var = tk.StringVar()
        production_stop_var = tk.StringVar(value="NON")
        temps_stop_var = tk.StringVar()
        gravite_var = tk.StringVar(value="Critique")

        # Champs
        row = 0
        def lbl(text): return tk.Label(dm_win, text=text, bg=self.colors['bg'], fg=self.colors['fg'])
        def ent(var): return tk.Entry(dm_win, textvariable=var, bg=self.colors['entry_bg'], fg=self.colors['entry_fg'])

        lbl("Nom :").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        ent(nom_var).grid(row=row, column=1, padx=5, pady=5)

        row += 1
        lbl("Heure :").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        ent(heure_var).grid(row=row, column=1, padx=5, pady=5)

        row += 1
        lbl("Equipement :").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        ent(equipement_var).grid(row=row, column=1, padx=5, pady=5)

        row += 1
        lbl("Description du problème :").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        ent(desc_var).grid(row=row, column=1, padx=5, pady=5)

        row += 1
        lbl("Actions entreprises :").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        ent(actions_var).grid(row=row, column=1, padx=5, pady=5)

        # Production stoppée ?
        row += 1
        lbl("Production stoppée ?").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        prod_frame = tk.Frame(dm_win, bg=self.colors['bg'])
        prod_frame.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        self.create_oui_non_radiobuttons(prod_frame, production_stop_var)

        # Si oui combien de temps ?
        row += 1
        lbl("Si oui, combien de temps ?").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        ent(temps_stop_var).grid(row=row, column=1, padx=5, pady=5)

        # Seuil de gravité
        row += 1
        lbl("Seuil de gravité du problème :").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        grav_frame = tk.Frame(dm_win, bg=self.colors['bg'])
        grav_frame.grid(row=row, column=1, sticky='w', padx=5, pady=5)

        gravites = [("Critique (dans la journée)", "Critique"),
                    ("Important (dans la semaine)", "Important"),
                    ("Modéré (dans le mois)", "Modéré"),
                    ("Faible (quand possible)", "Faible")]

        for text, val in gravites:
            tk.Radiobutton(grav_frame, text=text, variable=gravite_var, value=val,
                           bg=self.colors['bg'], fg=self.colors['fg'], selectcolor=self.colors['bg'],
                           activebackground=self.colors['bg'], activeforeground=self.colors['fg']).pack(anchor='w')

        # Boutons
        def valider():
            data = {
                'nom': nom_var.get(),
                'heure': heure_var.get(),
                'equipement': equipement_var.get(),
                'description': desc_var.get(),
                'actions': actions_var.get(),
                'production_stop': production_stop_var.get(),
                'temps_stop': temps_stop_var.get() if production_stop_var.get() == "OUI" else "",
                'gravite': gravite_var.get(),
                'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            self.requests.append(data)
            self.save_data(self.get_requests_filename(), self.requests)
            messagebox.showinfo("Demande Maintenance", "Demande enregistrée avec succès.")
            dm_win.destroy()

        row += 1
        btn_frame = tk.Frame(dm_win, bg=self.colors['bg'])
        btn_frame.grid(row=row, column=0, columnspan=2, pady=10)
        tk.Button(btn_frame, text="Valider", bg=self.colors['button_bg'], fg=self.colors['button_fg'], command=valider).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Annuler", bg=self.colors['button_bg'], fg=self.colors['button_fg'], command=dm_win.destroy).pack(side='left', padx=5)

    def create_oui_non_radiobuttons(self, parent, var):
        tk.Radiobutton(parent, text="OUI", variable=var, value="OUI",
                       bg=self.colors['bg'], fg='green', selectcolor=self.colors['bg'],
                       activebackground=self.colors['bg'], activeforeground='green').pack(side='left', padx=5)
        tk.Radiobutton(parent, text="NON", variable=var, value="NON",
                       bg=self.colors['bg'], fg='red', selectcolor=self.colors['bg'],
                       activebackground=self.colors['bg'], activeforeground='red').pack(side='left', padx=5)

    def show_requests_history(self):
        # Liste classée par gravité : Ordre gravité: Critique > Important > Modéré > Faible
        sorted_requests = sorted(self.requests, key=lambda r: self.gravite_sort_key(r['gravite']))

        req_win = tk.Toplevel(self.parent)
        req_win.title("Historique Maintenance (demandes)")
        req_win.configure(bg=self.colors['bg'])

        columns = ("gravite", "equipement", "description", "nom", "heure")
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview",
                        background=self.colors['tree_bg'],
                        foreground=self.colors['tree_fg'],
                        rowheight=25,
                        fieldbackground=self.colors['tree_field_bg'])
        style.map('Treeview', background=[('selected', self.colors['tree_selected_bg'])])

        tree = ttk.Treeview(req_win, columns=columns, show='headings', style="Treeview")
        tree.heading('gravite', text='Gravité')
        tree.heading('equipement', text='Equipement')
        tree.heading('description', text='Description')
        tree.heading('nom', text='Nom demandeur')
        tree.heading('heure', text='Heure')
        tree.column('gravite', width=120)
        tree.column('equipement', width=120)
        tree.column('description', width=200)
        tree.column('nom', width=120)
        tree.column('heure', width=100)

        for req in sorted_requests:
            tree.insert('', 'end', values=(req['gravite'], req['equipement'], req['description'], req['nom'], req['heure']))

        tree.pack(fill='both', expand=True, padx=10, pady=10)

        def on_double_click(event):
            item = tree.selection()
            if not item:
                return
            values = tree.item(item[0], 'values')
            # Rechercher la demande correspondante
            for r in self.requests:
                if (r['gravite'] == values[0] and r['equipement'] == values[1] and r['description'] == values[2]
                        and r['nom'] == values[3] and r['heure'] == values[4]):
                    self.show_request_detail(r)
                    break

        tree.bind("<Double-1>", on_double_click)

    def show_request_detail(self, req):
        detail_win = tk.Toplevel(self.parent)
        detail_win.title("Détails de la demande")
        detail_win.configure(bg=self.colors['bg'])

        def lbl_val(lbl_text, val_text):
            frame = tk.Frame(detail_win, bg=self.colors['bg'])
            frame.pack(fill='x', pady=5)
            tk.Label(frame, text=lbl_text, bg=self.colors['bg'], fg=self.colors['fg']).pack(side='left', padx=5)
            tk.Label(frame, text=val_text, bg=self.colors['bg'], fg=self.colors['fg']).pack(side='left', padx=5)

        lbl_val("Nom :", req['nom'])
        lbl_val("Heure :", req['heure'])
        lbl_val("Equipement :", req['equipement'])
        lbl_val("Description :", req['description'])
        lbl_val("Actions entreprises :", req['actions'])
        lbl_val("Production stoppée :", req['production_stop'])
        if req['production_stop'] == "OUI":
            lbl_val("Temps d'arrêt :", req['temps_stop'])
        lbl_val("Gravité :", req['gravite'])
        lbl_val("Date Demande :", req['datetime'])

    def gravite_sort_key(self, gravite):
        order = ["Critique", "Important", "Modéré", "Faible"]
        return order.index(gravite)

    def open_add_op_window(self):
        op_win = tk.Toplevel(self.parent)
        op_win.title("Ajouter opération maintenance")
        op_win.configure(bg=self.colors['bg'])

        equip_var = tk.StringVar()
        maintenance_var = tk.StringVar()
        changements_var = tk.StringVar()
        provisoire_var = tk.StringVar(value="NON")
        nom_var = tk.StringVar()
        date_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        heure_var = tk.StringVar(value=datetime.now().strftime('%H:%M'))
        duree_var = tk.StringVar()

        row = 0
        def lbl(text): return tk.Label(op_win, text=text, bg=self.colors['bg'], fg=self.colors['fg'])
        def ent(var): return tk.Entry(op_win, textvariable=var, bg=self.colors['entry_bg'], fg=self.colors['entry_fg'])

        lbl("Equipement :").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        ent(equip_var).grid(row=row, column=1, padx=5, pady=5)

        row += 1
        lbl("Maintenance effectuée :").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        ent(maintenance_var).grid(row=row, column=1, padx=5, pady=5)

        row += 1
        lbl("Changements à communiquer :").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        ent(changements_var).grid(row=row, column=1, padx=5, pady=5)

        row += 1
        lbl("Maintenance provisoire ?").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        prov_frame = tk.Frame(op_win, bg=self.colors['bg'])
        prov_frame.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        self.create_oui_non_radiobuttons(prov_frame, provisoire_var)

        row += 1
        lbl("Nom du technicien :").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        ent(nom_var).grid(row=row, column=1, padx=5, pady=5)

        row += 1
        lbl("Date :").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        ent(date_var).grid(row=row, column=1, padx=5, pady=5)

        row += 1
        lbl("Heure :").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        ent(heure_var).grid(row=row, column=1, padx=5, pady=5)

        row += 1
        lbl("Durée (min) :").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        ent(duree_var).grid(row=row, column=1, padx=5, pady=5)

        def valider():
            data = {
                'equipement': equip_var.get(),
                'maintenance': maintenance_var.get(),
                'changements': changements_var.get(),
                'provisoire': provisoire_var.get(),
                'nom': nom_var.get(),
                'date': date_var.get(),
                'heure': heure_var.get(),
                'duree': duree_var.get(),
                'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            self.ops.append(data)
            self.save_data(self.get_ops_filename(), self.ops)
            messagebox.showinfo("Opération Maintenance", "Opération enregistrée avec succès.")
            op_win.destroy()

        row += 1
        btn_frame = tk.Frame(op_win, bg=self.colors['bg'])
        btn_frame.grid(row=row, column=0, columnspan=2, pady=10)
        tk.Button(btn_frame, text="Valider", bg=self.colors['button_bg'], fg=self.colors['button_fg'], command=valider).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Annuler", bg=self.colors['button_bg'], fg=self.colors['button_fg'], command=op_win.destroy).pack(side='left', padx=5)

    def show_ops_history(self):
        ops_win = tk.Toplevel(self.parent)
        ops_win.title("Historique Maintenance (opérations)")
        ops_win.configure(bg=self.colors['bg'])

        columns = ("equipement", "maintenance", "nom", "date", "heure", "duree", "provisoire")
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview",
                        background=self.colors['tree_bg'],
                        foreground=self.colors['tree_fg'],
                        rowheight=25,
                        fieldbackground=self.colors['tree_field_bg'])
        style.map('Treeview', background=[('selected', self.colors['tree_selected_bg'])])

        tree = ttk.Treeview(ops_win, columns=columns, show='headings', style="Treeview")
        tree.heading('equipement', text='Equipement')
        tree.heading('maintenance', text='Maintenance')
        tree.heading('nom', text='Nom Tech')
        tree.heading('date', text='Date')
        tree.heading('heure', text='Heure')
        tree.heading('duree', text='Durée(min)')
        tree.heading('provisoire', text='Provisoire')

        tree.column('equipement', width=120)
        tree.column('maintenance', width=200)
        tree.column('nom', width=120)
        tree.column('date', width=100)
        tree.column('heure', width=80)
        tree.column('duree', width=80)
        tree.column('provisoire', width=80)

        for op in self.ops:
            tree.insert('', 'end', values=(op['equipement'], op['maintenance'], op['nom'], op['date'], op['heure'], op['duree'], op['provisoire']))

        tree.pack(fill='both', expand=True, padx=10, pady=10)

        def on_double_click(event):
            item = tree.selection()
            if not item:
                return
            values = tree.item(item[0], 'values')
            for o in self.ops:
                if (o['equipement'] == values[0] and o['maintenance'] == values[1] and o['nom'] == values[2]
                        and o['date'] == values[3] and o['heure'] == values[4] and o['duree'] == values[5]
                        and o['provisoire'] == values[6]):
                    self.show_op_detail(o)
                    break

        tree.bind("<Double-1>", on_double_click)

    def show_op_detail(self, op):
        detail_win = tk.Toplevel(self.parent)
        detail_win.title("Détails de l'opération de maintenance")
        detail_win.configure(bg=self.colors['bg'])

        def lbl_val(lbl_text, val_text):
            frame = tk.Frame(detail_win, bg=self.colors['bg'])
            frame.pack(fill='x', pady=5)
            tk.Label(frame, text=lbl_text, bg=self.colors['bg'], fg=self.colors['fg']).pack(side='left', padx=5)
            tk.Label(frame, text=val_text, bg=self.colors['bg'], fg=self.colors['fg']).pack(side='left', padx=5)

        lbl_val("Equipement :", op['equipement'])
        lbl_val("Maintenance effectuée :", op['maintenance'])
        lbl_val("Changements à communiquer :", op['changements'])
        lbl_val("Provisoire :", op['provisoire'])
        lbl_val("Nom Technicien :", op['nom'])
        lbl_val("Date :", op['date'])
        lbl_val("Heure :", op['heure'])
        lbl_val("Durée (min) :", op['duree'])
        lbl_val("Enregistré le :", op['datetime'])

    def load_data(self, filename):
        if os.path.exists(filename):
            try:
                with open(filename, 'rb') as f:
                    return pickle.load(f)
            except:
                return []
        return []

    def save_data(self, filename, data):
        with open(filename, 'wb') as f:
            pickle.dump(data, f)

    def get_requests_filename(self):
        module_dir = os.path.dirname(__file__)
        return os.path.join(module_dir, 'maintenance_requests.pkl')

    def get_ops_filename(self):
        module_dir = os.path.dirname(__file__)
        return os.path.join(module_dir, 'maintenance_ops.pkl')
