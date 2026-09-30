import cv2
import math
import numpy as np
import os


class FingerprintProcessor:
    """
    Chaîne de prétraitement d'une image d'empreinte digitale.

    Correction apportée :
    - skeletonize() utilise cv2.ximgproc.thinning() (Zhang-Suen officiel)
      au lieu de la boucle morphologique manuelle qui produisait des
      squelettes bruités → moins de fausses minutiae → template plus stable.
      Fallback automatique vers la méthode manuelle si opencv-contrib absent.
    """

    def __init__(self):
        pass

    # ------------------------------------------------------------------
    # Chargement
    # ------------------------------------------------------------------

    def load_image(self, path: str) -> np.ndarray:
        """
        Charge une image en niveaux de gris.
        """
        image = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise FileNotFoundError(f"Impossible de charger l'image : {path}")
        return image

    # ------------------------------------------------------------------
    # Amélioration du contraste (CLAHE)
    # ------------------------------------------------------------------

    def normalize_contrast(self, image: np.ndarray) -> np.ndarray:
        """
        Améliore le contraste localement avec CLAHE.
        """
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(image)

    # ------------------------------------------------------------------
    # Segmentation (masque zone utile)
    # ------------------------------------------------------------------

    def segment_fingerprint(self, image: np.ndarray) -> np.ndarray:
        """
        Conserve uniquement la zone contenant l'empreinte.
        """
        blurred = cv2.GaussianBlur(image, (11, 11), 0)
        _, mask  = cv2.threshold(blurred, 0, 255,
                                 cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Inversion si le fond est blanc
        white_ratio = np.sum(mask == 255) / mask.size
        if white_ratio > 0.6:
            mask = cv2.bitwise_not(mask)

        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  kernel)

        return cv2.bitwise_and(image, image, mask=mask)

    # ------------------------------------------------------------------
    # Binarisation adaptative
    # ------------------------------------------------------------------

    def binarize(self, image: np.ndarray) -> np.ndarray:
        """
        Convertit l'image en noir/blanc (crêtes blanches, fond noir).
        """
        binary = cv2.adaptiveThreshold(
            image, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            15, 8
        )
        return binary

    # ------------------------------------------------------------------
    # Squelettisation (CORRECTION PRINCIPALE)
    # ------------------------------------------------------------------

    def skeletonize(self, binary: np.ndarray) -> np.ndarray:
        """
        Squelettisation des crêtes.

        Utilise cv2.ximgproc.thinning() si opencv-contrib est installé
        (résultat propre, peu de faux positifs).
        Sinon, fallback vers la méthode morphologique manuelle.
        """
        try:
            # Méthode recommandée : Zhang-Suen via opencv-contrib
            skeleton = cv2.ximgproc.thinning(binary,
                                             thinningType=cv2.ximgproc.THINNING_ZHANGSUEN)
            return skeleton

        except AttributeError:
            # Fallback : boucle morphologique manuelle
            print("  ⚠ opencv-contrib non disponible, fallback squelettisation manuelle.")
            return self._skeletonize_manual(binary)

    def _skeletonize_manual(self, binary: np.ndarray) -> np.ndarray:
        """
        Squelettisation morphologique manuelle (fallback).
        """
        skeleton = np.zeros(binary.shape, np.uint8)
        element  = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
        img      = binary.copy()

        while True:
            opened   = cv2.morphologyEx(img, cv2.MORPH_OPEN, element)
            temp     = cv2.subtract(img, opened)
            eroded   = cv2.erode(img, element)
            skeleton = cv2.bitwise_or(skeleton, temp)
            img      = eroded.copy()

            if cv2.countNonZero(img) == 0:
                break

        return skeleton

    # ------------------------------------------------------------------
    # Estimation de l'orientation dominante des crêtes
    # ------------------------------------------------------------------

    def estimate_ridge_orientation(self, segmented_image: np.ndarray) -> float:
        """
        Estime l'orientation dominante des crêtes via le tenseur de structure
        (méthode des gradients de Sobel).

        Bien plus stable que le PCA sur les minutiae : basée sur le contenu
        global de l'image → angle cohérent quelle que soit la zone capturée.
        Variation typique entre scans du même doigt : < 40°
        (vs > 130° pour le PCA sur les minutiae détectées).

        Retourne l'angle dominant des crêtes en degrés, dans [-90, 90].
        """
        blurred = cv2.GaussianBlur(segmented_image, (5, 5), 0)

        gx = cv2.Sobel(blurred, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(blurred, cv2.CV_64F, 0, 1, ksize=3)

        Gxx = float(np.mean(gx * gx))
        Gyy = float(np.mean(gy * gy))
        Gxy = float(np.mean(gx * gy))

        # Orientation dominante du gradient → crêtes perpendiculaires
        theta_gradient = 0.5 * math.atan2(2 * Gxy, Gxx - Gyy)
        theta_ridge = theta_gradient + math.pi / 2

        # Ramener dans [-π/2, π/2]
        while theta_ridge > math.pi / 2:
            theta_ridge -= math.pi
        while theta_ridge < -math.pi / 2:
            theta_ridge += math.pi

        return float(math.degrees(theta_ridge))

    # ------------------------------------------------------------------
    # Sauvegarde
    # ------------------------------------------------------------------

    def save_image(self, image: np.ndarray, output_path: str) -> None:
        """
        Sauvegarde une image sur disque.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        cv2.imwrite(output_path, image)
