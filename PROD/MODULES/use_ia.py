import os
import json
import logging
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image

import tensorflow as tf
from tensorflow import keras
from sklearn.metrics import mean_squared_error

THEME = {
    'bg_main': '#2B2B2B',
    'bg_section': '#2B2B2B',
    'fg_text': 'white',
    'highlight': '#6e6e6e',
    'button_bg': '#6e6e6e',
    'button_fg': 'white',
    'accent': '#FFA500',
    'accent2': '#007ACC',
    'title_font': ("Helvetica", 14, "bold"),
    'label_font': ("Helvetica", 10),
    'entry_font': ("Helvetica", 10),
    'text_bg': '#3C3F41'
}

DATA_DIR = "DATA"
MODELS_DIR = "MODELS"
if not os.path.exists(MODELS_DIR):
    os.makedirs(MODELS_DIR)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger("use_ia")

IMAGE_SIZE = (32, 32)
NB_IMAGES_PER_SET = 3  # 3 images conformes + 3 non conformes = 6 images total
OUTPUT_DIM = 11

def create_thematic_frame(parent, title=None, theme=THEME):
    if title:
        frame = tk.LabelFrame(parent, text=title, bg=theme['bg_section'], fg='white', font=theme['title_font'])
    else:
        frame = tk.Frame(parent, bg=theme['bg_section'])
    return frame

def get_sechoir_data_file():
    main_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    data_file = os.path.join(main_dir, 'sechoir_data.json')
    if not os.path.exists(data_file):
        alt_file = os.path.join(os.getcwd(), 'sechoir_data.json')
        if os.path.exists(alt_file):
            data_file = alt_file
        else:
            messagebox.showwarning("Fichier non trouvé", "Le fichier sechoir_data.json est introuvable.\nVeuillez le sélectionner manuellement.")
            chosen = filedialog.askopenfilename(title="Sélectionnez sechoir_data.json", filetypes=[("JSON", "*.json")])
            if chosen and os.path.exists(chosen):
                data_file = chosen
            else:
                data_file = None
    return data_file

def load_sechoir_data():
    data_file = get_sechoir_data_file()
    if data_file is None or not os.path.exists(data_file):
        logger.warning("Fichier sechoir_data.json non trouvé.")
        return []
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not isinstance(data, list):
                logger.error("Format invalide de sechoir_data.json.")
                return []
            return data
    except Exception as e:
        logger.error(f"Erreur chargement sechoir_data.json: {e}")
        return []

def load_model_from_file(path):
    if not os.path.exists(path):
        return None
    try:
        model = keras.models.load_model(path)
        return model
    except Exception as e:
        logger.error(f"Erreur chargement modèle {path}: {e}")
        return None

def safe_float(x):
    try:
        return float(x)
    except:
        return 0.0

def get_last_valid_temp_entry(temp_list):
    for t in reversed(temp_list):
        cels = t.get('cels', [])
        if len(cels) == 6 and 'air_neuf' in t:
            return t
    return None

def load_and_concat_images(img_list_conformes, img_list_non_conformes, size=IMAGE_SIZE):
    all_paths = img_list_conformes + img_list_non_conformes
    imgs = []
    for p in all_paths:
        if not p or not os.path.exists(p):
            logger.error(f"Image invalide: {p}")
            return None
        img = Image.open(p).convert("RGB")
        img = img.resize(size)
        arr = np.array(img, dtype=np.float32)/255.0
        imgs.append(arr)
    final_img = np.concatenate(imgs, axis=1)
    return final_img

class UseIAModuleFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=THEME['bg_main'])
        self.loaded_model = None
        self.sechoir_data = load_sechoir_data()
        self.predict_result_var = tk.StringVar()

        self.img_paths_conformes = [tk.StringVar() for _ in range(NB_IMAGES_PER_SET)]
        self.img_paths_non_conformes = [tk.StringVar() for _ in range(NB_IMAGES_PER_SET)]

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(self, bg=THEME['bg_main'], highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=THEME['bg_section'])

        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.grid(row=0, column=0, sticky='nsew')
        self.scrollbar.grid(row=0, column=1, sticky='ns')

        self.setup_data_display_section()
        self.setup_use_model_section()
        self.setup_image_selection_section()
        self.setup_log_section()

        self.refresh_data_display()

    def setup_data_display_section(self):
        frame = create_thematic_frame(self.scrollable_frame, "Données du Séchoir")
        frame.pack(padx=10, pady=10, fill='x')

        tk.Label(frame, text="Ci-dessous, un aperçu des dernières données du séchoir (vitesses des tapis, températures) :",
                 bg=THEME['bg_section'], fg='white').pack(padx=5, pady=5)

        tk.Label(frame, text="Dernières vitesses Tapis :", bg=THEME['bg_section'], fg='white').pack(pady=5)
        self.tapis_tree = ttk.Treeview(frame, columns=("heure", "vit_stockeur", "tapis1", "tapis2", "tapis3"), show='headings', height=3)
        self.tapis_tree.pack(fill='x', padx=5, pady=5)
        self.tapis_tree.heading("heure", text="Heure")
        self.tapis_tree.heading("vit_stockeur", text="Vit. Stockeur (Hz)")
        self.tapis_tree.heading("tapis1", text="Tapis1 (Hz)")
        self.tapis_tree.heading("tapis2", text="Tapis2 (Hz)")
        self.tapis_tree.heading("tapis3", text="Tapis3 (Hz)")
        for col in ("heure", "vit_stockeur", "tapis1", "tapis2", "tapis3"):
            self.tapis_tree.column(col, width=100)

        tk.Label(frame, text="Dernières Températures (Consigne / Réelle) :", bg=THEME['bg_section'], fg='white').pack(pady=5)
        cols = ["heure", "CEL1 (C/R)", "CEL2 (C/R)", "CEL3 (C/R)", "CEL4 (C/R)", "CEL5/6 (C/R)", "CEL7/8 (C/R)", "AirNeuf (C/R)"]
        self.temp_tree = ttk.Treeview(frame, columns=cols, show='headings', height=3)
        self.temp_tree.pack(fill='x', padx=5, pady=5)
        for c in cols:
            self.temp_tree.heading(c, text=c)
            self.temp_tree.column(c, width=100)

    def setup_use_model_section(self):
        frame = create_thematic_frame(self.scrollable_frame, "Utilisation du Modèle")
        frame.pack(padx=10, pady=10, fill='x')

        tk.Label(frame, text="Pour utiliser le modèle, commencez par charger un modèle existant :", bg=THEME['bg_section'], fg='white').pack(padx=5, pady=5)

        btn_frame = tk.Frame(frame, bg=THEME['bg_section'])
        btn_frame.pack(pady=5)

        tk.Button(btn_frame, text="Charger un modèle", bg=THEME['button_bg'], fg='white', command=self.load_model).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Prédire sur la dernière entrée", bg=THEME['accent'], fg='white', command=self.predict_on_last_entry).pack(side='left', padx=5)

        tk.Label(frame, text="Résultat de la prédiction :", bg=THEME['bg_section'], fg='white').pack(padx=5, pady=5, fill='x')
        tk.Label(frame, textvariable=self.predict_result_var, bg=THEME['bg_section'], fg='white', wraplength=500, justify='left').pack(pady=5, fill='x')

    def setup_image_selection_section(self):
        frame = create_thematic_frame(self.scrollable_frame, "Sélection des Images pour la Prédiction")
        frame.pack(padx=10, pady=10, fill='x')

        tk.Label(frame, text="Sélectionnez ci-dessous :", bg=THEME['bg_section'], fg='white').pack(padx=5, pady=5, anchor='w')

        # Images CONFORMES
        tk.Label(frame, text=f"{NB_IMAGES_PER_SET} images CONFORMES (Aspect idéal du produit) :", bg=THEME['bg_section'], fg='white').pack(anchor='w', padx=5, pady=5)
        conformes_btn_frame = tk.Frame(frame, bg=THEME['bg_section'])
        conformes_btn_frame.pack(padx=5, pady=5)
        for i in range(NB_IMAGES_PER_SET):
            tk.Button(conformes_btn_frame, text=f"Image Conforme {i+1}", bg=THEME['button_bg'], fg='white', command=lambda idx=i: self.browse_image(self.img_paths_conformes[idx])).pack(side='left', padx=5)

        conformes_entry_frame = tk.Frame(frame, bg=THEME['bg_section'])
        conformes_entry_frame.pack(padx=5, pady=5)
        for i in range(NB_IMAGES_PER_SET):
            tk.Entry(conformes_entry_frame, textvariable=self.img_paths_conformes[i], width=50, bg=THEME['text_bg'], fg='white').pack(side='left', padx=5)

        # Images NON CONFORMES
        tk.Label(frame, text=f"{NB_IMAGES_PER_SET} images NON CONFORMES (Aspect actuel du produit) :", bg=THEME['bg_section'], fg='white').pack(anchor='w', padx=5, pady=5)
        non_conformes_btn_frame = tk.Frame(frame, bg=THEME['bg_section'])
        non_conformes_btn_frame.pack(padx=5, pady=5)
        for i in range(NB_IMAGES_PER_SET):
            tk.Button(non_conformes_btn_frame, text=f"Image NON Conforme {i+1}", bg=THEME['button_bg'], fg='white', command=lambda idx=i: self.browse_image(self.img_paths_non_conformes[idx])).pack(side='left', padx=5)

        non_conformes_entry_frame = tk.Frame(frame, bg=THEME['bg_section'])
        non_conformes_entry_frame.pack(padx=5, pady=5)
        for i in range(NB_IMAGES_PER_SET):
            tk.Entry(non_conformes_entry_frame, textvariable=self.img_paths_non_conformes[i], width=50, bg=THEME['text_bg'], fg='white').pack(side='left', padx=5)

    def setup_log_section(self):
        frame = create_thematic_frame(self.scrollable_frame, "Logs")
        frame.pack(padx=10, pady=10, fill='x')

        self.log_text = tk.Text(frame, height=5, bg=THEME['text_bg'], fg='white', wrap='word')
        self.log_text.pack(fill='x', padx=5, pady=5)
        self.log_text.insert('end', "Ici s'afficheront les logs.\n")
        self.log_text.config(state='disabled')

    def refresh_data_display(self):
        for i in self.tapis_tree.get_children():
            self.tapis_tree.delete(i)
        for i in self.temp_tree.get_children():
            self.temp_tree.delete(i)

        if not self.sechoir_data:
            return
        last_entry = self.sechoir_data[-1]
        four_data = last_entry.get('four_data', {})

        tapis = four_data.get('tapis', [])
        for t in tapis:
            self.tapis_tree.insert("", "end", values=(
                t.get('heure', ''),
                t.get('vit_stockeur', ''),
                t.get('tapis1', ''),
                t.get('tapis2', ''),
                t.get('tapis3', '')
            ))

        consignes = four_data.get('temperatures_consignes', [])
        reelles = four_data.get('temperatures_reelles', [])
        for con, re in zip(consignes, reelles):
            heure = con.get('heure', '')
            c_con = con.get('cels', [])
            c_re = re.get('cels', [])
            row_vals = [heure]
            for i in range(6):
                cval = c_con[i] if i < len(c_con) else ''
                rval = c_re[i] if i < len(c_re) else ''
                row_vals.append(f"{cval}/{rval}")
            c_air = con.get('air_neuf', '')
            r_air = re.get('air_neuf', '')
            row_vals.append(f"{c_air}/{r_air}")
            self.temp_tree.insert("", "end", values=tuple(row_vals))

    def load_model(self):
        path = filedialog.askopenfilename(title="Charger un modèle", filetypes=[("Modèle", "*.h5")])
        if path:
            mdl = load_model_from_file(path)
            if mdl:
                self.loaded_model = mdl
                messagebox.showinfo("Chargement Modèle", f"Modèle chargé depuis {path}")
                self.log("Modèle chargé depuis: " + path)
            else:
                messagebox.showerror("Erreur", "Impossible de charger le modèle.")

    def predict_on_last_entry(self):
        if self.loaded_model is None:
            messagebox.showerror("Erreur", "Aucun modèle chargé pour la prédiction.")
            return

        if not self.sechoir_data:
            messagebox.showerror("Erreur", "Aucune donnée de séchoir disponible.")
            return

        img_list_conformes = [v.get().strip() for v in self.img_paths_conformes]
        img_list_non_conformes = [v.get().strip() for v in self.img_paths_non_conformes]

        if any(not p or not os.path.exists(p) for p in img_list_conformes):
            messagebox.showerror("Erreur", "Veuillez sélectionner correctement les images CONFORMES (aspect idéal).")
            return
        if any(not p or not os.path.exists(p) for p in img_list_non_conformes):
            messagebox.showerror("Erreur", "Veuillez sélectionner correctement les images NON CONFORMES (aspect actuel).")
            return

        X_image, X_numeric, Y = self.extract_data_for_prediction(self.sechoir_data[-1], img_list_conformes, img_list_non_conformes)
        if X_image is None or X_numeric is None:
            messagebox.showerror("Erreur", "Impossible d'extraire les caractéristiques pour la prédiction.")
            return

        pred = self.loaded_model.predict([X_image, X_numeric])
        pred = pred.flatten()

        if pred.shape[0] < OUTPUT_DIM:
            messagebox.showerror("Erreur", f"Le modèle ne prédit pas assez de valeurs (attendu: {OUTPUT_DIM}).")
            return

        cels_pred = pred[0:6]
        air_neuf_pred = pred[6]
        vit_stock_pred = pred[7]
        tapis1_pred = pred[8]
        tapis2_pred = pred[9]
        tapis3_pred = pred[10]

        msg = (
            f"Prédictions des températures réelles (CELS):\n"
            f"CEL1: {cels_pred[0]:.2f}°C\n"
            f"CEL2: {cels_pred[1]:.2f}°C\n"
            f"CEL3: {cels_pred[2]:.2f}°C\n"
            f"CEL4: {cels_pred[3]:.2f}°C\n"
            f"CEL5/6: {cels_pred[4]:.2f}°C\n"
            f"CEL7/8: {cels_pred[5]:.2f}°C\n"
            f"AirNeuf: {air_neuf_pred:.2f}°C\n\n"
            f"Prédictions des vitesses:\n"
            f"Vit. Stockeur: {vit_stock_pred:.2f} Hz\n"
            f"Tapis1: {tapis1_pred:.2f} Hz\n"
            f"Tapis2: {tapis2_pred:.2f} Hz\n"
            f"Tapis3: {tapis3_pred:.2f} Hz\n"
        )

        if Y is not None:
            Y_flat = Y.flatten()
            mse = mean_squared_error(Y_flat[0:7], pred[0:7])
            msg += f"\nMSE (vs réel sur T°C et AirNeuf): {mse:.2f}"

        self.predict_result_var.set(msg)
        messagebox.showinfo("Prédiction", "Prédiction réalisée avec succès.\n\n" + msg)
        self.log("Prédiction effectuée.\n" + msg)

    def extract_data_for_prediction(self, entry, img_list_conformes, img_list_non_conformes):
        four_data = entry.get('four_data', {})

        consignes = four_data.get('temperatures_consignes', [])
        reelles = four_data.get('temperatures_reelles', [])
        tapis = four_data.get('tapis', [])

        last_con = get_last_valid_temp_entry(consignes)
        last_re = get_last_valid_temp_entry(reelles)
        if last_con is None or last_re is None or not tapis:
            return None, None, None

        last_tapis = tapis[-1]

        cels_con = last_con.get('cels', [])
        cels_re = last_re.get('cels', [])
        if len(cels_con) != 6 or len(cels_re) != 6:
            return None, None, None

        img_arr = load_and_concat_images(img_list_conformes, img_list_non_conformes, size=IMAGE_SIZE)
        if img_arr is None:
            return None, None, None
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

        return X_image, X_numeric, Y

    def browse_image(self, var):
        path = filedialog.askopenfilename(title="Sélectionnez une image (jpg, jpeg, png)", filetypes=[("Images", "*.jpg;*.jpeg;*.png")])
        if path:
            var.set(path)

    def log(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert('end', message+"\n")
        self.log_text.config(state='disabled')
        self.log_text.see('end')

def get_frame(parent, main_app=None):
    return UseIAModuleFrame(parent)

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Utilisation IA - Séchoir (Dense et CNN+Dense)")
    frame = get_frame(root, None)
    frame.pack(fill='both', expand=True)
    root.mainloop()
