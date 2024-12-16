# data_utils.py
# ===========================================================================================
# 👉 Ce module gère les opérations sur les données et les images. Il contient :
#    - Le thème de l'interface (THEME)
#    - Les chemins et constantes globales (DATA_DIR, MODELS_DIR, IMAGE_SIZE, NB_IMAGES_PER_SET)
#    - Des fonctions utilitaires pour charger les données du séchoir, extraire les sets,
#      charger/concaténer les images, trouver la dernière consigne valide, etc.
#    - Des fonctions pour charger/sauvegarder les modèles TensorFlow.
#
# Améliorations :
# - Ajout de commentaires plus détaillés.
# - Possibilité d'intégrer de la data augmentation via ImageDataGenerator ou transformations manuelles.
# - Gestion des erreurs et logs plus explicite.
# - Code plus flexible et clair.
# ===========================================================================================

import os
import json
import logging
import numpy as np
from PIL import Image
from tensorflow import keras

# ===========================================================================================
# 👉 THEME : défini les couleurs et styles utilisés dans l'interface.
# ===========================================================================================
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

# ===========================================================================================
# 👉 Répertoires et constantes :
# DATA_DIR : Répertoire principal des données
# MODELS_DIR : Répertoire pour stocker les modèles entraînés
# IMAGE_SIZE : Taille des images (redimensionnées à 32x32)
# NB_IMAGES_PER_SET : Nombre d'images CONFORMES et NON CONFORMES par set
# ===========================================================================================
DATA_DIR = "DATA"
MODELS_DIR = "MODELS"
if not os.path.exists(MODELS_DIR):
    os.makedirs(MODELS_DIR)

IMAGE_SIZE = (32, 32)
NB_IMAGES_PER_SET = 3

logger = logging.getLogger("train_ia_data")

class DataLoadingError(Exception):
    """
    Exception levée lors d'erreurs dans le chargement des données du séchoir ou des images.
    Permet de signaler à la couche supérieure qu'une opération de chargement a échoué.
    """
    pass

def safe_float(x):
    """
    Convertit une valeur en float sans lever d'erreur.
    Si la conversion échoue (ValueError, TypeError), renvoie 0.0.
    """
    try:
        return float(x)
    except (ValueError, TypeError):
        return 0.0

def get_sechoir_data_file():
    """
    Tente de localiser le fichier sechoir_data.json.
    Cherche dans le répertoire parent du script, puis dans le répertoire courant.

    Retourne :
    - str ou None : chemin absolu du fichier ou None si introuvable.
    """
    try:
        main_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    except:
        main_dir = os.getcwd()

    data_file = os.path.join(main_dir, 'sechoir_data.json')
    if not os.path.exists(data_file):
        alt_file = os.path.join(os.getcwd(), 'sechoir_data.json')
        if os.path.exists(alt_file):
            data_file = alt_file
        else:
            data_file = None
    return data_file

def load_sechoir_data():
    """
    Charge les données du séchoir depuis sechoir_data.json si disponible.
    Retourne une liste de dict ou une liste vide en cas d'erreur ou d'absence du fichier.
    """
    data_file = get_sechoir_data_file()
    if data_file is None or not os.path.exists(data_file):
        logger.warning("Fichier sechoir_data.json non trouvé.")
        return []
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not isinstance(data, list):
                logger.error("Format invalide de sechoir_data.json. Un tableau JSON est attendu.")
                return []
            return data
    except Exception as e:
        logger.error(f"Erreur chargement sechoir_data.json: {e}", exc_info=True)
        return []

def get_last_valid_temp_entry(temp_list):
    """
    Parcourt la liste des consignes ou relevés de températures à l'envers
    pour trouver la dernière entrée contenant 6 cels et un air_neuf.

    Retourne le dict de l'entrée valide ou None.
    """
    for t in reversed(temp_list):
        cels = t.get('cels', [])
        if len(cels) == 6 and 'air_neuf' in t:
            return t
    return None

def apply_data_augmentation(image_array):
    """
    Exemple de fonction qui applique de la data augmentation manuelle ou via ImageDataGenerator.

    Ici, on utilise ImageDataGenerator juste en exemple. Vous pouvez ajuster rotation_range, zoom_range, etc.
    Pour réellement augmenter les données, il faudrait le faire batch par batch pendant l'entraînement.
    """
    # Exemple d'utilisation d'un ImageDataGenerator
    datagen = keras.preprocessing.image.ImageDataGenerator(
        rotation_range=20,
        zoom_range=0.2,
        horizontal_flip=True,
        fill_mode='nearest'
    )

    # On suppose que image_array est (height, width, 3)
    # Pour utiliser datagen.flow, on doit rajouter une dimension batch : (1, height, width, 3)
    batch = np.expand_dims(image_array, axis=0)
    it = datagen.flow(batch, batch_size=1)
    augmented_batch = it.next()  # On génère une image augmentée
    return augmented_batch[0]  # Retourne l'image (height, width, 3) augmentée

def load_and_concat_images(img_list_conformes, img_list_non_conformes, size=IMAGE_SIZE, use_augmentation=False):
    """
    Charge, redimensionne et concatène horizontalement les images conformes et non conformes.
    Si use_augmentation=True, applique de la data augmentation sur chaque image chargée.

    Paramètres :
    - img_list_conformes (list[str]) : chemins des images conformes
    - img_list_non_conformes (list[str]) : chemins des images non conformes
    - size (tuple) : taille de redimensionnement, par défaut (32,32)
    - use_augmentation (bool) : si True, applique de la data augmentation

    Retourne :
    - np.ndarray (height, width_total, 3)
    Lève DataLoadingError si une image est introuvable ou illisible.
    """
    all_paths = img_list_conformes + img_list_non_conformes
    imgs = []
    for p in all_paths:
        if not p or not os.path.exists(p):
            msg = f"Image invalide ou non trouvée : {p}"
            logger.error(msg)
            raise DataLoadingError(msg)
        try:
            img = Image.open(p).convert("RGB")
            img = img.resize(size)
            img_array = np.array(img, dtype=np.float32) / 255.0

            if use_augmentation:
                # On applique la data augmentation
                img_array = apply_data_augmentation(img_array)

            imgs.append(img_array)
        except Exception as e:
            msg = f"Erreur lors du chargement de l'image {p}: {e}"
            logger.error(msg, exc_info=True)
            raise DataLoadingError(msg)

    final_img = np.concatenate(imgs, axis=1)
    return final_img

def extract_set_data(img_list_conformes, img_list_non_conformes, four_data=None, use_augmentation=False):
    """
    Extrait les données (X, Y) pour un set donné.
    Permet également de spécifier si on veut appliquer de la data augmentation sur les images.

    Paramètres :
    - img_list_conformes (list[str])
    - img_list_non_conformes (list[str])
    - four_data (dict ou None) : si None, on prend le dernier enregistrement du séchoir.
    - use_augmentation (bool) : si True, applique la data augmentation à chaque image.

    Retourne (X_image, X_numeric), Y ou (None, None) si données insuffisantes.
    Lève DataLoadingError en cas de problème de chargement d'images.
    """
    data = load_sechoir_data()
    if not data:
        return None, None

    if four_data is None:
        last_entry = data[-1]
        four_data = last_entry.get('four_data', {})

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

    try:
        img_arr = load_and_concat_images(img_list_conformes, img_list_non_conformes, size=IMAGE_SIZE, use_augmentation=use_augmentation)
    except DataLoadingError:
        return None, None

    if img_arr is None:
        return None, None

    X_image = img_arr[np.newaxis, ...]  # (1, height, width, 3)

    # Construction X_numeric
    X_numeric_values = [safe_float(val) for val in cels_con]
    X_numeric_values.append(safe_float(last_con.get('air_neuf', 0.0)))
    X_numeric_values.append(safe_float(last_tapis.get('vit_stockeur', 0.0)))
    X_numeric_values.append(safe_float(last_tapis.get('tapis1', 0.0)))
    X_numeric_values.append(safe_float(last_tapis.get('tapis2', 0.0)))
    X_numeric_values.append(safe_float(last_tapis.get('tapis3', 0.0)))
    X_numeric = np.array(X_numeric_values).reshape(1, -1)

    # Construction Y
    Y_values = [safe_float(val) for val in cels_re]
    Y_values.append(safe_float(last_re.get('air_neuf', 0.0)))
    Y_values.append(safe_float(last_tapis.get('vit_stockeur', 0.0)))
    Y_values.append(safe_float(last_tapis.get('tapis1', 0.0)))
    Y_values.append(safe_float(last_tapis.get('tapis2', 0.0)))
    Y_values.append(safe_float(last_tapis.get('tapis3', 0.0)))
    Y = np.array(Y_values).reshape(1, -1)

    return (X_image, X_numeric), Y

def load_model_from_file(path):
    """
    Charge un modèle Keras depuis un fichier .h5.
    Retourne le modèle ou None si échec.
    """
    if not os.path.exists(path):
        logger.warning(f"Fichier modèle non trouvé : {path}")
        return None
    try:
        model = keras.models.load_model(path)
        return model
    except Exception as e:
        logger.error(f"Erreur chargement modèle {path}: {e}", exc_info=True)
        return None

def get_latest_model(model_type):
    """
    Récupère le dernier modèle sauvegardé (le plus récent) pour un type de produit donné.
    Cherche dans MODELS_DIR des fichiers 'model_{model_type}_*.h5'.

    Retourne le chemin ou None si aucun modèle trouvé.
    """
    if not os.path.exists(MODELS_DIR):
        return None
    files = [f for f in os.listdir(MODELS_DIR) if f.startswith(f"model_{model_type}_") and f.endswith('.h5')]
    if not files:
        return None
    files.sort(key=lambda x: os.path.getmtime(os.path.join(MODELS_DIR, x)), reverse=True)
    return os.path.join(MODELS_DIR, files[0])
