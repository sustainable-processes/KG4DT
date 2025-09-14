import os
import pickle
import tempfile

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

        op_param_dicts = []
        for vals in self.request["op_params"]["val"]:
            op_param_dict = {}
            for op_param_ind, val in zip(self.request["op_params"]["ind"], vals):
                op_param_dict[op_param_ind] = val
            op_param_dicts.append(op_param_dict)

        model_str = self.model_agent.to_scipy_model()
        with tempfile.TemporaryDirectory() as temp_dir:
            with open(os.path.join(temp_dir, "simulate.py"), "w") as f:
                f.write(model_str)
                f.write("\n\n")
                f.write(f"op_param_dicts = {op_param_dicts}\n")
                f.write("param_dicts = []\n")
                f.write("for op_param_dict in op_param_dicts:\n")
                f.write("    for ind, val in op_param_dict.items():\n")
                f.write("        param_dict[ind] = val\n")
                f.write("    param_dicts.append(param_dict)\n\n")
                f.write("if __name__ == '__main__':\n")
                f.write("    import os\n")
                f.write("    import pickle\n")
                f.write("    from multiprocessing import Pool\n")
                f.write("    with Pool(8) as pool:\n")
                f.write("        res = pool.map(simulate, param_dicts)\n")
                f.write("        pickle.dump(res, open(os.path.join("
                        "os.path.dirname(__file__), 'res.pkl'), 'wb'))\n")
            # with open(os.path.join(temp_dir, "simulate.py"), "r") as f:
            #     print("".join(f.readlines()))
            # exit(0)
            os.system(f"python {temp_dir}/simulate.py")
            res = pickle.load(open(f"{temp_dir}/res.pkl", "rb"))
        return res