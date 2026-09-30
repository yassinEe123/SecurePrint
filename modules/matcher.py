import math
import numpy as np


class Authenticator:
    """
    Cosine-distance comparator for orientation-field templates (128-dim).

    Distance formula:  d = 1 − (t1·t2) / (|t1|·|t2|)   ∈ [0, 2]

    Calibrated on FVC2002 DB1_B:
      - Same finger, different scan  : d ≈ 0.12 – 0.72
      - Different finger             : d ≈ 0.50 – 1.10
      (templates are L2-normalised, so dot product = cosine similarity)

    Thresholds:
      - threshold           = 0.70  → ACCEPTED if d < 0.70
      - duplicate_threshold = 0.55  → DUPLICATE if d < 0.55
    """

    def __init__(self, threshold: float = 0.70, duplicate_threshold: float = 0.55):
        self.threshold           = threshold
        self.duplicate_threshold = duplicate_threshold

    def set_threshold(self, value: float):
        self.threshold = value

    def set_duplicate_threshold(self, value: float):
        self.duplicate_threshold = value

    # ------------------------------------------------------------------
    # Core comparison
    # ------------------------------------------------------------------

    def compare(self, t1: np.ndarray, t2: np.ndarray) -> float:
        """
        Cosine distance in [0, 2].  Lower = more similar.
        Templates are expected to be L2-normalised (unit vectors).
        """
        if t1.ndim != 1 or t2.ndim != 1 or len(t1) == 0 or len(t2) == 0:
            return 1.0
        n1 = float(np.linalg.norm(t1))
        n2 = float(np.linalg.norm(t2))
        if n1 < 1e-9 or n2 < 1e-9:
            return 1.0
        return 1.0 - float(np.dot(t1, t2) / (n1 * n2))

    # ------------------------------------------------------------------
    # Authentication 1:1
    # ------------------------------------------------------------------

    def authenticate(self, query_template: np.ndarray,
                     stored_template: np.ndarray):
        distance = self.compare(query_template, stored_template)
        return distance < self.threshold, distance

    # ------------------------------------------------------------------
    # Identification 1:N
    # ------------------------------------------------------------------

    def identify(self, query_template: np.ndarray, candidates: dict):
        """candidates = {username: np.ndarray}"""
        best_user     = None
        best_distance = math.inf

        for username, template in candidates.items():
            distance = self.compare(query_template, template)
            if distance < best_distance:
                best_distance = distance
                best_user     = username

        if best_user is not None and best_distance < self.threshold:
            return best_user, best_distance
        return None, best_distance

    # ------------------------------------------------------------------
    # Duplicate detection
    # ------------------------------------------------------------------

    def is_duplicate_fingerprint(self, new_template: np.ndarray,
                                  candidates: dict):
        """candidates = {username: np.ndarray}"""
        best_user     = None
        best_distance = math.inf

        for username, template in candidates.items():
            distance = self.compare(new_template, template)
            if distance < best_distance:
                best_distance = distance
                best_user     = username

        if best_user is not None and best_distance < self.duplicate_threshold:
            return True, best_user, best_distance
        return False, best_user, best_distance
