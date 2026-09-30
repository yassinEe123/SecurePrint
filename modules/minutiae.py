import cv2
import math
import numpy as np


class MinutiaeExtractor:
    def __init__(self, border_margin: int = 10):
        self.border_margin = border_margin

    def _get_8_neighbors(self, image: np.ndarray, x: int, y: int):
        """
        Retourne les 8 voisins autour du pixel (x, y) dans l'ordre circulaire.
        Ordre:
        p1 p2 p3
        p8  c p4
        p7 p6 p5
        """
        return [
            1 if image[y - 1, x - 1] > 0 else 0,  # p1
            1 if image[y - 1, x] > 0 else 0,      # p2
            1 if image[y - 1, x + 1] > 0 else 0,  # p3
            1 if image[y, x + 1] > 0 else 0,      # p4
            1 if image[y + 1, x + 1] > 0 else 0,  # p5
            1 if image[y + 1, x] > 0 else 0,      # p6
            1 if image[y + 1, x - 1] > 0 else 0,  # p7
            1 if image[y, x - 1] > 0 else 0       # p8
        ]

    def crossing_number(self, image: np.ndarray, x: int, y: int) -> int:
        """
        Calcule le Crossing Number d'un pixel blanc du squelette.
        """
        neighbors = self._get_8_neighbors(image, x, y)
        neighbors.append(neighbors[0])

        cn = 0
        for i in range(8):
            cn += abs(neighbors[i] - neighbors[i + 1])

        return cn // 2

    def estimate_angle(self, image: np.ndarray, x: int, y: int) -> float:
        """
        Estimation simple de l'angle local à partir des voisins actifs.
        """
        neighbors_coords = [
            (-1, -1), (0, -1), (1, -1),
            (1, 0), (1, 1), (0, 1),
            (-1, 1), (-1, 0)
        ]

        active = []
        for dx, dy in neighbors_coords:
            if image[y + dy, x + dx] > 0:
                active.append((dx, dy))

        if not active:
            return 0.0

        avg_dx = sum(p[0] for p in active) / len(active)
        avg_dy = sum(p[1] for p in active) / len(active)

        angle = math.degrees(math.atan2(avg_dy, avg_dx))
        return angle

    def is_valid_minutia(self, image: np.ndarray, x: int, y: int) -> bool:
        """
        Ignore les minutiae trop proches du bord.
        """
        h, w = image.shape
        return (
            self.border_margin <= x < w - self.border_margin
            and self.border_margin <= y < h - self.border_margin
        )

    def extract_features(self, skeleton: np.ndarray):
        """
        Extrait une liste de minutiae sous forme:
        (x, y, type, angle)
        """
        minutiae = []
        h, w = skeleton.shape

        for y in range(1, h - 1):
            for x in range(1, w - 1):
                if skeleton[y, x] == 0:
                    continue

                if not self.is_valid_minutia(skeleton, x, y):
                    continue

                cn = self.crossing_number(skeleton, x, y)

                if cn == 1:
                    minutia_type = "ending"
                elif cn == 3:
                    minutia_type = "bifurcation"
                else:
                    continue

                angle = self.estimate_angle(skeleton, x, y)
                minutiae.append((x, y, minutia_type, angle))

        return minutiae

    def filter_false_minutiae(self, minutiae, min_distance: int = 10):
        """
        Supprime les minutiae trop proches entre elles.
        """
        filtered = []

        for m in minutiae:
            x1, y1, t1, a1 = m
            keep = True

            for fm in filtered:
                x2, y2, t2, a2 = fm
                dist = math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

                if dist < min_distance and t1 == t2:
                    keep = False
                    break

            if keep:
                filtered.append(m)

        return filtered

    def draw_minutiae(self, image: np.ndarray, minutiae):
        """
        Dessine les minutiae sur une image couleur.
        ending = vert
        bifurcation = rouge
        """
        if len(image.shape) == 2:
            output = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        else:
            output = image.copy()

        for x, y, minutia_type, angle in minutiae:
            if minutia_type == "ending":
                color = (0, 255, 0)
            else:
                color = (0, 0, 255)

            cv2.circle(output, (x, y), 3, color, 1)

        return output
