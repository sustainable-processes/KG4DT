import numpy as np
from scipy.optimize import fsolve
from scipy.integrate import solve_ivp, solve_bvp
from .model_agent import ModelAgent


class ModelSimulationAgent:
    """Model simulation agent for solving ordinary/partial differential equations of chemical process models.

    Possible operating parameters included in the input data:
        - temperature
        - flow rate
        - initial concentration
    """

    def __init__(self, entity, model_simulation_request):
        self.entity = entity
        self.model_simulation_request = model_simulation_request
        self.model_agent = ModelAgent(entity, model_simulation_request["model_context"])

    def simulate_scipy(self):
        """Generate and run simulation for data.
            - `scipy_model`: includes`parameter_value_dict`, `derivative`, `boundary` and `simulation`
            - `boundary`: boundary function for solving
            - `data`: represents input operating parameters
        """
        exec(self.model_agent.to_scipy_model())
        local_simulation = locals()["simulation"]
        local_parameter_value_dict = locals()["parameter_value_dict"]
        for k, v in zip(self.model_simulation_request["parameter"]["key"], self.model_simulation_request["parameter"]["value"]):
            local_parameter_value_dict[tuple(k)] = v

        results = []
        streams = [s for s in self.model_agent.model_context["basic"]["streams"] 
                   if self.model_agent.model_context["information"]["streams"][s]["state"] == "liquid"]
        species = self.model_agent.model_context["basic"]["species"]
        for data in self.model_simulation_request["data"]["value"]:
            result = []
            # parameter setting from front end, without checking
            for k, v in zip(self.model_simulation_request["data"]["key"], data):
                local_parameter_value_dict[tuple(k)] = v
            res = local_simulation(local_parameter_value_dict)
            if res:
                for i, s in enumerate(streams):
                    for j, sp in enumerate(species):
                        r = {"data": [[t, v] for t, v in zip(res[0], res[1][i * len(species) + j])], "label": s + "  " + sp + ""}
                        result.append(r)
                average = (res[1].reshape(len(streams), len(species), -1) * res[2].reshape(-1, 1, 1)).sum(axis=0) / res[2].sum()
                for i, sp in enumerate(species):
                    r = {"data": [[t, v] for t, v in zip(res[0], average[i])], "label": "average" + "  " + sp + ""}
                    result.append(r)
            results.append(result)
        return results