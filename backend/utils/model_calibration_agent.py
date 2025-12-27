import os
import pickle
import tempfile

from .model_agent import ModelAgent


class ModelCalibrationAgent:
    """Model calibration agent for optimizing parameters of ordinary/partial differential equations of chemical process models.

    Possible calibration parameters included in the input data:
        - molecular transport-related parameters
        - reaction kinetics-related parameters
    """

    def __init__(self, entity, request):
        self.entity = entity
        self.request = request
        self.model_agent = ModelAgent(entity, request)
    
    def calibrate_scipy(self):
        """Generate and run simulation for data.
            - `scipy_model`: includes`parameter_value_dict`, `derivative`, `boundary` and `simulation`
            - `calibration_parameters`: boundary function for solving
            - `data`: represents input operating parameters
        """
        op_param_dicts = []
        for vals in self.request["op_params"]["val"]:
            op_param_dict = {}
            for op_param_ind, val in zip(self.request["op_params"]["ind"], vals):
                op_param_dict[op_param_ind] = val
            op_param_dicts.append(op_param_dict)
        
        # pheno2law = {}
        # for pheno in self.entity["pheno"]:
        #     pheno2law[pheno] = []
        #     for law, law_dict in self.entity["law"].items():
        #         if law_dict["pheno"] == pheno:
        #             pheno2law[pheno].append(law)
        # law2var = {}
        # for var, var_dict in self.entity["var"].items():
        #     for law in var_dict["laws"]:
        #         law2var[law] = var
        # ac_laws = pheno2law[self.request["context"]["desc"]["ac"]]
        # ac_law = [law for law in ac_laws if law2var[law] != "Concentration"][0]
        # if self.request["context"]["desc"]["ac"] in ["Batch", "Continuous"]:
        #     ivar = self.entity["law"][ac_law]["int_var"]
        # else:
        #     raise ValueError(f"Unsupported accumulation phenomenon: {self.request['context']['desc']['ac']}")
        # spcs = self.request["context"]["basic"]["spc"]
        # n_gas_spc = sum([len(v["spc"]) for v in self.request["context"]["basic"]["gas"].values()])
        # n_sld_spc = sum([len(v["spc"]) for v in self.request["context"]["basic"]["sld"].values()])
        # n_res = len(self.request["reals"]["val"])
        # reals = np.ones((n_res, len(spcs) + n_gas_spc + n_sld_spc), dtype=np.float64)
        # reals = reals * np.nan
        # out_inds = self.model_agent.get_out_inds()

        cal_param_inds = self.request["cal_params"]["ind"]
        cal_param_bounds = self.request["cal_params"]["val"]
        
        model_str = self.model_agent.to_scipy_model()
        with tempfile.TemporaryDirectory() as temp_dir:
            with open(os.path.join(temp_dir, "calibrate.py"), "w") as f:
                f.write(model_str)
                f.write("\n\n")
                f.write(f"op_param_dicts = {op_param_dicts}\n")
                f.write("param_dicts = []\n")
                f.write("for op_param_dict in op_param_dicts:\n")
                f.write("    _param_dict = param_dict.copy()\n")
                f.write("    for ind, val in op_param_dict.items():\n")
                f.write("        _param_dict[ind] = val\n")
                f.write("    param_dicts.append(_param_dict)\n\n")
                f.write(f"cal_param_inds = {cal_param_inds}\n\n")
                f.write(f"reals = {self.request['reals']}\n\n")
                f.writelines([
                    "def calc_mse(p):\n",
                    "    preds = []\n",
                    "    for param_dict in param_dicts:\n",
                    "        for ind, val in zip(cal_param_inds, p):\n",
                    "            param_dict[ind] = val\n",
                    "        res = simulate(param_dict)\n",
                    "        preds.append(res)\n"
                    "    error = 0\n"
                    "    real_inds = reals['ind']\n"
                    "    for real_vals, pred in zip(reals['val'], preds):\n"
                    "        pred_inds = pred['y']['ind']\n"
                    "        pred_vals = pred['y']['val']\n"
                    "        for real_ind, real_val in zip(real_inds, real_vals):\n"
                    "            if (real_ind in pred_inds) and (real_val is not None):\n"
                    "                pred_val = pred_vals[pred_inds.index(real_ind)][-1]\n"
                    "                error += (pred_val - real_val) ** 2\n"
                    "    return error\n\n"
                ])
                f.write("if __name__ == '__main__':\n")
                f.write("    import os\n")
                f.write("    import pickle\n")
                f.write("    res = differential_evolution(calc_mse, "
                        f"bounds={cal_param_bounds}, seed=42, maxiter=20, "
                        "popsize=8, atol=1e-8, updating='deferred', workers=8, "
                        "polish=False, disp=True)\n")
                f.write("    res_dict = {}\n")
                f.write(f"    res_dict['key'] = {cal_param_inds}\n")
                f.write(f"    res_dict['val'] = res.x.round(6).tolist()\n")
                f.write("    pickle.dump(res_dict, open(os.path.join("
                        "os.path.dirname(__file__), 'res.pkl'), 'wb'))\n")
            # with open(os.path.join(temp_dir, "calibrate.py"), "r") as f:
            #     print("".join(f.readlines()))
            os.system(f"python {temp_dir}/calibrate.py")
            res = pickle.load(open(f"{temp_dir}/res.pkl", "rb"))
        return res