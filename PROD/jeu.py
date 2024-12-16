# MODULES/jeu.py

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('TkAgg')  # Utilisation du backend TkAgg pour matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.dates as mdates
import pickle
import random
import os
import sys
import importlib
import shutil

# Import fictif de l'interface OpenAI (clé API factice)
from openai import OpenAI

def get_frame(parent_frame, controller):
    """
    Point d'entrée pour obtenir le frame principal du module 'jeu'.
    Instancie RochiasPodCalculator avec un client OpenAI fictif.
    Cette fonction est requise par l'architecture du projet
    afin de charger dynamiquement ce module.
    """
    # Clé API fictive, à remplacer par une vraie si nécessaire
    client = OpenAI(api_key='sk-FAKE-KEY')

    frame = tk.Frame(parent_frame, bg='#2B2B2B')
    app = RochiasPodCalculator(frame, client)
    return frame

class RochiasPodCalculator:
    """
    Classe principale gérant le module 'jeu'.

    Fonctionnalités :
    - Navigation entre différents modules (Production, Broyage, etc.).
    - Gestion d'un chronomètre de production (start/stop/reset).
    - Sauvegarde et chargement de l'état de la production (variables, fiches de prod).
    - Intégration d'un chatbot OpenAI fictif.
    - Affichage et saisie de données de production (eau, gaz, matières premières).
    - Calcul et affichage des données de finition (Lanière, Rejet Sortex, Rejet Finition).
    - Graphe (matplotlib) affichant la production cumulée.
    - Bouton "Sauvegarder" clignotant pour attirer l'attention.
    - Nouveau bouton "Historique des prod" : ouvre une fenêtre permettant de voir la liste des archives et d'en afficher le contenu.
    """

    def __init__(self, parent, client):
        self.parent = parent
        self.client = client

        # Liste des modules disponibles
        self.module_names = ['Production', 'Broyage', 'Cassage', 'Effectif', 'Maintenance', 'Qualité', 'Séchoir']
        self.current_module = 'Production'

        # Ajout du chemin MODULES au sys.path si nécessaire
        modules_path = os.path.join(os.path.dirname(__file__), 'MODULES')
        if modules_path not in sys.path:
            sys.path.append(modules_path)

        # Couleurs et polices par défaut
        self.colors = {
            'bg': '#2B2B2B',
            'fg': 'white',
            'button_bg': '#009688',
            'button_fg': 'white',
            'entry_bg': 'white',
            'entry_fg': 'black',
            'label_fg': 'white',
            'tree_bg': '#D3D3D3',
            'tree_fg': 'black',
            'tree_field_bg': '#D3D3D3',
            'tree_selected_bg': '#347083',
            'graph_bg': '#3E3E3E',
            'graph_facecolor': '#2B2B2B',
            'bot_button_bg': '#f44336',
            'bot_button_fg': 'white'
        }
        self.font_family = 'Helvetica'

        self.parent.configure(bg=self.colors['bg'])

        self.frames = []
        self.modules_frames = {}

        # Couleurs pour le clignotement du bouton "Sauvegarder"
        self.save_button_colors = ['#FF0000', '#FFA500', '#FFFF00', '#4CAF50', '#00FF00', '#00FFFF', '#0000FF', '#FF00FF']
        self.current_save_color_index = 0

        # Nom du fichier pour sauvegarder l'état
        self.state_filename = os.path.join(os.path.dirname(__file__), 'rochias_pod_calculator_state.pkl')

        # Configuration des styles et de l'UI
        self.setup_styles()
        self.setup_ui()

    def setup_styles(self):
        """
        Configure les styles ttk pour les widgets.
        Réduction de la taille des boutons en haut.
        """
        style = ttk.Style()
        style.theme_use('clam')

        # Style des boutons (on réduit un peu la taille)
        style.configure("TButton",
                        background=self.colors['button_bg'],
                        foreground=self.colors['button_fg'],
                        font=(self.font_family, 10, 'bold'),
                        padding=4)
        style.map("TButton",
                  background=[('active', '#00796B'), ('pressed', '#004D40')])

        # Labels
        style.configure("TLabel",
                        background=self.colors['bg'],
                        foreground=self.colors['fg'],
                        font=(self.font_family, 10))

        # LabelFrames
        style.configure("TLabelframe",
                        background=self.colors['bg'],
                        foreground=self.colors['fg'],
                        font=(self.font_family, 10, 'bold'),
                        borderwidth=2,
                        relief='groove')
        style.configure("TLabelframe.Label", foreground=self.colors['fg'])

        # Séparateur
        style.configure("TSeparator", background='#444444')

        # Treeview
        style.configure("Treeview",
                        background=self.colors['tree_bg'],
                        fieldbackground=self.colors['tree_field_bg'],
                        foreground=self.colors['tree_fg'],
                        font=(self.font_family, 9))
        style.map('Treeview', background=[('selected', self.colors['tree_selected_bg'])])

    def setup_ui(self):
        """
        Crée la structure de base de l'interface:
        - Conteneur principal.
        - Une zone de navigation à gauche (boutons de modules).
        - Une zone de contenu à droite.
        """
        colors = self.colors

        main_container = tk.Frame(self.parent, bg=colors['bg'])
        main_container.pack(fill='both', expand=True)
        self.frames.append(main_container)

        # Cadre de navigation (modules) à gauche
        nav_frame = tk.Frame(main_container, bg=colors['bg'])
        nav_frame.pack(side='left', fill='y', padx=5, pady=5)
        self.frames.append(nav_frame)

        # Cadre principal (contenu) à droite
        self.content_frame = tk.Frame(main_container, bg=colors['bg'])
        self.content_frame.pack(side='right', fill='both', expand=True, padx=5, pady=5)
        self.frames.append(self.content_frame)

        # Titre
        title_label = tk.Label(nav_frame, text="Rochias Pod\nCalculator", bg=colors['bg'], fg='white', font=(self.font_family, 12, 'bold'))
        title_label.pack(pady=10)
        self.frames.append(title_label)

        # Boutons pour naviguer entre les modules
        for module_name in self.module_names:
            button = ttk.Button(nav_frame, text=module_name, command=lambda name=module_name: self.switch_module(name))
            button.pack(fill='x', padx=5, pady=3)

        # Charge le module par défaut (Production)
        self.switch_module(self.current_module)

    def switch_module(self, module_name):
        """
        Permet de changer le module affiché dans la zone de contenu.
        Si le module n'est pas encore chargé, on essaie de l'importer.
        """
        for frame in self.content_frame.winfo_children():
            frame.pack_forget()

        if module_name in self.modules_frames:
            frame = self.modules_frames[module_name]
            frame.pack(fill='both', expand=True)
        else:
            if module_name == 'Production':
                # Module "Production" intégré dans ce code
                frame = tk.Frame(self.content_frame, bg=self.colors['bg'])
                frame.pack(fill='both', expand=True)
                self.modules_frames[module_name] = frame
                self.setup_production_ui(frame)
            else:
                # Chargement dynamique d'un autre module
                try:
                    module = importlib.import_module(module_name)
                    frame = module.get_frame(self.content_frame, self)
                    self.modules_frames[module_name] = frame
                    frame.pack(fill='both', expand=True)
                except ImportError as e:
                    messagebox.showerror("Erreur", f"Impossible de charger le module {module_name}: {e}")

    def setup_production_ui(self, parent_frame):
        """
        Configure l'interface du module "Production".
        """
        # Variables chrono/production
        self.chrono_running = False
        self.start_time = None
        self.elapsed_time = timedelta(0)
        self.production_start_time = None
        self.elapsed_time_var = tk.StringVar(value="00:00:00")

        # Variables de production
        self.eau_debut = tk.DoubleVar()
        self.eau_fin = tk.DoubleVar()
        self.eau_consomme = tk.DoubleVar()
        self.eau_consomme_par_heure = tk.DoubleVar()

        self.gaz_debut = tk.DoubleVar()
        self.gaz_fin = tk.DoubleVar()
        self.gaz_consomme_total = tk.DoubleVar()
        self.gaz_consomme_par_heure = tk.DoubleVar()

        self.matieres_premieres = tk.DoubleVar()
        self.matieres_premieres_moyenne_par_heure = tk.DoubleVar()
        self.lot = tk.StringVar()
        self.produit = tk.StringVar()
        self.observations = tk.StringVar()

        # Variables finition
        self.nb_sacs_laniere = tk.IntVar()
        self.poids_dernier_sac_laniere = tk.DoubleVar()
        self.poids_sac_laniere = tk.DoubleVar()
        self.total_laniere = tk.DoubleVar()

        self.nb_sacs_rejet_sortex = tk.IntVar()
        self.poids_dernier_sac_rejet_sortex = tk.DoubleVar()
        self.poids_sac_rejet_sortex = tk.DoubleVar()
        self.total_rejet_sortex = tk.DoubleVar()

        self.nb_sacs_rejet_finition = tk.IntVar()
        self.poids_dernier_sac_rejet_finition = tk.DoubleVar()
        self.poids_sac_rejet_finition = tk.DoubleVar()
        self.total_rejet_finition = tk.DoubleVar()

        self.total_sortie = tk.DoubleVar()
        self.ratio_entree_sortie = tk.DoubleVar()

        # Variables fiches de prod
        self.total_var = tk.DoubleVar()
        self.freq_var = tk.StringVar()
        self.fiches_de_prod = []
        self.heure_debut_poste = None

        # Cadre supérieur (chrono, sauvegarde, etc.)
        top_frame = tk.Frame(parent_frame, bg=self.colors['bg'])
        top_frame.pack(fill='x', pady=5)

        self.start_timer_button = ttk.Button(top_frame, text="Démarrer chrono", command=self.start_timer)
        self.start_timer_button.pack(side='left', padx=2)

        self.stop_timer_button = ttk.Button(top_frame, text="Arrêter chrono", command=self.stop_timer)
        self.stop_timer_button.pack(side='left', padx=2)

        self.reset_timer_button = ttk.Button(top_frame, text="Réinitialiser chrono", command=self.reset_timer)
        self.reset_timer_button.pack(side='left', padx=2)

        reset_button = ttk.Button(top_frame, text="Réinitialiser", command=self.reset_fields)
        reset_button.pack(side='left', padx=2)

        self.save_button = tk.Button(top_frame, text="Sauvegarder", command=self.save_data,
                                     bg=self.colors['button_bg'], fg=self.colors['button_fg'], font=(self.font_family, 9, 'bold'), padx=4, pady=2)
        self.save_button.pack(side='left', padx=2)
        self.blink_save_button()

        load_button = ttk.Button(top_frame, text="Recharger", command=self.load_state)
        load_button.pack(side='left', padx=2)

        self.bot_button = tk.Button(top_frame, text="BOT", command=self.open_chatbot_window,
                                    bg=self.colors['bot_button_bg'], fg=self.colors['bot_button_fg'], font=(self.font_family, 9, 'bold'), padx=4, pady=2)
        self.bot_button.pack(side='left', padx=2)

        self.histo_button = ttk.Button(top_frame, text="Historique des prod", command=self.open_historique_window)
        self.histo_button.pack(side='left', padx=2)

        self.timer_label = tk.Label(top_frame, text="00:00:00", fg='yellow', bg=self.colors['bg'], font=(self.font_family, 9, 'bold'))
        self.timer_label.pack(side='right', padx=10)

        self.clock_label = tk.Label(top_frame, text="", fg='green', bg=self.colors['bg'], font=(self.font_family, 9, 'bold'))
        self.clock_label.pack(side='right', padx=10)

        sep = ttk.Separator(parent_frame, orient='horizontal')
        sep.pack(fill='x', pady=5)

        input_finition_frame = tk.Frame(parent_frame, bg=self.colors['bg'])
        input_finition_frame.pack(side='top', fill='x', padx=5, pady=5)

        self.setup_input_frame(input_finition_frame, self.colors)
        self.setup_finition_frame(input_finition_frame, self.colors)

        prod_graph_frame = tk.Frame(parent_frame, bg=self.colors['bg'])
        prod_graph_frame.pack(fill='both', expand=True, pady=5)

        self.setup_prod_frame(prod_graph_frame, self.colors)
        self.setup_graph_frame(prod_graph_frame, self.colors)

        # Mises à jour régulières
        self.update_clock()
        self.update_timer()
        self.update_elapsed_time()
        self.update_chart()
        self.update_frequency()

    def setup_input_frame(self, parent_frame, colors):
        input_frame = ttk.Labelframe(parent_frame, text="Données de production")
        input_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)

        ttk.Label(input_frame, text="Heure de début de poste (HH:MM):").grid(row=1, column=0, sticky='e', pady=2)
        self.heure_debut_entry = tk.Entry(input_frame, bg=colors['entry_bg'], fg=colors['entry_fg'], font=(self.font_family, 9))
        self.heure_debut_entry.grid(row=1, column=1, pady=2)
        self.heure_debut_entry.insert(0, datetime.now().strftime('%H:%M'))

        ttk.Label(input_frame, text="Eau début (m³):").grid(row=2, column=0, sticky='e', pady=2)
        self.eau_debut_entry = tk.Entry(input_frame, textvariable=self.eau_debut, bg=colors['entry_bg'], fg=colors['entry_fg'], font=(self.font_family, 9))
        self.eau_debut_entry.grid(row=2, column=1, pady=2)

        ttk.Label(input_frame, text="Eau fin (m³):").grid(row=3, column=0, sticky='e', pady=2)
        self.eau_fin_entry = tk.Entry(input_frame, textvariable=self.eau_fin, bg=colors['entry_bg'], fg=colors['entry_fg'], font=(self.font_family, 9))
        self.eau_fin_entry.grid(row=3, column=1, pady=2)

        ttk.Label(input_frame, text="Matières premières (kg):").grid(row=4, column=0, sticky='e', pady=2)
        mat_entry = tk.Entry(input_frame, textvariable=self.matieres_premieres, bg=colors['entry_bg'], fg=colors['entry_fg'], font=(self.font_family, 9))
        mat_entry.grid(row=4, column=1, pady=2)

        ttk.Label(input_frame, text="Gaz début (m³):").grid(row=5, column=0, sticky='e', pady=2)
        self.gaz_debut_entry = tk.Entry(input_frame, textvariable=self.gaz_debut, bg=colors['entry_bg'], fg=colors['entry_fg'], font=(self.font_family, 9))
        self.gaz_debut_entry.grid(row=5, column=1, pady=2)

        ttk.Label(input_frame, text="Gaz fin (m³):").grid(row=6, column=0, sticky='e', pady=2)
        self.gaz_fin_entry = tk.Entry(input_frame, textvariable=self.gaz_fin, bg=colors['entry_bg'], fg=colors['entry_fg'], font=(self.font_family, 9))
        self.gaz_fin_entry.grid(row=6, column=1, pady=2)

        ttk.Label(input_frame, text="Lot:").grid(row=7, column=0, sticky='e', pady=2)
        self.lot_entry = tk.Entry(input_frame, textvariable=self.lot, bg=colors['entry_bg'], fg=colors['entry_fg'], font=(self.font_family, 9))
        self.lot_entry.grid(row=7, column=1, pady=2)

        ttk.Label(input_frame, text="Observations:").grid(row=8, column=0, sticky='ne', pady=2)
        self.observations_text = tk.Text(input_frame, width=30, height=5, bg=colors['entry_bg'], fg=colors['entry_fg'], font=(self.font_family, 9))
        self.observations_text.grid(row=8, column=1, pady=2)

        calc_button = ttk.Button(input_frame, text="Calculer données de production", command=self.calculate_production_data)
        calc_button.grid(row=11, column=0, columnspan=2, pady=10)

        self.resultat_frame_production = tk.Frame(input_frame, bg=colors['bg'])
        self.resultat_frame_production.grid(row=12, column=0, columnspan=2, pady=5)

    def setup_finition_frame(self, parent_frame, colors):
        finition_frame = ttk.Labelframe(parent_frame, text="Finition")
        finition_frame.pack(side='right', padx=5, pady=5, fill='both', expand=True)

        ttk.Label(finition_frame, text="Nb sacs Lanière:").grid(row=1, column=0, sticky='e', pady=2)
        tk.Entry(finition_frame, textvariable=self.nb_sacs_laniere, bg=colors['entry_bg'], fg=colors['entry_fg'], font=(self.font_family, 9)).grid(row=1, column=1, pady=2)

        ttk.Label(finition_frame, text="Poids sac Lanière (kg):").grid(row=2, column=0, sticky='e', pady=2)
        tk.Entry(finition_frame, textvariable=self.poids_sac_laniere, bg=colors['entry_bg'], fg=colors['entry_fg'], font=(self.font_family, 9)).grid(row=2, column=1, pady=2)

        ttk.Label(finition_frame, text="Poids dernier sac Lanière (kg):").grid(row=3, column=0, sticky='e', pady=2)
        tk.Entry(finition_frame, textvariable=self.poids_dernier_sac_laniere, bg=colors['entry_bg'], fg=colors['entry_fg'], font=(self.font_family, 9)).grid(row=3, column=1, pady=2)

        ttk.Label(finition_frame, text="Nb sacs Rejet Sortex:").grid(row=4, column=0, sticky='e', pady=2)
        tk.Entry(finition_frame, textvariable=self.nb_sacs_rejet_sortex, bg=colors['entry_bg'], fg=colors['entry_fg'], font=(self.font_family, 9)).grid(row=4, column=1, pady=2)

        ttk.Label(finition_frame, text="Poids sac Rejet Sortex (kg):").grid(row=5, column=0, sticky='e', pady=2)
        tk.Entry(finition_frame, textvariable=self.poids_sac_rejet_sortex, bg=colors['entry_bg'], fg=colors['entry_fg'], font=(self.font_family, 9)).grid(row=5, column=1, pady=2)

        ttk.Label(finition_frame, text="Poids dernier sac Rejet Sortex (kg):").grid(row=6, column=0, sticky='e', pady=2)
        tk.Entry(finition_frame, textvariable=self.poids_dernier_sac_rejet_sortex, bg=colors['entry_bg'], fg=colors['entry_fg'], font=(self.font_family, 9)).grid(row=6, column=1, pady=2)

        ttk.Label(finition_frame, text="Nb sacs Rejet Finition:").grid(row=7, column=0, sticky='e', pady=2)
        tk.Entry(finition_frame, textvariable=self.nb_sacs_rejet_finition, bg=colors['entry_bg'], fg=colors['entry_fg'], font=(self.font_family, 9)).grid(row=7, column=1, pady=2)

        ttk.Label(finition_frame, text="Poids sac Rejet Finition (kg):").grid(row=8, column=0, sticky='e', pady=2)
        tk.Entry(finition_frame, textvariable=self.poids_sac_rejet_finition, bg=colors['entry_bg'], fg=colors['entry_fg'], font=(self.font_family, 9)).grid(row=8, column=1, pady=2)

        ttk.Label(finition_frame, text="Poids dernier sac Rejet Finition (kg):").grid(row=9, column=0, sticky='e', pady=2)
        tk.Entry(finition_frame, textvariable=self.poids_dernier_sac_rejet_finition, bg=colors['entry_bg'], fg=colors['entry_fg'], font=(self.font_family, 9)).grid(row=9, column=1, pady=2)

        calc_button = ttk.Button(finition_frame, text="Calculer Totaux Finition", command=self.calculate_finition_totals)
        calc_button.grid(row=10, column=0, columnspan=2, pady=10)

        resultat_frame = tk.Frame(finition_frame, bg=colors['bg'])
        resultat_frame.grid(row=11, column=0, columnspan=2, pady=5)

        ttk.Label(resultat_frame, text="Total Lanière (kg):").grid(row=0, column=0, sticky='e', pady=2)
        tk.Label(resultat_frame, textvariable=self.total_laniere, fg='green', bg=colors['bg'], font=(self.font_family, 9)).grid(row=0, column=1, pady=2)

        ttk.Label(resultat_frame, text="Total Rejet Sortex (kg):").grid(row=1, column=0, sticky='e', pady=2)
        tk.Label(resultat_frame, textvariable=self.total_rejet_sortex, fg='green', bg=colors['bg'], font=(self.font_family, 9)).grid(row=1, column=1, pady=2)

        ttk.Label(resultat_frame, text="Total Rejet Finition (kg):").grid(row=2, column=0, sticky='e', pady=2)
        tk.Label(resultat_frame, textvariable=self.total_rejet_finition, fg='green', bg=colors['bg'], font=(self.font_family, 9)).grid(row=2, column=1, pady=2)

        ttk.Label(resultat_frame, text="Total Sortie (kg):").grid(row=3, column=0, sticky='e', pady=2)
        tk.Label(resultat_frame, textvariable=self.total_sortie, fg='green', bg=colors['bg'], font=(self.font_family, 9)).grid(row=3, column=1, pady=2)

        ttk.Label(resultat_frame, text="Ratio Entrée/Sortie (%):").grid(row=4, column=0, sticky='e', pady=2)
        tk.Label(resultat_frame, textvariable=self.ratio_entree_sortie, fg='green', bg=colors['bg'], font=(self.font_family, 9)).grid(row=4, column=1, pady=2)

    def setup_prod_frame(self, parent_frame, colors):
        prod_frame = ttk.Labelframe(parent_frame, text="Fiches de Production")
        prod_frame.pack(side='left', padx=5, pady=5, fill='both', expand=True)

        ttk.Label(prod_frame, text="Poids (kg):").grid(row=0, column=0, sticky='e', pady=2)
        self.prod_entry = tk.Entry(prod_frame, bg=colors['entry_bg'], fg=colors['entry_fg'], font=(self.font_family, 9))
        self.prod_entry.grid(row=0, column=1, pady=2)
        add_button = ttk.Button(prod_frame, text="Valider", command=self.add_production)
        add_button.grid(row=0, column=2, padx=5, pady=2)

        self.tree = ttk.Treeview(prod_frame, columns=('Number', 'Time', 'Weight'), show='headings', style="Treeview")
        self.tree.heading('Number', text='#')
        self.tree.heading('Time', text='Heure')
        self.tree.heading('Weight', text='Poids (kg)')
        self.tree.column('Number', width=50, anchor='center')
        self.tree.column('Time', width=100, anchor='center')
        self.tree.column('Weight', width=100, anchor='center')
        self.tree.grid(row=1, column=0, columnspan=3, pady=5, sticky='nsew')

        prod_frame.grid_rowconfigure(1, weight=1)
        prod_frame.grid_columnconfigure(0, weight=1)

        total_frame = tk.Frame(prod_frame, bg=colors['bg'])
        total_frame.grid(row=2, column=0, columnspan=3, pady=5)

        ttk.Label(total_frame, text="Total:").grid(row=0, column=0, sticky='e', pady=2)
        tk.Label(total_frame, textvariable=self.total_var, fg='green', bg=colors['bg'], font=(self.font_family, 9, 'bold')).grid(row=0, column=1, pady=2)

        ttk.Label(total_frame, text="Quantité passée par heure (kg/h):").grid(row=1, column=0, sticky='e', pady=2)
        tk.Label(total_frame, textvariable=self.freq_var, fg='green', bg=colors['bg'], font=(self.font_family, 9, 'bold')).grid(row=1, column=1, pady=2)

        ttk.Label(total_frame, text="Temps écoulé:").grid(row=2, column=0, sticky='e', pady=2)
        tk.Label(total_frame, textvariable=self.elapsed_time_var, fg='green', bg=colors['bg'], font=(self.font_family, 9, 'bold')).grid(row=2, column=1, pady=2)

    def setup_graph_frame(self, parent_frame, colors):
        graph_frame = ttk.Labelframe(parent_frame, text="Graphique de la Production")
        graph_frame.pack(side='right', padx=5, pady=5, fill='both', expand=True)

        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_xlabel('Temps')
        self.ax.set_ylabel('Production (kg)')
        self.ax.grid(True, which='both', linestyle='--', linewidth=0.5)
        self.figure.patch.set_facecolor(colors['graph_facecolor'])
        self.ax.set_facecolor(colors['graph_bg'])

        self.canvas = FigureCanvasTkAgg(self.figure, master=graph_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
        self.canvas.draw()

    def blink_save_button(self):
        self.current_save_color_index = (self.current_save_color_index + 1) % len(self.save_button_colors)
        new_color = self.save_button_colors[self.current_save_color_index]
        self.save_button.config(bg=new_color)
        self.parent.after(500, self.blink_save_button)

    def open_chatbot_window(self):
        colors = self.colors
        self.chatbot_window = tk.Toplevel(self.parent)
        self.chatbot_window.title("Chatbot")
        self.chatbot_window.configure(bg=colors['bg'])

        chatbot_frame = tk.Frame(self.chatbot_window, bg=colors['bg'])
        chatbot_frame.pack(fill='both', expand=True, padx=10, pady=10)

        self.chatbot_text = tk.Text(chatbot_frame, bg=self.colors['entry_bg'], fg=self.colors['entry_fg'], wrap='word', font=(self.font_family, 9))
        self.chatbot_text.pack(padx=5, pady=5, fill='both', expand=True)

        input_frame = tk.Frame(chatbot_frame, bg=colors['bg'])
        input_frame.pack(fill='x', pady=5)

        self.chatbot_entry = tk.Entry(input_frame, bg=self.colors['entry_bg'], fg=self.colors['entry_fg'], font=(self.font_family, 9))
        self.chatbot_entry.pack(side='left', fill='x', expand=True, padx=5)
        self.chatbot_entry.bind("<Return>", self.send_chatbot_message)

        send_button = ttk.Button(input_frame, text="Envoyer", command=self.send_chatbot_message)
        send_button.pack(side='left', padx=5)

        self.chatbot_conversation = []

    def send_chatbot_message(self, event=None):
        user_message = self.chatbot_entry.get()
        if user_message.strip() == "":
            return
        self.chatbot_conversation.append({'role': 'user', 'content': user_message})
        self.chatbot_text.insert(tk.END, f"Vous: {user_message}\n")
        self.chatbot_entry.delete(0, tk.END)
        self.chatbot_text.see(tk.END)

        response = self.get_chatbot_response()
        if response:
            self.chatbot_conversation.append({'role': 'assistant', 'content': response})
            self.chatbot_text.insert(tk.END, f"Bot: {response}\n")
            self.chatbot_text.see(tk.END)

    def get_chatbot_response(self):
        try:
            completion = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=self.chatbot_conversation
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"Erreur dans get_chatbot_response: {e}")
            return f"Erreur: {str(e)}"

    def start_timer(self):
        if not self.chrono_running:
            self.chrono_running = True
            if self.start_time is None:
                self.start_time = datetime.now() - self.elapsed_time
            else:
                self.start_time = datetime.now() - self.elapsed_time
            self.save_state()

    def stop_timer(self):
        if self.chrono_running:
            self.chrono_running = False
            self.elapsed_time = datetime.now() - self.start_time
            self.save_state()

    def reset_timer(self):
        self.chrono_running = False
        self.elapsed_time = timedelta(0)
        self.timer_label.config(text="00:00:00")
        self.start_time = None
        self.save_state()

    def update_timer(self):
        if self.chrono_running:
            elapsed_time = datetime.now() - self.start_time
            self.elapsed_time = elapsed_time
        else:
            elapsed_time = self.elapsed_time
        hours, remainder = divmod(int(elapsed_time.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        self.timer_label.config(text=time_str)
        self.parent.after(1000, self.update_timer)

    def update_elapsed_time(self):
        if self.production_start_time is not None:
            elapsed_time = datetime.now() - self.production_start_time
            hours, remainder = divmod(int(elapsed_time.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            self.elapsed_time_var.set(time_str)
        else:
            self.elapsed_time_var.set("00:00:00")
        self.parent.after(1000, self.update_elapsed_time)

    def update_clock(self):
        now = datetime.now().strftime('%H:%M:%S')
        self.clock_label.config(text=now)
        self.parent.after(1000, self.update_clock)

    def calculate_production_data(self):
        self.calculate_eau_consomme()
        self.calculate_gaz_consomme()
        self.determine_produit()
        try:
            matieres = self.matieres_premieres.get()
            moyenne_par_heure = matieres / 8
            self.matieres_premieres_moyenne_par_heure.set(round(moyenne_par_heure, 2))
        except tk.TclError:
            self.matieres_premieres_moyenne_par_heure.set(0)
        self.display_production_results()
        self.save_state()

    def calculate_eau_consomme(self):
        try:
            debut = self.eau_debut.get()
            fin = self.eau_fin.get()
            consomme = fin - debut
            self.eau_consomme.set(round(consomme, 2))
            consomme_par_heure = consomme / 8
            self.eau_consomme_par_heure.set(round(consomme_par_heure, 2))
        except tk.TclError:
            pass

    def calculate_gaz_consomme(self):
        try:
            debut = self.gaz_debut.get()
            fin = self.gaz_fin.get()
            total_consomme = fin - debut
            self.gaz_consomme_total.set(round(total_consomme, 2))
            consomme_par_heure = total_consomme / 8
            self.gaz_consomme_par_heure.set(round(consomme_par_heure, 2))
        except tk.TclError:
            pass

    def determine_produit(self):
        lot_num = self.lot.get()
        if lot_num.startswith('7'):
            self.produit.set('Ail')
        elif lot_num.startswith('4'):
            self.produit.set('Échalote')
        elif lot_num.startswith('3'):
            self.produit.set('Oignon')
        else:
            self.produit.set('Inconnu')

    def add_production(self):
        try:
            poids = float(self.prod_entry.get())
            time_now = datetime.now()
            time_str = time_now.strftime('%H:%M')
            index = len(self.fiches_de_prod) + 1

            if self.production_start_time is None:
                self.production_start_time = datetime.now()

            color = (random.random(), random.random(), random.random())

            self.fiches_de_prod.append({'Number': index, 'Time': time_now, 'TimeStr': time_str, 'Weight': poids, 'Color': color})
            self.tree.insert('', 'end', values=(index, time_str, poids))
            self.prod_entry.delete(0, 'end')
            self.update_total_and_frequency()
            self.save_state()
        except ValueError:
            messagebox.showerror("Erreur", "Veuillez entrer un poids valide.")

    def update_total_and_frequency(self):
        total_weight = sum(item['Weight'] for item in self.fiches_de_prod)
        self.total_var.set(round(total_weight, 2))

    def update_frequency(self):
        if not self.fiches_de_prod or self.production_start_time is None:
            self.freq_var.set("0 kg/h")
        else:
            elapsed_time_seconds = (datetime.now() - self.production_start_time).total_seconds()
            elapsed_time_hours = elapsed_time_seconds / 3600.0

            total_weight = sum(item['Weight'] for item in self.fiches_de_prod)

            if elapsed_time_hours < 1:
                self.freq_var.set(f"{round(total_weight, 2)} kg/h")
            else:
                frequency = total_weight / elapsed_time_hours
                self.freq_var.set(f"{round(frequency, 2)} kg/h")
        self.parent.after(60000, self.update_frequency)

    def update_chart(self):
        try:
            self.ax.clear()
            self.ax.set_xlabel('Temps')
            self.ax.set_ylabel('Production (kg)')
            self.ax.grid(True, which='both', linestyle='--', linewidth=0.5)
            self.ax.set_facecolor(self.colors['graph_bg'])
            self.figure.patch.set_facecolor(self.colors['graph_facecolor'])

            if self.fiches_de_prod:
                times = [item['Time'] for item in self.fiches_de_prod]
                weights = [item['Weight'] for item in self.fiches_de_prod]
                colors_list = [item['Color'] for item in self.fiches_de_prod]

                if len(times) > 1:
                    time_diffs = [(t2 - t1).total_seconds() for t1, t2 in zip(times[:-1], times[1:])]
                    min_time_diff = min(time_diffs) if min(time_diffs) > 0 else 60
                    bar_width_seconds = min(min_time_diff / 2, 60)
                    bar_width = timedelta(seconds=bar_width_seconds)
                else:
                    bar_width = timedelta(minutes=1)

                self.ax.bar(times, weights, width=bar_width.total_seconds() / 86400, color=colors_list, align='center', edgecolor='black')
                self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                self.figure.autofmt_xdate()

                for i, (x, y) in enumerate(zip(times, weights)):
                    self.ax.text(x, y, str(self.fiches_de_prod[i]['Number']), ha='center', va='bottom', color='white', fontweight='bold')
            self.figure.tight_layout()
            self.canvas.draw()
        except Exception as e:
            print(f"Erreur dans update_chart: {e}")
        finally:
            self.parent.after(5000, self.update_chart)

    def calculate_finition_totals(self, *args):
        def calc_total(nb_sacs, poids_sac, poids_dernier):
            if nb_sacs > 0 and poids_sac > 0:
                total = (nb_sacs - 1) * poids_sac
                if poids_dernier > 0:
                    total += poids_dernier
                else:
                    total += poids_sac
                return round(total, 2)
            return 0

        self.total_laniere.set(calc_total(self.nb_sacs_laniere.get(), self.poids_sac_laniere.get(), self.poids_dernier_sac_laniere.get()))
        self.total_rejet_sortex.set(calc_total(self.nb_sacs_rejet_sortex.get(), self.poids_sac_rejet_sortex.get(), self.poids_dernier_sac_rejet_sortex.get()))
        self.total_rejet_finition.set(calc_total(self.nb_sacs_rejet_finition.get(), self.poids_sac_rejet_finition.get(), self.poids_dernier_sac_rejet_finition.get()))

        total_sortie = self.total_laniere.get() + self.total_rejet_sortex.get() + self.total_rejet_finition.get()
        self.total_sortie.set(round(total_sortie, 2))

        try:
            matieres_entree = self.matieres_premieres.get()
            if matieres_entree > 0:
                ratio = (total_sortie / matieres_entree) * 100
                self.ratio_entree_sortie.set(round(ratio, 2))
            else:
                self.ratio_entree_sortie.set(0)
        except tk.TclError:
            self.ratio_entree_sortie.set(0)

        self.save_state()

    def reset_fields(self):
        self.eau_debut.set(0)
        self.eau_fin.set(0)
        self.eau_consomme.set(0)
        self.eau_consomme_par_heure.set(0)
        self.gaz_debut.set(0)
        self.gaz_fin.set(0)
        self.gaz_consomme_total.set(0)
        self.gaz_consomme_par_heure.set(0)
        self.matieres_premieres.set(0)
        self.matieres_premieres_moyenne_par_heure.set(0)
        self.lot.set('')
        self.produit.set('')
        self.observations_text.delete("1.0", tk.END)
        self.fiches_de_prod.clear()
        self.production_start_time = None
        self.elapsed_time_var.set("00:00:00")
        self.heure_debut_entry.delete(0, 'end')
        self.heure_debut_entry.insert(0, datetime.now().strftime('%H:%M'))

        self.nb_sacs_laniere.set(0)
        self.poids_dernier_sac_laniere.set(0)
        self.poids_sac_laniere.set(0)
        self.total_laniere.set(0)
        self.nb_sacs_rejet_sortex.set(0)
        self.poids_dernier_sac_rejet_sortex.set(0)
        self.poids_sac_rejet_sortex.set(0)
        self.total_rejet_sortex.set(0)
        self.nb_sacs_rejet_finition.set(0)
        self.poids_dernier_sac_rejet_finition.set(0)
        self.poids_sac_rejet_finition.set(0)
        self.total_rejet_finition.set(0)
        self.total_sortie.set(0)
        self.ratio_entree_sortie.set(0)

        for item in self.tree.get_children():
            self.tree.delete(item)

        self.total_var.set(0)
        self.freq_var.set("0 kg/h")
        self.elapsed_time_var.set("00:00:00")

        for widget in self.resultat_frame_production.winfo_children():
            widget.destroy()
        self.save_state()

    def archive_txt_file(self, filename):
        archive_dir = os.path.join(os.path.dirname(__file__), "Archive-Prod")
        if not os.path.exists(archive_dir):
            os.makedirs(archive_dir)
        base_name = os.path.basename(filename)
        dest = os.path.join(archive_dir, base_name)
        shutil.move(filename, dest)
        print(f"Fichier {filename} archivé dans {archive_dir}.")

    def save_data(self):
        data_to_save = []
        data_to_save.append(f"Heure de début de poste: {self.heure_debut_entry.get()}")
        data_to_save.append(f"Eau début: {self.eau_debut.get()}")
        data_to_save.append(f"Eau fin: {self.eau_fin.get()}")
        data_to_save.append(f"Gaz début: {self.gaz_debut.get()}")
        data_to_save.append(f"Gaz fin: {self.gaz_fin.get()}")
        data_to_save.append(f"Matières premières: {self.matieres_premieres.get()}")
        data_to_save.append(f"Lot: {self.lot.get()}")
        data_to_save.append(f"Produit: {self.produit.get()}")
        data_to_save.append("Observations:")
        observations_text = self.observations_text.get("1.0", "end").strip()
        data_to_save.append(observations_text)
        data_to_save.append("Finitions:")
        data_to_save.append(f"  Total Lanière (kg): {self.total_laniere.get()}")
        data_to_save.append(f"  Total Rejet Sortex (kg): {self.total_rejet_sortex.get()}")
        data_to_save.append(f"  Total Rejet Finition (kg): {self.total_rejet_finition.get()}")
        data_to_save.append(f"  Total Sortie (kg): {self.total_sortie.get()}")
        data_to_save.append(f"  Ratio Entrée/Sortie (%): {self.ratio_entree_sortie.get()}")
        data_to_save.append("Fiches de production:")
        for item in self.fiches_de_prod:
            data_to_save.append(f"  #{item['Number']} - Heure: {item['TimeStr']}, Poids: {item['Weight']} kg")
        data_to_save.append(f"Total Production: {self.total_var.get()} kg")
        data_to_save.append(f"Quantité passée par heure: {self.freq_var.get()}")

        filename = f"rochias_pod_calculator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            for line in data_to_save:
                f.write(line + '\n')
        messagebox.showinfo("Sauvegarde", f"Les données ont été sauvegardées dans le fichier {filename}")

        self.archive_txt_file(filename)
        self.save_state()

    def save_state(self):
        serializable_fiches_de_prod = []
        for item in self.fiches_de_prod:
            serializable_item = item.copy()
            serializable_item['Time'] = item['Time'].isoformat()
            serializable_fiches_de_prod.append(serializable_item)

        state = {
            'eau_debut': self.eau_debut.get(),
            'eau_fin': self.eau_fin.get(),
            'gaz_debut': self.gaz_debut.get(),
            'gaz_fin': self.gaz_fin.get(),
            'matieres_premieres': self.matieres_premieres.get(),
            'lot': self.lot.get(),
            'produit': self.produit.get(),
            'observations': self.observations_text.get("1.0", "end"),
            'nb_sacs_laniere': self.nb_sacs_laniere.get(),
            'poids_dernier_sac_laniere': self.poids_dernier_sac_laniere.get(),
            'poids_sac_laniere': self.poids_sac_laniere.get(),
            'nb_sacs_rejet_sortex': self.nb_sacs_rejet_sortex.get(),
            'poids_dernier_sac_rejet_sortex': self.poids_dernier_sac_rejet_sortex.get(),
            'poids_sac_rejet_sortex': self.poids_sac_rejet_sortex.get(),
            'nb_sacs_rejet_finition': self.nb_sacs_rejet_finition.get(),
            'poids_dernier_sac_rejet_finition': self.poids_dernier_sac_rejet_finition.get(),
            'poids_sac_rejet_finition': self.poids_sac_rejet_finition.get(),
            'total_laniere': self.total_laniere.get(),
            'total_rejet_sortex': self.total_rejet_sortex.get(),
            'total_rejet_finition': self.total_rejet_finition.get(),
            'total_sortie': self.total_sortie.get(),
            'ratio_entree_sortie': self.ratio_entree_sortie.get(),
            'fiches_de_prod': serializable_fiches_de_prod,
            'chrono_running': self.chrono_running,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'elapsed_time_seconds': self.elapsed_time.total_seconds(),
            'production_start_time': self.production_start_time.isoformat() if self.production_start_time else None,
            'heure_debut_poste': self.heure_debut_entry.get(),
            'total_var': self.total_var.get(),
            'freq_var': self.freq_var.get()
        }
        print("Sauvegarde de l'état dans", self.state_filename)
        with open(self.state_filename, 'wb') as f:
            pickle.dump(state, f)
        print("État sauvegardé avec succès.")

    def load_state(self):
        try:
            print("Chargement de l'état depuis", self.state_filename)
            with open(self.state_filename, 'rb') as f:
                state = pickle.load(f)
            print("État chargé avec succès:", state.keys())
            self.eau_debut.set(state['eau_debut'])
            self.eau_fin.set(state['eau_fin'])
            self.gaz_debut.set(state['gaz_debut'])
            self.gaz_fin.set(state['gaz_fin'])
            self.matieres_premieres.set(state['matieres_premieres'])
            self.lot.set(state['lot'])
            self.produit.set(state['produit'])
            self.observations_text.delete("1.0", tk.END)
            self.observations_text.insert(tk.END, state['observations'])
            self.nb_sacs_laniere.set(state['nb_sacs_laniere'])
            self.poids_dernier_sac_laniere.set(state['poids_dernier_sac_laniere'])
            self.poids_sac_laniere.set(state['poids_sac_laniere'])
            self.nb_sacs_rejet_sortex.set(state['nb_sacs_rejet_sortex'])
            self.poids_dernier_sac_rejet_sortex.set(state['poids_dernier_sac_rejet_sortex'])
            self.poids_sac_rejet_sortex.set(state['poids_sac_rejet_sortex'])
            self.nb_sacs_rejet_finition.set(state['nb_sacs_rejet_finition'])
            self.poids_dernier_sac_rejet_finition.set(state['poids_dernier_sac_rejet_finition'])
            self.poids_sac_rejet_finition.set(state['poids_sac_rejet_finition'])
            self.total_laniere.set(state['total_laniere'])
            self.total_rejet_sortex.set(state['total_rejet_sortex'])
            self.total_rejet_finition.set(state['total_rejet_finition'])
            self.total_sortie.set(state['total_sortie'])
            self.ratio_entree_sortie.set(state['ratio_entree_sortie'])
            self.chrono_running = state['chrono_running']
            self.start_time = datetime.fromisoformat(state['start_time']) if state['start_time'] else None
            self.elapsed_time = timedelta(seconds=state['elapsed_time_seconds'])
            self.production_start_time = datetime.fromisoformat(state['production_start_time']) if state['production_start_time'] else None
            self.heure_debut_entry.delete(0, tk.END)
            self.heure_debut_entry.insert(0, state['heure_debut_poste'])
            self.total_var.set(state['total_var'])
            self.freq_var.set(state['freq_var'])

            self.fiches_de_prod = []
            self.tree.delete(*self.tree.get_children())
            for item in state['fiches_de_prod']:
                item['Time'] = datetime.fromisoformat(item['Time'])
                self.fiches_de_prod.append(item)
                self.tree.insert('', 'end', values=(item['Number'], item['TimeStr'], item['Weight']))

            self.calculate_production_data()
            self.calculate_finition_totals()
            self.update_total_and_frequency()
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de charger l'état : {e}")
            print("Erreur lors du chargement de l'état:", e)

    def display_production_results(self):
        for widget in self.resultat_frame_production.winfo_children():
            widget.destroy()

        ttk.Label(self.resultat_frame_production, text=f"Eau consommée (m³) : {self.eau_consomme.get()}").pack(anchor='w', pady=2)
        ttk.Label(self.resultat_frame_production, text=f"Eau consommée par heure (m³/h) : {self.eau_consomme_par_heure.get()}").pack(anchor='w', pady=2)
        ttk.Label(self.resultat_frame_production, text=f"Gaz consommé (m³) : {self.gaz_consomme_total.get()}").pack(anchor='w', pady=2)
        ttk.Label(self.resultat_frame_production, text=f"Gaz consommé par heure (m³/h) : {self.gaz_consomme_par_heure.get()}").pack(anchor='w', pady=2)
        ttk.Label(self.resultat_frame_production, text=f"Matières premières (kg) : {self.matieres_premieres.get()}").pack(anchor='w', pady=2)
        ttk.Label(self.resultat_frame_production, text=f"Moyenne matières premières par heure (kg/h) : {self.matieres_premieres_moyenne_par_heure.get()}").pack(anchor='w', pady=2)
        ttk.Label(self.resultat_frame_production, text=f"Produit : {self.produit.get()}").pack(anchor='w', pady=2)

    def open_historique_window(self):
        archive_dir = os.path.join(os.path.dirname(__file__), "Archive-Prod")
        self.histo_window = tk.Toplevel(self.parent)
        self.histo_window.title("Historique des productions")
        self.histo_window.configure(bg=self.colors['bg'])

        histo_frame = tk.Frame(self.histo_window, bg=self.colors['bg'])
        histo_frame.pack(fill='both', expand=True, padx=10, pady=10)

        ttk.Label(histo_frame, text="Fichiers archivés:", background=self.colors['bg'], foreground=self.colors['fg']).pack(anchor='w', pady=5)

        self.histo_listbox = tk.Listbox(histo_frame, bg=self.colors['entry_bg'], fg=self.colors['entry_fg'], font=(self.font_family, 9))
        self.histo_listbox.pack(fill='both', expand=True, pady=5)

        if os.path.exists(archive_dir):
            files = os.listdir(archive_dir)
            for f in files:
                if f.startswith("rochias_pod_calculator_") and f.endswith(".txt"):
                    self.histo_listbox.insert(tk.END, f)

        btn_frame = tk.Frame(histo_frame, bg=self.colors['bg'])
        btn_frame.pack(fill='x', pady=5)

        afficher_button = ttk.Button(btn_frame, text="Afficher le contenu", command=self.afficher_historique_contenu)
        afficher_button.pack(side='left', padx=5)

        self.histo_text = tk.Text(histo_frame, bg=self.colors['entry_bg'], fg=self.colors['entry_fg'], wrap='word', font=(self.font_family, 9))
        self.histo_text.pack(fill='both', expand=True, pady=5)

    def afficher_historique_contenu(self):
        archive_dir = os.path.join(os.path.dirname(__file__), "Archive-Prod")
        selection = self.histo_listbox.curselection()
        if not selection:
            messagebox.showwarning("Attention", "Veuillez sélectionner un fichier.")
            return

        filename = self.histo_listbox.get(selection[0])
        file_path = os.path.join(archive_dir, filename)

        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.histo_text.delete("1.0", tk.END)
            self.histo_text.insert(tk.END, content)
        else:
            messagebox.showerror("Erreur", "Le fichier sélectionné n'existe pas.")
