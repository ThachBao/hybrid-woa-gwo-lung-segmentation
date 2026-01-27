import numpy as np
from skimage.filters import threshold_multiotsu


class OtsuMulti:
    """
    Multi-level Otsu thresholding.
    
    Compatible interface with GWO/WOA/HYBRID for easy integration.
    Note: Otsu is deterministic and doesn't use iterations or agents.
    
    IMPORTANT: This class is NOT used in the current UI implementation.
    The UI calls threshold_multiotsu directly for better performance.
    This class is kept for API compatibility with other optimizers.
    """
    def __init__(self, n_agents=None, n_iters=None, seed=None):
        # These parameters are ignored for Otsu (deterministic)
        # But kept for interface compatibility
        pass

    def optimize(self, fitness_fn, dim, lb, ub, repair_fn=None, init_pop=None):
        """
        Optimize using Otsu's method.
        
        NOTE: This method uses evenly-spaced thresholds as a fallback
        because Otsu needs direct image access, which is not available
        through the fitness_fn interface.
        
        For actual Otsu thresholding, use optimize_with_image() instead
        or call threshold_multiotsu directly (as done in app.py).
        
        Args:
            fitness_fn: Fitness function to evaluate thresholds
            dim: Dimension (number of thresholds = K)
            lb: Lower bounds
            ub: Upper bounds
            repair_fn: Optional repair function
            init_pop: Not used (Otsu is deterministic)
        
        Returns:
            best_x: Best solution found (evenly-spaced thresholds)
            best_f: Best fitness value
            history: List with single entry (Otsu runs once)
        """
        # Convert bounds to scalars
        if isinstance(lb, np.ndarray):
            lb_val = lb[0]
        else:
            lb_val = lb
        
        if isinstance(ub, np.ndarray):
            ub_val = ub[0]
        else:
            ub_val = ub
        
        # Generate evenly spaced thresholds as fallback
        # This is NOT true Otsu, but provides a reasonable baseline
        thresholds = np.linspace(lb_val, ub_val, dim + 2)[1:-1]
        
        # Apply repair if provided
        if repair_fn is not None:
            thresholds = repair_fn(thresholds)
        
        # Evaluate fitness
        best_f = fitness_fn(thresholds)
        
        # Create history (single iteration)
        history = [{
            "iter": 0,
            "best_f": float(best_f),
            "mean_f": float(best_f),
        }]
        
        return thresholds, best_f, history
    
    def optimize_with_image(self, image, dim):
        """
        Optimize using Otsu's method with direct image access.
        
        This is the CORRECT way to use Otsu thresholding.
        
        Args:
            image: Grayscale image (numpy array)
            dim: Number of thresholds (K)
        
        Returns:
            thresholds: Array of K thresholds computed by Otsu's method
        """
        # Use scikit-image's multi-Otsu
        # classes = K + 1 (number of segments)
        thresholds = threshold_multiotsu(image, classes=dim + 1)
        return thresholds
