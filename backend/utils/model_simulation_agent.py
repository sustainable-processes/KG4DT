from functools import lru_cache
import copy

from .model_agent import ModelAgent


class ModelSimulationAgent:
    """Model simulation agent for solving differential equation models.

    Possible operating parameters included in the input data:
        - flow rate
        - temperature
        - initial mass fraction
        - initial concentration
    """

    def __init__(self, entity, request):
        self.entity = entity
        self.request = request
        self.model_agent = ModelAgent(entity, request["context"])

    def simulate_scipy(self):
        """Generate and run simulation for data.
            - `scipy_model`: includes`parameter_value_dict`, `derivative`, `boundary` and `simulation`
            - `boundary`: boundary function for solving
            - `data`: represents input operating parameters
        """

        # Build per-run operating parameter dicts
        op_param_dicts = []
        for vals in self.request["op_params"]["val"]:
            op_param_dict = {}
            for op_param_ind, val in zip(self.request["op_params"]["ind"], vals):
                op_param_dict[op_param_ind] = val
            op_param_dicts.append(op_param_dict)

        # Generate model code and execute in-process
        model_str = self.model_agent.to_scipy_model()
        env = {}
        exec(model_str, env)

        base_param_dict = env.get("param_dict")
        simulate = env.get("simulate")
        if base_param_dict is None or simulate is None:
            raise RuntimeError("Generated model missing 'param_dict' or 'simulate' function.")

        # Prepare concrete param_dicts per operation case
        param_dicts = []
        for op_param_dict in op_param_dicts:
            pd = base_param_dict.copy()
            for ind, val in op_param_dict.items():
                pd[ind] = val
            param_dicts.append(pd)

        # Optional: small cache for repeated simulate calls
        @lru_cache(maxsize=512)
        def _simulate_cached(idx: int):
            return simulate(copy.deepcopy(param_dicts[idx]))

        results = []
        for i in range(len(param_dicts)):
            results.append(_simulate_cached(i))
        return results