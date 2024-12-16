# model_utils.py
# ===========================================================================================
# 👉 Ce module gère la construction, la configuration, la sauvegarde et l'historique des modèles IA.
# 👉 Il offre aussi une interface (ParamWindow, HistoryWindow) permettant d'ajuster les
#    paramètres du modèle (MODEL_PARAMS) et de visualiser l'historique des modèles entraînés.
# ===========================================================================================

import os
import json
import logging
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, regularizers

from data_utils import MODELS_DIR, THEME, NB_IMAGES_PER_SET

# ===========================================================================================
# 👉 Paramètres du modèle :
# Vous pouvez ajuster ici les paramètres par défaut. L'interface vous permet de les modifier dynamiquement.
# Ajoutez ou modifiez des champs si vous voulez plus de flexibilité (ex: nombre de couches CNN supplémentaires).
# ===========================================================================================
MODEL_PARAMS = {
    "model_label": "Réseau de Neurones",
    "n_epochs": 10,
    "batch_size": 32,
    "hidden_units": 64,
    "architecture": "Dense",
    "hidden_layers": "64,64",
    "activation": "relu",
    "optimizer": "adam",
    "learning_rate": 0.001,
    "loss": "mean_squared_error",
    "metrics": "mae,mean_squared_error",
    "weight_init": "glorot_uniform",
    "use_dropout": False,
    "dropout_rate": 0.0,
    "l2_reg": 0.0,
    "cnn_filters": "32,64",
    "cnn_kernel_size": "3,3",
    "cnn_pool_size": "2,2",
    "fine_tuning": False,
    "fine_tuning_layers": 0,
    # Paramètres avancés (ex : plus de couches CNN, BatchNormalization)
    "cnn_additional_layers": 0,  # Permet d'ajouter plus de couches CNN identiques
    "use_batch_norm": False,     # Si True, ajoute un BatchNormalization après certaines couches
}

logger = logging.getLogger("train_ia_model")

def create_optimizer(params):
    """
    Crée un optimiseur Keras en fonction des paramètres spécifiés.
    """
    opt_name = params.get('optimizer','adam').lower()
    lr = params.get('learning_rate',0.001)
    if opt_name == 'adam':
        return tf.keras.optimizers.Adam(learning_rate=lr)
    elif opt_name == 'sgd':
        return tf.keras.optimizers.SGD(learning_rate=lr)
    elif opt_name == 'rmsprop':
        return tf.keras.optimizers.RMSprop(learning_rate=lr)
    else:
        logger.warning(f"Optimiseur inconnu : {opt_name}, utilisation d'Adam par défaut.")
        return tf.keras.optimizers.Adam(learning_rate=lr)

def save_model(model, model_name):
    """
    Sauvegarde le modèle au format H5 dans le répertoire MODELS_DIR.
    """
    if not os.path.exists(MODELS_DIR):
        os.makedirs(MODELS_DIR)
    model_file = os.path.join(MODELS_DIR, f"model_{model_name}.h5")
    try:
        model.save(model_file)
        logger.info(f"Modèle sauvegardé : {model_file}")
    except Exception as e:
        logger.error(f"Erreur sauvegarde modèle : {e}", exc_info=True)

def build_dense_model(input_dim, output_dim, params):
    """
    Construit un modèle Dense (MLP) selon les paramètres.
    """
    activation = params.get('activation','relu')
    hidden_layers = params.get('hidden_layers','64,64')
    layers_units = [int(u) for u in hidden_layers.split(',') if u.strip().isdigit()]

    weight_init = params.get('weight_init','glorot_uniform')
    l2_reg = params.get('l2_reg',0.0)
    use_dropout = params.get('use_dropout',False)
    dropout_rate = params.get('dropout_rate',0.0)
    use_batch_norm = params.get('use_batch_norm', False)

    metrics_list = [m.strip() for m in params.get('metrics','mae,mean_squared_error').split(',')]
    reg = regularizers.l2(l2_reg) if l2_reg > 0 else None

    inputs = keras.Input(shape=(input_dim,))
    x = inputs
    for units in layers_units:
        x = layers.Dense(units, activation=activation, kernel_initializer=weight_init, kernel_regularizer=reg)(x)
        if use_batch_norm:
            x = layers.BatchNormalization()(x)
        if use_dropout and dropout_rate > 0:
            x = layers.Dropout(dropout_rate)(x)

    outputs = layers.Dense(output_dim, kernel_initializer=weight_init)(x)

    optimizer = create_optimizer(params)
    model = keras.Model(inputs=inputs, outputs=outputs)
    model.compile(optimizer=optimizer,
                  loss=params.get('loss','mean_squared_error'),
                  metrics=metrics_list)
    return model

def build_cnn_dense_model(image_shape, numeric_dim, output_dim, params):
    """
    Construit un modèle CNN+Dense combinant des couches convolutionnelles pour les images
    et des couches denses pour les features numériques.
    Permet d'ajouter plus de couches CNN (cnn_additional_layers) ou du batch normalization.
    """
    cnn_filters = params.get("cnn_filters", "32,64")
    cnn_filters = [int(x) for x in cnn_filters.split(',') if x.strip().isdigit()]
    if not cnn_filters:
        # Valeur par défaut si parsing échoue
        cnn_filters = [32,64]

    cnn_kernel = params.get("cnn_kernel_size","3,3")
    kernel_sizes = [int(x) for x in cnn_kernel.split(',') if x.strip().isdigit()]
    if len(kernel_sizes)<2:
        kernel_sizes = [3,3]

    cnn_pool = params.get("cnn_pool_size","2,2")
    pool_sizes = [int(x) for x in cnn_pool.split(',') if x.strip().isdigit()]
    if len(pool_sizes)<2:
        pool_sizes = [2,2]

    activation = params.get('activation','relu')
    hidden_layers = params.get('hidden_layers','64,64')
    layers_units = [int(u) for u in hidden_layers.split(',') if u.strip().isdigit()]

    weight_init = params.get('weight_init','glorot_uniform')
    l2_reg = params.get('l2_reg',0.0)
    use_dropout = params.get('use_dropout',False)
    dropout_rate = params.get('dropout_rate',0.0)
    use_batch_norm = params.get('use_batch_norm', False)

    cnn_additional_layers = params.get('cnn_additional_layers', 0)  # couches CNN supplémentaires à ajouter

    metrics_list = [m.strip() for m in params.get('metrics','mae,mean_squared_error').split(',')]
    reg = regularizers.l2(l2_reg) if l2_reg > 0 else None

    # Entrée image
    image_input = keras.Input(shape=image_shape, name='image_input')
    x = image_input
    # Convolution initiale
    for f in cnn_filters:
        x = layers.Conv2D(f, (kernel_sizes[0], kernel_sizes[1]), activation=activation, padding='same',
                          kernel_initializer=weight_init, kernel_regularizer=reg)(x)
        if use_batch_norm:
            x = layers.BatchNormalization()(x)
        x = layers.MaxPooling2D((pool_sizes[0], pool_sizes[1]))(x)

    # Ajout de couches CNN supplémentaires si demandé
    for _ in range(cnn_additional_layers):
        # On réutilise les mêmes filtres, kernel, etc. ou vous pourriez paramétrer plus finement
        for f in cnn_filters:
            x = layers.Conv2D(f, (kernel_sizes[0], kernel_sizes[1]), activation=activation, padding='same',
                              kernel_initializer=weight_init, kernel_regularizer=reg)(x)
            if use_batch_norm:
                x = layers.BatchNormalization()(x)
            x = layers.MaxPooling2D((pool_sizes[0], pool_sizes[1]))(x)

    x = layers.Flatten()(x)
    x = layers.Dense(64, activation=activation, kernel_initializer=weight_init, kernel_regularizer=reg)(x)
    if use_batch_norm:
        x = layers.BatchNormalization()(x)
    if use_dropout and dropout_rate > 0:
        x = layers.Dropout(dropout_rate)(x)

    # Entrée numérique
    numeric_input = keras.Input(shape=(numeric_dim,), name='numeric_input')
    y = layers.Dense(64, activation=activation, kernel_initializer=weight_init, kernel_regularizer=reg)(numeric_input)
    if use_batch_norm:
        y = layers.BatchNormalization()(y)
    if use_dropout and dropout_rate > 0:
        y = layers.Dropout(dropout_rate)(y)

    # Fusion des deux entrées (images & numérique)
    concat = layers.Concatenate()([x, y])

    # Ajout de couches denses finales
    for units in layers_units:
        concat = layers.Dense(units, activation=activation, kernel_initializer=weight_init, kernel_regularizer=reg)(concat)
        if use_batch_norm:
            concat = layers.BatchNormalization()(concat)
        if use_dropout and dropout_rate > 0:
            concat = layers.Dropout(dropout_rate)(concat)

    # Couche de sortie
    output = layers.Dense(output_dim, kernel_initializer=weight_init)(concat)

    # Compilation du modèle
    optimizer = create_optimizer(params)
    model = keras.Model(inputs=[image_input, numeric_input], outputs=output)
    model.compile(optimizer=optimizer,
                  loss=params.get('loss','mean_squared_error'),
                  metrics=metrics_list)
    return model

def build_model_from_params(image_shape, numeric_dim, output_dim, params):
    """
    Construit un modèle Dense ou CNN+Dense selon le paramètre 'architecture'.
    """
    arch = params.get('architecture','Dense')
    if arch == 'Dense':
        input_dim = numeric_dim
        return build_dense_model(input_dim, output_dim, params)
    elif arch == 'CNN+Dense':
        return build_cnn_dense_model(image_shape, numeric_dim, output_dim, params)
    else:
        logger.warning(f"Architecture inconnue: {arch}, utilisation CNN+Dense par défaut.")
        return build_cnn_dense_model(image_shape, numeric_dim, output_dim, params)


class ParamWindow(tk.Toplevel):
    """
    Fenêtre ParamWindow :
    Permet de voir et modifier les hyperparamètres du modèle.
    """
    def __init__(self, parent, params):
        super().__init__(parent)
        self.title("Paramètres du Modèle")
        self.configure(bg=THEME['bg_main'])
        self.params = params

        def add_label_entry(row, text, var_name, default):
            tk.Label(self, text=text, fg='white', bg=THEME['bg_main']).grid(row=row, column=0, sticky='e', padx=5, pady=5)
            e = tk.Entry(self, bg=THEME['text_bg'], fg='white')
            e.grid(row=row, column=1, padx=5, pady=5)
            e.insert(0, str(self.params.get(var_name, default)))
            return e

        self.epochs_entry = add_label_entry(0, "Nombre d'époques (n_epochs) :", "n_epochs", 10)
        self.batch_entry = add_label_entry(1, "Taille de batch (batch_size) :", "batch_size", 32)

        tk.Label(self, text="Architecture :", fg='white', bg=THEME['bg_main']).grid(row=2, column=0, sticky='e', padx=5, pady=5)
        self.arch_combo = ttk.Combobox(self, values=["Dense","CNN+Dense"], state="readonly")
        self.arch_combo.grid(row=2, column=1, padx=5, pady=5)
        current_arch = self.params.get('architecture', 'Dense')
        if current_arch not in ["Dense","CNN+Dense"]:
            current_arch = "Dense"
        self.arch_combo.set(current_arch)

        self.hidden_layers_entry = add_label_entry(3, "Couches cachées (ex: 64,64) :", "hidden_layers", "64,64")

        tk.Label(self, text="Activation :", fg='white', bg=THEME['bg_main']).grid(row=4, column=0, sticky='e', padx=5, pady=5)
        self.activation_combo = ttk.Combobox(self, values=["relu","sigmoid","tanh","linear"], state="readonly")
        self.activation_combo.grid(row=4, column=1, padx=5, pady=5)
        self.activation_combo.set(self.params.get('activation', 'relu'))

        tk.Label(self, text="Optimiseur :", fg='white', bg=THEME['bg_main']).grid(row=5, column=0, sticky='e', padx=5, pady=5)
        self.optimizer_combo = ttk.Combobox(self, values=["adam","sgd","rmsprop"], state="readonly")
        self.optimizer_combo.grid(row=5, column=1, padx=5, pady=5)
        self.optimizer_combo.set(self.params.get('optimizer', 'adam'))

        self.lr_entry = add_label_entry(6, "Learning rate :", "learning_rate", 0.001)

        tk.Label(self, text="Loss :", fg='white', bg=THEME['bg_main']).grid(row=7, column=0, sticky='e', padx=5, pady=5)
        self.loss_combo = ttk.Combobox(self, values=["mean_squared_error","mae","huber"], state="readonly")
        self.loss_combo.grid(row=7, column=1, padx=5, pady=5)
        self.loss_combo.set(self.params.get('loss','mean_squared_error'))

        self.metrics_entry = add_label_entry(8, "Metrics (séparées par ','):", "metrics", "mae,mean_squared_error")

        tk.Label(self, text="Initialisation poids :", fg='white', bg=THEME['bg_main']).grid(row=9, column=0, sticky='e', padx=5, pady=5)
        self.init_combo = ttk.Combobox(self, values=["glorot_uniform","he_normal","he_uniform","random_normal"], state="readonly")
        self.init_combo.grid(row=9, column=1, padx=5, pady=5)
        self.init_combo.set(self.params.get('weight_init','glorot_uniform'))

        tk.Label(self, text="Utiliser Dropout :", fg='white', bg=THEME['bg_main']).grid(row=10, column=0, sticky='e', padx=5, pady=5)
        self.dropout_var = tk.BooleanVar(value=self.params.get('use_dropout', False))
        tk.Checkbutton(self, variable=self.dropout_var, bg=THEME['bg_main'], fg='white', selectcolor=THEME['highlight']).grid(row=10, column=1, sticky='w', padx=5, pady=5)

        self.dropout_entry = add_label_entry(11, "Dropout rate :", "dropout_rate", 0.0)
        self.l2_entry = add_label_entry(12, "L2 régularisation :", "l2_reg", 0.0)

        # Frame CNN
        cnn_frame = tk.LabelFrame(self, text="Paramètres CNN (si CNN+Dense)", bg=THEME['bg_section'], fg='white', font=("Helvetica", 14, "bold"))
        cnn_frame.grid(row=13, column=0, columnspan=2, padx=5, pady=5, sticky='ew')

        tk.Label(cnn_frame, text="Filters (ex: 32,64):", bg=THEME['bg_section'], fg='white').grid(row=0, column=0, sticky='e', padx=5, pady=5)
        self.cnn_filters_entry = tk.Entry(cnn_frame, bg=THEME['text_bg'], fg='white')
        self.cnn_filters_entry.grid(row=0, column=1, padx=5, pady=5)
        self.cnn_filters_entry.insert(0, self.params.get('cnn_filters','32,64'))

        tk.Label(cnn_frame, text="Kernel size (ex: 3,3):", bg=THEME['bg_section'], fg='white').grid(row=1, column=0, sticky='e', padx=5, pady=5)
        self.cnn_kernel_entry = tk.Entry(cnn_frame, bg=THEME['text_bg'], fg='white')
        self.cnn_kernel_entry.grid(row=1, column=1, padx=5, pady=5)
        self.cnn_kernel_entry.insert(0, self.params.get('cnn_kernel_size','3,3'))

        tk.Label(cnn_frame, text="Pool size (ex: 2,2):", bg=THEME['bg_section'], fg='white').grid(row=2, column=0, sticky='e', padx=5, pady=5)
        self.cnn_pool_entry = tk.Entry(cnn_frame, bg=THEME['text_bg'], fg='white')
        self.cnn_pool_entry.grid(row=2, column=1, padx=5, pady=5)
        self.cnn_pool_entry.insert(0, self.params.get('cnn_pool_size','2,2'))

        # Couches CNN supplémentaires
        self.cnn_additional_entry = add_label_entry(14, "Couches CNN supplémentaires :", "cnn_additional_layers", 0)

        tk.Label(self, text="Fine-Tuning (réentrainement partiel) :", fg='white', bg=THEME['bg_main']).grid(row=15, column=0, sticky='e', padx=5, pady=5)
        self.finetune_var = tk.BooleanVar(value=self.params.get('fine_tuning',False))
        tk.Checkbutton(self, variable=self.finetune_var, bg=THEME['bg_main'], fg='white', selectcolor=THEME['highlight']).grid(row=15, column=1, sticky='w', padx=5, pady=5)

        self.finetune_layers_entry = add_label_entry(16, "Fine-Tuning Layers :", "fine_tuning_layers", 0)

        # Batch Norm optionnelle
        tk.Label(self, text="Utiliser Batch Normalization :", fg='white', bg=THEME['bg_main']).grid(row=17, column=0, sticky='e', padx=5, pady=5)
        self.batchnorm_var = tk.BooleanVar(value=self.params.get('use_batch_norm', False))
        tk.Checkbutton(self, variable=self.batchnorm_var, bg=THEME['bg_main'], fg='white', selectcolor=THEME['highlight']).grid(row=17, column=1, sticky='w', padx=5, pady=5)

        tk.Button(self, text="Exporter Config", bg=THEME['button_bg'], fg='white', command=self.export_config).grid(row=18, column=0, padx=5, pady=5)
        tk.Button(self, text="Importer Config", bg=THEME['button_bg'], fg='white', command=self.import_config).grid(row=18, column=1, padx=5, pady=5)

        tk.Button(self, text="Appliquer", bg=THEME['button_bg'], fg='white', command=self.apply_all_params).grid(row=19, column=0, columnspan=2, pady=10)

    def apply_all_params(self):
        """
        Applique les paramètres saisis par l'utilisateur, les valide, et met à jour MODEL_PARAMS.
        """
        global MODEL_PARAMS
        try:
            n_epochs = int(self.epochs_entry.get().strip())
            batch_size = int(self.batch_entry.get().strip())
            hidden_layers = self.hidden_layers_entry.get().strip()
            if not hidden_layers:
                hidden_layers = "64"
            activation = self.activation_combo.get()
            optimizer = self.optimizer_combo.get()
            learning_rate = float(self.lr_entry.get().strip())
            loss = self.loss_combo.get()
            metrics = self.metrics_entry.get().strip()
            weight_init = self.init_combo.get()
            use_dropout = self.dropout_var.get()
            dropout_rate = float(self.dropout_entry.get().strip())
            l2_reg = float(self.l2_entry.get().strip())
            arch = self.arch_combo.get()

            cnn_filters = self.cnn_filters_entry.get().strip()
            cnn_kernel_size = self.cnn_kernel_entry.get().strip()
            cnn_pool_size = self.cnn_pool_entry.get().strip()
            cnn_additional_layers = int(self.cnn_additional_entry.get().strip())

            fine_tuning = self.finetune_var.get()
            fine_tuning_layers = int(self.finetune_layers_entry.get().strip())
            use_batch_norm = self.batchnorm_var.get()

            # Vérifications de base
            if n_epochs <= 0:
                raise ValueError("n_epochs doit être > 0")
            if batch_size <= 0:
                raise ValueError("batch_size doit être > 0")
            if dropout_rate < 0.0 or dropout_rate > 1.0:
                raise ValueError("dropout_rate doit être entre 0.0 et 1.0")
            if l2_reg < 0.0:
                raise ValueError("l2_reg ne peut pas être négatif")
            if not metrics:
                raise ValueError("Vous devez spécifier au moins une métrique")

            MODEL_PARAMS['n_epochs'] = n_epochs
            MODEL_PARAMS['batch_size'] = batch_size
            MODEL_PARAMS['hidden_layers'] = hidden_layers
            MODEL_PARAMS['activation'] = activation
            MODEL_PARAMS['optimizer'] = optimizer
            MODEL_PARAMS['learning_rate'] = learning_rate
            MODEL_PARAMS['loss'] = loss
            MODEL_PARAMS['metrics'] = metrics
            MODEL_PARAMS['weight_init'] = weight_init
            MODEL_PARAMS['use_dropout'] = use_dropout
            MODEL_PARAMS['dropout_rate'] = dropout_rate
            MODEL_PARAMS['l2_reg'] = l2_reg
            MODEL_PARAMS['architecture'] = arch
            MODEL_PARAMS['cnn_filters'] = cnn_filters
            MODEL_PARAMS['cnn_kernel_size'] = cnn_kernel_size
            MODEL_PARAMS['cnn_pool_size'] = cnn_pool_size
            MODEL_PARAMS['fine_tuning'] = fine_tuning
            MODEL_PARAMS['fine_tuning_layers'] = fine_tuning_layers
            MODEL_PARAMS['cnn_additional_layers'] = cnn_additional_layers
            MODEL_PARAMS['use_batch_norm'] = use_batch_norm

            messagebox.showinfo("Paramètres", "Paramètres appliqués avec succès.")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'appliquer les paramètres.\n{e}")

    def export_config(self):
        global MODEL_PARAMS
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
        global MODEL_PARAMS
        file_path = filedialog.askopenfilename(title="Importer config (JSON)", filetypes=[("JSON", "*.json")])
        if not file_path:
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("Format JSON invalide.")
            MODEL_PARAMS.update(data)
            # Recharge les champs avec les nouvelles valeurs
            self.epochs_entry.delete(0, tk.END)
            self.epochs_entry.insert(0, str(MODEL_PARAMS.get('n_epochs',10)))
            self.batch_entry.delete(0, tk.END)
            self.batch_entry.insert(0, str(MODEL_PARAMS.get('batch_size',32)))
            self.hidden_layers_entry.delete(0, tk.END)
            self.hidden_layers_entry.insert(0, MODEL_PARAMS.get('hidden_layers','64,64'))
            arch = MODEL_PARAMS.get('architecture','Dense')
            if arch not in ["Dense","CNN+Dense"]:
                arch = "Dense"
            self.arch_combo.set(arch)
            self.activation_combo.set(MODEL_PARAMS.get('activation','relu'))
            self.optimizer_combo.set(MODEL_PARAMS.get('optimizer','adam'))
            self.lr_entry.delete(0, tk.END)
            self.lr_entry.insert(0, str(MODEL_PARAMS.get('learning_rate',0.001)))
            self.loss_combo.set(MODEL_PARAMS.get('loss','mean_squared_error'))
            self.metrics_entry.delete(0, tk.END)
            self.metrics_entry.insert(0, MODEL_PARAMS.get('metrics','mae,mean_squared_error'))
            self.init_combo.set(MODEL_PARAMS.get('weight_init','glorot_uniform'))
            self.dropout_var.set(MODEL_PARAMS.get('use_dropout',False))
            self.dropout_entry.delete(0, tk.END)
            self.dropout_entry.insert(0, str(MODEL_PARAMS.get('dropout_rate',0.0)))
            self.l2_entry.delete(0, tk.END)
            self.l2_entry.insert(0, str(MODEL_PARAMS.get('l2_reg',0.0)))
            self.cnn_filters_entry.delete(0, tk.END)
            self.cnn_filters_entry.insert(0, MODEL_PARAMS.get('cnn_filters','32,64'))
            self.cnn_kernel_entry.delete(0, tk.END)
            self.cnn_kernel_entry.insert(0, MODEL_PARAMS.get('cnn_kernel_size','3,3'))
            self.cnn_pool_entry.delete(0, tk.END)
            self.cnn_pool_entry.insert(0, MODEL_PARAMS.get('cnn_pool_size','2,2'))
            self.cnn_additional_entry.delete(0, tk.END)
            self.cnn_additional_entry.insert(0, str(MODEL_PARAMS.get('cnn_additional_layers',0)))
            self.finetune_var.set(MODEL_PARAMS.get('fine_tuning',False))
            self.finetune_layers_entry.delete(0, tk.END)
            self.finetune_layers_entry.insert(0, str(MODEL_PARAMS.get('fine_tuning_layers',0)))
            self.batchnorm_var.set(MODEL_PARAMS.get('use_batch_norm',False))
            messagebox.showinfo("Importation", f"Configuration importée depuis {file_path}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'importer la configuration:\n{e}")

class HistoryWindow(tk.Toplevel):
    """
    Fenêtre HistoryWindow :
    Permet de voir l'historique des modèles entraînés pour un type de produit donné.
    """
    def __init__(self, parent, model_type):
        super().__init__(parent)
        self.title("Historique du modèle")
        self.configure(bg=THEME['bg_main'])

        from data_utils import MODELS_DIR
        if not os.path.exists(MODELS_DIR):
            tk.Label(self, text="Aucun modèle trouvé (répertoire manquant).", bg=THEME['bg_main'], fg='white').pack(padx=10, pady=10)
            return
        files = [f for f in os.listdir(MODELS_DIR) if f.startswith(f"model_{model_type}_") and f.endswith('.h5')]
        if not files:
            tk.Label(self, text="Aucun modèle trouvé pour ce type.", bg=THEME['bg_main'], fg='white').pack(padx=10, pady=10)
            return
        files.sort(key=lambda x: os.path.getmtime(os.path.join(MODELS_DIR, x)), reverse=True)
        self.combo = ttk.Combobox(self, values=files, state="readonly")
        self.combo.pack(padx=10, pady=10)
        if files:
            self.combo.current(0)
        tk.Button(self, text="OK", bg=THEME['button_bg'], fg='white', command=self.select_model).pack(pady=5)

    def select_model(self):
        sel = self.combo.get()
        if sel:
            messagebox.showinfo("Historique", f"Modèle sélectionné: {sel}")
            self.destroy()
