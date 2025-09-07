import itertools
import json
import re

from .mml_expression import MMLExpression


class ScipyModel:
    """Helper of ModelAgent for creating scipy model codes."""

    def __init__(self):
        self.spaces = 4
        self.codes = []

    def add_header(self, context):
        self.codes.append('"""')
        self.codes.append("Scipy model created by OntoMo")
        self.codes.append("")
        self.codes.append("Model Context:")
        self.codes.extend(json.dumps(context, indent=self.spaces).split("\n"))
        self.codes.append('"""')
        self.codes.append("")

    def add_lib(self):
        self.codes.append("import numpy as np")
        self.codes.append("from scipy.optimize import fsolve")
        self.codes.append("from scipy.integrate import solve_bvp, solve_ivp")
        self.codes.append("from scipy.interpolate import interp1d")
        self.codes.append("")
    
    def add_func(self, var, syms, code, level):
        func_head = f"calc_{var.lower().replace('-', '_')}({', '.join(syms)})"
        self.add(f'def {func_head}:', level)
        if "=" not in code.split("\n")[0] and ":" not in code.split("\n")[0]:
            code = code.split("\n")[1:] + code.split("\n")[:1]
        else:
            code = code.split("\n")
        for c in code[:-1]:
            self.add(c, level + 1)
        self.add("return " + code[-1].strip(), level + 1)
        self.add("", 0)
        return func_head

    def add(self, code, level):
        if isinstance(code, str):
            self.codes.append(" " * self.spaces * level + code)
        if isinstance(code, list):
            for c in code:
                self.codes.append(" " * self.spaces * level + c)

    def get_model(self):
        return '\n'.join(self.codes)


# TODO: Pyomo model
# class PyomoModelCode:
#     """Helper of ModelAgent for creating pyomo model codes."""

#     def __init__(self):
#         self.spaces = 4
#         self.codes = []

#     def add_header(self, model_context):
#         self.codes.append('"""')
#         self.codes.append("Pyomo Model Created by OntoMo")
#         self.codes.append("")
#         self.codes.append("Model Context:")
#         self.codes.extend(json.dumps(model_context, indent=self.spaces).split("\n"))
#         self.codes.append('"""')
#         self.codes.append("")

#     def add_lib(self):
#         self.codes.append("import numpy as np")
#         self.codes.append("from scipy.optimize import fsolve")
#         self.codes.append("from pyomo import dae, environ")
#         self.codes.append("")
    
#     def add_function(self, model_variable, input_symbols, code, level):
#         function_head = f"calc_{model_variable.lower().replace('-', '_')}({', '.join(input_symbols)})"
#         self.add(f'def {function_head}:', level)
#         if "=" not in code.split("\n")[0] and ":" not in code.split("\n")[0]:
#             code = code.split("\n")[1:] + code.split("\n")[:1]
#         else:
#             code = code.split("\n")
#         for c in code[:-1]:
#             self.add(c, level + 1)
#         self.add("return " + code[-1].strip(), level + 1)
#         return function_head

#     def add(self, code, level):
#         if isinstance(code, str):
#             self.codes.append(" " * self.spaces * level + code)
#         if isinstance(code, list):
#             for c in code:
#                 self.codes.append(" " * self.spaces * level + c)

#     def get_model(self):
#         return '\n'.join(self.codes)


# TODO: Julia model
# class JuliaModelCode:
#     def __init__(self):
#         self.spaces = 4
#         self.codes = []

#     def add_header(self, model_context):
#         self.codes.append('"""')
#         self.codes.append("Julia Model Created by OntoMo")
#         self.codes.append("")
#         self.codes.append("Model Context:")
#         self.codes.extend(json.dumps(model_context, indent=self.spaces).split("\n"))
#         self.codes.append('"""')
#         self.codes.append("")

#     def add_lib(self):
#         self.codes.append("using DifferentialEquations")
#         self.codes.append("using DataStructures")
#         self.codes.append("")

#     def add_function(self, model_variable, input_symbols, code, level):
#         function_head = f"calc_{model_variable.lower().replace('-', '_')}({', '.join(input_symbols)})"
#         self.add(f'def {function_head}:', level)
#         if "=" not in code.split("\n")[0] and ":" not in code.split("\n")[0]:
#             code = code.split("\n")[1:] + code.split("\n")[:1]
#         else:
#             code = code.split("\n")
#         for c in code[:-1]:
#             self.add(c, level + 1)
#         self.add("return " + code[-1].strip(), level + 1)
#         return function_head

#     def add(self, code, level):
#         if isinstance(code, str):
#             self.codes.append(" " * self.spaces * level + code)
#         if isinstance(code, list):
#             for c in code:
#                 self.codes.append(" " * self.spaces * level + c)

#     def get_model(self):
#         return '\n'.join(self.codes)


class ModelAgent:
    """Model agent for generating model based on model context.

    The physical model is derived from given phenomena and parameters, including:
        - accumulation
        - flow pattern
        - mass transport
        - mass equilibrium
        - reaction
    
    For `bottom-up` modelling, the json structure is like:
    ```
    {
        "method": "bottom-up",
        "basic": {
            "spcs":     [],
            "rxns":     [],
            "stms":     [],
            "sols":     [],
            "cats":     [],
        },
        "description": {
            "accum":    "",
            "flow_pat": "",
            "mt":       [],
            "me":       [],
            "rxn": {"rxn 1": []},
            "param_law": {"param 1": ""},
        }, 
        "information": {
            "spc":  {"param 1": {}},
            "st":   {},
            "mt":   {},
            "me":   {"gas 1": {"stm 1": {"param 1": []}}},
            "stm":  {"stm 1": {"rxns": {}}},
            "rxn":  {"rxn 1": {"param 1": {}}},
        },
    }
    ```

    Model integration steps:
        - reaction rate
        - transport rate
            - mixing rate
            - transfer rate
            - dispersion rate
        - concentration derivative
    """

    dynamic_segs = 200
    rxn_pattern = r"^((\d+ )?.+ \+ )*(\d+ )?.+ > ((\d+ )?.+ \+ )*(\d+ )?.+$"
    sym_patterns = [
        ("^[sym]$", "[sym]"), # alone
        ("[sym],", "[sym],"), # comma
        ("^[sym] ", "[sym] "), # start
        (" [sym]$", " [sym]"), # end
        ("-[sym] ", "-[sym] "), # negative
        (" [sym] ", " [sym] "), # left-right space
        ("[sym] \*", "[sym] *"), # multiplication
        ("\([sym] ", "([sym] "), # left bracket
        (" [sym]\)", " [sym])"), # right bracket
        ("\[[sym] ", "[[sym] "), # left square bracket
        ("\([sym]\)", "([sym])"), # left-right bracket
        ("[sym](\[[^ <>\[\]]+(\[[:0-9]+\])* [<>] 0\])", "[sym]\\\\1"), # index
    ]
    dim2pos = {"Solid": 0, "Gas": 0, "Stream": 1, "Reaction": 2, "Species": 3}

    def __init__(self, entity, context, param_dict=None):
        self.entity = entity
        self.context = context
        self.param_dict = param_dict
    
    def validate_rxn(self):
        spcs = self.context["basic"]["spc"]
        rxns = self.context["basic"]["rxn"]
        for rxn in rxns:
            if not re.match(self.rxn_pattern, rxn):
                raise ValueError(f"invalid format for reaction: {rxn}")
            lhs, rhs = rxn.split(" > ")[0], rxn.split(" > ")[1]
            lhs_spcs = [s.split(" ")[-1] for s in lhs.split(" + ")]
            rhs_spcs = [s.split(" ")[-1] for s in rhs.split(" + ")]
            if any([rxn_spc not in spcs for rxn_spc in lhs_spcs + rhs_spcs]):
                return False, f"False reaction format: {rxn}"
        return True, ""

    def extract_param_dict(self):
        """Extract parameter from context with dimensions listed as: 
            [species, reaction, stream, and gas/solid]
        """
        
        param_dict = {}

        # Structure
        if "st" not in self.context["information"]:
            for p in self.context["information"]["st"]:
                if p not in self.entity["var"]:
                    continue
                dims = self.entity["var"][p]["dims"]
                if set(dims) == set([""]):
                    v = self.context["information"]["st"][p]
                    param_dict[(p, None, None, None, None)] = v
                else:
                    msg = f"Invalid dimensions for structure parameter {p}: {dims}"
                    return False, msg
        
        # Species
        if "spc" in self.context["information"]:
            for p in self.context["information"]["spc"]:
                if p not in self.entity["var"]:
                    continue
                dims = self.entity["var"][p]["dims"]
                if set(dims) == set(["Species"]):
                    for spc in self.context["information"]["spc"][p]:
                        v = self.context["information"]["spc"][p][spc]
                        param_dict[(p, spc, None, None, None)] = v
                else:
                    msg = f"Invalid dimensions for species parameter {p}: {dims}"
                    return False, msg
        
        # Stream
        if "stm" in self.context["information"]:
            for p in self.context["information"]["stm"]:
                if p not in self.entity["var"]:
                    continue
                dims = self.entity["var"][p]["dims"]
                if set(dims) == set(["Stream"]):
                    for stm in self.context["information"]["stm"][p]:
                        v = self.context["information"]["stm"][p][stm]
                        param_dict[(p, None, None, stm, None)] = v
                else:
                    msg = f"Invalid dimensions for stream parameter {p}: {dims}"
                    return False, msg

        # Gas
        if "gas" in self.context["information"]:
            for p in self.context["information"]["gas"]:
                if p not in self.entity["var"]:
                    continue
                dims = self.entity["var"][p]["dims"]
                if set(dims) == set(["Gas"]):
                    for gas in self.context["information"]["gas"][p]:
                        v = self.context["information"]["gas"][p][gas]
                        param_dict[(p, None, None, None, gas)] = v
                else:
                    msg = f"Invalid dimensions for gas parameter {p}: {dims}"
                    return False, msg

        # Solid
        if "sld" in self.context["information"]:
            for p in self.context["information"]["sld"]:
                if p not in self.entity["var"]:
                    continue
                dims = self.entity["var"][p]["dims"]
                if set(dims) == set(["Solid"]):
                    for sld in self.context["information"]["sld"][p]:
                        v = self.context["information"]["sld"][p][sld]
                        param_dict[(p, None, None, None, sld)] = v
                else:
                    msg = f"Invalid dimensions for solid parameter {p}: {dims}"
                    return False, msg

        # Mass transport
        if "mt" in self.context["information"]:
            for p in self.context["information"]["mt"]:
                if p not in self.entity["var"]:
                    continue
                dims = self.entity["var"][p]["dims"]
                if set(dims) == set([]):
                    v = self.context["information"]["mt"][p]
                    param_dict[(p, None, None, None, None)] = v
                elif set(dims) == set(["Species"]):
                    for spc in self.context["information"]["mt"][p]:
                        v = self.context["information"]["mt"][p][spc]
                        param_dict[(p, spc, None, None, None)] = v
                elif set(dims) == set(["Species", "Stream"]):
                    for stm in self.context["information"]["mt"][p]:
                        for spc in self.context["information"]["mt"][p][stm]:
                            v = self.context["information"]["mt"][p][stm][spc]
                            param_dict[(p, spc, None, stm, None)] = v
                elif set(dims) == set(["Species", "Gas"]):
                    for gas in self.context["information"]["mt"][p]:
                        for spc in self.context["information"]["mt"][p][gas]:
                            v = self.context["information"]["mt"][p][gas][spc]
                            param_dict[(p, spc, None, None, gas)] = v
                elif set(dims) == set(["Species", "Solid"]):
                    for sld in self.context["information"]["mt"][p]:
                        for spc in self.context["information"]["mt"][p][sld]:
                            v = self.context["information"]["mt"][p][sld][spc]
                            param_dict[(p, spc, None, None, sld)] = v
                elif set(dims) == set(["Species", "Stream", "Gas"]):
                    for gas in self.context["information"]["mt"][p]:
                        for stm in self.context["information"]["mt"][p][gas]:
                            for spc in self.context["information"]["mt"][p][gas][stm]:
                                v = self.context["information"]["mt"][p][gas][stm][spc]
                                param_dict[(p, spc, None, stm, gas)] = v
                elif set(dims) == set(["Species", "Stream", "Solid"]):
                    for sld in self.context["information"]["mt"][p]:
                        for stm in self.context["information"]["mt"][p][sld]:
                            for spc in self.context["information"]["mt"][p][sld][stm]:
                                v = self.context["information"]["mt"][p][sld][stm][spc]
                                param_dict[(p, spc, None, stm, sld)] = v
                else:
                    msg = f"Invalid dimensions for mass transport parameter {p}: {dims}"
                    return False, msg

        # Mass equilibrium
        if "me" in self.context["information"]:
            for p in self.context["information"]["me"]:
                if p not in self.entity["var"]:
                    continue
                dims = self.entity["var"][p]["dims"]
                if set(dims) == set(["Species", "Stream", "Gas"]):
                    for gas in self.context["information"]["me"][p]:
                        for stm in self.context["information"]["me"][p][gas]:
                            for spc in self.context["information"]["me"][p][gas][stm]:
                                v = self.context["information"]["me"][p][gas][stm][spc]
                                param_dict[(p, spc, None, stm, gas)] = v
                elif set(dims) == set(["Species", "Stream", "Solid"]):
                    for sld in self.context["information"]["me"][p]:
                        for stm in self.context["information"]["me"][p][sld]:
                            for spc in self.context["information"]["me"][p][sld][stm]:
                                v = self.context["information"]["me"][p][sld][stm][spc]
                                param_dict[(p, spc, None, stm, sld)] = v
                else:
                    msg = f"Invalid dimensions for mass equilibrium parameter {p}: {dims}"
                    return False, msg

        # Stoichiometric coefficient
        for r in self.context["basic"]["rxn"]:
            lhs_r = r.split(" > ")[0]
            rhs_r = r.split(" > ")[1]
            for item in lhs_r.split(" + "):
                if re.match(r"^\d+$", item.split(" ")[0]):
                    v = -float(item.split(" ")[0])
                    s = " ".join(item.split(" ")[1:])
                else:
                    v = -1.0
                    s = item
                param_dict[("Stoichiometric_Coefficient", s, r, None, None)] = v
            for item in rhs_r.split(" + "):
                if re.match(r"^\d+$", item.split(" ")[0]):
                    v = float(item.split(" ")[0])
                    s = " ".join(item.split(" ")[1:])
                else:
                    v = 1.0
                    s = item
                param_dict[("Stoichiometric_Coefficient", s, r, None, None)] = v

        # Reaction
        if "rxn" in self.context["information"]:
            for p in self.context["information"]["rxn"]:
                if p not in self.entity["var"]:
                    continue
                dims = self.entity["var"][p]["dims"]
                if set(dims) == set(["Reaction"]):
                    for rxn in self.context["information"]["rxn"][p]:
                        v = self.context["information"]["rxn"][p][rxn]
                        param_dict[(p, None, rxn, None, None)] = v
                elif set(dims) == set(["Reaction", "Stream"]):
                    for stm in self.context["information"]["rxn"][p]:
                        for rxn in self.context["information"]["rxn"][p][stm]:
                            v = self.context["information"]["rxn"][p][stm][rxn]
                            param_dict[(p, None, rxn, stm, None)] = v
                elif set(dims) == set(["Species", "Reaction"]):
                    for rxn in self.context["information"]["rxn"][p]:
                        for spc in self.context["information"]["rxn"][p][rxn]:
                            v = self.context["information"]["rxn"][p][rxn][spc]
                            param_dict[(p, spc, rxn, None, None)] = v
                else:
                    msg = f"Invalid dimensions for reaction parameter {p}: {dims}"
                    return False, msg

        # Operation
        phenos = []
        phenos.append(self.context["description"]["ac"])
        phenos.append(self.context["description"]["fp"])
        phenos.extend(self.context["description"]["mt"])
        for rxn in self.context["description"]["rxn"]:
            for rxn_pheno in self.context["description"]["rxn"][rxn]:
                if rxn_pheno not in phenos:
                    phenos.append(rxn_pheno)
        
        laws = []
        for law, law_dict in self.entity["law"].items():
            if law_dict["pheno"] in phenos:
                laws.append(law)
            if law_dict["pheno"] in self.context["description"]["mt"]:
                assoc_gas_law = self.entity["law"][law]["assoc_gas_law"]
                if assoc_gas_law and self.context["basic"]["gas"]:
                    if assoc_gas_law not in laws:
                        laws.append(assoc_gas_law)
                assoc_sld_law = self.entity["law"][law]["assoc_sld_law"]
                if assoc_sld_law and self.context["basic"]["sld"]:
                    if assoc_sld_law not in laws:
                        laws.append(assoc_sld_law)
        laws.extend(self.context["description"]["param_law"].values())
        
        op_ps = []
        for law in laws:
            for p in self.entity["law"][law]["vars"]:
                p_class = self.entity["var"][p]["class"]
                if p_class == "OperationParameter" and p not in op_ps:
                    op_ps.append(p)
        for p in op_ps:
            dims = self.entity["var"][p]["dims"]
            if set(dims) == set([]):
                param_dict[(p, None, None, None, None)] = None
            elif set(dims) == set(["Stream"]):
                for stm in self.context["basic"]["stm"]:
                    param_dict[(p, None, None, stm, None)] = None
            elif set(dims) == set(["Species", "Stream"]):
                for stm in self.context["basic"]["stm"]:
                    for spc in self.context["basic"]["stm"][stm]["spc"]:
                        param_dict[(p, spc, None, stm, None)] = None
            elif set(dims) == set(["Species", "Gas"]):
                for gas in self.context["basic"]["gas"]:
                    for spc in self.context["basic"]["gas"][gas]["spc"]:
                        param_dict[(p, spc, None, None, gas)] = None
            elif set(dims) == set(["Species", "Solid"]):
                for sld in self.context["basic"]["sld"]:
                    for spc in self.context["basic"]["sld"][sld]["spc"]:
                        param_dict[(p, spc, None, None, sld)] = None
            else:
                msg = f"Invalid dimensions for operation parameter {p}: {dims}"
                return False, msg

        if self.param_dict:
            for k, v in zip(self.param_dict["key"], self.param_dict["value"]):
                param_dict[tuple(k)] = v
        return True, param_dict

    def to_flowchart(self):
        # accumulation -> parameter / rate_variable -> parameter
        flowchart = {"chart": [[], [], []], "link": []}
        
        accumulation_chart = {}
        phenomenon = self.context["description"]["accumulation"]
        law = [l for l in self.entity["law"] if self.entity["law"][l]["phenomenon"] == phenomenon][0]
        accumulation_parameters = self.entity["law"][law]["model_variables"]
        accumulation_symbols = [self.entity["model_variable"][p]["symbol"].strip() for p in accumulation_parameters]
        molecular_transport_phenomena = self.context["description"]["molecular_transport"]
        parameter_law = self.context["description"]["parameter_law"]
        reaction_phenomena = list(set([p for r in self.context["description"]["reaction"] for p in self.context["description"]["reaction"][r]]))
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
        
        phenomenon = self.context["description"]["flow_pattern"]
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

        phenomena = self.context["description"]["molecular_transport"]
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
        for reaction in self.context["description"]["reaction"]:
            phenomena = self.context["description"]["reaction"][reaction]
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
                    formula["detail_formula"] = f'<div style="white-space: pre-line; color: gray;">{self.context["information"]["reactions"][reaction][self.entity["law"][law]["phenomenon"]].replace(" ", "&nbsp;")}</div>'
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

    def index_sym(self, fml, var, ind):
        sym = MMLExpression(self.entity["var"][var]["sym"]).to_numpy()
        for pat, rep in self.sym_patterns:
            pat = pat.replace("[sym]", sym)
            rep = rep.replace("[sym]", sym + ind)
            fml = re.sub(pat, rep, fml)
        return fml
    
    def index_fml(self, fml, vars, dims, ind):
        dim_ind = sorted(list(zip(dims, ind)), key=lambda d: self.dim2pos[d[0]])
        dims, ind = zip(*dim_ind)
        for var in vars:
            var_dims = self.entity["var"][var]["dims"]
            var_dims = sorted(var_dims, key=lambda d: self.dim2pos[d])
            var_ind = []
            for dim in var_dims:
                if dim in dims:
                    var_ind.append(str(ind[dims.index(dim)]))
                else:
                    var_ind.append(":")
            while var_ind and var_ind[-1] == ":":
                var_ind.pop()
            if not var_ind:
                var_ind = ""
            else:
                var_ind = f"[{', '.join(var_ind)}]"
            fml = self.index_sym(fml, var, var_ind)
        return fml
    
    def process_codes(self, codes):
        spcs = self.context["basic"]["spc"]
        codes = codes.replace("exp", "np.exp")
        codes = codes.replace("sum", "np.sum")
        for i, s in enumerate(spcs):
            codes = re.sub(r"['\"]" + s + r"['\"]", f"{i}", codes)
        sentences = codes.split("\n")
        codes = []
        for sentence in sentences:
            if ":" in sentence or "=" in sentence:
                codes.append(sentence)
            else:
                sentence = re.sub('^( *)([^ ].*)$', r'\1return \2', sentence)
                codes.append(sentence)
        return codes

    def to_scipy_model(self):
        """The converted scipy model is given as:
        
        param_dict: `{(parameter, species, reaction, stream, gas/solid): value}`
        def simulation(param_dict):
            p = list(param_dict.values())
            def derivative(c, x):
            def boundary(c_a, c_b):
            res = solve_bvp(derivative, boundary, x_init, c_init)
            return res.x, post_process(res.y)

        Returns:
            str: converted scipy model
        """

        # Validate reaction
        flag, res = self.validate_rxn()
        if not flag:
            return False, res

        # Model
        model = ScipyModel()
        # model.add_header(self.context)
        model.add_lib()

        # Parameter
        flag, res = self.extract_param_dict()
        if not flag:
            return False, res
        param_dict = res
        model.add("param_dict = {", 0)
        for k, v in res.items():
            model.add(f"{k}: {v},", 1)
        model.add("}", 0)
        model.add("", 0)

        # Law
        pheno2law = {}
        for pheno in self.entity["pheno"]:
            pheno2law[pheno] = []
            for law, law_dict in self.entity["law"].items():
                if law_dict["pheno"] == pheno:
                    pheno2law[pheno].append(law)
        law2var = {}
        for var, var_dict in self.entity["var"].items():
            for law in var_dict["laws"]:
                law2var[law] = var
            
        ac_laws = pheno2law[self.context["description"]["ac"]]
        ac_law = [law for law in ac_laws if law2var[law] != "Concentration"][0]
        ac_vars = self.entity["law"][ac_law]["vars"]
        ac_opt_vars = self.entity["law"][ac_law]["opt_vars"]

        conc_laws = [law for law in ac_laws if law2var[law] == "Concentration"]
        if conc_laws:
            conc_law = conc_laws[0]
            conc_vars = self.entity["law"][conc_law]["vars"]
        else:
            conc_law = None
            conc_vars = []
        
        # r_t_g, r_t_s
        mt_laws, mt_vars = [], []
        for mt_pheno in self.context["description"]["mt"]:
            for law in pheno2law[mt_pheno]:
                if law2var[law] in ac_opt_vars:
                    mt_laws.append(law)
                    mt_vars.extend(self.entity["law"][law]["vars"])
        
        assoc_gas_laws, assoc_sld_laws = [], []
        for mt_law in mt_laws:
            assoc_gas_law = self.entity["law"][mt_law]["assoc_gas_law"]
            if assoc_gas_law and assoc_gas_law not in assoc_gas_laws:
                assoc_gas_laws.append(assoc_gas_law)
            assoc_sld_law = self.entity["law"][mt_law]["assoc_sld_law"]
            if assoc_sld_law and assoc_sld_law not in assoc_sld_laws:
                assoc_sld_laws.append(assoc_sld_law)
        if len(assoc_gas_laws) > 1:
            return False, "Multiple associated gas law associated with mass transport."
        else:
            assoc_gas_law = assoc_gas_laws[0] if assoc_gas_laws else None
        if len(assoc_sld_laws) > 1:
            return False, "Multiple associated solid law associated with mass transport."
        else:
            assoc_sld_law = assoc_sld_laws[0] if assoc_sld_laws else None

        # c_g_star, c_s_star
        me_laws, me_vars = [], []
        for var in mt_vars:
            if var != "Concentration" and self.entity["var"][var]["laws"]:
                law = self.context["description"]["param_law"][var]
                law_dict = self.entity["law"][law]
                if law_dict["pheno"] in self.context["description"]["me"]:
                    me_laws.append(law)
                    me_vars.extend(law_dict["vars"])

        fp_laws, fp_vars = [], []
        # flow_velocity
        for var in ac_vars:
            for law in pheno2law[self.context["description"]["fp"]]:
                if law in self.entity["var"][var]["laws"]:
                    fp_laws.append(law)
                    fp_vars.extend(law_dict["vars"])
        # mixing_time
        for var in mt_vars:
            if var != "Concentration" and self.entity["var"][var]["laws"]:
                law = self.context["description"]["param_law"][var]
                law_dict = self.entity["law"][law]
                if law_dict["pheno"] == self.context["description"]["fp"]:
                    fp_laws.append(law)
                    fp_vars.extend(law_dict["vars"])

        # film_thickness
        sub_fp_laws, sub_fp_vars = [], []
        for var in fp_vars:
            if self.entity["var"][var]["laws"]:
                law = self.context["description"]["param_law"][var]
                law_dict = self.entity["law"][law]
                if law in pheno2law[self.context["description"]["fp"]]:
                    sub_fp_laws.append(law)
                    sub_fp_vars.extend(law_dict["vars"])

        rxn_laws, rxn_vars = {}, {}
        for rxn, rxn_phenos in self.context["description"]["rxn"].items():
            rxn_laws[rxn], rxn_vars[rxn] = [], []
            for rxn_pheno in rxn_phenos:
                for law in pheno2law[rxn_pheno]:
                    rxn_laws[rxn].append(law)
                    rxn_vars[rxn].extend(self.entity["law"][law]["vars"])
                    if "Stoichiometric_Coefficient" not in rxn_vars[rxn]:
                        rxn_vars[rxn].append("Stoichiometric_Coefficient")

        model_vars = []
        model_vars.extend(ac_vars)
        model_vars.extend(mt_vars)
        model_vars.extend(me_vars)
        model_vars.extend(fp_vars)
        model_vars.extend(sub_fp_vars)
        model_vars.extend(conc_vars)
        for rxn in rxn_vars:
            for var in rxn_vars[rxn]:
                if var not in model_vars:
                    model_vars.append(var)
        # definition
        for var in model_vars:
            for law in self.entity["var"][var]["laws"]:
                if not self.entity["law"][law]["pheno"]:
                    model_vars.extend(self.entity["law"][law]["vars"])
        model_vars = list(set(model_vars))

        fia = [self.entity["law"][law]["fml_int_with_accum"] for law in mt_laws]
        fia = [f for f in fia if f]
        assert len(fia) <= 1, "Multiple formulas integrated with accumulation"
        fia = fia[0] if fia else None

        # Basic
        spcs = self.context["basic"]["spc"]
        rxns = self.context["basic"]["rxn"]
        stms = list(self.context["basic"]["stm"].keys())
        slds = list(self.context["basic"]["sld"].keys())
        gass = list(self.context["basic"]["gas"].keys())
        nspc = len(spcs)
        nrxn = len(rxns)
        nstm = len(stms)
        nsld = len(slds)
        ngas = len(gass)
        dim2size = {
            "Species": nspc,
            "Reaction": nrxn,
            "Stream": nstm,
            "Solid": nsld,
            "Gas": ngas
        }

        # Simulate function
        if self.context["type"] not in ["dynamic", "steady"]:
            return False, f"Unknown operation type: {self.context['type']}"
        if self.context["type"] == "steady":
            model.add("def simulate(param_dict):", 0)
        if self.context["type"] == "dynamic":
            model.add("def simulate(param_dict, op_data):", 0)
            model.add("# dynamic parameter", 1)
            dvar = self.entity["law"][ac_law]["diff_var"]
            dsym = MMLExpression(self.entity["var"][dvar]["sym"]).to_numpy()
            model.add(f"if '{dsym}' not in op_data:", 1)
            model.add("return None", 2)
            model.add("interps = {}", 1)
            op_vars = [var for var in model_vars if self.entity["var"][var]["class"]
                == "OperationParameter" and not self.entity["var"][var]["dims"] 
                and var != self.entity["law"][ac_law]["int_up_lim"]]
            op_syms = [MMLExpression(
                self.entity["var"][var]["sym"]).to_numpy() for var in op_vars]
            for op_sym in op_syms:
                model.add(f"interps['{op_sym}'] = "
                    f"interp1d(op_data['{dsym}'], op_data['{op_sym}'])", 1)
            model.add("", 0)
        model.add("# parameter", 1)
        model.add("p = list(param_dict.values())", 1)

        # Parameter setup
        keys = list(param_dict.keys())
        for var in model_vars:
            if self.context["type"] == "dynamic" and var in op_vars:
                continue
            var_dict = self.entity["var"][var]
            sym = MMLExpression(var_dict["sym"]).to_numpy()
            dims = var_dict["dims"]
            
            if var_dict["class"] == "Constant":
                model.add(f'{sym} = {var_dict["val"]}', 1)            
            if "Parameter" not in var_dict["class"]:
                continue
            if var_dict["laws"]:
                continue

            if set(dims) == set([]):
                ind = keys.index((var, None, None, None, None))
                model.add(f'{sym} = p[{ind}]', 1)
            elif set(dims) == set(["Species"]):
                model.add(f"{sym} = np.zeros({nspc}, dtype=np.float64)", 1)
                for i, spc in enumerate(spcs):
                    ind = keys.index((var, spc, None, None, None))
                    model.add(f'{sym}[{i}] = p[{ind}]', 1)
            elif set(dims) == set(["Reaction"]):
                model.add(f"{sym} = np.zeros({nrxn}, dtype=np.float64)", 1)
                for i, rxn in enumerate(rxns):
                    if (var, None, rxn, None, None) in keys:
                        ind = keys.index((var, None, rxn, None, None))
                        model.add(f'{sym}[{i}] = p[{ind}]', 1)
            elif set(dims) == set(["Stream"]):
                model.add(f"{sym} = np.zeros({nstm}, dtype=np.float64)", 1)
                for i, stm in enumerate(stms):
                    ind = keys.index((var, None, None, stm, None))
                    model.add(f"{sym}[{i}] = p[{ind}]", 1)
            elif set(dims) == set(["Gas"]):
                model.add(f"{sym} = np.zeros({ngas}, dtype=np.float64)", 1)
                for i, gas in enumerate(gass):
                    ind = keys.index((var, None, None, None, gas))
                    model.add(f"{sym}[{i}] = p[{ind}]", 1)
            elif set(dims) == set(["Solid"]):
                model.add(f"{sym} = np.zeros({nsld}, dtype=np.float64)", 1)
                for i, sld in enumerate(slds):
                    ind = keys.index((var, None, None, None, sld))
                    model.add(f"{sym}[{i}] = p[{ind}]", 1)
            elif set(dims) == set(["Species", "Reaction"]):
                model.add(f"{sym} = np.zeros({nrxn, nspc}, dtype=np.float64)", 1)
                for i, rxn in enumerate(rxns):
                    for j, spc in enumerate(spcs):
                        if (var, spc, rxn, None, None) in keys:
                            ind = keys.index((var, spc, rxn, None, None))
                            model.add(f'{sym}[{i}, {j}] = p[{ind}]', 1)
            elif set(dims) == set(["Species", "Stream"]):
                model.add(f"{sym} = np.zeros({nstm, nspc}, dtype=np.float64)", 1)
                for i, stm in enumerate(stms):
                    for j, spc in enumerate(spcs):
                        if (var, spc, None, stm, None) in keys:
                            ind = keys.index((var, spc, None, stm, None))
                            model.add(f'{sym}[{i}, {j}] = p[{ind}]', 1)
            elif set(dims) == set(["Species", "Gas"]):
                model.add(f"{sym} = np.zeros({ngas, nspc}, dtype=np.float64)", 1)
                for i, gas in enumerate(gass):
                    for j, spc in enumerate(spcs):
                        if (var, spc, None, None, gas) in keys:
                            ind = keys.index((var, spc, None, None, gas))
                            model.add(f'{sym}[{i}, {j}] = p[{ind}]', 1)
            elif set(dims) == set(["Species", "Solid"]):
                model.add(f"{sym} = np.zeros({nsld, nspc}, dtype=np.float64)", 1)
                for i, sld in enumerate(slds):
                    for j, spc in enumerate(spcs):
                        if (var, spc, None, None, sld) in keys:
                            ind = keys.index((var, spc, None, None, sld))
                            model.add(f'{sym}[{i}, {j}] = p[{ind}]', 1)
            elif set(dims) == set(["Reaction", "Stream"]):
                model.add(f"{sym} = np.zeros({nstm, nrxn}, dtype=np.float64)", 1)
                for i, stm in enumerate(stms):
                    for j, rxn in enumerate(rxns):
                        if (var, None, rxn, stm, None) in keys:
                            ind = keys.index((var, None, rxn, stm, None))
                            model.add(f'{sym}[{i}, {j}] = p[{ind}]', 1)
            elif set(dims) == set(["Species", "Stream", "Gas"]):
                model.add(f"{sym} = np.zeros({ngas, nstm, nrxn}, dtype=np.float64)", 1)
                for i, gas in enumerate(gass):
                    for j, stm in enumerate(stms):
                        for k, spc in enumerate(spcs):
                            if (var, spc, None, stm, gas) in keys:
                                ind = keys.index((var, spc, None, stm, gas))
                                model.add(f'{sym}[{i}, {j}, {k}] = p[{ind}]', 1)
            elif set(dims) == set(["Species", "Stream", "Solid"]):
                model.add(f"{sym} = np.zeros({nsld, nstm, nrxn}, dtype=np.float64)", 1)
                for i, sld in enumerate(slds):
                    for j, stm in enumerate(stms):
                        for k, spc in enumerate(spcs):
                            if (var, spc, None, stm, sld) in keys:
                                ind = keys.index((var, spc, None, stm, sld))
                                model.add(f'{sym}[{i}, {j}, {k}] = p[{ind}]', 1)
            else:
                return False, f"Unknown parameter {var} with dimensions: {dims}"
            
            unit = self.entity["var"][var]["unit"]
            if unit:
                rto = self.entity["unit"][unit]["rto"]
                intcpt = self.entity["unit"][unit]["intcpt"]
                if rto:
                    model.add(f"{sym} *= {rto}", 1)
                if intcpt:
                    model.add(f"{sym} += {intcpt}", 1)
        model.add("", 0)

        # Flow pattern
        model.add("# flow pattern", 1)
        for law in sub_fp_laws + fp_laws:
            vars = self.entity["law"][law]["vars"]
            syms = [self.entity["var"][var]["sym"] for var in vars]
            syms = [MMLExpression(sym).to_numpy() for sym in syms]
            var = law2var[law]
            sym = MMLExpression(self.entity["var"][var]["sym"]).to_numpy()
            code = MMLExpression(self.entity["law"][law]["fml"]).to_numpy()
            if "\n" in code:
                func_head = model.add_func(var, syms, code, 1)
                model.add(f"{sym} = {func_head}", 1)
            else:
                model.add(f"{sym} = {code}", 1)
            model.add("", 0)
        model.add("", 0)

        # Concentration derivative
        if self.context["description"]["ac"] in ["Batch", "Continuous"]:
            ivar = self.entity["law"][ac_law]["int_var"]
            isym = MMLExpression(self.entity["var"][ivar]["sym"]).to_numpy()
            dvar = self.entity["law"][ac_law]["diff_var"]
            dsym = MMLExpression(self.entity["var"][dvar]["sym"]).to_numpy()
            model.add(f"def derivative({dsym}, {isym}):", 1)
            if self.context["type"] == "dynamic":
                for op_sym in op_syms:
                    model.add(f"{op_sym} = interps['{op_sym}']({dsym})", 2)
            if fia:
                ivar_shape = (len(stms), len(spcs) * 2)
                ivar_num = len(stms) * len(spcs) * 2
            else:
                ivar_shape = (len(stms), len(spcs))
                ivar_num = len(stms) * len(spcs)
            if assoc_gas_law and ngas:
                gvar = self.entity["law"][assoc_gas_law]["int_var"]
                gsym = MMLExpression(self.entity["var"][gvar]["sym"]).to_numpy()
                gind = f"[{ivar_num}:{ivar_num + ngas}]"
                model.add(f"{gsym} = np.array({isym}{gind}, dtype=np.float64)", 2)
            if assoc_gas_law and ngas:
                svar = self.entity["law"][assoc_sld_law]["int_var"]
                ssym = MMLExpression(self.entity["var"][svar]["sym"]).to_numpy()
                sind = f"[{ivar_num + ngas}:{ivar_num + ngas + nsld}]"
                model.add(f"{ssym} = np.array({isym}{sind}, dtype=np.float64)", 2)
            model.add(f"{isym} = np.array({isym}[:{ivar_num}], dtype=np.float64)", 2)
            model.add(f"{isym} = {isym}.reshape({ivar_shape})", 2)
        model.add("", 0)

        # Concentration
        if conc_law:
            model.add("# concentration", 2)
            var = law2var[conc_law]
            sym = MMLExpression(self.entity["var"][var]["sym"]).to_numpy()
            fml = MMLExpression(self.entity["law"][conc_law]["fml"]).to_numpy()
            vars = self.entity["law"][conc_law]["vars"]
            model.add(f"{sym} = np.zeros({ivar_shape}, dtype=np.float64)", 2)
            dims = ["Stream"]
            sizes = [dim2size[dim] for dim in dims]
            for ind in itertools.product(*[list(range(size)) for size in sizes]):
                ind_sym = self.index_fml(sym, [var], dims, ind)
                ind_fml = self.index_fml(fml, vars, dims, ind)
                model.add(f"{ind_sym} = {ind_fml}", 2)
        model.add("", 0)

        # Concentration derivative: definition
        model.add("# definition", 2)
        for var in vars:
            var_dict = self.entity["var"][var]
            if var_dict["class"] != "PhysicsParameter":
                continue
            if len(var_dict["laws"]) != 1:
                continue
            law = var_dict["laws"][0]
            law_dict = self.entity["law"][law]
            if law_dict["pheno"]:
                continue
            var = law2var[law]
            vars = self.entity["law"][law]["vars"]
            sym = MMLExpression(var_dict["sym"]).to_numpy()
            fml = MMLExpression(law_dict["fml"]).to_numpy()
            dims = ["Stream"]
            sizes = [dim2size[dim] for dim in dims]
            for ind in itertools.product(*[list(range(size)) for size in sizes]):
                ind_sym = self.index_fml(sym, [var], dims, ind)
                ind_fml = self.index_fml(fml, vars, dims, ind)
                model.add(f"{ind_sym} = {ind_fml}", 2)
            model.add("", 0)
        model.add("", 0)

        # Concentration derivative: reaction
        model.add("# reaction", 2)
        var = "Reaction_Rate"
        sym = MMLExpression(self.entity["var"][var]["sym"]).to_numpy()
        model.add(f"{sym} = np.zeros({nstm, nrxn}, dtype=np.float64)", 2)
        for i, stm in enumerate(stms):
            for rxn in self.context["basic"]["stm"][stm]["rxn"]:
                j = self.context["basic"]["rxn"].index(rxn)
                model.add(f"# stream: {stm}, reaction: {rxn}", 2)
                fml = []
                vars = []
                for sub_law in rxn_laws[rxn]:
                    sub_law_dict = self.entity["law"][sub_law]
                    sub_fml = MMLExpression(sub_law_dict["fml"]).to_numpy()
                    sub_vars = sub_law_dict["vars"]
                    if sub_fml == "specifically defined":
                        sub_syms = [self.entity["var"][v]["sym"] for v in sub_vars]
                        sub_syms = [MMLExpression(s).to_numpy() for s in sub_syms]
                        sub_pheno = sub_law_dict["pheno"]
                        sub_pheno = f"{sub_pheno.lower().replace('-', '_')}"
                        sub_head = f"calc_{sub_pheno}_term({', '.join(sub_syms)})"
                        model.add(f"def {sub_head}:", 2)
                        codes = self.context["information"]["rxn"][rxn][sub_law]
                        codes = self.process_codes(codes)
                        for code in codes:
                            model.add(code, 3)
                        fml.append(sub_head)
                    else:
                        fml.append(sub_fml)
                    vars.extend(sub_vars)
                fml = " * ".join(fml)
                dims = ["Stream", "Reaction"]
                ind = [i, j]
                ind_sym = self.index_fml(sym, [var], dims, ind)
                ind_fml = self.index_fml(fml, vars, dims, ind)
                model.add(f"{ind_sym} = {ind_fml}", 2)
                model.add("", 0)

        # Concentration derivative: mass equilibrium
        model.add("# mass equilibrium", 2)
        for law in me_laws:
            var = law2var[law]
            sym = MMLExpression(self.entity["var"][var]["sym"]).to_numpy()
            vars = self.entity["law"][law]["vars"]
            syms = [self.entity["var"][var]["sym"] for var in vars]
            syms = [MMLExpression(sym).to_numpy() for sym in syms]
            dims = self.entity["var"][var]["dims"]
            dims = sorted(dims, key=lambda d: self.dim2pos[d])
            if set(dims) == set(["Gas", "Stream", "Species"]):
                pha_dim, phas = "gas", gass
            elif set(dims) == set(["Solid", "Stream", "Species"]):
                pha_dim, phas = "sld", slds
            else:
                msg = f"Invalid dimensions for mass equilibrium parameter {var}: {dims}"
                return False, msg
            model.add(f"{sym} = np.zeros({len(phas), nstm, nspc}, dtype=np.float64)", 2)
            fml = MMLExpression(self.entity["law"][law]["fml"]).to_numpy()
            if fml == "specifically defined":
                pheno = self.entity["law"][law]["pheno"]
                pheno = f"{pheno.lower().replace('-', '_')}"
                head = f"calc_{pheno}_term({', '.join(syms)})"
                fml = head
                for pha in phas:
                    me_spcs = self.context["basic"][pha_dim][pha]["spc"]
                    prod = itertools.product([pha], stms, me_spcs)
                    for pha, stm, spc in prod:
                        model.add(f"def {head}:", 2)
                        codes = self.context["information"]["me"][law][pha][stm][spc]
                        codes = self.process_codes(codes)
                        for code in codes:
                            model.add(code, 3)
                        fml = head
                        ind = [phas.index(pha), stms.index(stm), spcs.index(spc)]
                        ind_sym = self.index_fml(sym, [var], dims, ind)
                        ind_fml = self.index_fml(fml, vars, ["Stream"], ind)
                        model.add(f"{ind_sym} = {ind_fml}", 2)
            else:
                for pha in phas:
                    me_spcs = self.context["basic"][pha_dim][pha]["spc"]
                    prod = itertools.product([pha], stms, me_spcs)
                    for pha, stm, spc in prod:
                        ind = [phas.index(pha), stms.index(stm), spcs.index(spc)]
                        ind_sym = self.index_fml(sym, [var], dims, ind)
                        ind_fml = self.index_fml(fml, vars, dims, ind)
                        model.add(f"{ind_sym} = {ind_fml}", 2)
            model.add("", 0)

        # Concentration derivative: mass transport
        model.add("# mass transport", 2)
        mt_vars = []
        for law in mt_laws:
            if self.entity["law"][law]["fml_int_with_accum"]:
                continue
            var = law2var[law]
            sym = MMLExpression(self.entity["var"][var]["sym"]).to_numpy()
            vars = self.entity["law"][law]["vars"]
            mass_vars = ["Mass", "Mass_Solid", "Mass_Used_Gas"]
            vars = [var for var in vars if var not in mass_vars]
            dims = self.entity["var"][var]["dims"]
            dims = sorted(dims, key=lambda d: self.dim2pos[d])
            if set(dims) == set(["Gas", "Stream", "Species"]):
                pha_dim, pha_dim_short, phas = "Gas", "gas", gass
            elif set(dims) == set(["Solid", "Stream", "Species"]):
                pha_dim, pha_dim_short, phas = "Solid", "sld", slds
            else:
                msg = f"Invalid dimensions for mass equilibrium parameter {var}: {dims}"
                return False, msg
            model.add(f"{sym} = np.zeros({len(phas), nstm, nspc}, dtype=np.float64)", 2)
            fml = MMLExpression(self.entity["law"][law]["fml"]).to_numpy()
            for pha in phas:
                me_spcs = self.context["basic"][pha_dim_short][pha]["spc"]
                prod = itertools.product([pha], stms, me_spcs)
                for pha, stm, spc in prod:
                    ind = [phas.index(pha), stms.index(stm), spcs.index(spc)]
                    ind_sym = self.index_fml(sym, [var], dims, ind)
                    ind_fml = self.index_fml(fml, vars, dims, ind)
                    ind_fml = self.index_fml(ind_fml, mass_vars, [pha_dim], [ind[0]])
                    ind_fml = self.index_fml(ind_fml, mass_vars, ["Stream"], [ind[1]])
                    model.add(f"{ind_sym} = {ind_fml}", 2)
                    if "Solid" in dims:
                        mass_var = "Mass_Solid"
                        mass_sym = self.entity["var"][mass_var]["sym"]
                        mass_sym = MMLExpression(mass_sym).to_numpy()
                        model.add(f"if {mass_sym}[{ind[0]}] < 1e-3:", 2)
                        model.add(f"{ind_sym} = 0", 3)
            model.add("", 0)

        # Concentration derivative: accumulation
        model.add("# accumulation", 2)
        assoc_gas_law = self.entity["law"][ac_law]["assoc_gas_law"]
        if assoc_gas_law and self.context["basic"]["gas"]:
            gas_var = law2var[assoc_gas_law]
            gas_fml = MMLExpression(self.entity["law"][assoc_gas_law]).to_numpy()
            gas_sym = MMLExpression(self.entity["var"][gas_var]).to_numpy()
            model.add(f"{gas_sym} = {gas_fml}", 2)

        opt_laws = mt_laws + [law for laws in rxn_laws.values() for law in laws]
        opt_vars = list(set([law2var[law] for law in opt_laws]))
        opt_vars = [var for var in opt_vars if var in ac_opt_vars]
        opt_syms = [self.entity["var"][opt_var]["sym"] for opt_var in opt_vars]
        opt_syms = [MMLExpression(opt_sym).to_numpy() for opt_sym in opt_syms]
        
        if fia:
            fml = MMLExpression(fia).to_numpy()
            for opt_sym in opt_syms:
                fml = re.sub(f"\[([^\[\]]*{opt_sym}[^\[\]]*)\]", r"\1", fml)
            fml = re.sub("\[[^\[\]]*\]", "0", fml)
            fml = fml.replace("dc / dx", f"c[:, {nspc}:]")
            model.add(f"dc = np.zeros({nstm, nspc * 2}, dtype=np.float64)", 2)
            model.add(f"dc[:, :{nspc}] = c[:, {nspc}:]", 2)
            model.add(f"dc[:, {nspc}:] = {fml}", 2)
        else:
            model.add(f"d{isym} = np.zeros({nstm, nspc}, dtype=np.float64)", 2)
            fml = MMLExpression(self.entity["law"][ac_law]["fml"]).to_numpy()
            for opt_sym in opt_syms:
                fml = re.sub(f"\[([^\[\]]*{opt_sym}[^\[\]]*)\]", r"\1", fml)
            fml = re.sub("\[[^\[\]]*\]", "0", fml)
            vars = ac_vars + ac_opt_vars
            dims = ["Stream", "Species"]
            sizes = [dim2size[dim] for dim in dims]
            for ind in itertools.product(*[list(range(size)) for size in sizes]):
                ind_isym = self.index_fml(isym, [ivar], dims, ind)
                ind_fml = self.index_fml(fml, vars, dims, ind)
                model.add(f"d{ind_isym} = {ind_fml}", 2)
            
            assoc_isyms = []
            assoc_iinds = []
            assoc_ivals = []
            for mt_law in mt_laws:
                if self.entity["law"][mt_law]["assoc_gas_law"]:
                    assoc_gas_law = self.entity["law"][mt_law]["assoc_gas_law"]
                    gas_ivar = self.entity["law"][assoc_gas_law]["int_var"]
                    gas_isym = self.entity["var"][gas_ivar]["sym"]
                    gas_isym = MMLExpression(gas_isym).to_numpy()
                    fml = self.entity["law"][assoc_gas_law]["fml"]
                    fml = MMLExpression(fml).to_numpy()
                    vars = self.entity["law"][assoc_gas_law]["vars"]
                    shape = f"{ngas, nstm, nspc}"
                    model.add(f"d{gas_isym} = np.zeros({shape}, dtype=np.float64)", 2)
                    gas_int_init_val = self.entity["law"][assoc_gas_law]["int_init_val"]
                    for i, gas in enumerate(gass):
                        for j, stm in enumerate(stms):
                            for spc in self.context["basic"]["gas"][gas]["spc"]:
                                k = spcs.index(spc)
                                assoc_isyms.append(gas_isym)
                                assoc_iinds.append(f"[{i}, {j}, {k}]")
                                if gas_int_init_val:
                                    key = (gas_int_init_val, spc, None, None, gas)
                                    assoc_ivals.append(f"p[{keys.index(key)}]")
                                else:
                                    assoc_ivals.append(0)
                                dims = ["Gas", "Stream", "Species"]
                                ind = [i, j, k]
                                ind_fml = self.index_fml(fml, vars, dims, ind)
                                model.add(f"d{gas_isym}[{i}, {j}, {k}] = {ind_fml}", 2)
                if self.entity["law"][mt_law]["assoc_sld_law"]:
                    assoc_sld_law = self.entity["law"][mt_law]["assoc_sld_law"]
                    sld_ivar = self.entity["law"][assoc_sld_law]["int_var"]
                    sld_isym = self.entity["var"][sld_ivar]["sym"]
                    sld_isym = MMLExpression(sld_isym).to_numpy()
                    fml = self.entity["law"][assoc_sld_law]["fml"]
                    fml = MMLExpression(fml).to_numpy()
                    vars = self.entity["law"][assoc_sld_law]["vars"]
                    shape = f"{nsld, nstm, nspc}"
                    model.add(f"d{sld_isym} = np.zeros({shape}, dtype=np.float64)", 2)
                    sld_int_init_val = self.entity["law"][assoc_sld_law]["int_init_val"]
                    for i, sld in enumerate(slds):
                        for j, stm in enumerate(stms):
                            for spc in self.context["basic"]["sld"][sld]["spc"]:
                                k = spcs.index(spc)
                                assoc_isyms.append(sld_isym)
                                assoc_iinds.append(f"[{i}, {j}, {k}]")
                                if sld_int_init_val:
                                    key = (sld_int_init_val, spc, None, None, sld)
                                    assoc_ivals.append(f"p[{keys.index(key)}]")
                                else:
                                    assoc_ivals.append(0)
                                dims = ["Solid", "Stream", "Species"]
                                ind = [i, j, k]
                                ind_fml = self.index_fml(fml, vars, dims, ind)
                                model.add(f"d{sld_isym}[{i}, {j}, {k}] = {ind_fml}", 2)
        
        model.add("", 0)
        model.add(f"d{isym} = d{isym}.reshape(-1, ).tolist()", 2)
        for sym, ind in zip(assoc_isyms, assoc_iinds):
            model.add(f"d{isym}.append(d{sym}{ind})", 2)
        model.add(f"d{isym} = np.array(d{isym}, dtype=np.float64)", 2)
        model.add(f"return d{isym}", 2)
        model.add("", 0)

        if fia:
            model.add("def derivative_axis(x, c):", 1)
            model.add("return np.stack([derivative(_x, _c) for _x, _c in "
                      "zip(x, c.transpose(1, 0))], axis=1)", 2)
            model.add("", 0)
            model.add("def boundary_func(ca, cb):", 1)
            model.add(f"ca = ca.reshape({nstm, nspc * 2})", 2)
            model.add(f"cb = cb.reshape({nstm, nspc * 2})", 2)
            model.add(f"bc = np.zeros({nstm, nspc * 2}, dtype=np.float64)", 2)
            model.add(
                f"bc[:, :{nspc}] = u * (ca[:, :{nspc}] - c_0) - D * ca[:, {nspc}:]", 2)
            model.add(f"bc[:, {nspc}:] = cb[:, {nspc}:]", 2)
            model.add("return bc.reshape(-1, )", 2)
            model.add("", 0)

        # Solution
        int_up_lim = self.entity["law"][ac_law]["int_up_lim"]
        int_up_lim_sym = MMLExpression(self.entity["var"][int_up_lim]["sym"]).to_numpy()
        if fia:
            model.add(f"{isym} = np.zeros(({nstm * nspc * 2}, 201), dtype=np.float64)", 1)
            model.add(
                f"res = solve_bvp(derivative_axis, boundary_func, {dsym}_eval, c)", 1)
        else:
            model.add(f"{isym}_0 = np.concatenate(["
                      f"{isym}_0.reshape(-1), "
                      f"np.array([{', '.join([str(v) for v in assoc_ivals])}]"
                      ", dtype=np.float64)])", 1)
            if self.context["type"] == "steady":
                model.add(
                    f"{dsym}_eval = "
                    f"np.linspace(0, {int_up_lim_sym}, 201, dtype=np.float64)", 1
                )
                model.add(
                    f"res = solve_ivp(derivative, (0, {int_up_lim_sym}), "
                    f"{isym}_0, t_eval={dsym}_eval, method='LSODA', atol=1e-12)", 1
                )
                model.add(f"if res.success:", 1)
                model.add(f"if np.isnan(res.y).any():", 2)
                model.add(f"return None", 3)
                model.add(f"else:", 2)
            if self.context["type"] == "dynamic":
                model.add(f"t_span = {int_up_lim_sym} / {self.dynamic_segs}", 1)
                if self.context["description"]["ac"] == "Continuous":
                    model.add(f"res = [[0], [{isym}_0], q]", 1)
                if self.context["description"]["ac"] == "Batch":
                    model.add(f"res = [[0], [{isym}_0], None]", 1)
                model.add(f"for i in range({self.dynamic_segs}):", 1)
                model.add(
                    "seg_res = solve_ivp(derivative, (t_span * i, t_span * (i+1)), "
                    f"{isym}_0, t_eval=[t_span * i, t_span * (i+1)], method='LSODA', "
                    "atol=1e-12)", 2
                )
                model.add("if np.isnan(seg_res.y).any():", 2)
                model.add("return None", 3)
                model.add("res[0].append(seg_res.t[-1])", 2)
                model.add("res[1].append(seg_res.y[-1])", 2)
                model.add(f"{isym}_0 = seg_res.y[-1]", 2)
        
        if fia:
            model.add(f"return [res.x.round(6), res.y.round(6)[:{nstm * nspc}], q]", 3)
            model.add(f"else:", 1)
            model.add(f"return None", 2)
        else:
            if self.context["type"] == "steady":
                int_up_lim_unit = self.entity["var"][int_up_lim]["unit"]
                if int_up_lim_unit and self.entity["unit"][int_up_lim_unit]["intcpt"]:
                    intcpt = self.entity["unit"][int_up_lim_unit]["intcpt"]
                    model.add(f"res.t -= {intcpt}", 3)
                if int_up_lim_unit and self.entity["unit"][int_up_lim_unit]["rto"]:
                    rto = self.entity["unit"][int_up_lim_unit]["rto"]
                    model.add(f"res.t /= {rto}", 3)
                if self.context["description"]["ac"] == "Continuous":
                    model.add(f"return [res.t.round(6), res.y.round(6), q]", 3)
                if self.context["description"]["ac"] == "Batch":
                    model.add(f"return [res.t.round(6), res.y.round(6), None]", 3)
                model.add(f"else:", 1)
                model.add(f"return None", 2)
            if self.context["type"] == "dynamic":
                model.add("res[0] = np.array(res[0]).round(6)", 1)
                model.add("res[1] = np.stack(res[1]).round(6)", 1)
                model.add("return res", 1)
        return True, model.get_model()
    

    # def to_pyomo_model(self):
    #     pyomo_model_code = PyomoModelCode()
    #     # pyomo_model_code.add_header(self.context)
    #     pyomo_model_code.add_lib()

    #     # param_dict
    #     param_dict = self.extract_parameter_value()
    #     pyomo_model_code.add("param_dict = {", 0)
    #     for k, v in param_dict.items():
    #         pyomo_model_code.add(f"{k}: {v},", 1)
    #     pyomo_model_code.add("}", 0)
    #     pyomo_model_code.add("", 0)

    #     # law identification
    #     # start from accumulation phenomenon
    #     # flow pattern laws -> subsidiary flow pattern laws
    #     accumulation_phenomenon = self.context["description"]["accumulation"]
    #     flow_pattern_phenomenon = self.context["description"]["flow_pattern"]
    #     molecular_transport_phenomena = self.context["description"]["molecular_transport"]
    #     parameter_law = self.context["description"]["parameter_law"]
    #     reaction_phenomena = self.context["description"]["reaction"]
    #     accumulation_law = [l for l in self.entity["law"] if self.entity["law"][l]["phenomenon"] == accumulation_phenomenon][0]
    #     accumulation_model_variables = self.entity["law"][accumulation_law]["model_variables"]
    #     molecular_transport_laws = [l for l in self.entity["law"] if self.entity["law"][l]["phenomenon"] in molecular_transport_phenomena]
    #     molecular_transport_model_variables = list(set([mv for l in molecular_transport_laws for mv in self.entity["law"][l]["model_variables"]]))
    #     flow_pattern_laws = [l for l in self.entity["law"] for mv in accumulation_model_variables if l in self.entity["model_variable"][mv]["laws"] and self.entity["law"][l]["phenomenon"] == flow_pattern_phenomenon] + \
    #         [parameter_law[mv] for mv in molecular_transport_model_variables if self.entity["model_variable"][mv]["laws"]]
    #     sub_flow_pattern_laws = [parameter_law[p] for p in set([mv for l in flow_pattern_laws for mv in self.entity["law"][l]["model_variables"] if [
    #         l for l in self.entity["model_variable"][mv]["laws"] if self.entity["law"][l]["rule"]]])]
    #     flow_pattern_model_variables = list(set([mv for l in flow_pattern_laws + sub_flow_pattern_laws for mv in self.entity["law"][l]["model_variables"]]))
    #     reaction_laws = {r: [l for l in self.entity["law"] if self.entity["law"][l]["phenomenon"] in p] for r, p in reaction_phenomena.items()}
    #     reaction_model_variables = {r: list(set([mv for l in ls for mv in self.entity["law"][l]["model_variables"]])) for r, ls in reaction_laws.items()}
    #     formula_integrated_with_accumulation = [self.entity["law"][l]["formula_integrated_with_accumulation"] for l in molecular_transport_laws if self.entity["law"][l]["formula_integrated_with_accumulation"]]
    #     if formula_integrated_with_accumulation:
    #         formula_integrated_with_accumulation = formula_integrated_with_accumulation[0]
    #     else:
    #         formula_integrated_with_accumulation = None
    #     model_variables = accumulation_model_variables + molecular_transport_model_variables + flow_pattern_model_variables + [mv for r in reaction_model_variables for mv in reaction_model_variables[r]]
    #     definitions = [self.entity["model_variable"][mv]["definition"] for mv in model_variables if self.entity["model_variable"][mv]["definition"]]
    #     model_variables = model_variables + [mv for d in definitions for mv in self.entity["definition"][d]["model_variables"]]
    #     if self.context["basic"]["reactions"]:
    #         model_variables += ["Coefficient"]
    #     model_variables = list(set(model_variables))

    #     # model basics
    #     parameter_value_keys = list(param_dict.keys())
    #     species = self.context["basic"]["species"]
    #     reactions = self.context["basic"]["reactions"]
    #     liquid_streams = [k for k, v in self.context["information"]["streams"].items() if v["state"] == "liquid"]
    #     gas_streams = [k for k, v in self.context["information"]["streams"].items() if v["state"] == "gaseous"]
    #     solvents = self.context["basic"]["solvents"]
    #     if self.context["description"]["accumulation"] in ["Continuous", "Batch"]:
    #         differential_model_variable = self.entity["law"][accumulation_law]["differential_model_variable"]
    #         differential_model_variable_symbol = MMLExpression(self.entity["model_variable"][differential_model_variable]['symbol']).to_numpy().strip()
        
    #     # simulation function head
    #     pyomo_model_code.add("def simulation(param_dict):", 0)
    #     pyomo_model_code.add("# MODEL DECLARATION", 1)
    #     pyomo_model_code.add("model = environ.ConcreteModel()", 1)
    #     pyomo_model_code.add("", 0)
    #     pyomo_model_code.add("# PARAMETER PART", 1)
    #     pyomo_model_code.add("p = list(param_dict.values())", 1)

    #     # parameter setup
    #     for model_variable in model_variables:
    #         symbol = MMLExpression(self.entity["model_variable"][model_variable]["symbol"]).to_numpy()
    #         model_variable_class = self.entity["model_variable"][model_variable]["class"]
            
    #         if model_variable_class == "Constant":
    #             pyomo_model_code.add(f'{symbol} = {self.entity["model_variable"][model_variable]["value"]}', 1)
    #             if self.entity["model_variable"][model_variable]["unit"] and self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["standard_unit"]:
    #                 pyomo_model_code.add(f'{symbol} *= {self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["ratio_to_standard_unit"]}', 1)
    #             pyomo_model_code.add(f'model.{symbol} = environ.Param(initialize={symbol})', 1)
    #         if "Parameter" not in model_variable_class: continue
            
    #         model_variable_laws = self.entity["model_variable"][model_variable]["laws"]
    #         model_variable_definition = self.entity["model_variable"][model_variable]["definition"]
    #         if model_variable_definition or model_variable_laws: continue
            
    #         model_variable_dimensions = self.entity["model_variable"][model_variable]["dimensions"]
    #         if set(model_variable_dimensions) == set([]):
    #             pyomo_model_code.add(f'{symbol} = p[{parameter_value_keys.index((model_variable, None, None, None, None))}]', 1)
    #             if self.entity["model_variable"][model_variable]["unit"] and self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["standard_unit"]:
    #                 pyomo_model_code.add(f'{symbol} *= {self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["ratio_to_standard_unit"]}', 1)
    #             pyomo_model_code.add(f'model.{symbol} = environ.Param(initialize={symbol})', 1)
    #         if set(model_variable_dimensions) == set(["Reaction"]):
    #             pyomo_model_code.add(f"{symbol} = np.zeros(({len(reactions)}), dtype=np.float64)", 1)
    #             for i, r in enumerate(reactions):
    #                 if (model_variable, None, r, None, None) not in parameter_value_keys: continue
    #                 pyomo_model_code.add(f'{symbol}[{i}] = p[{parameter_value_keys.index((model_variable, None, r, None, None))}]', 1)
    #             if self.entity["model_variable"][model_variable]["unit"] and self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["standard_unit"]:
    #                 pyomo_model_code.add(f'{symbol} *= {self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["ratio_to_standard_unit"]}', 1)
    #             pyomo_model_code.add(f'model.{symbol} = environ.Param(range({len(reactions)}), initialize=dict(np.ndenumerate({symbol})))', 1)
                
    #         if set(model_variable_dimensions) == set(["Reaction", "Solvent"]):
    #             pyomo_model_code.add(f"{symbol} = np.zeros(({len(reactions)}, {len(solvents)}), dtype=np.float64)", 1)
    #             for i, r in enumerate(reactions):
    #                 for j, s in enumerate(solvents):
    #                     if (model_variable, None, r, None, s) not in parameter_value_keys: continue
    #                     pyomo_model_code.add(f'{symbol}[{i}][{j}] = p[{parameter_value_keys.index((model_variable, None, r, None, s))}]', 1)
    #             if self.entity["model_variable"][model_variable]["unit"] and self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["standard_unit"]:
    #                 pyomo_model_code.add(f'{symbol} *= {self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["ratio_to_standard_unit"]}', 1)
    #             pyomo_model_code.add(f'model.{symbol} = environ.Param(range({len(reactions)}), range({len(solvents)}), initialize=dict(np.ndenumerate({symbol})))', 1)
    #         if set(model_variable_dimensions) == set(["Species"]):
    #             pyomo_model_code.add(f"{symbol} = np.zeros(({len(species)}, ), dtype=np.float64)", 1)
    #             for i, s in enumerate(species):
    #                 pyomo_model_code.add(f'{symbol}[{i}] = p[{parameter_value_keys.index((model_variable, s, None, None, None))}]', 1)
    #             if self.entity["model_variable"][model_variable]["unit"] and self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["standard_unit"]:
    #                 pyomo_model_code.add(f'{symbol} *= {self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["ratio_to_standard_unit"]}', 1)
    #             pyomo_model_code.add(f'model.{symbol} = environ.Param(range({len(species)}), initialize=dict(np.ndenumerate({symbol})))', 1)
    #         if set(model_variable_dimensions) == set(["Species", "Reaction"]):
    #             pyomo_model_code.add(f"{symbol} = np.zeros(({len(reactions)}, {len(species)}), dtype=np.float64)", 1)
    #             for i, r in enumerate(reactions):
    #                 for j, s in enumerate(species):
    #                     if (model_variable, s, r, None, None) not in parameter_value_keys: continue
    #                     pyomo_model_code.add(f'{symbol}[{i}][{j}] = p[{parameter_value_keys.index((model_variable, s, r, None, None))}]', 1)
    #             if self.entity["model_variable"][model_variable]["unit"] and self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["standard_unit"]:
    #                 pyomo_model_code.add(f'{symbol} *= {self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["ratio_to_standard_unit"]}', 1)
    #             pyomo_model_code.add(f'model.{symbol} = environ.Param(range({len(reactions)}), range({len(species)}), initialize=dict(np.ndenumerate({symbol})))', 1)
    #         if set(model_variable_dimensions) == set(["Stream"]):
    #             if "Gas" not in model_variable:
    #                 pyomo_model_code.add(f"{symbol} = np.zeros(({len(liquid_streams)}, ), dtype=np.float64)", 1)
    #                 for i, s in enumerate(liquid_streams):
    #                     if (model_variable, None, None, s, None) not in parameter_value_keys: continue
    #                     pyomo_model_code.add(f'{symbol}[{i}] = p[{parameter_value_keys.index((model_variable, None, None, s, None))}]', 1)
    #                 if self.entity["model_variable"][model_variable]["unit"] and self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["standard_unit"]:
    #                     pyomo_model_code.add(f'{symbol} *= {self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["ratio_to_standard_unit"]}', 1)
    #                 pyomo_model_code.add(f'model.{symbol} = environ.Param(range({len(liquid_streams)}), initialize=dict(np.ndenumerate({symbol})))', 1)
    #             else:
    #                 pyomo_model_code.add(f"{symbol} = np.zeros(({len(gas_streams)}, ), dtype=np.float64)", 1)
    #                 for i, s in enumerate(gas_streams):
    #                     if (model_variable, None, None, s, None) not in parameter_value_keys: continue
    #                     pyomo_model_code.add(f'{symbol}[{i}] = p[{parameter_value_keys.index((model_variable, None, None, s, None))}]', 1)
    #                 if self.entity["model_variable"][model_variable]["unit"] and self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["standard_unit"]:
    #                     pyomo_model_code.add(f'{symbol} *= {self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["ratio_to_standard_unit"]}', 1)
    #                 pyomo_model_code.add(f'model.{symbol} = environ.Param(range({len(gas_streams)}), initialize=dict(np.ndenumerate({symbol})))', 1)
    #         if set(model_variable_dimensions) == set(["Stream", "Species"]):
    #             pyomo_model_code.add(f"{symbol} = np.zeros(({len(liquid_streams)}, {len(species)}), dtype=np.float64)", 1)
    #             for i, s in enumerate(liquid_streams):
    #                 for j, sp in enumerate(species):
    #                     if (model_variable, sp, None, s, None) not in parameter_value_keys: continue
    #                     pyomo_model_code.add(f'{symbol}[{i}][{j}] = p[{parameter_value_keys.index((model_variable, sp, None, s, None))}]', 1)
    #             if self.entity["model_variable"][model_variable]["unit"] and self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["standard_unit"]:
    #                 pyomo_model_code.add(f'{symbol} *= {self.entity["unit"][self.entity["model_variable"][model_variable]["unit"]]["ratio_to_standard_unit"]}', 1)
    #             pyomo_model_code.add(f'model.{symbol} = environ.Param(range({len(liquid_streams)}), range({len(species)}), initialize=dict(np.ndenumerate({symbol})))', 1)
    #     pyomo_model_code.add("", 0)

    #     # flow pattern (parameter irrelevant with variable)
    #     pyomo_model_code.add("# FLOW PATTERN PART", 1)
    #     for law in sub_flow_pattern_laws:
    #         model_variables = self.entity["law"][law]["model_variables"]
    #         symbols = [MMLExpression(self.entity["model_variable"][mv]["symbol"]).to_numpy() for mv in model_variables]
    #         for model_variable in [mv for mv in self.entity["model_variable"] if law in self.entity["model_variable"][mv]["laws"]]:
    #             symbol = MMLExpression(self.entity["model_variable"][model_variable]["symbol"]).to_numpy()
    #             formula = MMLExpression(self.entity["law"][law]["formula"]).to_numpy()
    #             pyomo_model_code.add(f"model.{symbol} = environ.Var(within=environ.PositiveReals)", 1)
    #             function_head = pyomo_model_code.add_function(model_variable, symbols, formula, 1)
    #             pyomo_model_code.add(f"def {model_variable.lower()}_rule(model):", 1)
    #             for s in symbols:
    #                 pyomo_model_code.add(f"{s} = np.array(model.{s})", 2)
    #             pyomo_model_code.add(f"return model.{symbol} == {function_head}.item()", 2)
    #             pyomo_model_code.add(f"model.{model_variable.lower()}_constraint = environ.Constraint(rule={model_variable.lower()}_rule)", 1)
    #             pyomo_model_code.add("", 0)
    #     for law in flow_pattern_laws:
    #         law_model_variables = self.entity["law"][law]["model_variables"]
    #         law_symbols = [MMLExpression(self.entity["model_variable"][mv]["symbol"]).to_numpy() for mv in law_model_variables]
    #         for model_variable in [mv for mv in self.entity["model_variable"] if law in self.entity["model_variable"][mv]["laws"]]:
    #             symbol = MMLExpression(self.entity["model_variable"][model_variable]["symbol"]).to_numpy()
    #             formula = MMLExpression(self.entity["law"][law]["formula"]).to_numpy()
    #             pyomo_model_code.add(f"model.{symbol} = environ.Var(within=environ.PositiveReals)", 1)
    #             function_head = pyomo_model_code.add_function(model_variable, law_symbols, formula, 1)
    #             pyomo_model_code.add(f"def {model_variable.lower()}_rule(model):", 1)
    #             for s in law_symbols:
    #                 pyomo_model_code.add(f"{s} = np.array(model.{s})", 2)
    #             pyomo_model_code.add(f"return model.{symbol} == {function_head}.item()", 2)
    #             pyomo_model_code.add(f"model.{model_variable.lower()}_constraint = environ.Constraint(rule={model_variable.lower()}_rule)", 1)
    #             pyomo_model_code.add("", 0)

    #     # concentration axial position derivative function
    #     if self.context["description"]["accumulation"] == "Continuous":
    #         differential_upper_limit = self.entity["law"][accumulation_law]["differential_upper_limit"]
    #         differential_upper_limit_symbol = MMLExpression(self.entity["model_variable"][differential_upper_limit]['symbol']).to_numpy().strip()
    #         pyomo_model_code.add(f"model.{differential_model_variable_symbol} = dae.ContinuousSet(bounds=(0, model.{differential_upper_limit_symbol}.value))", 1)
    #         if formula_integrated_with_accumulation:
    #             pyomo_model_code.add(f"model.c = environ.Var(range({len(liquid_streams)}), range({len(species) * 2}), model.{differential_model_variable_symbol})", 1)
    #         else:
    #             pyomo_model_code.add(f"model.c = environ.Var(range({len(liquid_streams)}), range({len(species)}), model.{differential_model_variable_symbol})", 1)
    #     # TODO: concentration axial position derivative function
    #     if self.context["description"]["accumulation"] == "Batch":
    #         return "Not supported in pyomo mode now."
    #     # concentration error function
    #     if self.context["description"]["accumulation"] == "CSTR":
    #         return "Not supported in pyomo mode now."
    #     pyomo_model_code.add("", 0)

    #     # reaction part
    #     pyomo_model_code.add("# REACTION PART", 1)
    #     reaction_rate_symbol = MMLExpression(self.entity["model_variable"]["Reaction_Rate"]["symbol"]).to_numpy()
    #     if self.context["description"]["accumulation"] in ["Continuous", "Batch"]:
    #         pyomo_model_code.add(f'model.{reaction_rate_symbol} = environ.Var(range({len(liquid_streams)}), range({len(reactions)}), model.{differential_model_variable_symbol})', 1)
    #         pyomo_model_code.add("", 0)
    #     definition_model_variables = list(set([mv for laws in reaction_laws.values() for l in laws for mv in self.entity["law"][l]["model_variables"] if self.entity["model_variable"][mv]["definition"]]))
    #     for definition_model_variable in definition_model_variables:
    #         definition_parameter = self.entity["model_variable"][definition_model_variable]
    #         definition_dimensions = definition_parameter["dimensions"]
    #         symbol = MMLExpression(definition_parameter["symbol"]).to_numpy()
    #         if "Stream" not in definition_dimensions:
    #             pyomo_model_code.add(f'model.{symbol} = environ.Var(model.{differential_model_variable_symbol})', 1)
    #             model_variables = list(set([mv for mv in self.entity["definition"][definition_parameter["definition"]]["model_variables"]]))
    #             parameters = [self.entity["model_variable"][mv] for mv in model_variables]
    #             symbols = [MMLExpression(p["symbol"]).to_numpy() for p in parameters]
    #             formula = MMLExpression(self.entity["definition"][definition_parameter["definition"]]["formula"]).to_numpy()
    #             function_head = pyomo_model_code.add_function(definition_model_variable, symbols, formula, 1)
    #             pyomo_model_code.add(f"def {definition_model_variable.lower()}_rule(model, {differential_model_variable_symbol}):", 1)
    #             for model_variable, s in zip(model_variables, symbols):
    #                 if "Variable" in self.entity["model_variable"][model_variable]["class"] or model_variable == "Concentration":
    #                     dimensions = self.entity["model_variable"][model_variable]["dimensions"]
    #                     pyomo_model_code.add(f"{s} = np.array(model.{s}[{' '.join([':,'] * len(dimensions))} x])", 2)
    #                 else:
    #                     pyomo_model_code.add(f"{s} = np.array(model.{s})", 2)
    #             pyomo_model_code.add(f"return model.{symbol}[{differential_model_variable_symbol}] == {function_head}", 2)
    #             pyomo_model_code.add(f"model.{definition_model_variable.lower()}_constraint = environ.Constraint(rule={definition_model_variable.lower()}_rule)", 1)
    #         else:
    #             pyomo_model_code.add(f'model.{symbol} = environ.Var(range({len(liquid_streams)}), model.{differential_model_variable_symbol})', 1)
    #             model_variables = list(set([mv for mv in self.entity["definition"][definition_parameter["definition"]]["model_variables"]]))
    #             parameters = [self.entity["model_variable"][mv] for mv in model_variables]
    #             symbols = [MMLExpression(p["symbol"]).to_numpy() for p in parameters]
    #             formula = MMLExpression(self.entity["definition"][definition_parameter["definition"]]["formula"]).to_numpy()
    #             function_head = pyomo_model_code.add_function(definition_model_variable, symbols, formula, 1)
    #             pyomo_model_code.add(f"def {definition_model_variable.lower()}_rule(model, i, {differential_model_variable_symbol}):", 1)
    #             for model_variable, s in zip(model_variables, symbols):
    #                 if "Variable" in self.entity["model_variable"][model_variable]["class"] or model_variable == "Concentration":
    #                     dimensions = self.entity["model_variable"][model_variable]["dimensions"]
    #                     pyomo_model_code.add(f"{s} = np.array(model.{s}[{' '.join(['i,' if d == 'Stream' else ':,' for d in dimensions])} x])", 2)
    #                 else:
    #                     pyomo_model_code.add(f"{s} = np.array(model.{s})", 2)
    #             pyomo_model_code.add(f"return model.{symbol}[{differential_model_variable_symbol}] == {function_head}", 2)
    #             pyomo_model_code.add(f"model.{definition_model_variable.lower()}_constraint = environ.Constraint(rule={definition_model_variable.lower()}_rule)", 1)
    #         pyomo_model_code.add("", 0)
        
    #     if self.context["description"]["accumulation"] in ["Continuous", "Batch"]:
    #         for stream_index, stream in enumerate(liquid_streams):
    #             for reaction_index, reaction in enumerate(reactions):
    #                 if reaction not in self.context["information"]["streams"][stream]["reactions"]: continue
    #                 solvent_index = solvents.index(self.context["information"]["streams"][stream]["solvent"])
    #                 pyomo_model_code.add(f"# stream: {stream}, reaction: {reaction}", 1)
    #                 laws = reaction_laws[reaction]
    #                 reaction_formulas = [self.entity["law"][l]["formula"] for l in laws if "specifically defined" not in self.entity["law"][l]["formula"]]
    #                 reaction_formulas = [MMLExpression(f).to_numpy() for f in reaction_formulas]
    #                 model_variables = [mv for l in laws for mv in self.entity["law"][l]["model_variables"]]
    #                 parameters = [self.entity["model_variable"][mv] for mv in model_variables]
    #                 symbols = [MMLExpression(p["symbol"]).to_numpy() for p in parameters]
                    
    #                 reaction_special_laws = [l for l in laws if "specifically defined" in self.entity["law"][l]["formula"]]
    #                 reaction_special_phenomena = [self.entity["law"][l]["phenomenon"] for l in reaction_special_laws]
    #                 reaction_special_formulas = [self.context["information"]["reactions"][reaction][p] for p in reaction_special_phenomena]
    #                 for phenomenon, formula, law in zip(reaction_special_phenomena, reaction_special_formulas, reaction_special_laws):
    #                     special_model_variables = self.entity["law"][law]["model_variables"]
    #                     special_parameters = [self.entity["model_variable"][mv] for mv in special_model_variables]
    #                     special_symbols = [MMLExpression(p["symbol"]).to_numpy() for p in special_parameters]
    #                     formula_fun = f'calc_reaction_term_{phenomenon.lower().replace("-", "_")}({", ".join(special_symbols)})'
    #                     formula = [s if '=' in s or ':' in s else re.sub('^( *)([^ ].*)$', r'\1return \2', s) for s in formula.split('\n')]
    #                     pyomo_model_code.add("def " + formula_fun + ":", 1)
    #                     pyomo_model_code.add(formula, 2)
    #                     reaction_formulas.append(formula_fun)
    #                     for mv, p, s in zip(special_model_variables, special_parameters, special_symbols):
    #                         if mv not in model_variables:
    #                             model_variables.append(mv)
    #                             parameters.append(p)
    #                             symbols.append(s)
    #                 model_variables.append(differential_model_variable)
    #                 parameters.append(self.entity["model_variable"][differential_model_variable])
    #                 symbols.append(differential_model_variable_symbol)

    #                 formula = " * ".join(reaction_formulas)
    #                 for p, s in zip(parameters, symbols):
    #                     if s == f"{differential_model_variable_symbol}": continue
    #                     if set(p["dimensions"]) == set([]):
    #                         formula = re.sub(f'{s}([ \),]|$)', f'{s}\\1', formula)
    #                     if set(p["dimensions"]) == set(["Reaction"]):
    #                         formula = re.sub(f'{s}([ \),]|$)', f'{s}[{reaction_index}]\\1', formula)
    #                     if set(p["dimensions"]) == set(["Reaction", "Species"]):
    #                         formula = re.sub(f'{s}([ \),]|$)', f'{s}[{reaction_index}, s_index]\\1', formula)
    #                     if set(p["dimensions"]) == set(["Reaction", "Solvent"]):
    #                         formula = re.sub(f'{s}([ \),]|$)', f'{s}[{reaction_index}, {solvent_index}]\\1', formula)
    #                     if set(p["dimensions"]) == set(["Stream", "Species"]):
    #                         if "Variable" in p["class"]:
    #                             formula = re.sub(f'{s}([ \),]|$)', f'{s}[{stream_index}, s_index, x]\\1', formula)
    #                         else:
    #                             formula = re.sub(f'{s}([ \),]|$)', f'{s}[{stream_index}, s_index]\\1', formula)
    #                 formula = re.sub(r'np.prod\(([^\(\)]*)\)', f'np.prod([\\1 for s_index in range({len(species)})])', formula)
    #                 function_head = pyomo_model_code.add_function(f"Reaction_Rate_{stream_index}_{reaction_index}", symbols, formula, 1)
    #                 for s in symbols:
    #                     if s == f"{differential_model_variable_symbol}": continue
    #                     function_head = re.sub(f'{s}([ \),])', f'model.{s}\\1', function_head)

    #                 pyomo_model_code.add(f"def reaction_rate_{stream_index}_{reaction_index}_rule(model, {differential_model_variable_symbol}):", 1)
    #                 pyomo_model_code.add(f"return model.{reaction_rate_symbol}[{stream_index}, {reaction_index}, {differential_model_variable_symbol}] == {function_head}", 2)
    #                 pyomo_model_code.add(f"model.reaction_rate_{stream_index}_{reaction_index}_constraint = environ.Constraint(model.{differential_model_variable_symbol}, rule=reaction_rate_{stream_index}_{reaction_index}_rule)", 1)
    #                 pyomo_model_code.add("", 0)
    #     # TODO
    #     else:
    #         return "Not supported in pyomo mode now."

    #     # TODO molecular transport part
    #     pyomo_model_code.add("# MOLECULAR TRANSPORT PART", 1)

    #     pyomo_model_code.add("# MASS BALANCE PART", 1)
    #     optional_model_variables = self.entity["law"][accumulation_law]["optional_model_variables"]
    #     model_variables = [mv for mv in optional_model_variables for l in self.entity["model_variable"][mv]["laws"] if self.entity["law"][l]["phenomenon"] in molecular_transport_phenomena + [p for v in reaction_phenomena.values() for p in v]]\
    #         + [mv for mv in optional_model_variables if self.entity["model_variable"][mv]["laws"] == []]
    #     model_variables.extend(self.entity["law"][accumulation_law]["model_variables"])
    #     model_variables = list(set([mv for mv in model_variables if mv != "Initial_Concentration"]))
    #     parameters = [self.entity["model_variable"][mv] for mv in model_variables]
    #     symbols = [MMLExpression(p["symbol"]).to_numpy() for p in parameters]
    #     model_variables.append(differential_model_variable)
    #     parameters.append(self.entity["model_variable"][differential_model_variable])
    #     symbols.append(differential_model_variable_symbol)
    #     if self.context["description"]["accumulation"] == "Continuous":
    #         if formula_integrated_with_accumulation:
    #             return "Not supported in pyomo mode now."
    #         else:
    #             pyomo_model_code.add(f"model.dc = dae.DerivativeVar(model.c, wrt=model.{differential_model_variable_symbol})", 1)
    #             formula = MMLExpression(self.entity["law"][accumulation_law]["formula"]).to_numpy()
    #             for s in symbols:
    #                 formula = re.sub(f'\[([^\[\]]*{s}[^\[\]]*)\]', r'\1', formula)
    #             formula = re.sub('\[[^\[\],]*\]', '0', formula)
    #             for p, s in zip(parameters, symbols):
    #                 if s == f"{differential_model_variable_symbol}": continue
    #                 if set(p["dimensions"]) == set([]):
    #                     formula = re.sub(f'{s}([ \),]|$)', f'{s}\\1', formula)
    #                 if set(p["dimensions"]) == set(["Stream", "Reaction"]):
    #                     if "Variable" in p["class"]:
    #                         formula = re.sub(f'{s}([ \),]|$)', f'{s}[i, r_index, x]\\1', formula)
    #                     else:
    #                         formula = re.sub(f'{s}([ \),]|$)', f'{s}[i, r_index]\\1', formula)
    #                 if set(p["dimensions"]) == set(["Reaction", "Species"]):
    #                     formula = re.sub(f'{s}([ \),]|$)', f'{s}[r_index, j]\\1', formula)
    #             formula = re.sub(r'np.matmul\(([^\(\)]*)(?<=\]), ([^\(\)]*)\)', f'np.prod([\\1 * \\2 for r_index in range({len(reactions)})])', formula)

    #             function_head = pyomo_model_code.add_function(f"Concentration_Derivative", symbols + ["i", "j"], formula, 1)
    #             for s in symbols:
    #                 if s == f"{differential_model_variable_symbol}": continue
    #                 function_head = re.sub(f'{s}([ \),])', f'model.{s}\\1', function_head)
    #             pyomo_model_code.add(f"def concentration_derivative_rule(model, i, j, {differential_model_variable_symbol}):", 1)
    #             pyomo_model_code.add(f"return model.dc[i, j, {differential_model_variable_symbol}] == {function_head}", 2)
    #             pyomo_model_code.add(f"model.concentration_derivative_constraint = environ.Constraint(range({len(liquid_streams)}), range({len(species)}), model.{differential_model_variable_symbol}, rule=concentration_derivative_rule)", 1)
    #             pyomo_model_code.add("", 0)
    #     # TODO
    #     if self.context["description"]["accumulation"] == "Batch":
    #         pass
    #     # TODO
    #     if self.context["description"]["accumulation"] == "CSTR":
    #         pass

    #     # boundary function
    #     # TODO
    #     if formula_integrated_with_accumulation:
    #         pass
    #     else:
    #         pyomo_model_code.add(f"for i in range({len(liquid_streams)}):", 1)
    #         pyomo_model_code.add(f"for j in range({len(species)}):", 2)
    #         pyomo_model_code.add(f"model.c[i, j, 0].fix(np.array(model.c_0)[i, j])", 3)
    #     pyomo_model_code.add("", 0)

    #     # integrate calculation
    #     if self.context["description"]["accumulation"] == "Continuous":
    #         pyomo_model_code.add("discretizer = environ.TransformationFactory('dae.finite_difference')", 1)
    #         pyomo_model_code.add("discretizer.apply_to(model, nfe=400, scheme='BACKWARD')", 1)
    #         pyomo_model_code.add("solver = environ.SolverFactory('ipopt')", 1)
    #         pyomo_model_code.add("solver.solve(model)", 1)
    #         differential_upper_limit = self.entity["law"][accumulation_law]["differential_upper_limit"]
    #         differential_upper_limit_symbol = MMLExpression(self.entity["model_variable"][differential_upper_limit]['symbol']).to_numpy().strip()
    #         pyomo_model_code.add(f"{differential_model_variable_symbol} = np.array(model.{differential_model_variable_symbol})", 1)
    #         pyomo_model_code.add(f"c = np.array([model.c.get_values()[k] for k in sorted(list(model.c.get_values().keys()))]).reshape({len(liquid_streams)}, {len(species)}, -1)", 1)
    #         pyomo_model_code.add(f"q = np.array(model.q)", 1)
    #         pyomo_model_code.add(f"return [{differential_model_variable_symbol}, c, q]", 1)
    #     if self.context["description"]["accumulation"] == "Batch":
    #         pass
    #     if self.context["description"]["accumulation"] == "CSTR":
    #         pass
    #     return pyomo_model_code.get_model()


    # def to_julia_model(self):
        """The converted julia model is given as:
        param_dict: `{(parameter, species, reaction, stream, solvent): value}`
        def simulation(param_dict):
            p = list(param_dict.values())
            def derivative(c, x):
            def boundary(c_a, c_b):
            sol = solve(prob, Tsit5(); saveat=x_eval, reltol=1e-12, abstol=1e-12)
            return(sol.t, sol.u)
        Returns:
            str: converted julia model
        """

        julia_model_code = JuliaModelCode()
        # julia_model_code.add_header(self.context)
        julia_model_code.add_lib()

        # param_dict
        param_dict = self.extract_parameter_value()
        julia_model_code.add("param_dict = OrderedDict(", 0)
        for k, v in param_dict.items():
            k = tuple('nothing' if x is None else x for x in k)
            formatted_key = ', '.join(f'nothing' if elem == 'nothing' else f'"{elem}"' for elem in k)
            julia_model_code.add(f"({formatted_key}) => {v if v else 'nothing'},", 1)
        julia_model_code.add(")", 0)
        julia_model_code.add("", 0)

        # law identification
        # start from accumulation phenomenon
        # flow pattern laws -> subsidiary flow pattern laws
        accumulation_phenomenon = self.context["description"]["accumulation"]
        flow_pattern_phenomenon = self.context["description"]["flow_pattern"]
        molecular_transport_phenomena = self.context["description"]["molecular_transport"]
        parameter_law = self.context["description"]["parameter_law"]
        reaction_phenomena = self.context["description"]["reaction"]

        # law and name of parameters
        accumulation_phenomenon = self.context["description"]["accumulation"]
        flow_pattern_phenomenon = self.context["description"]["flow_pattern"]
        molecular_transport_phenomena = self.context["description"]["molecular_transport"]
        parameter_law = self.context["description"]["parameter_law"]
        reaction_phenomena = self.context["description"]["reaction"]
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
        if self.context["basic"]["reactions"]:
            model_variables += ["Coefficient"]
        model_variables = list(set(model_variables))

        # model basics, get differentiable variable
        parameter_value_keys = list(param_dict.keys())
        species = self.context["basic"]["species"]
        reactions = self.context["basic"]["reactions"]
        liquid_streams = [k for k, v in self.context["information"]["streams"].items() if v["state"] == "liquid"]
        gas_streams = [k for k, v in self.context["information"]["streams"].items() if v["state"] == "gaseous"]
        solvents = self.context["basic"]["solvents"]
        if self.context["description"]["accumulation"] in ["Continuous", "Batch"]:
            differential_model_variable = self.entity["law"][accumulation_law]["differential_model_variable"]
            differential_model_variable_symbol = MMLExpression(
                self.entity["model_variable"][differential_model_variable]['symbol']).to_numpy().strip()

        # simulation function head
        julia_model_code.add("function simulation(param_dict)", 0)
        julia_model_code.add("# PARAMETER PART", 1)
        julia_model_code.add("p = collect(values(param_dict))", 1)

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
        if self.context["description"]["accumulation"] == "Continuous":
            julia_model_code.add(f"function derivative(dc, c, p, {differential_model_variable_symbol})", 1)
            if formula_integrated_with_accumulation:
                julia_model_code.add(f"c = reshape(c, {len(liquid_streams)}, {len(species) * 2})", 2)
            else:
                julia_model_code.add(f"c = reshape(c, {len(liquid_streams)}, {len(species)})", 2)

        # concentration axial position derivative function
        if self.context["description"]["accumulation"] == "Batch":
            julia_model_code.add(f"function derivative(dc, c, p, {differential_model_variable_symbol})", 1)
            julia_model_code.add(f"c = reshape(c, {len(liquid_streams)}, {len(species)})", 2)

        # concentration error function
        # TODO: need to check
        if self.context["description"]["accumulation"] == "CSTR":
            julia_model_code.add(f"def conversion(c):", 1)
            if self.context["description"]["flow_pattern"] == "Well_Mixed":
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
                if reaction not in self.context["information"]["streams"][stream]["reactions"]: continue
                solvent_index = solvents.index(self.context["information"]["streams"][stream]["solvent"])
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
                reaction_special_formulas = [self.context["information"]["reactions"][reaction][p] for p in reaction_special_phenomena]
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
        if self.context["description"]["accumulation"] == "Continuous":
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

        if self.context["description"]["accumulation"] == "Batch":
            formula = MMLExpression(self.entity["law"][accumulation_law]["formula"]).to_numpy()
            for s in symbols:
                formula = re.sub(f'\[([^\[\]]*{s}[^\[\]]*)\]', r'\1', formula)
            formula = re.sub('\[[^\[\]]*\]', '0', formula)
            # TO DO: change here for matmul
            formula = formula.replace("np.matmul", "").replace('(', '').replace(')', '').replace(',', ' * ')
            julia_model_code.add(f'dc = reshape(dc, {len(liquid_streams)}, {len(species)})', 2)
            julia_model_code.add(f'dc .= {formula}', 2)

        # TODO: need to check
        if self.context["description"]["accumulation"] == "CSTR":
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
        if self.context["description"]["accumulation"] == "Continuous":
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

        if self.context["description"]["accumulation"] == "Batch":
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
        if self.context["description"]["accumulation"] == "CSTR":
            pass

        julia_model_code.add(f"end", 1)
        julia_model_code.add(f"end", 0)
        return julia_model_code.get_model() 