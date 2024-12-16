# train_ia.py
import os
import json
import logging
import threading
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image
from datetime import datetime
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.model_selection import KFold
from tensorflow.keras.callbacks import ModelCheckpoint

from data_utils import (THEME, DATA_DIR, MODELS_DIR, IMAGE_SIZE, NB_IMAGES_PER_SET,
                        load_sechoir_data, extract_set_data, get_last_valid_temp_entry,
                        load_model_from_file, get_latest_model, load_and_concat_images,
                        safe_float)
from model_utils import (MODEL_PARAMS, build_model_from_params, save_model, create_optimizer,
                         ParamWindow, HistoryWindow)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger("train_ia")

DATA_LOADED = False  # Indicateur global indiquant si les données du séchoir sont chargées.


class ModelController:
    """
    Cette classe gère la logique métier du modèle IA :
    - Création/validation
    - Chargement/sauvegarde
    - Entraînement, validation croisée, évaluation
    - Mise à jour du modèle avec les données de production (fine-tuning)
    """

    def __init__(self, params):
        self.params = params
        self.model = None
        self.validated = False

    def validate_model(self, model_name, model_type):
        if self.model is not None:
            raise ValueError("Le modèle est déjà validé.")
        if not model_name.strip():
            raise ValueError("Veuillez saisir un nom de modèle.")
        image_shape = (32, 32 * 6, 3)
        numeric_dim = 11
        self.model = build_model_from_params(image_shape, numeric_dim, 11, self.params)
        self.validated = True

    def load_model(self, path):
        m = load_model_from_file(path)
        if m is None:
            raise ValueError("Impossible de charger le modèle.")
        self.model = m
        self.validated = True

    def is_validated(self):
        return self.validated and self.model is not None

    def train_model(self, sets_info, product_type):
        if not self.is_validated():
            raise ValueError("Modèle non validé pour l'entraînement.")

        arch = self.params.get('architecture', 'Dense')
        if self.params.get('fine_tuning', False) and arch != 'CNN+Dense':
            self.params['fine_tuning'] = False
            self.params['fine_tuning_layers'] = 0
            logger.info("Fine-tuning désactivé: architecture non CNN+Dense.")

        use_augmentation = self.params.get('use_augmentation', False)

        X_image_list = []
        X_num_list = []
        Y_list = []

        for s in sets_info:
            set_name, set_product, img_list_conformes, img_list_non_conformes = s
            if set_product == product_type:
                X, Y = extract_set_data(img_list_conformes, img_list_non_conformes, use_augmentation=use_augmentation)
                if X is not None and Y is not None:
                    X_image, X_numeric = X
                    X_image_list.append(X_image)
                    X_num_list.append(X_numeric)
                    Y_list.append(Y)

        if not Y_list:
            raise ValueError("Aucun set pour ce type de produit.")

        X_image_all = np.vstack(X_image_list)
        X_numeric_all = np.vstack(X_num_list)
        Y_all = np.vstack(Y_list)

        n_epochs = self.params['n_epochs']
        batch_size = self.params['batch_size']

        callbacks = []
        if self.params.get('use_checkpoints', False):
            checkpoint_path = os.path.join(MODELS_DIR, "best_model.h5")
            checkpoint_cb = ModelCheckpoint(checkpoint_path, save_best_only=True, monitor='loss', mode='min')
            callbacks.append(checkpoint_cb)

        self.model.fit([X_image_all, X_numeric_all], Y_all,
                       epochs=n_epochs, batch_size=batch_size, verbose=1, callbacks=callbacks)

        if self.params.get('use_checkpoints', False):
            if os.path.exists(checkpoint_path):
                self.model.load_weights(checkpoint_path)
                logger.info("Meilleur modèle rechargé depuis checkpoints.")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_name = f"{product_type}_model_{timestamp}"
        save_model(self.model, model_name)
        return model_name

    def cross_validate(self, sets_info, product_type):
        if not self.is_validated():
            raise ValueError("Modèle non validé pour la validation croisée.")

        filtered_sets = [s for s in sets_info if s[1] == product_type]
        if not filtered_sets:
            raise ValueError("Aucun set pour le produit spécifié.")

        use_augmentation = self.params.get('use_augmentation', False)

        X_image_list = []
        X_num_list = []
        Y_list = []
        for s in filtered_sets:
            set_name, set_product, img_list_conformes, img_list_non_conformes = s
            X, Y = extract_set_data(img_list_conformes, img_list_non_conformes, use_augmentation=use_augmentation)
            if X is not None and Y is not None:
                X_image, X_numeric = X
                X_image_list.append(X_image)
                X_num_list.append(X_numeric)
                Y_list.append(Y)

        if not Y_list:
            raise ValueError("Impossible de constituer un dataset pour la validation croisée.")

        X_image_all = np.vstack(X_image_list)
        X_numeric_all = np.vstack(X_num_list)
        Y_all = np.vstack(Y_list)

        n_splits = 5
        kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)
        mse_scores = []
        mae_scores = []
        r2_scores = []

        image_shape = (32, 32 * 6, 3)
        numeric_dim = 11

        for train_index, val_index in kf.split(X_image_all):
            X_image_train, X_image_val = X_image_all[train_index], X_image_all[val_index]
            X_num_train, X_num_val = X_numeric_all[train_index], X_numeric_all[val_index]
            Y_train, Y_val = Y_all[train_index], Y_all[val_index]

            model = build_model_from_params(image_shape, numeric_dim, 11, self.params)
            model.fit([X_image_train, X_num_train], Y_train,
                      epochs=self.params['n_epochs'], batch_size=self.params['batch_size'], verbose=0)
            pred = model.predict([X_image_val, X_num_val], verbose=0)
            mse = mean_squared_error(Y_val, pred)
            mae = mean_absolute_error(Y_val, pred)
            r2 = r2_score(Y_val, pred)

            mse_scores.append(mse)
            mae_scores.append(mae)
            r2_scores.append(r2)

        return np.mean(mse_scores), np.mean(mae_scores), np.mean(r2_scores)

    def evaluate(self, validation_data, model_type):
        if self.model is None:
            latest = get_latest_model(model_type)
            if not latest:
                raise ValueError("Aucun modèle disponible.")
            m = load_model_from_file(latest)
            if m is None:
                raise ValueError("Impossible de charger le modèle.")
            self.model = m

        X_image_list = []
        X_num_list = []
        Y_list = []
        # Pas d'augmentation sur validation externe
        for entry in validation_data:
            img_list_conformes = entry.get('img_list_conformes', [])
            img_list_non_conformes = entry.get('img_list_non_conformes', [])
            X, Y = self.extract_from_validation_entry(entry, img_list_conformes, img_list_non_conformes)
            if X is not None and Y is not None:
                X_image, X_numeric = X
                X_image_list.append(X_image)
                X_num_list.append(X_numeric)
                Y_list.append(Y)

        if not Y_list:
            raise ValueError("Données validation non exploitables.")

        X_image_val = np.vstack(X_image_list)
        X_num_val = np.vstack(X_num_list)
        Y_val = np.vstack(Y_list)
        pred = self.model.predict([X_image_val, X_num_val])
        mse = mean_squared_error(Y_val, pred)
        mae = mean_absolute_error(Y_val, pred)
        r2 = r2_score(Y_val, pred)
        return mse, mae, r2

    def extract_from_validation_entry(self, entry, img_list_conformes, img_list_non_conformes):
        four_data = entry.get('four_data', {})
        consignes = four_data.get('temperatures_consignes', [])
        reelles = four_data.get('temperatures_reelles', [])
        tapis = four_data.get('tapis', [])

        last_con = get_last_valid_temp_entry(consignes)
        last_re = get_last_valid_temp_entry(reelles)
        if last_con is None or last_re is None or not tapis:
            return None, None

        last_tapis = tapis[-1]
        cels_con = last_con.get('cels', [])
        cels_re = last_re.get('cels', [])
        if len(cels_con) != 6 or len(cels_re) != 6:
            return None, None

        img_arr = load_and_concat_images(img_list_conformes, img_list_non_conformes, size=IMAGE_SIZE, use_augmentation=False)
        if img_arr is None:
            logger.warning("Impossible de charger certaines images validation. Images nulles.")
            img_arr = np.zeros((32, 32*6, 3), dtype=np.float32)

        X_image = img_arr[np.newaxis, ...]
        X_numeric = []
        for val in cels_con:
            X_numeric.append(safe_float(val))
        X_numeric.append(safe_float(last_con.get('air_neuf', 0.0)))
        X_numeric.append(safe_float(last_tapis.get('vit_stockeur', 0.0)))
        X_numeric.append(safe_float(last_tapis.get('tapis1', 0.0)))
        X_numeric.append(safe_float(last_tapis.get('tapis2', 0.0)))
        X_numeric.append(safe_float(last_tapis.get('tapis3', 0.0)))
        X_numeric = np.array(X_numeric).reshape(1, -1)

        Y = []
        for val in cels_re:
            Y.append(safe_float(val))
        Y.append(safe_float(last_re.get('air_neuf', 0.0)))
        Y.append(safe_float(last_tapis.get('vit_stockeur', 0.0)))
        Y.append(safe_float(last_tapis.get('tapis1', 0.0)))
        Y.append(safe_float(last_tapis.get('tapis2', 0.0)))
        Y.append(safe_float(last_tapis.get('tapis3', 0.0)))
        Y = np.array(Y).reshape(1, -1)

        return (X_image, X_numeric), Y

    def update_with_production(self, production_data_sets):
        if self.model is None:
            raise ValueError("Aucun modèle chargé pour la mise à jour.")
        if not production_data_sets:
            raise ValueError("Aucune donnée de production ajoutée.")

        X_image_list = []
        X_num_list = []
        Y_list = []
        for (X, Y) in production_data_sets:
            X_image, X_numeric = X
            X_image_list.append(X_image)
            X_num_list.append(X_numeric)
            Y_list.append(Y)

        X_image_all = np.vstack(X_image_list)
        X_numeric_all = np.vstack(X_num_list)
        Y_all = np.vstack(Y_list)

        arch = self.params.get('architecture', 'Dense')
        if self.params.get('fine_tuning', False) and arch == 'CNN+Dense':
            from tensorflow import keras
            conv_layers = [l for l in self.model.layers if isinstance(l, keras.layers.Conv2D)]
            fine_tuning_layers = self.params.get('fine_tuning_layers', 0)
            if conv_layers:
                for layer in conv_layers:
                    layer.trainable = False
                for layer in conv_layers[-fine_tuning_layers:]:
                    layer.trainable = True
                self.model.compile(optimizer=create_optimizer(self.params),
                                   loss='mean_squared_error',
                                   metrics=['mae','mean_squared_error'])

        self.model.fit([X_image_all, X_numeric_all], Y_all, epochs=1, batch_size=self.params['batch_size'], verbose=1)


def create_thematic_frame(parent, title=None, theme=THEME):
    if title:
        frame = tk.LabelFrame(parent, text=title, bg=theme['bg_section'], fg='white', font=theme['title_font'])
    else:
        frame = tk.Frame(parent, bg=theme['bg_section'])
    return frame


class TrainIAModuleFrame(tk.Frame):
    """
    Cette classe gère l'interface graphique et communique avec ModelController pour la logique du modèle.
    """

    def __init__(self, parent, main_app):
        super().__init__(parent, bg=THEME['bg_main'])
        self.main_app = main_app
        self.controller = ModelController(MODEL_PARAMS)
        self.validation_data = None

        self.model_name_var = tk.StringVar(value="mon_modele")
        self.model_type_var = tk.StringVar(value="Ail")
        self.model_algo_var = tk.StringVar(value=MODEL_PARAMS.get('model_label', 'Réseau de Neurones'))

        self.sets_info = []
        self.img_paths_conformes = [tk.StringVar() for _ in range(NB_IMAGES_PER_SET)]
        self.img_paths_non_conformes = [tk.StringVar() for _ in range(NB_IMAGES_PER_SET)]

        self.set_name_var = tk.StringVar(value="set_1")
        self.set_product_type_var = tk.StringVar(value="Ail")
        self.train_product_type_var = tk.StringVar(value="Ail")

        self.auto_collect_var = tk.BooleanVar(value=True)

        self.manual_vit_stockeur_var = tk.StringVar()
        self.manual_tapis1_var = tk.StringVar()
        self.manual_tapis2_var = tk.StringVar()
        self.manual_tapis3_var = tk.StringVar()

        self.manual_con_cels_var = [tk.StringVar() for _ in range(6)]
        self.manual_con_air_var = tk.StringVar()

        self.manual_re_cels_var = [tk.StringVar() for _ in range(6)]
        self.manual_re_air_var = tk.StringVar()

        self.production_data_sets = []

        self.setup_ui()
        self.update_ui_state()

    def setup_ui(self):
        # Canvas principal avec scroll
        self.canvas = tk.Canvas(self, bg=THEME['bg_main'], highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.inner_frame = tk.Frame(self.canvas, bg=THEME['bg_main'])
        self.inner_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.create_window((0,0), window=self.inner_frame, anchor="nw")
        self.inner_frame.bind("<Enter>", self._bind_mousewheel)
        self.inner_frame.bind("<Leave>", self._unbind_mousewheel)

        # Frame Modèle
        model_frame = create_thematic_frame(self.inner_frame, "Création du Modèle IA")
        model_frame.pack(padx=10, pady=10, fill='x')

        tk.Label(model_frame, text="Nom du Modèle :", bg=THEME['bg_section'], fg='white').grid(row=0, column=0, sticky='e', padx=5, pady=5)
        self.model_name_entry = tk.Entry(model_frame, textvariable=self.model_name_var, bg=THEME['text_bg'], fg='white')
        self.model_name_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(model_frame, text="Type de produit (Modèle) :", bg=THEME['bg_section'], fg='white').grid(row=1, column=0, sticky='e', padx=5, pady=5)
        product_options = ["Ail", "Oignon", "Échalote"]
        self.product_combo_model = ttk.Combobox(model_frame, textvariable=self.model_type_var, values=product_options, state="readonly")
        self.product_combo_model.grid(row=1, column=1, padx=5, pady=5, sticky='w')

        tk.Label(model_frame, text="Type d'algorithme :", bg=THEME['bg_section'], fg='white').grid(row=2, column=0, sticky='e', padx=5, pady=5)
        algo_options = ['Réseau de Neurones']
        self.algo_combo = ttk.Combobox(model_frame, textvariable=self.model_algo_var, values=algo_options, state="readonly")
        self.algo_combo.grid(row=2, column=1, padx=5, pady=5, sticky='w')

        tk.Button(model_frame, text="Paramètres du Modèle", bg=THEME['button_bg'], fg='white', command=self.open_param_window).grid(row=3, column=0, columnspan=2, pady=5)
        tk.Button(model_frame, text="Historique du modèle", bg=THEME['button_bg'], fg='white', command=self.open_history_window).grid(row=4, column=0, columnspan=2, pady=5)

        tk.Button(model_frame, text="Nouveau Modèle", bg=THEME['accent2'], fg='white', command=self.new_model_action).grid(row=5, column=0, padx=5, pady=5)
        tk.Button(model_frame, text="Valider le Modèle", bg=THEME['accent'], fg='white', command=self.validate_model_action).grid(row=5, column=1, padx=5, pady=5)

        tk.Button(model_frame, text="Charger un modèle", bg=THEME['button_bg'], fg='white', command=self.load_model_action).grid(row=6, column=0, padx=5, pady=5)
        tk.Button(model_frame, text="Exporter un modèle", bg=THEME['button_bg'], fg='white', command=self.export_model_action).grid(row=6, column=1, padx=5, pady=5)

        tk.Button(model_frame, text="Afficher résumé du modèle", bg=THEME['button_bg'], fg='white', command=self.show_model_summary).grid(row=7, column=0, columnspan=2, pady=5)

        tk.Button(model_frame, text="Exporter config", bg=THEME['button_bg'], fg='white', command=self.export_config).grid(row=8, column=0, padx=5, pady=5)
        tk.Button(model_frame, text="Importer config", bg=THEME['button_bg'], fg='white', command=self.import_config).grid(row=8, column=1, padx=5, pady=5)

        # Frame Données
        data_frame = create_thematic_frame(self.inner_frame, "Préparation des Sets de Données")
        data_frame.pack(padx=10, pady=10, fill='x')

        tk.Label(data_frame, text="Nom du set :", bg=THEME['bg_section'], fg='white').grid(row=0, column=0, sticky='e', padx=5, pady=5)
        tk.Entry(data_frame, textvariable=self.set_name_var, bg=THEME['text_bg'], fg='white').grid(row=0, column=1, padx=5, pady=5)

        tk.Label(data_frame, text="Type de produit (Set) :", bg=THEME['bg_section'], fg='white').grid(row=1, column=0, sticky='e', padx=5, pady=5)
        product_combo_set = ttk.Combobox(data_frame, textvariable=self.set_product_type_var, values=["Ail", "Oignon", "Échalote"], state="readonly")
        product_combo_set.grid(row=1, column=1, padx=5, pady=5, sticky='w')

        tk.Label(data_frame, text=f"Sélectionnez {NB_IMAGES_PER_SET} images CONFORMES :", bg=THEME['bg_section'], fg='white').grid(row=2, column=0, columnspan=NB_IMAGES_PER_SET, sticky='w', padx=5, pady=5)
        for i in range(NB_IMAGES_PER_SET):
            tk.Button(data_frame, text=f"Image Conforme {i+1}", bg=THEME['button_bg'], fg='white', command=lambda idx=i: self.browse_image(self.img_paths_conformes[idx])).grid(row=3, column=i, padx=5, pady=5)
            tk.Entry(data_frame, textvariable=self.img_paths_conformes[i], width=50, bg=THEME['text_bg'], fg='white').grid(row=4, column=i, padx=5, pady=5)

        tk.Label(data_frame, text=f"Sélectionnez {NB_IMAGES_PER_SET} images NON CONFORMES :", bg=THEME['bg_section'], fg='white').grid(row=5, column=0, columnspan=NB_IMAGES_PER_SET, sticky='w', padx=5, pady=5)
        for i in range(NB_IMAGES_PER_SET):
            tk.Button(data_frame, text=f"Image NON Conforme {i+1}", bg=THEME['button_bg'], fg='white', command=lambda idx=i: self.browse_image(self.img_paths_non_conformes[idx])).grid(row=6, column=i, padx=5, pady=5)
            tk.Entry(data_frame, textvariable=self.img_paths_non_conformes[i], width=50, bg=THEME['text_bg'], fg='white').grid(row=7, column=i, padx=5, pady=5)

        auto_check = tk.Checkbutton(data_frame, text="Collecte automatique des données (séchoir)",
                                    variable=self.auto_collect_var, bg=THEME['bg_section'], fg='white',
                                    selectcolor=THEME['highlight'], activebackground=THEME['bg_section'],
                                    activeforeground='white')
        auto_check.grid(row=8, column=0, columnspan=NB_IMAGES_PER_SET, sticky='w', padx=5, pady=5)

        manual_frame = create_thematic_frame(data_frame, "Données Manuelles (si auto non-coché)")
        manual_frame.grid(row=9, column=0, columnspan=NB_IMAGES_PER_SET, pady=10)

        tk.Label(manual_frame, text="Vit. Stockeur (Hz)", bg=THEME['bg_section'], fg='white').grid(row=0, column=0, padx=2, pady=5)
        tk.Entry(manual_frame, textvariable=self.manual_vit_stockeur_var, width=8, bg=THEME['text_bg'], fg='white').grid(row=0, column=1, padx=2, pady=5)
        tk.Label(manual_frame, text="Tapis1 (Hz)", bg=THEME['bg_section'], fg='white').grid(row=0, column=2, padx=2, pady=5)
        tk.Entry(manual_frame, textvariable=self.manual_tapis1_var, width=8, bg=THEME['text_bg'], fg='white').grid(row=0, column=3, padx=2, pady=5)
        tk.Label(manual_frame, text="Tapis2 (Hz)", bg=THEME['bg_section'], fg='white').grid(row=0, column=4, padx=2, pady=5)
        tk.Entry(manual_frame, textvariable=self.manual_tapis2_var, width=8, bg=THEME['text_bg'], fg='white').grid(row=0, column=5, padx=2, pady=5)
        tk.Label(manual_frame, text="Tapis3 (Hz)", bg=THEME['bg_section'], fg='white').grid(row=0, column=6, padx=2, pady=5)
        tk.Entry(manual_frame, textvariable=self.manual_tapis3_var, width=8, bg=THEME['text_bg'], fg='white').grid(row=0, column=7, padx=2, pady=5)

        cels_names = ["CEL1","CEL2","CEL3","CEL4","CEL5/6","CEL7/8"]
        tk.Label(manual_frame, text="Consignes CELS:", bg=THEME['bg_section'], fg='white').grid(row=1, column=0, padx=2, pady=5)
        for i,cn in enumerate(cels_names):
            tk.Label(manual_frame, text=cn, bg=THEME['bg_section'], fg='white').grid(row=1, column=1+i*2, padx=2, pady=5)
            tk.Entry(manual_frame, textvariable=self.manual_con_cels_var[i], width=5, bg=THEME['text_bg'], fg='white').grid(row=1, column=2+i*2, padx=2, pady=5)
        tk.Label(manual_frame, text="AirNeuf Consigne", bg=THEME['bg_section'], fg='white').grid(row=2, column=0, padx=2, pady=5)
        self.manual_con_air_var.set("0")
        tk.Entry(manual_frame, textvariable=self.manual_con_air_var, width=5, bg=THEME['text_bg'], fg='white').grid(row=2, column=1, padx=2, pady=5)

        tk.Label(manual_frame, text="Réelles CELS:", bg=THEME['bg_section'], fg='white').grid(row=3, column=0, padx=2, pady=5)
        for i,cn in enumerate(cels_names):
            tk.Label(manual_frame, text=cn, bg=THEME['bg_section'], fg='white').grid(row=3, column=1+i*2, padx=2, pady=5)
            tk.Entry(manual_frame, textvariable=self.manual_re_cels_var[i], width=5, bg=THEME['text_bg'], fg='white').grid(row=3, column=2+i*2, padx=2, pady=5)
        tk.Label(manual_frame, text="AirNeuf Réelle", bg=THEME['bg_section'], fg='white').grid(row=4, column=0, padx=2, pady=5)
        self.manual_re_air_var.set("0")
        tk.Entry(manual_frame, textvariable=self.manual_re_air_var, width=5, bg=THEME['text_bg'], fg='white').grid(row=4, column=1, padx=2, pady=5)

        tk.Button(data_frame, text="Ajouter ce set de données", bg=THEME['accent'], fg='white', command=self.add_data_set_action).grid(row=10, column=0, columnspan=NB_IMAGES_PER_SET, pady=10)

        sets_list_frame = create_thematic_frame(self.inner_frame, "Sets Ajoutés")
        sets_list_frame.pack(padx=10, pady=10, fill='x')

        self.sets_tree = ttk.Treeview(sets_list_frame, columns=("name", "product", "images"), show='headings', height=5)
        self.sets_tree.pack(fill='x', padx=5, pady=5)
        self.sets_tree.heading("name", text="Nom du set")
        self.sets_tree.heading("product", text="Produit")
        self.sets_tree.heading("images", text="Nb Images")
        self.sets_tree.column("name", width=150)
        self.sets_tree.column("product", width=100)
        self.sets_tree.column("images", width=100)

        tk.Button(sets_list_frame, text="Charger sets (JSON)", bg=THEME['button_bg'], fg='white', command=self.load_sets_action).pack(side='left', padx=5, pady=5)
        tk.Button(sets_list_frame, text="Exporter sets (JSON)", bg=THEME['button_bg'], fg='white', command=self.export_sets_action).pack(side='left', padx=5, pady=5)

        train_frame = create_thematic_frame(self.inner_frame, "Entraînement & Évaluation")
        train_frame.pack(padx=10, pady=10, fill='x')

        tk.Label(train_frame, text="Type de produit pour l'entraînement :", bg=THEME['bg_section'], fg='white').grid(row=0, column=0, sticky='e', padx=5, pady=5)
        product_combo_train = ttk.Combobox(train_frame, textvariable=self.train_product_type_var, values=["Ail", "Oignon", "Échalote"], state="readonly")
        product_combo_train.grid(row=0, column=1, padx=5, pady=5, sticky='w')

        tk.Button(train_frame, text="Entraîner le modèle avec tous les sets (même produit)", bg=THEME['accent2'], fg='white', command=self.start_training_thread).grid(row=1, column=0, columnspan=2, pady=5)
        tk.Button(train_frame, text="Validation Croisée Interne", bg=THEME['button_bg'], fg='white', command=self.start_cross_validation_thread).grid(row=2, column=0, columnspan=2, pady=5)

        eval_frame = tk.Frame(train_frame, bg=THEME['bg_section'])
        eval_frame.grid(row=3, column=0, columnspan=2, pady=5)
        tk.Button(eval_frame, text="Charger dataset de validation", bg=THEME['button_bg'], fg='white', command=self.load_validation_data_action).pack(side='left', padx=5)
        tk.Button(eval_frame, text="Évaluer le modèle", bg=THEME['button_bg'], fg='white', command=self.evaluate_model_action).pack(side='left', padx=5)

        production_frame = create_thematic_frame(self.inner_frame, "Mode Production (adaptation continue)")
        production_frame.pack(padx=10, pady=10, fill='x')

        tk.Label(production_frame, text="Ajouter de nouvelles données (conformes / non conformes + valeurs) en cours de production, puis réactualiser le modèle :", bg=THEME['bg_section'], fg='white').pack(padx=5, pady=5)

        tk.Button(production_frame, text="Ajouter données de Production", bg=THEME['accent'], fg='white', command=self.add_production_data_action).pack(padx=5, pady=5)
        tk.Button(production_frame, text="Mettre à jour le modèle avec données de Production", bg=THEME['accent2'], fg='white', command=self.update_model_with_production_data_action).pack(padx=5, pady=5)

    def update_ui_state(self):
        if self.controller.is_validated():
            self.model_name_entry.config(state='disabled')
            self.product_combo_model.config(state='disabled')
        else:
            self.model_name_entry.config(state='normal')
            self.product_combo_model.config(state='readonly')

    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _bind_mousewheel(self, _event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel_linux)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel_linux)

    def _unbind_mousewheel(self, _event):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _on_mousewheel_linux(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")

    def browse_image(self, var):
        path = filedialog.askopenfilename(title="Sélectionnez une image", filetypes=[("Images", "*.jpg;*.jpeg;*.png")])
        if path:
            var.set(path)

    def validate_model_action(self):
        try:
            self.controller.validate_model(self.model_name_var.get(), self.model_type_var.get())
            messagebox.showinfo("Validation", "Le modèle est validé. Vous pouvez ajouter des sets.")
            self.update_ui_state()
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def add_data_set_action(self):
        global DATA_LOADED
        if not self.controller.is_validated():
            messagebox.showerror("Erreur", "Validez le modèle avant d'ajouter des sets.")
            return
        if not DATA_LOADED:
            messagebox.showerror("Erreur", "Aucune donnée séchoir n'est disponible.")
            return

        set_name = self.set_name_var.get().strip()
        if not set_name:
            messagebox.showerror("Erreur", "Veuillez saisir un nom de set.")
            return

        set_product = self.set_product_type_var.get()
        model_type = self.model_type_var.get()
        if set_product != model_type:
            messagebox.showerror("Erreur", f"Le set est {set_product}, le modèle est {model_type}.")
            return

        img_conformes = [v.get().strip() for v in self.img_paths_conformes]
        img_non_conformes = [v.get().strip() for v in self.img_paths_non_conformes]

        if any(not p for p in img_conformes):
            messagebox.showerror("Erreur", f"Sélectionnez {NB_IMAGES_PER_SET} images conformes.")
            return
        if any(not p for p in img_non_conformes):
            messagebox.showerror("Erreur", f"Sélectionnez {NB_IMAGES_PER_SET} images non conformes.")
            return

        for p in img_conformes + img_non_conformes:
            if not os.path.exists(p):
                messagebox.showerror("Erreur", f"Image invalide: {p}")
                return

        use_augmentation = MODEL_PARAMS.get('use_augmentation', False)
        X, Y = extract_set_data(img_conformes, img_non_conformes, use_augmentation=use_augmentation)
        if X is None or Y is None:
            messagebox.showerror("Erreur", "Impossible d'extraire les données de ce set.")
            return

        self.sets_info.append([set_name, set_product, img_conformes, img_non_conformes])
        self.sets_tree.insert("", "end", values=(set_name, set_product, 6))
        messagebox.showinfo("Set ajouté", f"Set '{set_name}' ajouté avec succès !")

        self.set_name_var.set(f"set_{len(self.sets_info) + 1}")
        for v in self.img_paths_conformes:
            v.set("")
        for v in self.img_paths_non_conformes:
            v.set("")

    def open_param_window(self):
        if self.controller.is_validated():
            messagebox.showinfo("Info", "Le modèle est déjà validé, vous ne pouvez plus modifier les paramètres.")
            return
        ParamWindow(self, MODEL_PARAMS)

    def open_history_window(self):
        model_type = self.model_type_var.get()
        HistoryWindow(self, model_type)

    def load_validation_data_action(self):
        self.load_validation_data()

    def load_validation_data(self):
        file_path = filedialog.askopenfilename(title="Charger dataset de validation", filetypes=[("JSON", "*.json")])
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if not isinstance(data, list) or not data:
                    raise ValueError("Dataset de validation vide ou invalide.")
                self.validation_data = data
                messagebox.showinfo("Validation", f"Dataset de validation chargé ({len(self.validation_data)} entrées).")
                logger.info(f"Dataset de validation chargé depuis {file_path}")
            except Exception as e:
                messagebox.showerror("Erreur", f"Impossible de charger le dataset de validation:\n{e}")
                self.validation_data = None
        else:
            self.validation_data = None

    def load_sets_action(self):
        file_path = filedialog.askopenfilename(title="Charger sets (JSON)", filetypes=[("JSON", "*.json")])
        if not file_path:
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("JSON invalide (liste attendue).")
            for i in self.sets_tree.get_children():
                self.sets_tree.delete(i)
            self.sets_info = data
            for s in data:
                if len(s) == 4:
                    self.sets_tree.insert("", "end", values=(s[0], s[1], 6))
            messagebox.showinfo("Chargement", f"{len(data)} sets chargés.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de charger les sets:\n{e}")

    def export_sets_action(self):
        file_path = filedialog.asksaveasfilename(title="Exporter sets (JSON)", defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not file_path:
            return
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.sets_info, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("Exportation", f"{len(self.sets_info)} sets exportés.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'exporter les sets:\n{e}")

    def load_model_action(self):
        file_path = filedialog.askopenfilename(title="Charger un modèle", filetypes=[("Model Files", "*.h5")])
        if not file_path:
            return
        try:
            self.controller.load_model(file_path)
            self.update_ui_state()
            messagebox.showinfo("Chargement Modèle", f"Modèle chargé depuis {file_path}.")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def export_model_action(self):
        if not self.controller.is_validated():
            messagebox.showerror("Erreur", "Aucun modèle chargé ou validé.")
            return
        file_path = filedialog.asksaveasfilename(title="Exporter le modèle", defaultextension=".h5", filetypes=[("Model H5", "*.h5")])
        if not file_path:
            return
        try:
            self.controller.model.save(file_path)
            messagebox.showinfo("Exportation", f"Modèle exporté: {file_path}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'exporter le modèle:\n{e}")

    def show_model_summary(self):
        if not self.controller.is_validated():
            messagebox.showinfo("Résumé du Modèle", "Aucun modèle chargé ou créé.")
            return

        summary_str = []
        self.controller.model.summary(print_fn=lambda x: summary_str.append(x))
        summary_text = "\n".join(summary_str)
        win = tk.Toplevel(self)
        win.title("Résumé du Modèle")
        win.configure(bg=THEME['bg_main'])
        text = tk.Text(win, bg=THEME['text_bg'], fg='white', wrap='none')
        text.insert("1.0", summary_text)
        text.config(state='disabled')
        text.pack(fill='both', expand=True)

    def export_config(self):
        file_path = filedialog.asksaveasfilename(title="Exporter config (JSON)", defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not file_path:
            return
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(MODEL_PARAMS, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("Exportation", f"Configuration exportée: {file_path}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'exporter la configuration:\n{e}")

    def import_config(self):
        if self.controller.is_validated():
            messagebox.showinfo("Info", "Le modèle est déjà validé, vous ne pouvez plus modifier les paramètres.")
            return
        file_path = filedialog.askopenfilename(title="Importer config (JSON)", filetypes=[("JSON", "*.json")])
        if not file_path:
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("Format JSON invalide.")
            MODEL_PARAMS.update(data)
            messagebox.showinfo("Importation", f"Configuration importée depuis {file_path}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'importer la configuration:\n{e}")

    def new_model_action(self):
        self.model_name_var.set("mon_modele")
        self.model_type_var.set("Ail")
        self.controller.model = None
        self.controller.validated = False
        self.update_ui_state()
        for i in self.sets_tree.get_children():
            self.sets_tree.delete(i)
        self.sets_info.clear()
        messagebox.showinfo("Nouveau Modèle", "Configuration réinitialisée.")

    def add_production_data_action(self):
        set_product = self.set_product_type_var.get()
        img_conformes = [v.get().strip() for v in self.img_paths_conformes]
        img_non_conformes = [v.get().strip() for v in self.img_paths_non_conformes]

        if any(not p for p in img_conformes) or any(not p for p in img_non_conformes):
            messagebox.showerror("Erreur", f"Veuillez sélectionner {NB_IMAGES_PER_SET} images conformes et {NB_IMAGES_PER_SET} non conformes.")
            return

        four_data = None
        if not self.auto_collect_var.get():
            tapis_data = [{
                'vit_stockeur': self.manual_vit_stockeur_var.get(),
                'tapis1': self.manual_tapis1_var.get(),
                'tapis2': self.manual_tapis2_var.get(),
                'tapis3': self.manual_tapis3_var.get(),
            }]
            c_con = [cv.get() for cv in self.manual_con_cels_var]
            cons_data = [{'cels': c_con, 'air_neuf': self.manual_con_air_var.get()}]
            c_re = [rv.get() for rv in self.manual_re_cels_var]
            re_data = [{'cels': c_re, 'air_neuf': self.manual_re_air_var.get()}]

            four_data = {
                'produit': {'type_produit': set_product, 'humide': "Non", 'observations': ""},
                'tapis': tapis_data,
                'temperatures_consignes': cons_data,
                'temperatures_reelles': re_data
            }

        use_augmentation = MODEL_PARAMS.get('use_augmentation', False)
        X, Y = extract_set_data(img_conformes, img_non_conformes, four_data=four_data, use_augmentation=use_augmentation)
        if X is None or Y is None:
            messagebox.showerror("Erreur", "Impossible d'extraire les données de production.")
            return

        self.production_data_sets.append((X, Y))
        messagebox.showinfo("Production", "Données de production ajoutées.")

        for v in self.img_paths_conformes:
            v.set("")
        for v in self.img_paths_non_conformes:
            v.set("")

    def update_model_with_production_data_action(self):
        if not self.controller.is_validated():
            messagebox.showerror("Erreur", "Aucun modèle chargé/validé pour mise à jour.")
            return
        try:
            self.controller.update_with_production(self.production_data_sets)
            self.production_data_sets.clear()
            messagebox.showinfo("Mise à jour", "Modèle mis à jour avec les données de production.")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def start_training_thread(self):
        t = threading.Thread(target=self.train_model_action)
        t.start()

    def train_model_action(self):
        if not self.sets_info:
            messagebox.showerror("Erreur", "Aucun set ajouté pour l'entraînement.")
            return
        product_type = self.train_product_type_var.get()
        if not self.controller.is_validated():
            messagebox.showerror("Erreur", "Modèle non validé.")
            return
        try:
            messagebox.showinfo("Entraînement", "Entraînement du modèle en cours, veuillez patienter...")
            model_name = self.controller.train_model(self.sets_info, product_type)
            messagebox.showinfo("Succès", f"Modèle '{model_name}' entraîné et sauvegardé.")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def start_cross_validation_thread(self):
        t = threading.Thread(target=self.cross_validate_action)
        t.start()

    def cross_validate_action(self):
        if not self.sets_info:
            messagebox.showerror("Erreur", "Aucun set ajouté pour la validation croisée.")
            return
        product_type = self.train_product_type_var.get()
        try:
            messagebox.showinfo("Validation Croisée", "Validation croisée en cours, veuillez patienter...")
            mse_mean, mae_mean, r2_mean = self.controller.cross_validate(self.sets_info, product_type)
            msg = f"Validation Croisée (5-fold):\nMSE moyen: {mse_mean:.2f}\nMAE moyen: {mae_mean:.2f}\nR² moyen: {r2_mean:.2f}"
            messagebox.showinfo("Validation Croisée", msg)
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def evaluate_model_action(self):
        if not self.validation_data:
            messagebox.showerror("Erreur", "Pas de données de validation chargées.")
            return
        model_type = self.model_type_var.get()
        try:
            mse, mae, r2 = self.controller.evaluate(self.validation_data, model_type)
            msg = f"Métriques Validation:\nMSE: {mse:.2f}\nMAE: {mae:.2f}\nR²: {r2:.2f}"
            messagebox.showinfo("Évaluation du modèle", msg)
        except Exception as e:
            messagebox.showerror("Erreur", str(e))


def get_frame(parent, main_app):
    return TrainIAModuleFrame(parent, main_app)

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Application IA - Séchoir (Dense et CNN+Dense) - Adaptation Continue (Final)")
    frame = get_frame(root, None)
    frame.pack(fill='both', expand=True)
    root.mainloop()
