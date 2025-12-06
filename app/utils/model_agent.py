import re
import json
from .mml_expression import MMLExpression


class ScipyModelCode:
    """Helper of ModelAgent for creating scipy model codes."""

    def __init__(self):
        self.spaces = 4
        self.codes = []

    def add_header(self, model_context):
        self.codes.append('"""')
        self.codes.append("Scipy Model Created by OntoMo")
        self.codes.append("")
        self.codes.append("Model Context:")
        self.codes.extend(json.dumps(model_context, indent=self.spaces).split("\n"))
        self.codes.append('"""')
        self.codes.append("")

    def add_lib(self):
        self.codes.append("import numpy as np")
        self.codes.append("from scipy.optimize import fsolve")
        self.codes.append("from scipy.integrate import solve_bvp, solve_ivp")
        self.codes.append("")
    
    def add_function(self, model_variable, input_symbols, code, level):
        function_head = f"calc_{model_variable.lower().replace('-', '_')}({', '.join(input_symbols)})"
        self.add(f'def {function_head}:', level)
        if "=" not in code.split("\n")[0] and ":" not in code.split("\n")[0]:
            code = code.split("\n")[1:] + code.split("\n")[:1]
        else:
            code = code.split("\n")
        for c in code[:-1]:
            self.add(c, level + 1)
        self.add("return " + code[-1].strip(), level + 1)
        return function_head

    def add(self, code, level):
        if isinstance(code, str):
            self.codes.append(" " * self.spaces * level + code)
        if isinstance(code, list):
            for c in code:
                self.codes.append(" " * self.spaces * level + c)

    def get_model(self):
        return '\n'.join(self.codes)


class PyomoModelCode:
    """Helper of ModelAgent for creating pyomo model codes."""

    def __init__(self):
        self.spaces = 4
        self.codes = []

    def add_header(self, model_context):
        self.codes.append('"""')
        self.codes.append("Pyomo Model Created by OntoMo")
        self.codes.append("")
        self.codes.append("Model Context:")
        self.codes.extend(json.dumps(model_context, indent=self.spaces).split("\n"))
        self.codes.append('"""')
        self.codes.append("")

    def add_lib(self):
        self.codes.append("import numpy as np")
        self.codes.append("from scipy.optimize import fsolve")
        self.codes.append("from pyomo import dae, environ")
        self.codes.append("")
    
    def add_function(self, model_variable, input_symbols, code, level):
        function_head = f"calc_{model_variable.lower().replace('-', '_')}({', '.join(input_symbols)})"
        self.add(f'def {function_head}:', level)
        if "=" not in code.split("\n")[0] and ":" not in code.split("\n")[0]:
            code = code.split("\n")[1:] + code.split("\n")[:1]
        else:
            code = code.split("\n")
        for c in code[:-1]:
            self.add(c, level + 1)
        self.add("return " + code[-1].strip(), level + 1)
        return function_head

    def add(self, code, level):
        if isinstance(code, str):
            self.codes.append(" " * self.spaces * level + code)
        if isinstance(code, list):
            for c in code:
                self.codes.append(" " * self.spaces * level + c)

    def get_model(self):
        return '\n'.join(self.codes)


class JuliaModelCode:
    def __init__(self):
        self.spaces = 4
        self.codes = []

    def add_header(self, model_context):
        self.codes.append('"""')
        self.codes.append("Julia Model Created by OntoMo")
        self.codes.append("")
        self.codes.append("Model Context:")
        self.codes.extend(json.dumps(model_context, indent=self.spaces).split("\n"))
        self.codes.append('"""')
        self.codes.append("")

    def add_lib(self):
        self.codes.append("using DifferentialEquations")
        self.codes.append("using DataStructures")
        self.codes.append("")

    def add_function(self, model_variable, input_symbols, code, level):
        function_head = f"calc_{model_variable.lower().replace('-', '_')}({', '.join(input_symbols)})"
        self.add(f'def {function_head}:', level)
        if "=" not in code.split("\n")[0] and ":" not in code.split("\n")[0]:
            code = code.split("\n")[1:] + code.split("\n")[:1]
        else:
            code = code.split("\n")
        for c in code[:-1]:
            self.add(c, level + 1)
        self.add("return " + code[-1].strip(), level + 1)
        return function_head

    def add(self, code, level):
        if isinstance(code, str):
            self.codes.append(" " * self.spaces * level + code)
        if isinstance(code, list):
            for c in code:
                self.codes.append(" " * self.spaces * level + c)

    def get_model(self):
        return '\n'.join(self.codes)


class ModelAgent:
    """Model agent for generating model based on model context.

    The physical model is derived from given phenomena and parameters, including:
        - mass accumulation
        - flow pattern
        - molecular transport
        - chemical reaction
    
    For `bottom-up` modelling, the json structure is like:
    ```
    {
        "method": "bottom-up",
        "basic": {
            "species":      [],
            "reactions":    [],
            "streams":      [],
            "solvents":     [],
            "catalysts":     [],
        },
        "description": {
            "accumulation":         "",
            "flow_pattern":         "",
            "molecular_transport":  [],
            "reaction":             {"reaction 1": []},
        }, 
        "information": {
            "species":              {"parameter 1": {}},
            "reactor":              {},
            "molecular_transport":  {},
            "streams":              {"stream 1": {"reactions": []}},
            "reactions":            {"reaction 1": {"parameter 1": {}}},
        },
    }
    ```

    Model integration steps:
        - reaction rate
        - molecular transport rate
            - mixing rate
            - mass transfer rate
            - diffusion rate
        - concentration derivative
    """

    def __init__(self, entity, model_context, calibrated_parameter=None):
        self.entity = entity
        self.model_context = model_context
        self.calibrated_parameter = calibrated_parameter
    
    def extract_parameter_value(self):
        parameter_value_dict = {}

        # reaction coefficient parameter
        for r in self.model_context["basic"]["reactions"]:
            lhs_r = r.split(" > ")[0]
            rhs_r = r.split(" > ")[1]
            for item in lhs_r.split(" + "):
                if re.match(r"^\d+$", item.split(" ")[0]):
                    v = -float(item.split(" ")[0])
                    s = " ".join(item.split(" ")[1:])
                else:
                    v = -1.0
                    s = item
                parameter_value_dict[("Coefficient", s, r, None, None)] = v
            for item in rhs_r.split(" + "):
                if re.match(r"^\d+$", item.split(" ")[0]):
                    v = float(item.split(" ")[0])
                    s = " ".join(item.split(" ")[1:])
                else:
                    v = 1.0
                    s = item
                parameter_value_dict[("Coefficient", s, r, None, None)] = v
        
        # species parameter: species charge
        if "species" in self.model_context["information"]:
            for p in self.model_context["information"]["species"]:
                for s in self.model_context["information"]["species"][p]:
                    v = self.model_context["information"]["species"][p][s]
                    parameter_value_dict[(p, s, None, None, None)] = v
        
        # reactor parameter: reactor length, reactor radius, reactor height, reactor width
        if "reactor" in self.model_context["information"]:
            for p in self.model_context["information"]["reactor"]:
                v = self.model_context["information"]["reactor"][p]
                parameter_value_dict[(p, None, None, None, None)] = v

        # molecular transport paramter: mixing time slope, mass transfer coefficient
        if "molecular_transport" in self.model_context["information"]:
            for p in self.model_context["information"]["molecular_transport"]:
                dimensions = self.entity["model_variable"][p]["dimensions"]
                if "Species" not in dimensions:
                    v = self.model_context["information"]["molecular_transport"][p]
                    parameter_value_dict[(p, None, None, None, None)] = v
                if "Species" in dimensions and "Stream" not in dimensions:
                    for species in self.model_context["information"]["molecular_transport"][p]:
                        v = self.model_context["information"]["molecular_transport"][p][species]
                        parameter_value_dict[(p, species, None, None, None)] = v
                if "Stream" in dimensions and "Species" in dimensions:
                    for stream in self.model_context["information"]["molecular_transport"][p]:
                        for species in self.model_context["information"]["molecular_transport"][p][stream]:
                            v = self.model_context["information"]["molecular_transport"][p][stream][species]
                            parameter_value_dict[(p, species, None, stream, None)] = v
        
        # stream parameter: flow rate, density, viscosity, ionicity
        if "streams" in self.model_context["information"]:
            for s in self.model_context["information"]["streams"]:
                for p in self.model_context["information"]["streams"][s]:
                    v = self.model_context["information"]["streams"][s][p]
                    # exclude stream state, solvent, etc.
                    if p in self.entity["model_variable"]:
                        parameter_value_dict[(p, None, None, s, None)] = v

        # reaction parameter: activation energy, partial order, pre-exponential factor, rate constant
        if "reactions" in self.model_context["information"]:
            for r in self.model_context["information"]["reactions"]:
                for p in self.model_context["information"]["reactions"][r]:
                    if p not in self.entity["model_variable"]: continue
                    dimensions = self.entity["model_variable"][p]["dimensions"]
                    if set(dimensions) == set(["Reaction"]):
                        v = self.model_context["information"]["reactions"][r][p]
                        parameter_value_dict[(p, None, r, None, None)] = v
                    if set(dimensions) == set(["Reaction", "Solvent"]):
                        for s in self.model_context["information"]["reactions"][r][p]:
                            v = self.model_context["information"]["reactions"][r][p][s]
                            parameter_value_dict[(p, None, r, None, s)] = v
                    if set(dimensions) == set(["Species", "Reaction"]):
                        for s in self.model_context["information"]["reactions"][r][p]:
                            v = self.model_context["information"]["reactions"][r][p][s]
                            parameter_value_dict[(p, s, r, None, None)] = v
        
        if self.calibrated_parameter:
            for k, v in zip(self.calibrated_parameter["key"], self.calibrated_parameter["value"]):
                parameter_value_dict[tuple(k)] = v

        # operating parameter (placeholder): flow rate, temperature, initial concentration
        phenomena = \
            [self.model_context["description"]["accumulation"]] + \
            [self.model_context["description"]["flow_pattern"]] + \
            [p for p in self.model_context["description"]["molecular_transport"]] + \
            [p for r in self.model_context["description"]["reaction"] for p in self.model_context["description"]["reaction"][r]]
        laws = [l for l in self.entity["law"] if self.entity["law"][l]["phenomenon"] in phenomena]
        parameters = list(set([p for l in laws for p in self.entity["law"][l]["model_variables"]]))
        operating_parameters = [p for p in parameters if self.entity["model_variable"][p]["class"] == "OperatingParameter"]
        liquid_streams = [s for s, d in self.model_context["information"]["streams"].items() if d["state"] == "liquid"]
        gaseous_streams = [s for s, d in self.model_context["information"]["streams"].items() if d["state"] == "gaseous"]
        for p in operating_parameters:
            dimensions = self.entity["model_variable"][p]["dimensions"]
            if "Species" not in dimensions and "Stream" not in dimensions:
                parameter_value_dict[(p, None, None, None, None)] = None
            if "Species" not in dimensions and "Stream" in dimensions:
                if "Gas" in p:
                    for s in gaseous_streams:
                        parameter_value_dict[(p, None, None, s, None)] = None
                if "Gas" not in p:
                    for s in liquid_streams:
                        parameter_value_dict[(p, None, None, s, None)] = None
            if "Stream" in dimensions and "Species" in dimensions:
                if "Gas" not in p:
                    for s in liquid_streams:
                        for sp in self.model_context["basic"]["species"]:
                            parameter_value_dict[(p, sp, None, s, None)] = None
        
        return parameter_value_dict


    def to_flowchart(self):
        # accumulation -> parameter / rate_variable -> parameter
        flowchart = {"chart": [[], [], []], "link": []}
        
        accumulation_chart = {}
        phenomenon = self.model_context["description"]["accumulation"]
        law = [l for l in self.entity["law"] if self.entity["law"][l]["phenomenon"] == phenomenon][0]
        accumulation_parameters = self.entity["law"][law]["model_variables"]
        accumulation_symbols = [self.entity["model_variable"][p]["symbol"].strip() for p in accumulation_parameters]
        molecular_transport_phenomena = self.model_context["description"]["molecular_transport"]
        parameter_law = self.model_context["description"]["parameter_law"]
        reaction_phenomena = list(set([p for r in self.model_context["description"]["reaction"] for p in self.model_context["description"]["reaction"][r]]))
        accumulation_optional_parameters = []
        accumulation_optional_symbols = []
        for p in self.entity["law"][law]["optional_model_variables"]:
            if (len([l for l in self.entity["model_variable"][p]["laws"] if self.entity["law"][l]["phenomenon"] in molecular_transport_phenomena + reaction_phenomena])):
                accumulation_optional_parameters.append(p)
                accumulation_optional_symbols.append(re.sub(r"> *<", "><", self.entity["model_variable"][p]["symbol"].replace("\n", "")))
        accumulation_formula = self.entity["law"][law]["formula"]
        for k in accumulation_formula:
            accumulation_formula[k] = re.sub(r"> *<", "><", accumulation_formula[k].strip().replace("\n", ""))
            for accumulation_optional_term in re.findall(r'<mrow><mo>\[</mo>[^\[\]]*<mo>\]</mo></mrow>', accumulation_formula[k]):
                if len([s for s in accumulation_optional_symbols if s.replace("<math><mrow>", "").replace("</mrow></math>", "") in accumulation_optional_term]) == 0:
                    accumulation_formula[k] = accumulation_formula[k].replace("<mo>+</mo>" + accumulation_optional_term, "")
                    accumulation_formula[k] = accumulation_formula[k].replace(accumulation_optional_term + "<mo>+</mo>", "")
            accumulation_formula[k] = accumulation_formula[k].replace("<mo>[</mo>", "").replace("<mo>]</mo>", "")
        if phenomenon == "Continuous":
            accumulation_chart["target_parameter"] = "Concentration_Derivative"
            accumulation_chart["target_symbol"] = "<math><mrow><mrow><mi>d</mi><mi>c</mi></mrow><mo>/</mo><mrow><mi>d</mi><mi>x</mi></mrow></mrow></math>"
        if phenomenon == "Batch":
            accumulation_chart["target_parameter"] = "Concentration_Derivative"
            accumulation_chart["target_symbol"] = "<math><mrow><mrow><mi>d</mi><mi>c</mi></mrow><mo>/</mo><mrow><mi>d</mi><mi>t</mi></mrow></mrow></math>"
        if phenomenon == "CSTR":
            accumulation_chart["target_parameter"] = "Concentration"
            accumulation_chart["target_symbol"] = "<math><mrow><mi>c</mi></mrow></math>"
        accumulation_chart["phenomena"] = [phenomenon]
        accumulation_chart["parameters"] = accumulation_parameters + accumulation_optional_parameters
        accumulation_chart["symbols"] = accumulation_symbols + accumulation_optional_symbols
        accumulation_chart["formula"] = accumulation_formula
        flowchart["chart"][0].append(accumulation_chart)
        
        phenomenon = self.model_context["description"]["flow_pattern"]
        target_parameters = []
        laws = []
        flow_pattern_parameters = []
        for p in accumulation_parameters:
            for l in self.entity["model_variable"][p]["laws"]:
                if self.entity["law"][l]["phenomenon"] == phenomenon:
                    target_parameters.append(p)
                    laws.append(l)
        for target_parameter, law in zip(target_parameters, laws):
            flow_pattern_chart = {}
            flow_pattern_chart["target_parameter"] = target_parameter
            flow_pattern_chart["target_symbol"] = self.entity["model_variable"][target_parameter]["symbol"]
            flow_pattern_chart["phenomena"] = [phenomenon]
            flow_pattern_chart["parameters"] = self.entity["law"][law]["model_variables"]
            flow_pattern_chart["symbols"] = [self.entity["model_variable"][p]["symbol"].strip() for p in self.entity["law"][law]["model_variables"]]
            flow_pattern_chart["formula"] = self.entity["law"][law]["formula"]
            flowchart["chart"][1].append(flow_pattern_chart)
            flowchart["link"].append(((0, 0), (1, len(flowchart["chart"][1]) - 1)))
            flow_pattern_parameters.extend(self.entity["law"][law]["model_variables"])
        flow_pattern_parameters = list(set(flow_pattern_parameters))

        phenomena = self.model_context["description"]["molecular_transport"]
        target_parameters = []
        laws = []
        molecular_transport_parameters = []
        for p in accumulation_optional_parameters:
            for l in self.entity["model_variable"][p]["laws"]:
                if self.entity["law"][l]["phenomenon"] in phenomena:
                    target_parameters.append(p)
                    laws.append(l)
        for target_parameter, law in zip(target_parameters, laws):
            molecular_transport_chart = {}
            molecular_transport_chart["target_parameter"] = target_parameter
            molecular_transport_chart["target_symbol"] = self.entity["model_variable"][target_parameter]["symbol"]
            molecular_transport_chart["phenomena"] = [self.entity["law"][law]["phenomenon"]]
            molecular_transport_chart["parameters"] = self.entity["law"][law]["model_variables"]
            molecular_transport_chart["symbols"] = [self.entity["model_variable"][p]["symbol"].strip() for p in self.entity["law"][law]["model_variables"]]
            molecular_transport_chart["formula"] = self.entity["law"][law]["formula"]
            flowchart["chart"][1].append(molecular_transport_chart)
            flowchart["link"].append(((0, 0), (1, len(flowchart["chart"][1]) - 1)))
            molecular_transport_parameters.extend(self.entity["law"][law]["model_variables"])
        molecular_transport_parameters = list(set(molecular_transport_parameters))

        reaction_parameters = []
        for reaction in self.model_context["description"]["reaction"]:
            phenomena = self.model_context["description"]["reaction"][reaction]
            target_parameters = []
            laws = []
            for p in accumulation_optional_parameters:
                for l in self.entity["model_variable"][p]["laws"]:
                    if self.entity["law"][l]["phenomenon"] in phenomena:
                        target_parameters.append(p)
                        laws.append(l)
            reaction_chart = {}
            reaction_chart["target_parameter"] = None
            reaction_chart["target_symbol"] = None
            reaction_chart["phenomena"] = []
            reaction_chart["parameters"] = []
            reaction_chart["symbols"] = []
            reaction_chart["formula"] = []
            reaction_chart["reaction"] = reaction
            for target_parameter, law in zip(target_parameters, laws):
                reaction_chart["target_parameter"] = target_parameter
                reaction_chart["target_symbol"] = self.entity["model_variable"][target_parameter]["symbol"]
                reaction_chart["phenomena"].append(self.entity["law"][law]["phenomenon"])
                if self.entity["law"][law]["phenomenon"] == "Instantaneous": continue
                reaction_chart["parameters"].extend(self.entity["law"][law]["model_variables"])
                # hide subscript operation
                if self.entity["phenomenon"][self.entity["law"][law]["phenomenon"]]["class"] == "ChemicalReactionPhenomenon":
                    symbols = [self.entity["model_variable"][p]["symbol"] for p in self.entity["law"][law]["model_variables"] if p != "Coefficient"]
                else:
                    symbols = [self.entity["model_variable"][p]["symbol"] for p in self.entity["law"][law]["model_variables"]]
                reaction_chart["symbols"].extend(symbols)
                formula = self.entity["law"][law]["formula"]
                # hide subscript operation
                for k in formula:
                    if formula[k]:
                        formula[k] = re.sub(r'<mo>\[</mo>[^\[\]]*<mo>(&lt;|&gt;)</mo>[^\[\]]*<mo>\]</mo>', '', formula[k])
                if "specifically defined" in formula["detail_formula"]:
                    formula["concise_formula"] = f'<math><mrow><mtext>fun</mtext><mfenced><mrow>{"<mtext>,&nbsp;</mtext>".join([s.replace("<math>", "").replace("</math>", "") for s in symbols])}</mrow></mfenced></mrow></math>'
                    formula["detail_formula"] = f'<div style="white-space: pre-line; color: gray;">{self.model_context["information"]["reactions"][reaction][self.entity["law"][law]["phenomenon"]].replace(" ", "&nbsp;")}</div>'
                reaction_chart["formula"].append(self.entity["law"][law]["formula"])
            reaction_chart["parameters"] = list(set(reaction_chart["parameters"]))
            reaction_chart["symbols"] = [symbol.strip() for symbol in list(set(reaction_chart["symbols"]))]
            detail_formulas = [f["detail_formula"] for f in reaction_chart["formula"] if f["detail_formula"]]
            reaction_chart["formula"] = {
                "concise_formula": "<math><mo>×</mo></math>".join([f["concise_formula"] for f in reaction_chart["formula"] if f["concise_formula"]]),
                "detail_formula": "".join(detail_formulas) if detail_formulas else None,
            }
            flowchart["chart"][1].append(reaction_chart)
            flowchart["link"].append(((0, 0), (1, len(flowchart["chart"][1]) - 1)))
            reaction_parameters.extend(reaction_chart["parameters"])
        reaction_parameters = list(set(reaction_parameters))

        parameters = []
        laws = []
        for p in flow_pattern_parameters + molecular_transport_parameters + reaction_parameters:
            if self.entity["model_variable"][p]["definition"]:
                parameters.append(p)
                laws.append(self.entity["model_variable"][p]["definition"])
            if self.entity["model_variable"][p]["laws"]:
                if p in parameter_law:
                    l = parameter_law[p]
                    parameters.append(p)
                    laws.append(l)
        for target_parameter, law in zip(parameters, laws):
            parameter_chart = {}
            parameter_chart["target_parameter"] = target_parameter
            parameter_chart["target_symbol"] = self.entity["model_variable"][target_parameter]["symbol"]
            if law in self.entity["definition"]:
                parameter_chart["phenomena"] = []
                parameter_chart["parameters"] = self.entity["definition"][law]["model_variables"]
                parameter_chart["symbols"] = [self.entity["model_variable"][p]["symbol"].strip() for p in parameter_chart["parameters"]]
                parameter_chart["formula"] = self.entity["definition"][law]["formula"]
                flowchart["chart"][2].append(parameter_chart)
            if law in self.entity["law"]:
                parameter_chart["phenomena"] = [self.entity["law"][law]["phenomenon"]]
                parameter_chart["parameters"] = self.entity["law"][law]["model_variables"]
                parameter_chart["symbols"] = [self.entity["model_variable"][p]["symbol"].strip() for p in parameter_chart["parameters"]]
                parameter_chart["formula"] = self.entity["law"][law]["formula"]
                parameter_chart["doi"] = self.entity["law"][law]["doi"]
                if not parameter_chart["formula"]["concise_formula"]:
                    parameter_chart["formula"]["concise_formula"] = f'<math><mrow><mtext>fun</mtext><mo>(</mo><mrow>{"<mtext>,&nbsp;</mtext>".join([s.replace("<math>", "").replace("</math>", "") for s in parameter_chart["symbols"]])}</mrow><mo>)</mo></mrow></math>'
                flowchart["chart"][2].append(parameter_chart)
        for i, chart in enumerate(flowchart["chart"][1]):
            for j, parameter in enumerate(parameters):
                if parameter in chart["parameters"]:
                    flowchart["link"].append(((1, i), (2, j)))
        for i, chart in enumerate(flowchart["chart"][2]):
            for j, parameter in enumerate(parameters):
                if parameter in chart["parameters"]:
                    flowchart["link"].append(((2, i), (2, j)))
        for i, chart1 in enumerate(flowchart["chart"][1]):
            for j, chart2 in enumerate(flowchart["chart"][2]):
                if chart1["target_parameter"] in chart2["parameters"]:
                    flowchart["link"].append(((2, j), (1, i)))

        return flowchart


    def to_scipy_model(self):
        """The converted scipy model is given as:
        
        parameter_value_dict: `{(parameter, species, reaction, stream, solvent): value}`
        def simulation(parameter_value_dict):
            p = list(parameter_value_dict.values())
            def derivative(c, x):
            def boundary(c_a, c_b):
            res = solve_bvp(derivative, boundary, x_init, c_init)
            return res.x, post_process(res.y)

        Returns:
            str: converted scipy model
        """

        scipy_model_code = ScipyModelCode()
        # scipy_model_code.add_header(self.model_context)
        scipy_model_code.add_lib()

        # parameter_value_dict
        parameter_value_dict = self.extract_parameter_value()
        scipy_model_code.add("parameter_value_dict = {", 0)
        for k, v in parameter_value_dict.items():
            scipy_model_code.add(f"{k}: {v},", 1)
        scipy_model_code.add("}", 0)
        scipy_model_code.add("", 0)

        # law identification
        # start from accumulation phenomenon
        # flow pattern laws -> subsidiary flow pattern laws
        accumulation_phenomenon = self.model_context["description"]["accumulation"]
        flow_pattern_phenomenon = self.model_context["description"]["flow_pattern"]
        molecular_transport_phenomena = self.model_context["description"]["molecular_transport"]
        parameter_law = self.model_context["description"]["parameter_law"]
        reaction_phenomena = self.model_context["description"]["reaction"]
        accumulation_law = [l for l in self.entity["law"] if self.entity["law"][l]["phenomenon"] == accumulation_phenomenon][0]
        accumulation_model_variables = self.entity["law"][accumulation_law]["model_variables"]
        molecular_transport_laws = [l for l in self.entity["law"] if self.entity["law"][l]["phenomenon"] in molecular_transport_phenomena]
        molecular_transport_model_variables = list(set([mv for l in molecular_transport_laws for mv in self.entity["law"][l]["model_variables"]]))
        flow_pattern_laws = [l for l in self.entity["law"] for mv in accumulation_model_variables if l in self.entity["model_variable"][mv]["laws"] and self.entity["law"][l]["phenomenon"] == flow_pattern_phenomenon] + \
            [parameter_law[mv] for mv in molecular_transport_model_variables if self.entity["model_variable"][mv]["laws"]]
        sub_flow_pattern_laws = [parameter_law[p] for p in set([mv for l in flow_pattern_laws for mv in self.entity["law"][l]["model_variables"] if [
            l for l in self.entity["model_variable"][mv]["laws"] if self.entity["law"][l]["rule"]]])]
        flow_pattern_model_variables = list(set([mv for l in flow_pattern_laws + sub_flow_pattern_laws for mv in self.entity["law"][l]["model_variables"]]))
        reaction_laws = {r: [l for l in self.entity["law"] if self.entity["law"][l]["phenomenon"] in p] for r, p in reaction_phenomena.items()}
        reaction_model_variables = {r: list(set([mv for l in ls for mv in self.entity["law"][l]["model_variables"]])) for r, ls in reaction_laws.items()}
        formula_integrated_with_accumulation = [self.entity["law"][l]["formula_integrated_with_accumulation"] for l in molecular_transport_laws if self.entity["law"][l]["formula_integrated_with_accumulation"]]
        if formula_integrated_with_accumulation:
            formula_integrated_with_accumulation = formula_integrated_with_accumulation[0]
        else:
            formula_integrated_with_accumulation = None
        model_variables = accumulation_model_variables + molecular_transport_model_variables + flow_pattern_model_variables + [mv for r in reaction_model_variables for mv in reaction_model_variables[r]]
        definitions = [self.entity["model_variable"][mv]["definition"] for mv in model_variables if self.entity["model_variable"][mv]["definition"]]
        model_variables = model_variables + [mv for d in definitions for mv in self.entity["definition"][d]["model_variables"]]
        if self.model_context["basic"]["reactions"]:
            model_variables += ["Coefficient"]
        model_variables = list(set(model_variables))

        # model basics
        parameter_value_keys = list(parameter_value_dict.keys())
        species = self.model_context["basic"]["species"]
        reactions = self.model_context["basic"]["reactions"]
        liquid_streams = [k for k, v in self.model_context["information"]["streams"].items() if v["state"] == "liquid"]
        gas_streams = [k for k, v in self.model_context["information"]["streams"].items() if v["state"] == "gaseous"]
        solvents = self.model_context["basic"]["solvents"]
        if self.model_context["description"]["accumulation"] in ["Continuous", "Batch"]:
            differential_model_variable = self.entity["law"][accumulation_law]["differential_model_variable"]
            differential_model_variable_symbol = MMLExpression(self.entity["model_variable"][differential_model_variable]['symbol']).to_numpy().strip()

        # simulation function head
        scipy_model_code.add("def simulation(parameter_value_dict):", 0)
        scipy_model_code.add("# PARAMETER PART", 1)
        scipy_model_code.add("p = list(parameter_value_dict.values())", 1)

        # parameter setup
        for model_variable in model_variables:
            symbol = MMLExpression(self.entity["model_variable"][model_variable]["symbol"]).to_numpy()
            model_variable_class = self.entity["model_variable"][model_variable]["class"]
            
            if model_variable_class == "Constant":
                scipy_model_code.add(f'{symbol} = {self.entity["model_variable"][model_variable]["value"]}', 1)
            if "Parameter" not in model_variable_class: continue
            
            model_variable_laws = self.entity["model_variable"][model_variable]["laws"]
            model_variable_definition = self.entity["model_variable"][model_variable]["definition"]
            if model_variable_definition or model_variable_laws: continue
            
            model_variable_dimensions = self.entity["model_variable"][model_variable]["dimensions"]
            if set(model_variable_dimensions) == set([]):
                scipy_model_code.add(f'{symbol} = p[{parameter_value_keys.index((model_variable, None, None, None, None))}]', 1)
            if set(model_variable_dimensions) == set(["Reaction"]):
                scipy_model_code.add(f"{symbol} = np.zeros(({len(reactions)}), dtype=np.float64)", 1)
                for i, r in enumerate(reactions):
                    if (model_variable, None, r, None, None) not in parameter_value_keys: continue
                    scipy_model_code.add(f'{symbol}[{i}] = p[{parameter_value_keys.index((model_variable, None, r, None, None))}]', 1)
            if set(model_variable_dimensions) == set(["Reaction", "Solvent"]):
                scipy_model_code.add(f"{symbol} = np.zeros(({len(reactions)}, {len(solvents)}), dtype=np.float64)", 1)
                for i, r in enumerate(reactions):
                    for j, s in enumerate(solvents):
                        if (model_variable, None, r, None, s) not in parameter_value_keys: continue
                        scipy_model_code.add(f'{symbol}[{i}][{j}] = p[{parameter_value_keys.index((model_variable, None, r, None, s))}]', 1)
            if set(model_variable_dimensions) == set(["Species"]):
                scipy_model_code.add(f"{symbol} = np.zeros(({len(species)}, ), dtype=np.float64)", 1)
                for i, s in enumerate(species):
                    scipy_model_code.add(f'{symbol}[{i}] = p[{parameter_value_keys.index((model_variable, s, None, None, None))}]', 1)
            if set(model_variable_dimensions) == set(["Species", "Reaction"]):
                scipy_model_code.add(f"{symbol} = np.zeros(({len(reactions)}, {len(species)}), dtype=np.float64)", 1)
                for i, r in enumerate(reactions):
                    for j, s in enumerate(species):
                        if (model_variable, s, r, None, None) not in parameter_value_keys: continue
                        scipy_model_code.add(f'{symbol}[{i}][{j}] = p[{parameter_value_keys.index((model_variable, s, r, None, None))}]', 1)
            if set(model_variable_dimensions) == set(["Stream"]):
                if "Gas" not in model_variable:
                    scipy_model_code.add(f"{symbol} = np.zeros(({len(liquid_streams)}, ), dtype=np.float64)", 1)
                    for i, s in enumerate(liquid_streams):
                        if (model_variable, None, None, s, None) not in parameter_value_keys: continue
                        scipy_model_code.add(f'{symbol}[{i}] = p[{parameter_value_keys.index((model_variable, None, None, s, None))}]', 1)
                else:
                    scipy_model_code.add(f"{symbol} = np.zeros(({len(gas_streams)}, ), dtype=np.float64)", 1)
                    for i, s in enumerate(gas_streams):
                        if (model_variable, None, None, s, None) not in parameter_value_keys: continue
                        scipy_model_code.add(f'{symbol}[{i}] = p[{parameter_value_keys.index((model_variable, None, None, s, None))}]', 1)
            if set(model_variable_dimensions) == set(["Stream", "Species"]):
                scipy_model_code.add(f"{symbol} = np.zeros(({len(liquid_streams)}, {len(species)}), dtype=np.float64)", 1)
                for i, s in enumerate(liquid_streams):
                    for j, sp in enumerate(species):
                        if (model_variable, sp, None, s, None) not in parameter_value_keys: continue
                        scipy_model_code.add(f'{symbol}[{i}][{j}] = p[{parameter_value_keys.index((model_variable, sp, None, s, None))}]', 1)
            # unit processing
            if self.entity["model_variable"][model_variable]["unit"] and self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["standard_unit"]:
                scipy_model_code.add(f'{symbol} *= {self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["ratio_to_standard_unit"]}', 1)
        scipy_model_code.add("", 0)

        # flow pattern (parameter irrelevant with variable)
        scipy_model_code.add("# FLOW PATTERN PART", 1)
        for law in sub_flow_pattern_laws:
            model_variables = self.entity["law"][law]["model_variables"]
            symbols = [MMLExpression(self.entity["model_variable"][mv]["symbol"]).to_numpy() for mv in model_variables]
            for model_variable in [mv for mv in self.entity["model_variable"] if law in self.entity["model_variable"][mv]["laws"]]:
                symbol = MMLExpression(self.entity["model_variable"][model_variable]["symbol"]).to_numpy()
                code = MMLExpression(self.entity["law"][law]["formula"]).to_numpy()
                if "\n" in code:
                    function_head = scipy_model_code.add_function(model_variable, symbols, code, 1)
                    scipy_model_code.add(f"{symbol} = {function_head}", 1)
                else:
                    scipy_model_code.add(f"{symbol} = {code}", 1)
                scipy_model_code.add("", 0)
        for law in flow_pattern_laws:
            law_model_variables = self.entity["law"][law]["model_variables"]
            law_symbols = [MMLExpression(self.entity["model_variable"][mv]["symbol"]).to_numpy() for mv in law_model_variables]
            for model_variable in [mv for mv in self.entity["model_variable"] if law in self.entity["model_variable"][mv]["laws"]]:
                symbol = MMLExpression(self.entity["model_variable"][model_variable]["symbol"]).to_numpy()
                code = MMLExpression(self.entity["law"][law]["formula"]).to_numpy()
                if "\n" in code:
                    function_head = scipy_model_code.add_function(model_variable, law_symbols, code, 1)
                    scipy_model_code.add(f"{symbol} = {function_head}", 1)
                else:
                    scipy_model_code.add(f"{symbol} = {code}", 1)
                scipy_model_code.add("", 0)
        scipy_model_code.add("", 0)

        # concentration axial position derivative function
        if self.model_context["description"]["accumulation"] == "Continuous":
            scipy_model_code.add(f"def derivative({differential_model_variable_symbol}, c):", 1)
            if formula_integrated_with_accumulation:
                scipy_model_code.add(f"c = np.array(c, dtype=np.float64).reshape({len(liquid_streams)}, {len(species) * 2})", 2)
            else:
                scipy_model_code.add(f"c = np.array(c, dtype=np.float64).reshape({len(liquid_streams)}, {len(species)})", 2)
        # concentration axial position derivative function
        if self.model_context["description"]["accumulation"] == "Batch":
            scipy_model_code.add(f"def derivative({differential_model_variable_symbol}, c):", 1)
            scipy_model_code.add(f"c = np.array(c, dtype=np.float64).reshape({len(liquid_streams)}, {len(species)})", 2)
        # concentration error function
        if self.model_context["description"]["accumulation"] == "CSTR":
            scipy_model_code.add(f"def conversion(c):", 1)
            if self.model_context["description"]["flow_pattern"] == "Well_Mixed":
                scipy_model_code.add(f"_c_0 = (c_0 * q.reshape(-1, 1)).sum(axis=0) / q.sum()", 2)
                scipy_model_code.add(f"c = np.array(c, dtype=np.float64).reshape(1, {len(species)})", 2)
        scipy_model_code.add("", 0)

        # reaction part
        scipy_model_code.add("# REACTION PART", 2)
        reaction_rate_symbol = MMLExpression(self.entity["model_variable"]["Reaction_Rate"]["symbol"]).to_numpy()
        scipy_model_code.add(f'{reaction_rate_symbol} = np.zeros(({len(liquid_streams)}, {len(reactions)}), dtype=np.float64)', 2)
        scipy_model_code.add("", 0)
        definition_model_variables = list(set([mv for laws in reaction_laws.values() for l in laws for mv in self.entity["law"][l]["model_variables"] if self.entity["model_variable"][mv]["definition"]]))
        definition_parameters = [self.entity["model_variable"][mv] for mv in definition_model_variables]
        for definition_parameter in definition_parameters:
            definition_dimensions = definition_parameter["dimensions"]
            symbol = MMLExpression(definition_parameter["symbol"]).to_numpy()
            formula = MMLExpression(self.entity["definition"][definition_parameter["definition"]]["formula"]).to_numpy()
            if "Stream" not in definition_dimensions:
                scipy_model_code.add(f'{symbol} = {formula}', 2)
            else:
                scipy_model_code.add(f'{symbol} = np.zeros(({len(liquid_streams)}, ), dtype=np.float64)', 2)
                model_variables = list(set([mv for mv in self.entity["definition"][definition_parameter["definition"]]["model_variables"]]))
                parameters = [self.entity["model_variable"][mv] for mv in model_variables]
                symbols = [MMLExpression(p["symbol"]).to_numpy() for p in parameters]
                for stream_index, stream in enumerate(liquid_streams):
                    for p, s in zip(parameters, symbols):
                        if "Stream" in p["dimensions"]:
                            formula = re.sub(f'-{s} ', f'-{s}[{stream_index}] ', formula)
                            formula = re.sub(f'{s},', f'{s}[{stream_index}],', formula)
                            formula = re.sub(f' {s}\)', f' {s}[{stream_index}])', formula)
                            formula = re.sub(f'\({s} ', f'({s}[{stream_index}] ', formula)
                            formula = re.sub(f' {s} ', f' {s}[{stream_index}] ', formula)
                            formula = re.sub(f'^{s}$', f'{s}[{stream_index}]', formula)
                            formula = re.sub(f'\[{s}', f'[{s}[{stream_index}]', formula)
                            formula = re.sub(f'{s}(\[[^ <>\[\]]+(\[[:0-9]+\])* [<>] 0\])', f'{s}[{stream_index}]\\1', formula)
                    scipy_model_code.add(f'{symbol}[{stream_index}] = {formula}', 2)
        scipy_model_code.add("", 0)
        for stream_index, stream in enumerate(liquid_streams):
            for reaction_index, reaction in enumerate(reactions):
                if reaction not in self.model_context["information"]["streams"][stream]["reactions"]: continue
                solvent_index = solvents.index(self.model_context["information"]["streams"][stream]["solvent"])
                scipy_model_code.add(f"# stream: {stream}  reaction: {reaction}", 2)
                laws = reaction_laws[reaction]
                reaction_formulas = [self.entity["law"][l]["formula"] for l in laws if "specifically defined" not in self.entity["law"][l]["formula"]]
                reaction_formulas = [MMLExpression(f).to_numpy() for f in reaction_formulas]
                parameters = [self.entity["model_variable"][mv] for l in laws for mv in self.entity["law"][l]["model_variables"]]
                symbols = [MMLExpression(p["symbol"]).to_numpy() for p in parameters]
                
                reaction_special_laws = [l for l in laws if "specifically defined" in self.entity["law"][l]["formula"]]
                reaction_special_phenomena = [self.entity["law"][l]["phenomenon"] for l in reaction_special_laws]
                reaction_special_formulas = [self.model_context["information"]["reactions"][reaction][p] for p in reaction_special_phenomena]
                for phenomenon, formula, law in zip(reaction_special_phenomena, reaction_special_formulas, reaction_special_laws):
                    special_parameters = [self.entity["model_variable"][mv] for mv in self.entity["law"][law]["model_variables"]]
                    special_symbols = [MMLExpression(p["symbol"]).to_numpy() for p in special_parameters]
                    formula_fun = f'calc_reaction_term_{phenomenon.lower().replace("-", "_")}({", ".join(special_symbols)})'
                    formula = [s if '=' in s or ':' in s else re.sub('^( *)([^ ].*)$', r'\1return \2', s) for s in formula.split('\n')]
                    scipy_model_code.add("def " + formula_fun + ":", 2)
                    scipy_model_code.add(formula, 3)
                    reaction_formulas.append(formula_fun)
                
                for p, s in zip(parameters, symbols):
                    if "Stream" in p["dimensions"] and "Species" not in p["dimensions"]:
                        reaction_formulas = [re.sub(f'-{s} ', f'-{s}[{stream_index}] ', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'{s},', f'{s}[{stream_index}],', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f' {s}\)', f' {s}[{stream_index}])', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'\({s} ', f'({s}[{stream_index}] ', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'\({s}\)', f'({s}[{stream_index}])', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f' {s} ', f' {s}[{stream_index}] ', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'^{s}$', f'{s}[{stream_index}]', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'\[{s}', f'[{s}[{stream_index}]', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'{s}(\[[^ <>\[\]]+(\[[:0-9]+\])* [<>] 0\])', f'{s}[{stream_index}]\\1', f) for f in reaction_formulas]
                    if "Stream" in p["dimensions"] and "Species" in p["dimensions"]:
                        if formula_integrated_with_accumulation:
                            reaction_formulas = [re.sub(f'-{s} ', f'-{s}[{stream_index}][:{len(species)}] ', f) for f in reaction_formulas]
                            reaction_formulas = [re.sub(f'{s},', f'{s}[{stream_index}][:{len(species)}],', f) for f in reaction_formulas]
                            reaction_formulas = [re.sub(f' {s}\)', f' {s}[{stream_index}][:{len(species)}])', f) for f in reaction_formulas]
                            reaction_formulas = [re.sub(f'\({s} ', f'({s}[{stream_index}][:{len(species)}] ', f) for f in reaction_formulas]
                            reaction_formulas = [re.sub(f'\({s}\)', f'({s}[{stream_index}][:{len(species)}])', f) for f in reaction_formulas]
                            reaction_formulas = [re.sub(f' {s} ', f' {s}[{stream_index}][:{len(species)}] ', f) for f in reaction_formulas]
                            reaction_formulas = [re.sub(f'^{s}$', f'{s}[{stream_index}][:{len(species)}]', f) for f in reaction_formulas]
                            reaction_formulas = [re.sub(f'\[{s}', f'[{s}[{stream_index}][:{len(species)}]', f) for f in reaction_formulas]
                            reaction_formulas = [re.sub(f'{s}(\[[^ <>\[\]]+(\[[:0-9]+\])* [<>] 0\])', f'{s}[{stream_index}][:{len(species)}]\\1', f) for f in reaction_formulas]
                        else:
                            reaction_formulas = [re.sub(f'-{s} ', f'-{s}[{stream_index}] ', f) for f in reaction_formulas]
                            reaction_formulas = [re.sub(f'{s},', f'{s}[{stream_index}],', f) for f in reaction_formulas]
                            reaction_formulas = [re.sub(f' {s}\)', f' {s}[{stream_index}])', f) for f in reaction_formulas]
                            reaction_formulas = [re.sub(f'\({s} ', f'({s}[{stream_index}] ', f) for f in reaction_formulas]
                            reaction_formulas = [re.sub(f'\({s}\)', f'({s}[{stream_index}])', f) for f in reaction_formulas]
                            reaction_formulas = [re.sub(f' {s} ', f' {s}[{stream_index}] ', f) for f in reaction_formulas]
                            reaction_formulas = [re.sub(f'^{s}$', f'{s}[{stream_index}]', f) for f in reaction_formulas]
                            reaction_formulas = [re.sub(f'\[{s}', f'[{s}[{stream_index}]', f) for f in reaction_formulas]
                            reaction_formulas = [re.sub(f'{s}(\[[^ <>\[\]]+(\[[:0-9]+\])* [<>] 0\])', f'{s}[{stream_index}]\\1', f) for f in reaction_formulas]
                    if "Reaction" in p["dimensions"] and "Solvent" not in p["dimensions"]:
                        reaction_formulas = [re.sub(f'-{s} ', f'-{s}[{reaction_index}] ', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'{s},', f'{s}[{reaction_index}],', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f' {s}\)', f' {s}[{reaction_index}])', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'\({s} ', f'({s}[{reaction_index}] ', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'\({s}\)', f'({s}[{reaction_index}])', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f' {s} ', f' {s}[{reaction_index}] ', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'^{s}$', f'{s}[{reaction_index}]', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'\[{s}', f'[{s}[{reaction_index}]', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'{s}(\[[^ <>\[\]]+(\[[:0-9]+\])* [<>] 0\])', f'{s}[{reaction_index}]\\1', f) for f in reaction_formulas]
                    if "Reaction" in p["dimensions"] and "Solvent" in p["dimensions"]:
                        reaction_formulas = [re.sub(f'-{s} ', f'-{s}[{reaction_index}][{solvent_index}] ', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'{s},', f'{s}[{reaction_index}][{solvent_index}],', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f' {s}\)', f' {s}[{reaction_index}][{solvent_index}])', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'\({s} ', f'({s}[{reaction_index}][{solvent_index}] ', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'\({s}\)', f'({s}[{reaction_index}][{solvent_index}])', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f' {s} ', f' {s}[{reaction_index}][{solvent_index}] ', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'^{s}$', f'{s}[{reaction_index}][{solvent_index}]', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'\[{s}', f'[{s}[{reaction_index}][{solvent_index}]', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'{s}(\[[^ <>\[\]]+(\[[:0-9]+\])* [<>] 0\])', f'{s}[{reaction_index}][{solvent_index}]\\1', f) for f in reaction_formulas]
                scipy_model_code.add(f'{reaction_rate_symbol}[{stream_index}][{reaction_index}] = {" * ".join(reaction_formulas)}', 2)
                scipy_model_code.add("", 0)
        scipy_model_code.add("", 0)

        # molecular transport part
        scipy_model_code.add("# MOLECULAR TRANSPORT PART", 2)
        for law in molecular_transport_laws:
            if self.entity["law"][law]["formula_integrated_with_accumulation"]: continue
            parameters = [self.entity["model_variable"][mv] for mv in self.entity["law"][law]["model_variables"]]
            symbols = [MMLExpression(p["symbol"]).to_numpy() for p in parameters]
            for model_variable in [mv for mv in self.entity["model_variable"] if law in self.entity["model_variable"][mv]["laws"]]:
                symbol = MMLExpression(self.entity["model_variable"][model_variable]["symbol"]).to_numpy()
                scipy_model_code.add(f'{symbol} = np.zeros(({len(liquid_streams)}, {len(species)}), dtype=np.float64)', 2)
                scipy_model_code.add("", 0)
                code = MMLExpression(self.entity["law"][law]["formula"]).to_numpy()
                function_head = scipy_model_code.add_function(model_variable, symbols, code, 2)
                for species_index, s in enumerate(species):
                    species_function_head = function_head
                    for p, s in zip(parameters, symbols):
                        if "Species" in p["dimensions"] and "Stream" not in p["dimensions"]:
                            species_function_head = species_function_head.replace(f'{s},', f'{s}[{species_index}],')
                            species_function_head = species_function_head.replace(f' {s})', f' {s}[{species_index}])')
                        if "Species" in p["dimensions"] and "Stream" in p["dimensions"]:
                            species_function_head = species_function_head.replace(f'{s},', f'{s}[:, {species_index}],')
                            species_function_head = species_function_head.replace(f' {s})', f' {s}[:, {species_index}])')
                    scipy_model_code.add(f"{symbol}[:, {species_index}] = {species_function_head}", 2)
                scipy_model_code.add("", 0)
        scipy_model_code.add("", 0)

        scipy_model_code.add("# MASS BALANCE PART", 2)
        optional_model_variables = self.entity["law"][accumulation_law]["optional_model_variables"]
        parameters = [self.entity["model_variable"][mv] for mv in optional_model_variables]
        parameters = [p for p in parameters for l in p["laws"] if self.entity["law"][l]["phenomenon"] in molecular_transport_phenomena + [p for v in reaction_phenomena.values() for p in v]]
        symbols = list(set([MMLExpression(p["symbol"]).to_numpy() for p in parameters]))
        if self.model_context["description"]["accumulation"] == "Continuous":
            if formula_integrated_with_accumulation:
                formula = MMLExpression(formula_integrated_with_accumulation).to_numpy()
                for s in symbols:
                    formula = re.sub(f'\[([^\[\]]*{s}[^\[\]]*)\]', r'\1', formula)
                formula = re.sub('\[[^\[\]]*\]', '0', formula)
                formula = formula.replace("dc / dz", f"c[:, {len(species)}:]")
                scipy_model_code.add(f'dc = np.zeros(({len(liquid_streams)}, {len(species) * 2}), dtype=np.float64)', 2)
                scipy_model_code.add(f'dc[:, :{len(species)}] = c[:, {len(species)}:]', 2)
                scipy_model_code.add(f'dc[:, {len(species)}:] = {formula}', 2)
            else:
                formula = MMLExpression(self.entity["law"][accumulation_law]["formula"]).to_numpy()
                for s in symbols:
                    formula = re.sub(f'\[([^\[\]]*{s}[^\[\]]*)\]', r'\1', formula)
                formula = re.sub('\[[^\[\]]*\]', '0', formula)
                scipy_model_code.add(f'dc = np.zeros(({len(liquid_streams)}, {len(species)}), dtype=np.float64)', 2)
                scipy_model_code.add(f'dc = {formula}', 2)
        if self.model_context["description"]["accumulation"] == "Batch":
            formula = MMLExpression(self.entity["law"][accumulation_law]["formula"]).to_numpy()
            for s in symbols:
                formula = re.sub(f'\[([^\[\]]*{s}[^\[\]]*)\]', r'\1', formula)
            formula = re.sub('\[[^\[\]]*\]', '0', formula)
            scipy_model_code.add(f'dc = np.zeros(({len(liquid_streams)}, {len(species)}), dtype=np.float64)', 2)
            scipy_model_code.add(f'dc = {formula}', 2)
        if self.model_context["description"]["accumulation"] == "CSTR":
            formula = MMLExpression(self.entity["law"][accumulation_law]["formula"]).to_numpy()
            formula = formula.replace("c_0", "_c_0")
            scipy_model_code.add(f'dc = {formula} - c', 2)
        scipy_model_code.add("", 0)
        scipy_model_code.add("dc = dc.reshape(-1, )", 2)
        scipy_model_code.add("return dc", 2)
        scipy_model_code.add("", 0)
        if formula_integrated_with_accumulation:
            scipy_model_code.add("def derivative_axis(x, c):", 1)
            scipy_model_code.add("return np.stack([derivative(_x, _c) for _x, _c in zip(x, c.transpose(1, 0))], axis=1)", 2)
            scipy_model_code.add("", 0)

        # boundary function
        if formula_integrated_with_accumulation:
            scipy_model_code.add("def boundary_function(ca, cb):", 1)
            scipy_model_code.add(f'ca = ca.reshape(({len(liquid_streams)}, {len(species) * 2}))', 2)
            scipy_model_code.add(f'cb = cb.reshape(({len(liquid_streams)}, {len(species) * 2}))', 2)
            scipy_model_code.add(f'bc = np.zeros(({len(liquid_streams)}, {len(species) * 2}), dtype=np.float64)', 2)
            scipy_model_code.add(f'bc[:, :{len(species)}] = u * (ca[:, :{len(species)}] - c_0) - D * ca[:, {len(species)}:]', 2)
            scipy_model_code.add(f'bc[:, {len(species)}:] = cb[:, {len(species)}:]', 2)
            scipy_model_code.add('return bc.reshape(-1, )', 2)
        scipy_model_code.add("", 0)

        # integrate calculation
        if self.model_context["description"]["accumulation"] == "Continuous":
            differential_upper_limit = self.entity["law"][accumulation_law]["differential_upper_limit"]
            differential_upper_limit_symbol = MMLExpression(self.entity["model_variable"][differential_upper_limit]['symbol']).to_numpy().strip()
            scipy_model_code.add(f"{differential_model_variable_symbol}_eval = np.linspace(0, {differential_upper_limit_symbol}, 201, dtype=np.float64)", 1)
            if formula_integrated_with_accumulation:
                scipy_model_code.add(f"c = np.zeros(({len(liquid_streams) * len(species) * 2}, 201), dtype=np.float64)", 1)
                scipy_model_code.add(f"res = solve_bvp(derivative_axis, boundary_function, {differential_model_variable_symbol}_eval, c)", 1)
            else:
                scipy_model_code.add(f"res = solve_ivp(derivative, (0, {differential_upper_limit_symbol}), c_0.reshape(-1, ), t_eval={differential_model_variable_symbol}_eval, method='LSODA', atol=1e-12)", 1)
            scipy_model_code.add(f"if res.success:", 1)
            scipy_model_code.add(f"if np.isnan(res.y).any():", 2)
            scipy_model_code.add(f"return None", 3)
            scipy_model_code.add(f"else:", 2)
            if formula_integrated_with_accumulation:
                scipy_model_code.add(f"return [res.x.round(6), res.y.round(6)[:{len(liquid_streams) * len(species)}], q]", 3)
            else:
                scipy_model_code.add(f"return [res.t.round(6), res.y.round(6), q]", 3)
        if self.model_context["description"]["accumulation"] == "Batch":
            differential_upper_limit = self.entity["law"][accumulation_law]["differential_upper_limit"]
            differential_upper_limit_symbol = MMLExpression(self.entity["model_variable"][differential_upper_limit]['symbol']).to_numpy().strip()
            scipy_model_code.add(f"{differential_model_variable_symbol}_eval = np.linspace(0, {differential_upper_limit_symbol}, 201, dtype=np.float64)", 1)
            scipy_model_code.add(f"res = solve_ivp(derivative, (0, {differential_upper_limit_symbol}), c_0.reshape(-1, ), t_eval={differential_model_variable_symbol}_eval, method='LSODA', atol=1e-12)", 1)
            scipy_model_code.add(f"if res.success:", 1)
            scipy_model_code.add(f"if np.isnan(res.y).any():", 2)
            scipy_model_code.add(f"return None", 3)
            scipy_model_code.add(f"else:", 2)
            scipy_model_code.add(f"return [(res.t / 60).round(6), res.y.round(6), np.array([1, ])]", 3)
        if self.model_context["description"]["accumulation"] == "CSTR":
            scipy_model_code.add(f"res = fsolve(conversion, (c_0 / 2).reshape(-1, ))", 1)
            scipy_model_code.add(f"if not np.isnan(res).any():", 1)
            scipy_model_code.add(f"return [[0, V * 1e6], np.concatenate((c_0.round(6).reshape(-1, 1), res.round(6).reshape(-1, 1)), axis=1), q]", 2)        
        scipy_model_code.add(f"else:", 1)
        scipy_model_code.add(f"return None", 2)
        return scipy_model_code.get_model()
    

    def to_pyomo_model(self):
        pyomo_model_code = PyomoModelCode()
        # pyomo_model_code.add_header(self.model_context)
        pyomo_model_code.add_lib()

        # parameter_value_dict
        parameter_value_dict = self.extract_parameter_value()
        pyomo_model_code.add("parameter_value_dict = {", 0)
        for k, v in parameter_value_dict.items():
            pyomo_model_code.add(f"{k}: {v},", 1)
        pyomo_model_code.add("}", 0)
        pyomo_model_code.add("", 0)

        # law identification
        # start from accumulation phenomenon
        # flow pattern laws -> subsidiary flow pattern laws
        accumulation_phenomenon = self.model_context["description"]["accumulation"]
        flow_pattern_phenomenon = self.model_context["description"]["flow_pattern"]
        molecular_transport_phenomena = self.model_context["description"]["molecular_transport"]
        parameter_law = self.model_context["description"]["parameter_law"]
        reaction_phenomena = self.model_context["description"]["reaction"]
        accumulation_law = [l for l in self.entity["law"] if self.entity["law"][l]["phenomenon"] == accumulation_phenomenon][0]
        accumulation_model_variables = self.entity["law"][accumulation_law]["model_variables"]
        molecular_transport_laws = [l for l in self.entity["law"] if self.entity["law"][l]["phenomenon"] in molecular_transport_phenomena]
        molecular_transport_model_variables = list(set([mv for l in molecular_transport_laws for mv in self.entity["law"][l]["model_variables"]]))
        flow_pattern_laws = [l for l in self.entity["law"] for mv in accumulation_model_variables if l in self.entity["model_variable"][mv]["laws"] and self.entity["law"][l]["phenomenon"] == flow_pattern_phenomenon] + \
            [parameter_law[mv] for mv in molecular_transport_model_variables if self.entity["model_variable"][mv]["laws"]]
        sub_flow_pattern_laws = [parameter_law[p] for p in set([mv for l in flow_pattern_laws for mv in self.entity["law"][l]["model_variables"] if [
            l for l in self.entity["model_variable"][mv]["laws"] if self.entity["law"][l]["rule"]]])]
        flow_pattern_model_variables = list(set([mv for l in flow_pattern_laws + sub_flow_pattern_laws for mv in self.entity["law"][l]["model_variables"]]))
        reaction_laws = {r: [l for l in self.entity["law"] if self.entity["law"][l]["phenomenon"] in p] for r, p in reaction_phenomena.items()}
        reaction_model_variables = {r: list(set([mv for l in ls for mv in self.entity["law"][l]["model_variables"]])) for r, ls in reaction_laws.items()}
        formula_integrated_with_accumulation = [self.entity["law"][l]["formula_integrated_with_accumulation"] for l in molecular_transport_laws if self.entity["law"][l]["formula_integrated_with_accumulation"]]
        if formula_integrated_with_accumulation:
            formula_integrated_with_accumulation = formula_integrated_with_accumulation[0]
        else:
            formula_integrated_with_accumulation = None
        model_variables = accumulation_model_variables + molecular_transport_model_variables + flow_pattern_model_variables + [mv for r in reaction_model_variables for mv in reaction_model_variables[r]]
        definitions = [self.entity["model_variable"][mv]["definition"] for mv in model_variables if self.entity["model_variable"][mv]["definition"]]
        model_variables = model_variables + [mv for d in definitions for mv in self.entity["definition"][d]["model_variables"]]
        if self.model_context["basic"]["reactions"]:
            model_variables += ["Coefficient"]
        model_variables = list(set(model_variables))

        # model basics
        parameter_value_keys = list(parameter_value_dict.keys())
        species = self.model_context["basic"]["species"]
        reactions = self.model_context["basic"]["reactions"]
        liquid_streams = [k for k, v in self.model_context["information"]["streams"].items() if v["state"] == "liquid"]
        gas_streams = [k for k, v in self.model_context["information"]["streams"].items() if v["state"] == "gaseous"]
        solvents = self.model_context["basic"]["solvents"]
        if self.model_context["description"]["accumulation"] in ["Continuous", "Batch"]:
            differential_model_variable = self.entity["law"][accumulation_law]["differential_model_variable"]
            differential_model_variable_symbol = MMLExpression(self.entity["model_variable"][differential_model_variable]['symbol']).to_numpy().strip()
        
        # simulation function head
        pyomo_model_code.add("def simulation(parameter_value_dict):", 0)
        pyomo_model_code.add("# MODEL DECLARATION", 1)
        pyomo_model_code.add("model = environ.ConcreteModel()", 1)
        pyomo_model_code.add("", 0)
        pyomo_model_code.add("# PARAMETER PART", 1)
        pyomo_model_code.add("p = list(parameter_value_dict.values())", 1)

        # parameter setup
        for model_variable in model_variables:
            symbol = MMLExpression(self.entity["model_variable"][model_variable]["symbol"]).to_numpy()
            model_variable_class = self.entity["model_variable"][model_variable]["class"]
            
            if model_variable_class == "Constant":
                pyomo_model_code.add(f'{symbol} = {self.entity["model_variable"][model_variable]["value"]}', 1)
                if self.entity["model_variable"][model_variable]["unit"] and self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["standard_unit"]:
                    pyomo_model_code.add(f'{symbol} *= {self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["ratio_to_standard_unit"]}', 1)
                pyomo_model_code.add(f'model.{symbol} = environ.Param(initialize={symbol})', 1)
            if "Parameter" not in model_variable_class: continue
            
            model_variable_laws = self.entity["model_variable"][model_variable]["laws"]
            model_variable_definition = self.entity["model_variable"][model_variable]["definition"]
            if model_variable_definition or model_variable_laws: continue
            
            model_variable_dimensions = self.entity["model_variable"][model_variable]["dimensions"]
            if set(model_variable_dimensions) == set([]):
                pyomo_model_code.add(f'{symbol} = p[{parameter_value_keys.index((model_variable, None, None, None, None))}]', 1)
                if self.entity["model_variable"][model_variable]["unit"] and self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["standard_unit"]:
                    pyomo_model_code.add(f'{symbol} *= {self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["ratio_to_standard_unit"]}', 1)
                pyomo_model_code.add(f'model.{symbol} = environ.Param(initialize={symbol})', 1)
            if set(model_variable_dimensions) == set(["Reaction"]):
                pyomo_model_code.add(f"{symbol} = np.zeros(({len(reactions)}), dtype=np.float64)", 1)
                for i, r in enumerate(reactions):
                    if (model_variable, None, r, None, None) not in parameter_value_keys: continue
                    pyomo_model_code.add(f'{symbol}[{i}] = p[{parameter_value_keys.index((model_variable, None, r, None, None))}]', 1)
                if self.entity["model_variable"][model_variable]["unit"] and self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["standard_unit"]:
                    pyomo_model_code.add(f'{symbol} *= {self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["ratio_to_standard_unit"]}', 1)
                pyomo_model_code.add(f'model.{symbol} = environ.Param(range({len(reactions)}), initialize=dict(np.ndenumerate({symbol})))', 1)
                
            if set(model_variable_dimensions) == set(["Reaction", "Solvent"]):
                pyomo_model_code.add(f"{symbol} = np.zeros(({len(reactions)}, {len(solvents)}), dtype=np.float64)", 1)
                for i, r in enumerate(reactions):
                    for j, s in enumerate(solvents):
                        if (model_variable, None, r, None, s) not in parameter_value_keys: continue
                        pyomo_model_code.add(f'{symbol}[{i}][{j}] = p[{parameter_value_keys.index((model_variable, None, r, None, s))}]', 1)
                if self.entity["model_variable"][model_variable]["unit"] and self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["standard_unit"]:
                    pyomo_model_code.add(f'{symbol} *= {self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["ratio_to_standard_unit"]}', 1)
                pyomo_model_code.add(f'model.{symbol} = environ.Param(range({len(reactions)}), range({len(solvents)}), initialize=dict(np.ndenumerate({symbol})))', 1)
            if set(model_variable_dimensions) == set(["Species"]):
                pyomo_model_code.add(f"{symbol} = np.zeros(({len(species)}, ), dtype=np.float64)", 1)
                for i, s in enumerate(species):
                    pyomo_model_code.add(f'{symbol}[{i}] = p[{parameter_value_keys.index((model_variable, s, None, None, None))}]', 1)
                if self.entity["model_variable"][model_variable]["unit"] and self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["standard_unit"]:
                    pyomo_model_code.add(f'{symbol} *= {self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["ratio_to_standard_unit"]}', 1)
                pyomo_model_code.add(f'model.{symbol} = environ.Param(range({len(species)}), initialize=dict(np.ndenumerate({symbol})))', 1)
            if set(model_variable_dimensions) == set(["Species", "Reaction"]):
                pyomo_model_code.add(f"{symbol} = np.zeros(({len(reactions)}, {len(species)}), dtype=np.float64)", 1)
                for i, r in enumerate(reactions):
                    for j, s in enumerate(species):
                        if (model_variable, s, r, None, None) not in parameter_value_keys: continue
                        pyomo_model_code.add(f'{symbol}[{i}][{j}] = p[{parameter_value_keys.index((model_variable, s, r, None, None))}]', 1)
                if self.entity["model_variable"][model_variable]["unit"] and self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["standard_unit"]:
                    pyomo_model_code.add(f'{symbol} *= {self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["ratio_to_standard_unit"]}', 1)
                pyomo_model_code.add(f'model.{symbol} = environ.Param(range({len(reactions)}), range({len(species)}), initialize=dict(np.ndenumerate({symbol})))', 1)
            if set(model_variable_dimensions) == set(["Stream"]):
                if "Gas" not in model_variable:
                    pyomo_model_code.add(f"{symbol} = np.zeros(({len(liquid_streams)}, ), dtype=np.float64)", 1)
                    for i, s in enumerate(liquid_streams):
                        if (model_variable, None, None, s, None) not in parameter_value_keys: continue
                        pyomo_model_code.add(f'{symbol}[{i}] = p[{parameter_value_keys.index((model_variable, None, None, s, None))}]', 1)
                    if self.entity["model_variable"][model_variable]["unit"] and self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["standard_unit"]:
                        pyomo_model_code.add(f'{symbol} *= {self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["ratio_to_standard_unit"]}', 1)
                    pyomo_model_code.add(f'model.{symbol} = environ.Param(range({len(liquid_streams)}), initialize=dict(np.ndenumerate({symbol})))', 1)
                else:
                    pyomo_model_code.add(f"{symbol} = np.zeros(({len(gas_streams)}, ), dtype=np.float64)", 1)
                    for i, s in enumerate(gas_streams):
                        if (model_variable, None, None, s, None) not in parameter_value_keys: continue
                        pyomo_model_code.add(f'{symbol}[{i}] = p[{parameter_value_keys.index((model_variable, None, None, s, None))}]', 1)
                    if self.entity["model_variable"][model_variable]["unit"] and self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["standard_unit"]:
                        pyomo_model_code.add(f'{symbol} *= {self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["ratio_to_standard_unit"]}', 1)
                    pyomo_model_code.add(f'model.{symbol} = environ.Param(range({len(gas_streams)}), initialize=dict(np.ndenumerate({symbol})))', 1)
            if set(model_variable_dimensions) == set(["Stream", "Species"]):
                pyomo_model_code.add(f"{symbol} = np.zeros(({len(liquid_streams)}, {len(species)}), dtype=np.float64)", 1)
                for i, s in enumerate(liquid_streams):
                    for j, sp in enumerate(species):
                        if (model_variable, sp, None, s, None) not in parameter_value_keys: continue
                        pyomo_model_code.add(f'{symbol}[{i}][{j}] = p[{parameter_value_keys.index((model_variable, sp, None, s, None))}]', 1)
                if self.entity["model_variable"][model_variable]["unit"] and self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["standard_unit"]:
                    pyomo_model_code.add(f'{symbol} *= {self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["ratio_to_standard_unit"]}', 1)
                pyomo_model_code.add(f'model.{symbol} = environ.Param(range({len(liquid_streams)}), range({len(species)}), initialize=dict(np.ndenumerate({symbol})))', 1)
        pyomo_model_code.add("", 0)

        # flow pattern (parameter irrelevant with variable)
        pyomo_model_code.add("# FLOW PATTERN PART", 1)
        for law in sub_flow_pattern_laws:
            model_variables = self.entity["law"][law]["model_variables"]
            symbols = [MMLExpression(self.entity["model_variable"][mv]["symbol"]).to_numpy() for mv in model_variables]
            for model_variable in [mv for mv in self.entity["model_variable"] if law in self.entity["model_variable"][mv]["laws"]]:
                symbol = MMLExpression(self.entity["model_variable"][model_variable]["symbol"]).to_numpy()
                formula = MMLExpression(self.entity["law"][law]["formula"]).to_numpy()
                pyomo_model_code.add(f"model.{symbol} = environ.Var(within=environ.PositiveReals)", 1)
                function_head = pyomo_model_code.add_function(model_variable, symbols, formula, 1)
                pyomo_model_code.add(f"def {model_variable.lower()}_rule(model):", 1)
                for s in symbols:
                    pyomo_model_code.add(f"{s} = np.array(model.{s})", 2)
                pyomo_model_code.add(f"return model.{symbol} == {function_head}.item()", 2)
                pyomo_model_code.add(f"model.{model_variable.lower()}_constraint = environ.Constraint(rule={model_variable.lower()}_rule)", 1)
                pyomo_model_code.add("", 0)
        for law in flow_pattern_laws:
            law_model_variables = self.entity["law"][law]["model_variables"]
            law_symbols = [MMLExpression(self.entity["model_variable"][mv]["symbol"]).to_numpy() for mv in law_model_variables]
            for model_variable in [mv for mv in self.entity["model_variable"] if law in self.entity["model_variable"][mv]["laws"]]:
                symbol = MMLExpression(self.entity["model_variable"][model_variable]["symbol"]).to_numpy()
                formula = MMLExpression(self.entity["law"][law]["formula"]).to_numpy()
                pyomo_model_code.add(f"model.{symbol} = environ.Var(within=environ.PositiveReals)", 1)
                function_head = pyomo_model_code.add_function(model_variable, law_symbols, formula, 1)
                pyomo_model_code.add(f"def {model_variable.lower()}_rule(model):", 1)
                for s in law_symbols:
                    pyomo_model_code.add(f"{s} = np.array(model.{s})", 2)
                pyomo_model_code.add(f"return model.{symbol} == {function_head}.item()", 2)
                pyomo_model_code.add(f"model.{model_variable.lower()}_constraint = environ.Constraint(rule={model_variable.lower()}_rule)", 1)
                pyomo_model_code.add("", 0)

        # concentration axial position derivative function
        if self.model_context["description"]["accumulation"] == "Continuous":
            differential_upper_limit = self.entity["law"][accumulation_law]["differential_upper_limit"]
            differential_upper_limit_symbol = MMLExpression(self.entity["model_variable"][differential_upper_limit]['symbol']).to_numpy().strip()
            pyomo_model_code.add(f"model.{differential_model_variable_symbol} = dae.ContinuousSet(bounds=(0, model.{differential_upper_limit_symbol}.value))", 1)
            if formula_integrated_with_accumulation:
                pyomo_model_code.add(f"model.c = environ.Var(range({len(liquid_streams)}), range({len(species) * 2}), model.{differential_model_variable_symbol})", 1)
            else:
                pyomo_model_code.add(f"model.c = environ.Var(range({len(liquid_streams)}), range({len(species)}), model.{differential_model_variable_symbol})", 1)
        # TODO: concentration axial position derivative function
        if self.model_context["description"]["accumulation"] == "Batch":
            return "Not supported in pyomo mode now."
        # concentration error function
        if self.model_context["description"]["accumulation"] == "CSTR":
            return "Not supported in pyomo mode now."
        pyomo_model_code.add("", 0)

        # reaction part
        pyomo_model_code.add("# REACTION PART", 1)
        reaction_rate_symbol = MMLExpression(self.entity["model_variable"]["Reaction_Rate"]["symbol"]).to_numpy()
        if self.model_context["description"]["accumulation"] in ["Continuous", "Batch"]:
            pyomo_model_code.add(f'model.{reaction_rate_symbol} = environ.Var(range({len(liquid_streams)}), range({len(reactions)}), model.{differential_model_variable_symbol})', 1)
            pyomo_model_code.add("", 0)
        definition_model_variables = list(set([mv for laws in reaction_laws.values() for l in laws for mv in self.entity["law"][l]["model_variables"] if self.entity["model_variable"][mv]["definition"]]))
        for definition_model_variable in definition_model_variables:
            definition_parameter = self.entity["model_variable"][definition_model_variable]
            definition_dimensions = definition_parameter["dimensions"]
            symbol = MMLExpression(definition_parameter["symbol"]).to_numpy()
            if "Stream" not in definition_dimensions:
                pyomo_model_code.add(f'model.{symbol} = environ.Var(model.{differential_model_variable_symbol})', 1)
                model_variables = list(set([mv for mv in self.entity["definition"][definition_parameter["definition"]]["model_variables"]]))
                parameters = [self.entity["model_variable"][mv] for mv in model_variables]
                symbols = [MMLExpression(p["symbol"]).to_numpy() for p in parameters]
                formula = MMLExpression(self.entity["definition"][definition_parameter["definition"]]["formula"]).to_numpy()
                function_head = pyomo_model_code.add_function(definition_model_variable, symbols, formula, 1)
                pyomo_model_code.add(f"def {definition_model_variable.lower()}_rule(model, {differential_model_variable_symbol}):", 1)
                for model_variable, s in zip(model_variables, symbols):
                    if "Variable" in self.entity["model_variable"][model_variable]["class"] or model_variable == "Concentration":
                        dimensions = self.entity["model_variable"][model_variable]["dimensions"]
                        pyomo_model_code.add(f"{s} = np.array(model.{s}[{' '.join([':,'] * len(dimensions))} x])", 2)
                    else:
                        pyomo_model_code.add(f"{s} = np.array(model.{s})", 2)
                pyomo_model_code.add(f"return model.{symbol}[{differential_model_variable_symbol}] == {function_head}", 2)
                pyomo_model_code.add(f"model.{definition_model_variable.lower()}_constraint = environ.Constraint(rule={definition_model_variable.lower()}_rule)", 1)
            else:
                pyomo_model_code.add(f'model.{symbol} = environ.Var(range({len(liquid_streams)}), model.{differential_model_variable_symbol})', 1)
                model_variables = list(set([mv for mv in self.entity["definition"][definition_parameter["definition"]]["model_variables"]]))
                parameters = [self.entity["model_variable"][mv] for mv in model_variables]
                symbols = [MMLExpression(p["symbol"]).to_numpy() for p in parameters]
                formula = MMLExpression(self.entity["definition"][definition_parameter["definition"]]["formula"]).to_numpy()
                function_head = pyomo_model_code.add_function(definition_model_variable, symbols, formula, 1)
                pyomo_model_code.add(f"def {definition_model_variable.lower()}_rule(model, i, {differential_model_variable_symbol}):", 1)
                for model_variable, s in zip(model_variables, symbols):
                    if "Variable" in self.entity["model_variable"][model_variable]["class"] or model_variable == "Concentration":
                        dimensions = self.entity["model_variable"][model_variable]["dimensions"]
                        pyomo_model_code.add(f"{s} = np.array(model.{s}[{' '.join(['i,' if d == 'Stream' else ':,' for d in dimensions])} x])", 2)
                    else:
                        pyomo_model_code.add(f"{s} = np.array(model.{s})", 2)
                pyomo_model_code.add(f"return model.{symbol}[{differential_model_variable_symbol}] == {function_head}", 2)
                pyomo_model_code.add(f"model.{definition_model_variable.lower()}_constraint = environ.Constraint(rule={definition_model_variable.lower()}_rule)", 1)
            pyomo_model_code.add("", 0)
        
        if self.model_context["description"]["accumulation"] in ["Continuous", "Batch"]:
            for stream_index, stream in enumerate(liquid_streams):
                for reaction_index, reaction in enumerate(reactions):
                    if reaction not in self.model_context["information"]["streams"][stream]["reactions"]: continue
                    solvent_index = solvents.index(self.model_context["information"]["streams"][stream]["solvent"])
                    pyomo_model_code.add(f"# stream: {stream}, reaction: {reaction}", 1)
                    laws = reaction_laws[reaction]
                    reaction_formulas = [self.entity["law"][l]["formula"] for l in laws if "specifically defined" not in self.entity["law"][l]["formula"]]
                    reaction_formulas = [MMLExpression(f).to_numpy() for f in reaction_formulas]
                    model_variables = [mv for l in laws for mv in self.entity["law"][l]["model_variables"]]
                    parameters = [self.entity["model_variable"][mv] for mv in model_variables]
                    symbols = [MMLExpression(p["symbol"]).to_numpy() for p in parameters]
                    
                    reaction_special_laws = [l for l in laws if "specifically defined" in self.entity["law"][l]["formula"]]
                    reaction_special_phenomena = [self.entity["law"][l]["phenomenon"] for l in reaction_special_laws]
                    reaction_special_formulas = [self.model_context["information"]["reactions"][reaction][p] for p in reaction_special_phenomena]
                    for phenomenon, formula, law in zip(reaction_special_phenomena, reaction_special_formulas, reaction_special_laws):
                        special_model_variables = self.entity["law"][law]["model_variables"]
                        special_parameters = [self.entity["model_variable"][mv] for mv in special_model_variables]
                        special_symbols = [MMLExpression(p["symbol"]).to_numpy() for p in special_parameters]
                        formula_fun = f'calc_reaction_term_{phenomenon.lower().replace("-", "_")}({", ".join(special_symbols)})'
                        formula = [s if '=' in s or ':' in s else re.sub('^( *)([^ ].*)$', r'\1return \2', s) for s in formula.split('\n')]
                        pyomo_model_code.add("def " + formula_fun + ":", 1)
                        pyomo_model_code.add(formula, 2)
                        reaction_formulas.append(formula_fun)
                        for mv, p, s in zip(special_model_variables, special_parameters, special_symbols):
                            if mv not in model_variables:
                                model_variables.append(mv)
                                parameters.append(p)
                                symbols.append(s)
                    model_variables.append(differential_model_variable)
                    parameters.append(self.entity["model_variable"][differential_model_variable])
                    symbols.append(differential_model_variable_symbol)

                    formula = " * ".join(reaction_formulas)
                    for p, s in zip(parameters, symbols):
                        if s == f"{differential_model_variable_symbol}": continue
                        if set(p["dimensions"]) == set([]):
                            formula = re.sub(f'{s}([ \),]|$)', f'{s}\\1', formula)
                        if set(p["dimensions"]) == set(["Reaction"]):
                            formula = re.sub(f'{s}([ \),]|$)', f'{s}[{reaction_index}]\\1', formula)
                        if set(p["dimensions"]) == set(["Reaction", "Species"]):
                            formula = re.sub(f'{s}([ \),]|$)', f'{s}[{reaction_index}, s_index]\\1', formula)
                        if set(p["dimensions"]) == set(["Reaction", "Solvent"]):
                            formula = re.sub(f'{s}([ \),]|$)', f'{s}[{reaction_index}, {solvent_index}]\\1', formula)
                        if set(p["dimensions"]) == set(["Stream", "Species"]):
                            if "Variable" in p["class"]:
                                formula = re.sub(f'{s}([ \),]|$)', f'{s}[{stream_index}, s_index, x]\\1', formula)
                            else:
                                formula = re.sub(f'{s}([ \),]|$)', f'{s}[{stream_index}, s_index]\\1', formula)
                    formula = re.sub(r'np.prod\(([^\(\)]*)\)', f'np.prod([\\1 for s_index in range({len(species)})])', formula)
                    function_head = pyomo_model_code.add_function(f"Reaction_Rate_{stream_index}_{reaction_index}", symbols, formula, 1)
                    for s in symbols:
                        if s == f"{differential_model_variable_symbol}": continue
                        function_head = re.sub(f'{s}([ \),])', f'model.{s}\\1', function_head)

                    pyomo_model_code.add(f"def reaction_rate_{stream_index}_{reaction_index}_rule(model, {differential_model_variable_symbol}):", 1)
                    pyomo_model_code.add(f"return model.{reaction_rate_symbol}[{stream_index}, {reaction_index}, {differential_model_variable_symbol}] == {function_head}", 2)
                    pyomo_model_code.add(f"model.reaction_rate_{stream_index}_{reaction_index}_constraint = environ.Constraint(model.{differential_model_variable_symbol}, rule=reaction_rate_{stream_index}_{reaction_index}_rule)", 1)
                    pyomo_model_code.add("", 0)
        # TODO
        else:
            return "Not supported in pyomo mode now."

        # TODO molecular transport part
        pyomo_model_code.add("# MOLECULAR TRANSPORT PART", 1)

        pyomo_model_code.add("# MASS BALANCE PART", 1)
        optional_model_variables = self.entity["law"][accumulation_law]["optional_model_variables"]
        model_variables = [mv for mv in optional_model_variables for l in self.entity["model_variable"][mv]["laws"] if self.entity["law"][l]["phenomenon"] in molecular_transport_phenomena + [p for v in reaction_phenomena.values() for p in v]]\
            + [mv for mv in optional_model_variables if self.entity["model_variable"][mv]["laws"] == []]
        model_variables.extend(self.entity["law"][accumulation_law]["model_variables"])
        model_variables = list(set([mv for mv in model_variables if mv != "Initial_Concentration"]))
        parameters = [self.entity["model_variable"][mv] for mv in model_variables]
        symbols = [MMLExpression(p["symbol"]).to_numpy() for p in parameters]
        model_variables.append(differential_model_variable)
        parameters.append(self.entity["model_variable"][differential_model_variable])
        symbols.append(differential_model_variable_symbol)
        if self.model_context["description"]["accumulation"] == "Continuous":
            if formula_integrated_with_accumulation:
                return "Not supported in pyomo mode now."
            else:
                pyomo_model_code.add(f"model.dc = dae.DerivativeVar(model.c, wrt=model.{differential_model_variable_symbol})", 1)
                formula = MMLExpression(self.entity["law"][accumulation_law]["formula"]).to_numpy()
                for s in symbols:
                    formula = re.sub(f'\[([^\[\]]*{s}[^\[\]]*)\]', r'\1', formula)
                formula = re.sub('\[[^\[\],]*\]', '0', formula)
                for p, s in zip(parameters, symbols):
                    if s == f"{differential_model_variable_symbol}": continue
                    if set(p["dimensions"]) == set([]):
                        formula = re.sub(f'{s}([ \),]|$)', f'{s}\\1', formula)
                    if set(p["dimensions"]) == set(["Stream", "Reaction"]):
                        if "Variable" in p["class"]:
                            formula = re.sub(f'{s}([ \),]|$)', f'{s}[i, r_index, x]\\1', formula)
                        else:
                            formula = re.sub(f'{s}([ \),]|$)', f'{s}[i, r_index]\\1', formula)
                    if set(p["dimensions"]) == set(["Reaction", "Species"]):
                        formula = re.sub(f'{s}([ \),]|$)', f'{s}[r_index, j]\\1', formula)
                formula = re.sub(r'np.matmul\(([^\(\)]*)(?<=\]), ([^\(\)]*)\)', f'np.prod([\\1 * \\2 for r_index in range({len(reactions)})])', formula)

                function_head = pyomo_model_code.add_function(f"Concentration_Derivative", symbols + ["i", "j"], formula, 1)
                for s in symbols:
                    if s == f"{differential_model_variable_symbol}": continue
                    function_head = re.sub(f'{s}([ \),])', f'model.{s}\\1', function_head)
                pyomo_model_code.add(f"def concentration_derivative_rule(model, i, j, {differential_model_variable_symbol}):", 1)
                pyomo_model_code.add(f"return model.dc[i, j, {differential_model_variable_symbol}] == {function_head}", 2)
                pyomo_model_code.add(f"model.concentration_derivative_constraint = environ.Constraint(range({len(liquid_streams)}), range({len(species)}), model.{differential_model_variable_symbol}, rule=concentration_derivative_rule)", 1)
                pyomo_model_code.add("", 0)
        # TODO
        if self.model_context["description"]["accumulation"] == "Batch":
            pass
        # TODO
        if self.model_context["description"]["accumulation"] == "CSTR":
            pass

        # boundary function
        # TODO
        if formula_integrated_with_accumulation:
            pass
        else:
            pyomo_model_code.add(f"for i in range({len(liquid_streams)}):", 1)
            pyomo_model_code.add(f"for j in range({len(species)}):", 2)
            pyomo_model_code.add(f"model.c[i, j, 0].fix(np.array(model.c_0)[i, j])", 3)
        pyomo_model_code.add("", 0)

        # integrate calculation
        if self.model_context["description"]["accumulation"] == "Continuous":
            pyomo_model_code.add("discretizer = environ.TransformationFactory('dae.finite_difference')", 1)
            pyomo_model_code.add("discretizer.apply_to(model, nfe=400, scheme='BACKWARD')", 1)
            pyomo_model_code.add("solver = environ.SolverFactory('ipopt')", 1)
            pyomo_model_code.add("solver.solve(model)", 1)
            differential_upper_limit = self.entity["law"][accumulation_law]["differential_upper_limit"]
            differential_upper_limit_symbol = MMLExpression(self.entity["model_variable"][differential_upper_limit]['symbol']).to_numpy().strip()
            pyomo_model_code.add(f"{differential_model_variable_symbol} = np.array(model.{differential_model_variable_symbol})", 1)
            pyomo_model_code.add(f"c = np.array([model.c.get_values()[k] for k in sorted(list(model.c.get_values().keys()))]).reshape({len(liquid_streams)}, {len(species)}, -1)", 1)
            pyomo_model_code.add(f"q = np.array(model.q)", 1)
            pyomo_model_code.add(f"return [{differential_model_variable_symbol}, c, q]", 1)
        if self.model_context["description"]["accumulation"] == "Batch":
            pass
        if self.model_context["description"]["accumulation"] == "CSTR":
            pass
        return pyomo_model_code.get_model()


    def to_julia_model(self):
        """The converted julia model is given as:
        parameter_value_dict: `{(parameter, species, reaction, stream, solvent): value}`
        def simulation(parameter_value_dict):
            p = list(parameter_value_dict.values())
            def derivative(c, x):
            def boundary(c_a, c_b):
            sol = solve(prob, Tsit5(); saveat=x_eval, reltol=1e-12, abstol=1e-12)
            return(sol.t, sol.u)
        Returns:
            str: converted julia model
        """

        julia_model_code = JuliaModelCode()
        # julia_model_code.add_header(self.model_context)
        julia_model_code.add_lib()

        # parameter_value_dict
        parameter_value_dict = self.extract_parameter_value()
        julia_model_code.add("parameter_value_dict = OrderedDict(", 0)
        for k, v in parameter_value_dict.items():
            k = tuple('nothing' if x is None else x for x in k)
            formatted_key = ', '.join(f'nothing' if elem == 'nothing' else f'"{elem}"' for elem in k)
            julia_model_code.add(f"({formatted_key}) => {v if v else 'nothing'},", 1)
        julia_model_code.add(")", 0)
        julia_model_code.add("", 0)

        # law identification
        # start from accumulation phenomenon
        # flow pattern laws -> subsidiary flow pattern laws
        accumulation_phenomenon = self.model_context["description"]["accumulation"]
        flow_pattern_phenomenon = self.model_context["description"]["flow_pattern"]
        molecular_transport_phenomena = self.model_context["description"]["molecular_transport"]
        parameter_law = self.model_context["description"]["parameter_law"]
        reaction_phenomena = self.model_context["description"]["reaction"]

        # law and name of parameters
        accumulation_phenomenon = self.model_context["description"]["accumulation"]
        flow_pattern_phenomenon = self.model_context["description"]["flow_pattern"]
        molecular_transport_phenomena = self.model_context["description"]["molecular_transport"]
        parameter_law = self.model_context["description"]["parameter_law"]
        reaction_phenomena = self.model_context["description"]["reaction"]
        accumulation_law = [l for l in self.entity["law"] if self.entity["law"][l]["phenomenon"] == accumulation_phenomenon][0]
        accumulation_model_variables = self.entity["law"][accumulation_law]["model_variables"]
        molecular_transport_laws = [l for l in self.entity["law"] if self.entity["law"][l]["phenomenon"] in molecular_transport_phenomena]
        molecular_transport_model_variables = list(set([mv for l in molecular_transport_laws for mv in self.entity["law"][l]["model_variables"]]))
        flow_pattern_laws = [l for l in self.entity["law"] for mv in accumulation_model_variables if l in self.entity["model_variable"][mv]["laws"] and self.entity["law"][l]["phenomenon"] == flow_pattern_phenomenon] + \
            [parameter_law[mv] for mv in molecular_transport_model_variables if self.entity["model_variable"][mv]["laws"]]
        sub_flow_pattern_laws = [parameter_law[p] for p in set([mv for l in flow_pattern_laws for mv in self.entity["law"][l]["model_variables"] if [
            l for l in self.entity["model_variable"][mv]["laws"] if self.entity["law"][l]["rule"]]])]
        flow_pattern_model_variables = list(set([mv for l in flow_pattern_laws + sub_flow_pattern_laws for mv in self.entity["law"][l]["model_variables"]]))
        reaction_laws = {r: [l for l in self.entity["law"] if self.entity["law"][l]["phenomenon"] in p] for r, p in reaction_phenomena.items()}
        reaction_model_variables = {r: list(set([mv for l in ls for mv in self.entity["law"][l]["model_variables"]])) for r, ls in reaction_laws.items()}
        formula_integrated_with_accumulation = [self.entity["law"][l]["formula_integrated_with_accumulation"] for l in molecular_transport_laws if self.entity["law"][l]["formula_integrated_with_accumulation"]]
        
        if formula_integrated_with_accumulation:
            formula_integrated_with_accumulation = formula_integrated_with_accumulation[0]
        else:
            formula_integrated_with_accumulation = None

        model_variables = accumulation_model_variables + molecular_transport_model_variables + flow_pattern_model_variables + [mv for r in reaction_model_variables for mv in reaction_model_variables[r]]
        definitions = [self.entity["model_variable"][mv]["definition"] for mv in model_variables if self.entity["model_variable"][mv]["definition"]]
        model_variables = model_variables + [mv for d in definitions for mv in self.entity["definition"][d]["model_variables"]]
        if self.model_context["basic"]["reactions"]:
            model_variables += ["Coefficient"]
        model_variables = list(set(model_variables))

        # model basics, get differentiable variable
        parameter_value_keys = list(parameter_value_dict.keys())
        species = self.model_context["basic"]["species"]
        reactions = self.model_context["basic"]["reactions"]
        liquid_streams = [k for k, v in self.model_context["information"]["streams"].items() if v["state"] == "liquid"]
        gas_streams = [k for k, v in self.model_context["information"]["streams"].items() if v["state"] == "gaseous"]
        solvents = self.model_context["basic"]["solvents"]
        if self.model_context["description"]["accumulation"] in ["Continuous", "Batch"]:
            differential_model_variable = self.entity["law"][accumulation_law]["differential_model_variable"]
            differential_model_variable_symbol = MMLExpression(
                self.entity["model_variable"][differential_model_variable]['symbol']).to_numpy().strip()

        # simulation function head
        julia_model_code.add("function simulation(parameter_value_dict)", 0)
        julia_model_code.add("# PARAMETER PART", 1)
        julia_model_code.add("p = collect(values(parameter_value_dict))", 1)

        # parameter setup
        for model_variable in model_variables:
            symbol = MMLExpression(self.entity["model_variable"][model_variable]["symbol"]).to_numpy()
            model_variable_class = self.entity["model_variable"][model_variable]["class"]

            if model_variable_class == "Constant":
                julia_model_code.add(f'{symbol} = {self.entity["model_variable"][model_variable]["value"]}', 1)
            if "Parameter" not in model_variable_class: continue

            model_variable_laws = self.entity["model_variable"][model_variable]["laws"]
            model_variable_definition = self.entity["model_variable"][model_variable]["definition"]
            if model_variable_definition or model_variable_laws: continue

            model_variable_dimensions = self.entity["model_variable"][model_variable]["dimensions"]
            if set(model_variable_dimensions) == set([]):
                julia_model_code.add(f'{symbol} = p[{parameter_value_keys.index((model_variable, None, None, None, None)) + 1}]', 1)
            if set(model_variable_dimensions) == set(["Reaction"]):
                julia_model_code.add(f"{symbol} = zeros({len(reactions)})", 1)
                for i, r in enumerate(reactions):
                    if (model_variable, None, r, None, None) not in parameter_value_keys: continue
                    julia_model_code.add(f'{symbol}[{i + 1}] = p[{parameter_value_keys.index((model_variable, None, r, None, None)) + 1}]', 1)
            if set(model_variable_dimensions) == set(["Reaction", "Solvent"]):
                julia_model_code.add(f"{symbol} = zeros({len(reactions)}, {len(solvents)})", 1)
                for i, r in enumerate(reactions):
                    for j, s in enumerate(solvents):
                        if (model_variable, None, r, None, s) not in parameter_value_keys: continue
                        julia_model_code.add(f'{symbol}[{i + 1}, {j + 1}] = p[{parameter_value_keys.index((model_variable, None, r, None, s)) + 1}]', 1)
            if set(model_variable_dimensions) == set(["Species"]):
                julia_model_code.add(f"{symbol} = zeros({len(species)}, )", 1)
                for i, s in enumerate(species):
                    julia_model_code.add(f'{symbol}[{i + 1}] = p[{parameter_value_keys.index((model_variable, s, None, None, None)) + 1}]', 1)
            if set(model_variable_dimensions) == set(["Species", "Reaction"]):
                julia_model_code.add(f"{symbol} = zeros({len(reactions)}, {len(species)})", 1)
                for i, r in enumerate(reactions):
                    for j, s in enumerate(species):
                        if (model_variable, s, r, None, None) not in parameter_value_keys: continue
                        julia_model_code.add(f'{symbol}[{i + 1}, {j + 1}] = p[{parameter_value_keys.index((model_variable, s, r, None, None)) + 1}]', 1)
            if set(model_variable_dimensions) == set(["Stream"]):
                if "Gas" not in model_variable:
                    julia_model_code.add(f"{symbol} = zeros(({len(liquid_streams)}, ))", 1)
                    for i, s in enumerate(liquid_streams):
                        if (model_variable, None, None, s, None) not in parameter_value_keys: continue
                        julia_model_code.add(f'{symbol}[{i + 1}] = p[{parameter_value_keys.index((model_variable, None, None, s, None)) + 1}]', 1)
                else:
                    julia_model_code.add(f"{symbol} = zeros(({len(gas_streams)}, ))", 1)
                    for i, s in enumerate(gas_streams):
                        if (model_variable, None, None, s, None) not in parameter_value_keys: continue
                        julia_model_code.add(f'{symbol}[{i + 1}] = p[{parameter_value_keys.index((model_variable, None, None, s, None)) + 1}]', 1)
            if set(model_variable_dimensions) == set(["Stream", "Species"]):
                julia_model_code.add(f"{symbol} = zeros({len(liquid_streams)}, {len(species)})", 1)
                for i, s in enumerate(liquid_streams):
                    for j, sp in enumerate(species):
                        if (model_variable, sp, None, s, None) not in parameter_value_keys: continue
                        julia_model_code.add(f'{symbol}[{i + 1}, {j + 1}] = p[{parameter_value_keys.index((model_variable, sp, None, s, None)) + 1}]', 1)
            # unit processing
            if self.entity["model_variable"][model_variable]["unit"] and \
                    self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["standard_unit"]:
                julia_model_code.add(f'{symbol} *= {self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["ratio_to_standard_unit"]}', 1)
        julia_model_code.add("", 0)

        # flow pattern (parameter irrelevant with variable)
        julia_model_code.add("# FLOW PATTERN PART", 1)
        # TODO: need to check
        for law in sub_flow_pattern_laws:
            model_variables = self.entity["law"][law]["model_variables"]
            symbols = [MMLExpression(self.entity["model_variable"][mv]["symbol"]).to_numpy() for mv in model_variables]
            for model_variable in [mv for mv in self.entity["model_variable"] if law in self.entity["model_variable"][mv]["laws"]]:
                symbol = MMLExpression(self.entity["model_variable"][model_variable]["symbol"]).to_numpy()
                code = MMLExpression(self.entity["law"][law]["formula"]).to_numpy()
                if "\n" in code:
                    function_head = julia_model_code.add_function(model_variable, symbols, code, 1)
                    julia_model_code.add(f"{symbol} = {function_head}", 1)
                else:
                    julia_model_code.add(f"{symbol} = {code}", 1)
                julia_model_code.add("", 0)

        for law in flow_pattern_laws:
            law_model_variables = self.entity["law"][law]["model_variables"]
            law_symbols = [MMLExpression(self.entity["model_variable"][mv]["symbol"]).to_numpy() for mv in law_model_variables]
            for model_variable in [mv for mv in self.entity["model_variable"] if law in self.entity["model_variable"][mv]["laws"]]:
                symbol = MMLExpression(self.entity["model_variable"][model_variable]["symbol"]).to_numpy()
                code = MMLExpression(self.entity["law"][law]["formula"]).to_numpy()
                # TODO: need to change np.sum and np.pi not to be default, delete them for now
                if "np." in code:
                    code = code.replace("np.", "").replace("pi", "π")
                if "**" in code:
                    code = code.replace("**", "^")
                if "\n" in code:
                    function_head = julia_model_code.add_function(model_variable, law_symbols, code, 1)
                    julia_model_code.add(f"{symbol} = {function_head}", 1)
                else:
                    julia_model_code.add(f"{symbol} = {code}", 1)
                julia_model_code.add("", 0)
        julia_model_code.add("", 0)

        # concentration axial position derivative function
        if self.model_context["description"]["accumulation"] == "Continuous":
            julia_model_code.add(f"function derivative(dc, c, p, {differential_model_variable_symbol})", 1)
            if formula_integrated_with_accumulation:
                julia_model_code.add(f"c = reshape(c, {len(liquid_streams)}, {len(species) * 2})", 2)
            else:
                julia_model_code.add(f"c = reshape(c, {len(liquid_streams)}, {len(species)})", 2)

        # concentration axial position derivative function
        if self.model_context["description"]["accumulation"] == "Batch":
            julia_model_code.add(f"function derivative(dc, c, p, {differential_model_variable_symbol})", 1)
            julia_model_code.add(f"c = reshape(c, {len(liquid_streams)}, {len(species)})", 2)

        # concentration error function
        # TODO: need to check
        if self.model_context["description"]["accumulation"] == "CSTR":
            julia_model_code.add(f"def conversion(c):", 1)
            if self.model_context["description"]["flow_pattern"] == "Well_Mixed":
                julia_model_code.add(f"_c_0 = (c_0 * q.reshape(-1, 1)).sum(axis=0) / q.sum()", 2)
                julia_model_code.add(f"c = reshape(c, 1, {len(species)})", 2)
        julia_model_code.add("", 0)

        # reaction part
        julia_model_code.add("# REACTION PART", 2)
        reaction_rate_symbol = MMLExpression(self.entity["model_variable"]["Reaction_Rate"]["symbol"]).to_numpy()
        julia_model_code.add(f'{reaction_rate_symbol} = reshape([0.0], {len(liquid_streams)}, {len(reactions)})', 2)
        julia_model_code.add("", 0)
        definition_model_variables = list(set([mv for laws in reaction_laws.values() for l in laws for mv in self.entity["law"][l]["model_variables"] if self.entity["model_variable"][mv]["definition"]]))
        definition_parameters = [self.entity["model_variable"][mv] for mv in definition_model_variables]

        for definition_parameter in definition_parameters:
            definition_dimensions = definition_parameter["dimensions"]
            symbol = MMLExpression(definition_parameter["symbol"]).to_numpy()
            if "Stream" not in definition_dimensions:
                julia_model_code.add(f'{symbol} = {formula}', 2)
            else:
                # TODO: need check
                julia_model_code.add(f'{symbol} = np.zeros(({len(liquid_streams)}, ), dtype=np.float64)', 2)
                model_variables = list(set([mv for mv in self.entity["definition"][definition_parameter["definition"]]["model_variables"]]))
                parameters = [self.entity["model_variable"][mv] for mv in model_variables]
                symbols = [MMLExpression(p["symbol"]).to_numpy() for p in parameters]
                for stream_index, stream in enumerate(liquid_streams):
                    formula = MMLExpression(self.ntity["definition"][definition_parameter["definition"]]["formula"]).to_numpy()
                    for p, s in zip(parameters, symbols):
                        if "Stream" in p["dimensions"]:
                            formula = re.sub(f'-{s} ', f'-{s}[{stream_index}] ', formula)
                            formula = re.sub(f'{s},', f'{s}[{stream_index}],', formula)
                            formula = re.sub(f' {s}\)', f' {s}[{stream_index}])', formula)
                            formula = re.sub(f'\({s} ', f'({s}[{stream_index}] ', formula)
                            formula = re.sub(f' {s} ', f' {s}[{stream_index}] ', formula)
                            formula = re.sub(f'^{s}$', f'{s}[{stream_index}]', formula)
                            formula = re.sub(f'\[{s}', f'[{s}[{stream_index}]', formula)
                            formula = re.sub(f'{s}(\[[^ <>\[\]]+(\[[:0-9]+\])* [<>] 0\])', f'{s}[{stream_index}]\\1', formula)
                    julia_model_code.add(f'{symbol}[{stream_index}] = {formula}', 2)
        julia_model_code.add("", 0)

        for stream_index, stream in enumerate(liquid_streams):
            for reaction_index, reaction in enumerate(reactions):
                if reaction not in self.model_context["information"]["streams"][stream]["reactions"]: continue
                solvent_index = solvents.index(self.model_context["information"]["streams"][stream]["solvent"])
                julia_model_code.add(f"# stream: {stream}  reaction: {reaction}", 2)
                laws = reaction_laws[reaction]
                reaction_formulas = [self.entity["law"][l]["formula"] for l in laws if "specifically defined" not in self.entity["law"][l]["formula"]]
                reaction_formulas = [MMLExpression(f).to_numpy() for f in reaction_formulas]
                # TODO: here MMLExpression needs to change, np.prod()
                parameters = [self.entity["model_variable"][mv] for l in laws for mv in self.entity["law"][l]["model_variables"]]
                symbols = [MMLExpression(p["symbol"]).to_numpy() for p in parameters]

                # TODO: need to check
                reaction_special_laws = [l for l in laws if "specifically defined" in self.entity["law"][l]["formula"]]
                reaction_special_phenomena = [self.entity["law"][l]["phenomenon"] for l in reaction_special_laws]
                reaction_special_formulas = [self.model_context["information"]["reactions"][reaction][p] for p in reaction_special_phenomena]
                for phenomenon, formula, law in zip(reaction_special_phenomena, reaction_special_formulas, reaction_special_laws):
                    special_parameters = [self.entity["model_variable"][mv] for mv in self.entity["law"][law]["model_variables"]]
                    special_symbols = [MMLExpression(p["symbol"]).to_numpy() for p in special_parameters]
                    formula_fun = f'calc_reaction_term_{phenomenon.lower().replace("-", "_")}({", ".join(special_symbols)})'
                    formula = [s if '=' in s or ':' in s else re.sub('^( *)([^ ].*)$', r'\1return \2', s) for s in formula.split('\n')]
                    julia_model_code.add("def " + formula_fun + ":", 2)
                    julia_model_code.add(formula, 3)
                    reaction_formulas.append(formula_fun)

                for p, s in zip(parameters, symbols):
                    if "Stream" in p["dimensions"] and "Species" not in p["dimensions"]:
                        reaction_formulas = [re.sub(f'-{s} ', f'-{s}[{stream_index}] ', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'{s},', f'{s}[{stream_index}],', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f' {s}\)', f' {s}[{stream_index}])', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'\({s} ', f'({s}[{stream_index}] ', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'\({s}\)', f'({s}[{stream_index}])', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f' {s} ', f' {s}[{stream_index}] ', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'^{s}$', f'{s}[{stream_index}]', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'\[{s}', f'[{s}[{stream_index}]', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'{s}(\[[^ <>\[\]]+(\[[:0-9]+\])* [<>] 0\])', f'{s}[{stream_index}]\\1', f) for f in reaction_formulas]
                    # Add c[0]
                    if "Stream" in p["dimensions"] and "Species" in p["dimensions"]:
                        if formula_integrated_with_accumulation:
                            reaction_formulas = [re.sub(f'-{s} ', f'-{s}[{stream_index + 1}][:{len(species)}] ', f) for f in reaction_formulas]
                            reaction_formulas = [re.sub(f'{s},', f'{s}[{stream_index + 1}][:{len(species)}],', f) for f in reaction_formulas]
                            reaction_formulas = [re.sub(f' {s}\)', f' {s}[{stream_index + 1}][:{len(species)}])', f) for f in reaction_formulas]
                            reaction_formulas = [re.sub(f'\({s} ', f'({s}[{stream_index + 1}][:{len(species)}] ', f) for f in reaction_formulas]
                            reaction_formulas = [re.sub(f'\({s}\)', f'({s}[{stream_index + 1}][:{len(species)}])', f) for f in reaction_formulas]
                            reaction_formulas = [re.sub(f' {s} ', f' {s}[{stream_index + 1}][:{len(species)}] ', f) for f in reaction_formulas]
                            reaction_formulas = [re.sub(f'^{s}$', f'{s}[{stream_index + 1}][:{len(species)}]', f) for f in reaction_formulas]
                            reaction_formulas = [re.sub(f'\[{s}', f'[{s}[{stream_index + 1}][:{len(species)}]', f) for f in reaction_formulas]
                            reaction_formulas = [re.sub(f'{s}(\[[^ <>\[\]]+(\[[:0-9]+\])* [<>] 0\])', f'{s}[{stream_index + 1}][:{len(species)}]\\1', f) for f in reaction_formulas]
                        else:
                            reaction_formulas = [re.sub(f'-{s} ', f'-{s}[{stream_index + 1}, :] ', f) for f in reaction_formulas]
                            reaction_formulas = [re.sub(f'{s},', f'{s}[{stream_index + 1}, :],', f) for f in reaction_formulas]
                            reaction_formulas = [re.sub(f' {s}\)', f' {s}[{stream_index + 1}, :])', f) for f in reaction_formulas]
                            reaction_formulas = [re.sub(f'\({s} ', f'({s}[{stream_index + 1}, :] ', f) for f in reaction_formulas]
                            reaction_formulas = [re.sub(f'\({s}\)', f'({s}[{stream_index + 1}, :])', f) for f in reaction_formulas]
                            reaction_formulas = [re.sub(f' {s} ', f' {s}[{stream_index + 1}, :] ', f) for f in reaction_formulas]
                            reaction_formulas = [re.sub(f'^{s}$', f'{s}[{stream_index + 1}, :]', f) for f in reaction_formulas]
                            reaction_formulas = [re.sub(f'\[{s}', f'[{s}[{stream_index + 1}, :]', f) for f in reaction_formulas]
                            reaction_formulas = [re.sub(f'{s}(\[[^ <>\[\]]+(\[[:0-9]+\])* [<>] 0\])', f'{s}[{stream_index + 1}, :]\\1', f) for f in reaction_formulas]
                    # Add n[0]
                    if "Reaction" in p["dimensions"] and "Solvent" not in p["dimensions"]:
                        reaction_formulas = [re.sub(f'-{s} ', f'-{s}[{reaction_index + 1}, :] ', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'{s},', f'{s}[{reaction_index + 1}, :],', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f' {s}\)', f' {s}[{reaction_index + 1}, :])', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'\({s} ', f'({s}[{reaction_index + 1}, :] ', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'\({s}\)', f'({s}[{reaction_index + 1, :}])', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f' {s} ', f' {s}[{reaction_index + 1}, :] ', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'^{s}$', f'{s}[{reaction_index + 1}, :]', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'\[{s}', f'[{s}[{reaction_index + 1}, :]', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'{s}(\[[^ <>\[\]]+(\[[:0-9]+\])* [<>] 0\])', f'{s}[{reaction_index + 1}, :]\\1', f) for f in reaction_formulas]
                    # Add k[1][1]
                    if "Reaction" in p["dimensions"] and "Solvent" in p["dimensions"]:
                        reaction_formulas = [re.sub(f'-{s} ', f'-{s}[{reaction_index + 1}, {solvent_index + 1}] ', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'{s},', f'{s}[{reaction_index + 1}, {solvent_index + 1}],', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f' {s}\)', f' {s}[{reaction_index + 1}, {solvent_index + 1}])', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'\({s} ', f'({s}[{reaction_index + 1}, {solvent_index + 1}] ', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'\({s}\)', f'({s}[{reaction_index + 1}, {solvent_index + 1}])', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f' {s} ', f' {s}[{reaction_index + 1}, {solvent_index + 1}] ', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'^{s}$', f'{s}[{reaction_index + 1}, {solvent_index + 1}]', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'\[{s}', f'[{s}[{reaction_index + 1}, {solvent_index + 1}]', f) for f in reaction_formulas]
                        reaction_formulas = [re.sub(f'{s}(\[[^ <>\[\]]+(\[[:0-9]+\])* [<>] 0\])', f'{s}[{reaction_index}, {solvent_index}]\\1', f) for f in reaction_formulas]
                
                # TODO: change to Julia format here
                reaction_formulas[0] = reaction_formulas[0].replace('**', '.^').replace('np.prod', 'prod')
                julia_model_code.add(f'{reaction_rate_symbol}[{stream_index + 1}, {reaction_index + 1}] = {" * ".join(reaction_formulas)}',2)
                julia_model_code.add("", 0)
        julia_model_code.add("", 0)

        # TODO: need to check
        # molecular transport part
        julia_model_code.add("# MOLECULAR TRANSPORT PART", 2)
        for law in molecular_transport_laws:
            if self.entity["law"][law]["formula_integrated_with_accumulation"]: continue
            parameters = [self.entity["model_variable"][mv] for mv in self.entity["law"][law]["model_variables"]]
            symbols = [MMLExpression(p["symbol"]).to_numpy() for p in parameters]
            for model_variable in [mv for mv in self.entity["model_variable"] if law in self.entity["model_variable"][mv]["laws"]]:
                symbol = MMLExpression(self.entity["model_variable"][model_variable]["symbol"]).to_numpy()
                julia_model_code.add(f'{symbol} = np.zeros(({len(liquid_streams)}, {len(species)}), dtype=np.float64)', 2)
                julia_model_code.add("", 0)
                code = MMLExpression(self.entity["law"][law]["formula"]).to_numpy()
                function_head = julia_model_code.add_function(model_variable, symbols, code, 2)
                for species_index, s in enumerate(species):
                    species_function_head = function_head
                    for p, s in zip(parameters, symbols):
                        if "Species" in p["dimensions"] and "Stream" not in p["dimensions"]:
                            species_function_head = species_function_head.replace(f'{s},', f'{s}[{species_index}],')
                            species_function_head = species_function_head.replace(f' {s})', f' {s}[{species_index}])')
                        if "Species" in p["dimensions"] and "Stream" in p["dimensions"]:
                            species_function_head = species_function_head.replace(f'{s},', f'{s}[:, {species_index}],')
                            species_function_head = species_function_head.replace(f' {s})', f' {s}[:, {species_index}])')
                    julia_model_code.add(f"{symbol}[:, {species_index}] = {species_function_head}", 2)
                julia_model_code.add("", 0)
        julia_model_code.add("", 0)

        julia_model_code.add("# ACCUMULATION PART", 2)
        optional_model_variables = self.entity["law"][accumulation_law]["optional_model_variables"]
        parameters = [self.entity["model_variable"][mv] for mv in optional_model_variables]
        parameters = [p for p in parameters for l in p["laws"] if self.entity["law"][l]["phenomenon"] in molecular_transport_phenomena + [p for v in reaction_phenomena.values() for p in v]]
        symbols = list(set([MMLExpression(p["symbol"]).to_numpy() for p in parameters]))

        # TODO: not check
        if self.model_context["description"]["accumulation"] == "Continuous":
            if formula_integrated_with_accumulation:
                formula = MMLExpression(formula_integrated_with_accumulation).to_numpy()
                for s in symbols:
                    formula = re.sub(f'\[([^\[\]]*{s}[^\[\]]*)\]', r'\1', formula)
                formula = re.sub('\[[^\[\]]*\]', '0', formula)
                formula = formula.replace("dc / dz", f"c[:, {len(species)}:]")
                julia_model_code.add(f'dc = reshape(dc, {len(liquid_streams)}, {len(species) * 2})', 2)
                julia_model_code.add(f'dc[:, :{len(species)}] = c[:, {len(species)}:]', 2)
                julia_model_code.add(f'dc[:, {len(species)}:] = {formula}', 2)
            else:
                formula = MMLExpression(self.entity["law"][accumulation_law]["formula"]).to_numpy()
                for s in symbols:
                    formula = re.sub(f'\[([^\[\]]*{s}[^\[\]]*)\]', r'\1', formula)
                formula = re.sub('\[[^\[\]]*\]', '0', formula)
                # TODO: change here for matmul
                formula = formula.replace("np.matmul", "").replace(',', ' .* ').replace('+', '.+')
                julia_model_code.add(f'dc = reshape(dc, {len(liquid_streams)}, {len(species)})', 2)
                julia_model_code.add(f'dc .= {formula}', 2)

        if self.model_context["description"]["accumulation"] == "Batch":
            formula = MMLExpression(self.entity["law"][accumulation_law]["formula"]).to_numpy()
            for s in symbols:
                formula = re.sub(f'\[([^\[\]]*{s}[^\[\]]*)\]', r'\1', formula)
            formula = re.sub('\[[^\[\]]*\]', '0', formula)
            # TO DO: change here for matmul
            formula = formula.replace("np.matmul", "").replace('(', '').replace(')', '').replace(',', ' * ')
            julia_model_code.add(f'dc = reshape(dc, {len(liquid_streams)}, {len(species)})', 2)
            julia_model_code.add(f'dc .= {formula}', 2)

        # TODO: need to check
        if self.model_context["description"]["accumulation"] == "CSTR":
            formula = MMLExpression(self.entity["law"][accumulation_law]["formula"]).to_numpy()
            formula = formula.replace("c_0", "_c_0")
            julia_model_code.add(f'dc = {formula} - c', 2)

        julia_model_code.add("", 0)
        julia_model_code.add("end", 1)
        julia_model_code.add("", 0)
        if formula_integrated_with_accumulation:
            julia_model_code.add("def derivative_axis(x, c):", 1)
            julia_model_code.add(
                "return np.stack([derivative(_x, _c) for _x, _c in zip(x, c.transpose(1, 0))], axis=1)", 2)
            julia_model_code.add("", 0)

        # TODO: need to check
        # boundary function
        if formula_integrated_with_accumulation:
            julia_model_code.add("def boundary_function(ca, cb):", 1)
            julia_model_code.add(f'ca = ca.reshape(({len(liquid_streams)}, {len(species) * 2}))', 2)
            julia_model_code.add(f'cb = cb.reshape(({len(liquid_streams)}, {len(species) * 2}))', 2)
            julia_model_code.add(f'bc = np.zeros(({len(liquid_streams)}, {len(species) * 2}), dtype=np.float64)', 2)
            julia_model_code.add(
                f'bc[:, :{len(species)}] = u * (ca[:, :{len(species)}] - c_0) - D * ca[:, {len(species)}:]', 2)
            julia_model_code.add(f'bc[:, {len(species)}:] = cb[:, {len(species)}:]', 2)
            julia_model_code.add('return bc.reshape(-1, )', 2)
        julia_model_code.add("", 0)

        # integrate calculation
        if self.model_context["description"]["accumulation"] == "Continuous":
            differential_upper_limit = self.entity["law"][accumulation_law]["differential_upper_limit"]
            differential_upper_limit_symbol = MMLExpression(self.entity["model_variable"][differential_upper_limit]['symbol']).to_numpy().strip()
            julia_model_code.add(f"{differential_model_variable_symbol}_eval = LinRange(0, {differential_upper_limit_symbol}, 201)", 1)
            # TODO: change if here for bvp problem
            if formula_integrated_with_accumulation:
                julia_model_code.add(f"c = zeros(({len(liquid_streams) * len(species) * 2}, 201)", 1)
                julia_model_code.add(f"res = solve_bvp(derivative_axis, boundary_function, {differential_model_variable_symbol}_eval, c)", 1)
            else:
                julia_model_code.add(f"prob = ODEProblem(derivative, reshape(c_0, {len(species)}), (0, {differential_upper_limit_symbol}))", 1)
                julia_model_code.add(f"sol = solve(prob, Tsit5(); saveat={differential_model_variable_symbol}_eval, reltol=1e-12, abstol=1e-12)", 1)
            julia_model_code.add(f"if sol.retcode == ReturnCode.Success", 1)
            julia_model_code.add(f"return(sol.t, sol.u, q)", 2)
            julia_model_code.add(f"else", 1)
            julia_model_code.add(f"return nothing", 2)

        if self.model_context["description"]["accumulation"] == "Batch":
            differential_upper_limit = self.entity["law"][accumulation_law]["differential_upper_limit"]
            differential_upper_limit_symbol = MMLExpression(self.entity["model_variable"][differential_upper_limit]['symbol']).to_numpy().strip()
            julia_model_code.add(f"{differential_model_variable_symbol}_eval = LinRange(0, {differential_upper_limit_symbol}, 201)", 1)
            julia_model_code.add(f"prob = ODEProblem(derivative, reshape(c_0, {len(species)}), (0, {differential_upper_limit_symbol}))", 1)
            julia_model_code.add(f"sol = solve(prob, Tsit5(); saveat={differential_model_variable_symbol}_eval, reltol=1e-12, abstol=1e-12)", 1)
            julia_model_code.add(f"if sol.retcode == ReturnCode.Success", 1)
            julia_model_code.add(f"return(sol.{differential_model_variable_symbol}/ 60, sol.u, q)", 2)
            julia_model_code.add(f"else", 1)
            julia_model_code.add(f"return nothing", 2)

        # TODO: need check
        if self.model_context["description"]["accumulation"] == "CSTR":
            pass

        julia_model_code.add(f"end", 1)
        julia_model_code.add(f"end", 0)
        return julia_model_code.get_model() 