import numpy as np
from src.optim.bounds import clamp


class PSO:
    """
    Particle Swarm Optimization for threshold optimization.
    
    Compatible interface with GWO/WOA/HYBRID for easy integration.
    """
    def __init__(
        self,
        n_agents=30,
        n_iters=80,
        w_max=0.6,
        w_min=0.4,
        c1=1.2,
        c2=1.2,
        seed=None
    ):
        self.n_agents = n_agents
        self.n_iters = n_iters
        self.w_max = w_max
        self.w_min = w_min
        self.c1 = c1
        self.c2 = c2
        self.seed = seed
        # Dùng Generator thay vì seed toàn cục
        self.rng = np.random.default_rng(seed)

    def optimize(self, fitness_fn, dim, lb, ub, repair_fn=None, init_pop=None):
        """
        Optimize using PSO.
        
        Args:
            fitness_fn: Fitness function to minimize
            dim: Dimension (number of thresholds)
            lb: Lower bounds (array or scalar)
            ub: Upper bounds (array or scalar)
            repair_fn: Optional repair function
            init_pop: Optional initial population (n_agents x dim)
        
        Returns:
            best_x: Best solution found
            best_f: Best fitness value (minimization)
            history: List of dicts with iteration info
        """
        # Không dùng np.random.seed toàn cục nữa
        
        # Convert bounds to scalars
        if isinstance(lb, np.ndarray):
            lb_val = lb[0]
        else:
            lb_val = lb
        
        if isinstance(ub, np.ndarray):
            ub_val = ub[0]
        else:
            ub_val = ub
        
        # Initialize swarm
        if init_pop is not None:
            X = init_pop.copy()
        else:
            X = self.rng.uniform(lb_val, ub_val, size=(self.n_agents, dim))

        V = np.zeros_like(X)
        
        # Personal best
        pbest = X.copy()
        pbest_score = np.full(self.n_agents, np.inf)  # Minimization
        
        # Global best
        gbest = None
        gbest_score = np.inf
        
        # History
        history = []
        
        for it in range(self.n_iters):
            # Calculate inertia weight using linear decrease (Eq. 3 from PSO paper)
            if self.n_iters <= 1:
                w = self.w_min
            else:
                w = self.w_max - it * (self.w_max - self.w_min) / (self.n_iters - 1)
            
            for i in range(self.n_agents):
                # Apply repair if provided
                if repair_fn is not None:
                    x_repaired = repair_fn(X[i])
                else:
                    x_repaired = np.sort(X[i])
                
                # Evaluate fitness (minimization)
                score = fitness_fn(x_repaired)
                
                # Update personal best
                if score < pbest_score[i]:
                    pbest_score[i] = score
                    pbest[i] = x_repaired.copy()
                
                # Update global best
                if score < gbest_score:
                    gbest_score = score
                    gbest = x_repaired.copy()
            
            # Update velocity & position
            r1 = self.rng.random((self.n_agents, dim))
            r2 = self.rng.random((self.n_agents, dim))
            
            V = (
                w * V
                + self.c1 * r1 * (pbest - X)
                + self.c2 * r2 * (gbest - X)
            )
            
            X = X + V
            X = clamp(X, lb_val, ub_val)
            
            # Record history
            mean_f = np.mean([fitness_fn(repair_fn(X[i]) if repair_fn else np.sort(X[i])) 
                             for i in range(self.n_agents)])
            history.append({
                "iter": it,
                "best_f": float(gbest_score),
                "mean_f": float(mean_f),
            })
        
        # Apply final repair
        if repair_fn is not None:
            gbest = repair_fn(gbest)
        else:
            gbest = np.sort(gbest)
        
        return gbest, gbest_score, history
