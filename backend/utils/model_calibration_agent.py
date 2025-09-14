import numpy as np
from scipy.integrate import solve_bvp, solve_ivp
from scipy.optimize import fsolve, differential_evolution
import os
import pickle
import tempfile
from .model_agent import ScipyModel
from .model_agent import ModelAgent


class ModelCalibrationAgent:
    """Model calibration agent for optimizing parameters of ordinary/partial differential equations of chemical process models.

    Possible calibration parameters included in the input data:
        - molecular transport-related parameters
        - reaction kinetics-related parameters
    """

    def __init__(self, entity, model_calibration_request):
        self.entity = entity
        self.model_calibration_request = model_calibration_request
        self.model_agent = ModelAgent(entity, model_calibration_request["model_context"])
    
    def calibration_scipy(self):
        """Generate and run simulation for data.
            - `scipy_model`: includes`parameter_value_dict`, `derivative`, `boundary` and `simulation`
            - `calibration_parameters`: boundary function for solving
            - `data`: represents input operating parameters
        """
        exec(self.model_agent.to_scipy_model())
        local_simulation = locals()["simulation"]
        local_parameter_value_dict = locals()["parameter_value_dict"]
        parameter_key = []
        parameter_bounds = []
        for key, init_value, min_value, max_value in zip(self.model_calibration_request["parameter"]["key"], 
                                                         self.model_calibration_request["parameter"]["init"],
                                                         self.model_calibration_request["parameter"]["min"],
                                                         self.model_calibration_request["parameter"]["max"]):
            if init_value == min_value and min_value == max_value:
                local_parameter_value_dict[tuple(key)] = init_value
            else:
                parameter_key.append(key)
                parameter_bounds.append((min_value, max_value))
        # parameter_inits = np.array(self.model_calibration_request["parameter"]["init"], dtype=np.float64)

        streams = [s for s in self.model_agent.model_context["basic"]["streams"] 
                if self.model_agent.model_context["information"]["streams"][s]["state"] == "liquid"]
        species = self.model_agent.model_context["basic"]["species"]
        reals = np.array([[v if isinstance(v, (float, int)) else np.nan for v in record[-len(species):]] 
                            for record in self.model_calibration_request["data"]["value"]], dtype=np.float64)
        atol = 0.1 * reals[~np.isnan(reals)].min()
        
        calibration_code = ScipyModel()
        calibration_code.codes.append("import os")
        calibration_code.codes.append("import pickle")
        calibration_code.codes.append("from scipy.optimize import differential_evolution")
        calibration_code.codes.extend(self.model_agent.to_scipy_model().split("\n"))
        calibration_code.add("", 0)
        calibration_code.add(f"parameter_key = {parameter_key}", 0)
        calibration_code.add(f"data_key = {self.model_calibration_request['data']['key']}", 0)
        calibration_code.add(f"data_value = {self.model_calibration_request['data']['value']}", 0)
        calibration_code.add(f"reals = np.array({str(reals.tolist()).replace('nan', 'np.nan')}, dtype=np.float64)", 0)
        calibration_code.add([
            "def calc_mse(p):",
            "    for k, v in zip(parameter_key, p):",
            "        parameter_value_dict[tuple(k)] = v",
            "    preds = []",
            "    for value in data_value:",
            "        for k, v in zip(data_key, value):",
            "            parameter_value_dict[tuple(k)] = v",
            "        res = simulation(parameter_value_dict)",
            "        if res:",
            f"            average = (res[1].reshape({len(streams)}, {len(species)}, -1) * res[2].reshape(-1, 1, 1)).sum(axis=0)[:, -1] / res[2].sum()",
            "        else:",
            f"            average = np.array([np.nan] * {len(species)})",
            "        preds.append(average)",
            "    preds = np.array(preds, dtype=np.float64)",
            "    errors = (preds - reals)",
            "    mse = (errors[~np.isnan(errors)] ** 2).mean()",
            "    return mse",
            "",
            "if __name__ == '__main__':",
            f"    res = differential_evolution(calc_mse, bounds={parameter_bounds if parameter_bounds else [(0, 0)]}, seed=1, maxiter=30, popsize=16, atol={atol}, workers=8, polish=False)",
            "    pickle.dump(res, open(os.path.join(os.path.dirname(__file__), 'res.pkl'), 'wb'))"
        ], 0)

        with tempfile.TemporaryDirectory() as temp_dir:
            with open(os.path.join(temp_dir, "calibration.py"), "w") as f:
                f.write(calibration_code.get_model())
            os.system(f"python {temp_dir}/calibration.py")
            res = pickle.load(open(f"{temp_dir}/res.pkl", "rb"))

        # FOR NON-MULTIPROCESS SOLVING
        # def calc_mse(p):
        #     for k, v in zip(parameter_key, p):
        #         local_parameter_value_dict[tuple(k)] = v
        #     preds = []
        #     for data in self.model_calibration_request["data"]["value"]:
        #         # parameter setting from front end, without checking
        #         for k, v in zip(self.model_calibration_request["data"]["key"], data):
        #             local_parameter_value_dict[tuple(k)] = v
        #         res = local_simulation(local_parameter_value_dict)
        #         if res:
        #             average = (res[1].reshape(len(streams), len(species), -1) * res[2].reshape(-1, 1, 1)).sum(axis=0)[:, -1] / res[2].sum()
        #         else:
        #             average = np.array([np.nan] * len(species))
        #         preds.append(average)
        #     preds = np.array(preds, dtype=np.float64)
        #     errors = (preds - reals)
        #     mse = (errors[~np.isnan(errors)] ** 2).mean() ** .5
        #     return mse
        # res = differential_evolution(calc_mse, bounds=parameter_bounds, seed=42, maxiter=10, popsize=8, atol=atol, polish=False)
        
        if res:
            response = {
                "parameter": {"key": parameter_key, "value": res.x.tolist()},
                "rmse": res.fun.item() ** 0.5,
            }
            for k, v in zip(parameter_key, res.x.tolist()):
                local_parameter_value_dict[tuple(k)] = v
            results = []
            streams = [s for s in self.model_agent.model_context["basic"]["streams"] 
                    if self.model_agent.model_context["information"]["streams"][s]["state"] == "liquid"]
            species = self.model_agent.model_context["basic"]["species"]
            for data in self.model_calibration_request["data"]["value"]:
                result = []
                # parameter setting from front end, without checking
                for k, v in zip(self.model_calibration_request["data"]["key"], data):
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
            response["simulation"] = results
            return response
        else:
            return None
