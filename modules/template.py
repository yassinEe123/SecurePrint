import math
import numpy as np
import cv2


class TemplateGenerator:
    """
    Generates a 128-dimensional orientation-field template from the fingerprint image.

    Algorithm:
      1. Divide the segmented image into a GRID×GRID grid of blocks.
      2. Compute ridge orientation for each block via the structure tensor
         (Sobel gradients → Gxx, Gyy, Gxy → θ = ½·atan2(2Gxy, Gxx−Gyy) + π/2).
      3. Subtract the global mean orientation (rotation normalisation).
      4. Represent each block as (cos 2Δθ, sin 2Δθ) to handle the π-periodicity
         of ridge orientations → 2·GRID² features = 128 dims with GRID=8.
      5. L2-normalise the final vector.

    Comparison: cosine distance  d = 1 − (t1·t2)/(|t1|·|t2|) ∈ [0, 2]
      - Same finger, different scan  : typically 0.12 – 0.72
      - Different finger             : typically 0.50 – 1.10

    Thresholds (calibrated on FVC2002 DB1_B):
      - Authentication  threshold = 0.70   (accept if d < 0.70)
      - Duplicate       threshold = 0.55   (block enrollment if d < 0.55)
    """

    GRID = 8  # grid size → 2 × GRID² = 128 features

    def generate_template(self, minutiae,
                          image=None,
                          image_orientation_deg: float = None) -> np.ndarray:
        """
        Parameters
        ----------
        minutiae   : list of (x, y, type, angle) — accepted but not used.
        image      : np.ndarray — segmented fingerprint image (preferred).
        image_orientation_deg : float — legacy parameter, ignored.

        Returns
        -------
        np.ndarray of shape (128,), dtype float32.
        """
        if image is not None:
            return self._from_image(image)
        # Fallback: no image available → zero template (shouldn't happen in practice)
        return np.zeros(2 * self.GRID * self.GRID, dtype=np.float32)

    # ------------------------------------------------------------------
    # Internal: orientation-field extraction
    # ------------------------------------------------------------------

    def _from_image(self, img: np.ndarray) -> np.ndarray:
        h, w = img.shape[:2]
        bh = h // self.GRID
        bw = w // self.GRID

        # Sobel gradient magnitudes
        blurred = cv2.GaussianBlur(img.astype(np.float64), (5, 5), 0)
        gx = cv2.Sobel(blurred, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(blurred, cv2.CV_64F, 0, 1, ksize=3)
        Gxx = gx * gx
        Gyy = gy * gy
        Gxy = gx * gy

        thetas = np.empty(self.GRID * self.GRID, dtype=np.float64)
        for row in range(self.GRID):
            for col in range(self.GRID):
                r0, r1 = row * bh, (row + 1) * bh
                c0, c1 = col * bw, (col + 1) * bw
                sxx = Gxx[r0:r1, c0:c1].mean()
                syy = Gyy[r0:r1, c0:c1].mean()
                sxy = Gxy[r0:r1, c0:c1].mean()
                # Ridge orientation (perpendicular to gradient direction)
                thetas[row * self.GRID + col] = (
                    0.5 * math.atan2(2 * sxy, sxx - syy) + math.pi / 2
                )

        # Subtract global mean (rotation normalisation)
        g = thetas.mean()
        delta = ((thetas - g + math.pi / 2) % math.pi) - math.pi / 2

        # Encode as (cos 2Δθ, sin 2Δθ) to handle π-periodicity
        feat = np.concatenate([np.cos(2 * delta), np.sin(2 * delta)]).astype(np.float32)

        # L2 normalise
        norm = np.linalg.norm(feat)
        if norm > 1e-9:
            feat /= norm
        return feat
