import itertools
import multiprocessing

from .model_calibration_agent import ModelCalibrationAgent


def _calibration_scipy(model_calibration_agent):
    return model_calibration_agent.calibration_scipy()


class ModelExplorationAgent:
    """Model exploration agent for selecting the most fitted ordinary/partial differential equations of chemical process models.

    Possible calibration parameters included during model calibration:
        - molecular transport-related parameters
        - reaction kinetics-related parameters
    """

    def __init__(self, entity, model_exploration_request):
        self.entity = entity
        self.model_exploration_request = model_exploration_request
    
    def exploration_scipy(self):
        """Generate and run calibration for all possible models.
            - `scipy_model`: includes`parameter_value_dict`, `derivative`, `boundary` and `simulation`
            - `calibration_parameters`: boundary function for solving
            - `data`: represents input operating parameters
        """
        flow_pattern_phenomena = self.model_exploration_request["model_context"]["description"]["flow_pattern"]
        all_molecular_transport_phenomena = self.model_exploration_request["model_context"]["description"]["molecular_transport"]
        model_calibration_agents = []
        model_contexts = []
        cand_molecular_transport_phenomena = []
        for i in range(len(all_molecular_transport_phenomena) + 1):
            for phenomena in itertools.combinations(all_molecular_transport_phenomena, i):
                cand_molecular_transport_phenomena.append(list(phenomena))
        for flow_pattern_phenomenon in flow_pattern_phenomena:
            for molecular_transport_phenomena in cand_molecular_transport_phenomena:
                if self.entity["phenomenon"][flow_pattern_phenomenon]["molecular_transport_phenomena"]:
                    if not molecular_transport_phenomena:
                        continue
                    if molecular_transport_phenomena and any([phenomenon not in self.entity["phenomenon"][flow_pattern_phenomenon]["molecular_transport_phenomena"] for phenomenon in molecular_transport_phenomena]):
                        continue
                else:
                    if molecular_transport_phenomena:
                        continue
                parameters = []
                for _, law_dict in self.entity["law"].items():
                    if law_dict["phenomenon"] == flow_pattern_phenomenon:
                        parameters.extend(law_dict["model_variables"])
                    if law_dict["phenomenon"] in molecular_transport_phenomena:
                        parameters.extend(law_dict["model_variables"])
                parameters = [parameter for parameter in parameters if [law for law in self.entity['model_variable'][parameter]['laws'] if self.entity['law'][law]['rule']]]
                phenomena = molecular_transport_phenomena + [flow_pattern_phenomenon]
                parameter_law_dict = {}
                for parameter in parameters:
                    parameter_laws = []
                    for law in self.entity["model_variable"][parameter]["laws"]:
                        if law not in self.model_exploration_request["parameter"]["law"]: continue
                        rule = self.entity["law"][law]["rule"]
                        if all([phenomenon in phenomena for phenomenon in self.entity["rule"][rule]["phenomena"]]):
                            parameter_laws.append(law)
                    if parameter_laws:
                        parameter_law_dict[parameter] = parameter_laws
                if not parameter_law_dict.values(): continue
                for laws in itertools.product(*parameter_law_dict.values()):
                    calibration_parameter = {"key": [], "init": [], "max": [], "min": []}
                    calibration_model_context = {
                        "method": "bottom-up",
                        "basic": {
                            "species": self.model_exploration_request["model_context"]["basic"]["species"],
                            "reactions": self.model_exploration_request["model_context"]["basic"]["reactions"],
                            "streams": self.model_exploration_request["model_context"]["basic"]["streams"],
                            "solvents": self.model_exploration_request["model_context"]["basic"]["solvents"],
                            # "catalysts": self.model_exploration_request["model_context"]["basic"]["catalysts"],
                        },
                        "description": {
                            "accumulation": self.model_exploration_request["model_context"]["description"]["accumulation"],
                            "flow_pattern": flow_pattern_phenomenon,
                            "molecular_transport": molecular_transport_phenomena,
                            "reaction": self.model_exploration_request["model_context"]["description"]["reaction"],
                            "parameter_law": {parameter: law for parameter, law in zip(parameters, laws)},
                        },
                        "information": {
                            "species": self.model_exploration_request["model_context"]["information"]["species"],
                            "reactor": self.model_exploration_request["model_context"]["information"]["reactor"],
                            "streams": self.model_exploration_request["model_context"]["information"]["streams"],
                        }
                    }
                    molecular_transport_info_dict = {}
                    for law in laws:
                        law_parameter_dict = self.model_exploration_request["parameter"]["law"][law]
                        for (parameter, species, reaction, _, solvent), value in zip(law_parameter_dict["key"], law_parameter_dict["init"]):
                            molecular_transport_info_dict[parameter] = value
                        calibration_parameter["key"].extend(law_parameter_dict["key"])
                        calibration_parameter["init"].extend(law_parameter_dict["init"])
                        calibration_parameter["min"].extend(law_parameter_dict["min"])
                        calibration_parameter["max"].extend(law_parameter_dict["max"])
                    reaction_info_dict = {}
                    reaction_parameter_dict = self.model_exploration_request["parameter"]["reaction"]
                    for (parameter, species, reaction, _, solvent), value in zip(reaction_parameter_dict["key"], reaction_parameter_dict["init"]):
                        if reaction not in reaction_info_dict:
                            reaction_info_dict[reaction] = {}
                        if parameter not in reaction_info_dict[reaction]:
                            reaction_info_dict[reaction][parameter] = {}
                        if species != None:
                            reaction_info_dict[reaction][parameter][species] = value
                        if solvent != None:
                            reaction_info_dict[reaction][parameter][solvent] = value
                    calibration_parameter["key"].extend(reaction_parameter_dict["key"])
                    calibration_parameter["init"].extend(reaction_parameter_dict["init"])
                    calibration_parameter["min"].extend(reaction_parameter_dict["min"])
                    calibration_parameter["max"].extend(reaction_parameter_dict["max"])
                    calibration_model_context["information"]["reactions"] = reaction_info_dict
                    calibration_model_context["information"]["molecular_transport"] = molecular_transport_info_dict
                    model_calibration_request = {
                        "task": "calibration",
                        "data": self.model_exploration_request["data"],
                        "parameter": calibration_parameter,
                        "model_type": self.model_exploration_request["model_type"],
                        "model_context": calibration_model_context,
                    }
                    model_contexts.append(calibration_model_context)
                    model_calibration_agents.append(ModelCalibrationAgent(self.entity, model_calibration_request))

        # FOR MULTIPROCESSING
        pool = multiprocessing.Pool(8)
        model_calibration_results = pool.map(_calibration_scipy, model_calibration_agents)
        pool.close()

        # FOR SINGLE PROCESSING
        # model_calibration_results = []
        # for model_calibration_agent in model_calibration_agents:
        #     model_calibration_results.append(model_calibration_agent.calibration_scipy())
        
        return {
            "model_contexts": model_contexts,
            "model_calibration_results": model_calibration_results,
        }
