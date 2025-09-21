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
        self.codes.append("from scipy.integrate import solve_bvp, solve_ivp")
        self.codes.append("from scipy.interpolate import interp1d")
        self.codes.append("from scipy.optimize import differential_evolution, fsolve")
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


class ModelAgent:
    """Model agent for generating model based on model context.

    The physical model is derived from given phenomena and parameters, including:
        - accumulation
        - flow pattern
        - mass transport
        - mass equilibrium
        - reaction
    
    The context json structure is like:
    ```
    {
        "type": "steady",
        "basic": {
            "spc":     [],
            "rxn":     [],
            "stm":     {"stm1": {"spc": [], "rxn": []}},
            "gas":     {"gas1": {"spc": []}},
            "sld":     {"sld1": {"spc": []}},
        },
        "desc": {
            "ac": "",
            "fp": "",
            "mt": [],
            "me": [],
            "rxn": {"rxn1": []},
            "param_law": {"param1": ""},
        }, 
        "info": {
            "spc":  {"param1": {"spc1": ...}},
            "st":   {},
            "mt":   {},
            "me":   {"param1": {"gas1": {"stm1": ...}},
            "stm":  {"param1": {"stm1": ...}},
            "rxn":  {"param1": {"stm1": {"rxn1": ...}}},
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
                raise ValueError(f"False reaction format: {rxn}")

    def extract_param_dict(self):
        """Extract parameter from context with dimensions listed as: 
            [gas/solid, stream, reaction, and species]
        """
        
        param_dict = {}

        # Structure
        if "st" not in self.context["info"]:
            for p in self.context["info"]["st"]:
                if p not in self.entity["var"]:
                    continue
                dims = self.entity["var"][p]["dims"]
                if set(dims) == set([""]):
                    v = self.context["info"]["st"][p]
                    param_dict[(p, None, None, None, None)] = v
                else:
                    raise ValueError(f"Invalid dimensions for structure parameter {p}: {dims}")
        
        # Species
        if "spc" in self.context["info"]:
            for p in self.context["info"]["spc"]:
                if p not in self.entity["var"]:
                    continue
                dims = self.entity["var"][p]["dims"]
                if set(dims) == set(["Species"]):
                    for spc in self.context["info"]["spc"][p]:
                        v = self.context["info"]["spc"][p][spc]
                        param_dict[(p, None, None, None, spc)] = v
                else:
                    raise ValueError(f"Invalid dimensions for species parameter {p}: {dims}")
        
        # Stream
        if "stm" in self.context["info"]:
            for p in self.context["info"]["stm"]:
                if p not in self.entity["var"]:
                    continue
                dims = self.entity["var"][p]["dims"]
                if set(dims) == set(["Stream"]):
                    for stm in self.context["info"]["stm"][p]:
                        v = self.context["info"]["stm"][p][stm]
                        param_dict[(p, None, stm, None, None)] = v
                else:
                    raise ValueError(f"Invalid dimensions for stream parameter {p}: {dims}")

        # Gas
        if "gas" in self.context["info"]:
            for p in self.context["info"]["gas"]:
                if p not in self.entity["var"]:
                    continue
                dims = self.entity["var"][p]["dims"]
                if set(dims) == set(["Gas"]):
                    for gas in self.context["info"]["gas"][p]:
                        v = self.context["info"]["gas"][p][gas]
                        param_dict[(p, gas, None, None, None)] = v
                else:
                    raise ValueError(f"Invalid dimensions for gas parameter {p}: {dims}")

        # Solid
        if "sld" in self.context["info"]:
            for p in self.context["info"]["sld"]:
                if p not in self.entity["var"]:
                    continue
                dims = self.entity["var"][p]["dims"]
                if set(dims) == set(["Solid"]):
                    for sld in self.context["info"]["sld"][p]:
                        v = self.context["info"]["sld"][p][sld]
                        param_dict[(p, sld, None, None, None)] = v
                else:
                    raise ValueError(f"Invalid dimensions for solid parameter {p}: {dims}")

        # Mass transport
        if "mt" in self.context["info"]:
            for p in self.context["info"]["mt"]:
                if p not in self.entity["var"]:
                    continue
                dims = self.entity["var"][p]["dims"]
                if set(dims) == set([]):
                    v = self.context["info"]["mt"][p]
                    param_dict[(p, None, None, None, None)] = v
                elif set(dims) == set(["Species"]):
                    for spc in self.context["info"]["mt"][p]:
                        v = self.context["info"]["mt"][p][spc]
                        param_dict[(p, None, None, None, spc)] = v
                elif set(dims) == set(["Species", "Stream"]):
                    for stm in self.context["info"]["mt"][p]:
                        for spc in self.context["info"]["mt"][p][stm]:
                            v = self.context["info"]["mt"][p][stm][spc]
                            param_dict[(p, None, stm, None, spc)] = v
                elif set(dims) == set(["Species", "Gas"]):
                    for gas in self.context["info"]["mt"][p]:
                        for spc in self.context["info"]["mt"][p][gas]:
                            v = self.context["info"]["mt"][p][gas][spc]
                            param_dict[(p, gas, None, None, spc)] = v
                elif set(dims) == set(["Species", "Solid"]):
                    for sld in self.context["info"]["mt"][p]:
                        for spc in self.context["info"]["mt"][p][sld]:
                            v = self.context["info"]["mt"][p][sld][spc]
                            param_dict[(p, sld, None, None, spc)] = v
                elif set(dims) == set(["Species", "Stream", "Gas"]):
                    for gas in self.context["info"]["mt"][p]:
                        for stm in self.context["info"]["mt"][p][gas]:
                            for spc in self.context["info"]["mt"][p][gas][stm]:
                                v = self.context["info"]["mt"][p][gas][stm][spc]
                                param_dict[(p, gas, stm, None, spc)] = v
                elif set(dims) == set(["Species", "Stream", "Solid"]):
                    for sld in self.context["info"]["mt"][p]:
                        for stm in self.context["info"]["mt"][p][sld]:
                            for spc in self.context["info"]["mt"][p][sld][stm]:
                                v = self.context["info"]["mt"][p][sld][stm][spc]
                                param_dict[(p, sld, stm, None, spc)] = v
                else:
                    raise ValueError(f"Invalid dimensions for mass transport parameter {p}: {dims}")

        # Mass equilibrium
        if "me" in self.context["info"]:
            for p in self.context["info"]["me"]:
                if p not in self.entity["var"]:
                    continue
                dims = self.entity["var"][p]["dims"]
                if set(dims) == set(["Species", "Stream", "Gas"]):
                    for gas in self.context["info"]["me"][p]:
                        for stm in self.context["info"]["me"][p][gas]:
                            for spc in self.context["info"]["me"][p][gas][stm]:
                                v = self.context["info"]["me"][p][gas][stm][spc]
                                param_dict[(p, gas, stm, None, spc)] = v
                elif set(dims) == set(["Species", "Stream", "Solid"]):
                    for sld in self.context["info"]["me"][p]:
                        for stm in self.context["info"]["me"][p][sld]:
                            for spc in self.context["info"]["me"][p][sld][stm]:
                                v = self.context["info"]["me"][p][sld][stm][spc]
                                param_dict[(p, sld, stm, None, spc)] = v
                else:
                    raise ValueError(f"Invalid dimensions for mass equilibrium parameter {p}: {dims}")

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
                param_dict[("Stoichiometric_Coefficient", None, None, r, s)] = v
            for item in rhs_r.split(" + "):
                if re.match(r"^\d+$", item.split(" ")[0]):
                    v = float(item.split(" ")[0])
                    s = " ".join(item.split(" ")[1:])
                else:
                    v = 1.0
                    s = item
                param_dict[("Stoichiometric_Coefficient", None, None, r, s)] = v

        # Reaction
        if "rxn" in self.context["info"]:
            for p in self.context["info"]["rxn"]:
                if p not in self.entity["var"]:
                    continue
                dims = self.entity["var"][p]["dims"]
                if set(dims) == set(["Reaction"]):
                    for rxn in self.context["info"]["rxn"][p]:
                        v = self.context["info"]["rxn"][p][rxn]
                        param_dict[(p, None, None, rxn, None)] = v
                elif set(dims) == set(["Reaction", "Stream"]):
                    for stm in self.context["info"]["rxn"][p]:
                        for rxn in self.context["info"]["rxn"][p][stm]:
                            v = self.context["info"]["rxn"][p][stm][rxn]
                            param_dict[(p, None, stm, rxn, None)] = v
                elif set(dims) == set(["Species", "Reaction"]):
                    for rxn in self.context["info"]["rxn"][p]:
                        for spc in self.context["info"]["rxn"][p][rxn]:
                            v = self.context["info"]["rxn"][p][rxn][spc]
                            param_dict[(p, None, None, rxn, spc)] = v
                else:
                    raise ValueError(f"Invalid dimensions for reaction parameter {p}: {dims}")

        # Operation
        phenos = []
        phenos.append(self.context["desc"]["ac"])
        phenos.append(self.context["desc"]["fp"])
        phenos.extend(self.context["desc"]["mt"])
        for rxn in self.context["desc"]["rxn"]:
            for rxn_pheno in self.context["desc"]["rxn"][rxn]:
                if rxn_pheno not in phenos:
                    phenos.append(rxn_pheno)
        
        laws = []
        for law, law_dict in self.entity["law"].items():
            if law_dict["pheno"] in phenos:
                laws.append(law)
            if law_dict["pheno"] in self.context["desc"]["mt"]:
                assoc_gas_law = self.entity["law"][law]["assoc_gas_law"]
                if assoc_gas_law and self.context["basic"]["gas"]:
                    if assoc_gas_law not in laws:
                        laws.append(assoc_gas_law)
                assoc_sld_law = self.entity["law"][law]["assoc_sld_law"]
                if assoc_sld_law and self.context["basic"]["sld"]:
                    if assoc_sld_law not in laws:
                        laws.append(assoc_sld_law)
        laws.extend(self.context["desc"]["param_law"].values())
        
        op_ps = []
        for law in laws:
            for p in self.entity["law"][law]["vars"]:
                p_class = self.entity["var"][p]["cls"]
                if p_class == "OperationParameter" and p not in op_ps:
                    op_ps.append(p)
        for p in op_ps:
            dims = self.entity["var"][p]["dims"]
            if set(dims) == set([]):
                param_dict[(p, None, None, None, None)] = None
            elif set(dims) == set(["Stream"]):
                for stm in self.context["basic"]["stm"]:
                    param_dict[(p, None, stm, None, None)] = None
            elif set(dims) == set(["Species", "Stream"]):
                for stm in self.context["basic"]["stm"]:
                    for spc in self.context["basic"]["stm"][stm]["spc"]:
                        param_dict[(p, None, stm, None, spc)] = None
            elif set(dims) == set(["Species", "Gas"]):
                for gas in self.context["basic"]["gas"]:
                    for spc in self.context["basic"]["gas"][gas]["spc"]:
                        param_dict[(p, gas, None, None, spc)] = None
            elif set(dims) == set(["Species", "Solid"]):
                for sld in self.context["basic"]["sld"]:
                    for spc in self.context["basic"]["sld"][sld]["spc"]:
                        param_dict[(p, sld, None, None, spc)] = None
            else:
                raise ValueError(f"Invalid dimensions for operation parameter {p}: {dims}")

        if self.param_dict:
            for k, v in zip(self.param_dict["ind"], self.param_dict["val"]):
                param_dict[tuple(k)] = v
        return param_dict

    def to_flowchart(self):
        # accumulation -> parameter / rate_variable -> parameter
        flowchart = {"chart": [[], [], []], "link": []}
        
        accumulation_chart = {}
        phenomenon = self.context["desc"]["accumulation"]
        law = [l for l in self.entity["law"] if self.entity["law"][l]["phenomenon"] == phenomenon][0]
        accumulation_parameters = self.entity["law"][law]["model_variables"]
        accumulation_symbols = [self.entity["model_variable"][p]["symbol"].strip() for p in accumulation_parameters]
        molecular_transport_phenomena = self.context["desc"]["molecular_transport"]
        parameter_law = self.context["desc"]["parameter_law"]
        reaction_phenomena = list(set([p for r in self.context["desc"]["reaction"] for p in self.context["desc"]["reaction"][r]]))
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
        
        phenomenon = self.context["desc"]["flow_pattern"]
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

        phenomena = self.context["desc"]["molecular_transport"]
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
        for reaction in self.context["desc"]["reaction"]:
            phenomena = self.context["desc"]["reaction"][reaction]
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
                if self.entity["phenomenon"][self.entity["law"][law]["phenomenon"]]["cls"] == "ChemicalReactionPhenomenon":
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
                    formula["detail_formula"] = f'<div style="white-space: pre-line; color: gray;">{self.context["info"]["reactions"][reaction][self.entity["law"][law]["phenomenon"]].replace(" ", "&nbsp;")}</div>'
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
        codes = codes.replace("maximum", "np.maximum")
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
    
    def get_out_inds(self):
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
            
        ac_laws = pheno2law[self.context["desc"]["ac"]]
        ac_law = [law for law in ac_laws if law2var[law] != "Concentration"][0]
        ac_vars = self.entity["law"][ac_law]["vars"]
        ac_opt_vars = self.entity["law"][ac_law]["opt_vars"]
        
        # r_t_g, r_t_s
        mt_laws, mt_vars = [], []
        for mt_pheno in self.context["desc"]["mt"]:
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
            raise ValueError("Multiple associated gas law associated with mass transport.")
        else:
            assoc_gas_law = assoc_gas_laws[0] if assoc_gas_laws else None
        if len(assoc_sld_laws) > 1:
            raise ValueError("Multiple associated solid law associated with mass transport.")
        else:
            assoc_sld_law = assoc_sld_laws[0] if assoc_sld_laws else None

        if self.context["desc"]["ac"] in ["Batch", "Continuous"]:
            ivar = self.entity["law"][ac_law]["int_var"]
        else:
            raise ValueError(f"Unknown integral variable for {self.context['desc']['ac']}")

        if assoc_gas_law and ngas:
            gvar = self.entity["law"][assoc_gas_law]["int_var"]
        if assoc_sld_law and nsld:
            svar = self.entity["law"][assoc_sld_law]["int_var"]
        
        out_inds = []
        for stm in stms:
            for spc in spcs:
                out_inds.append([ivar, None, stm, None, spc])
        for spc in spcs:
            out_inds.append([ivar, None, "Overall", None, spc])
        if assoc_gas_law and ngas:
            for gas in gass:
                for spc in self.context["basic"]["gas"][gas]["spc"]:
                    out_inds.append([gvar, gas, None, None, spc])
        if assoc_sld_law and nsld:
            for sld in slds:
                for spc in self.context["basic"]["sld"][sld]["spc"]:
                    out_inds.append([svar, sld, None, None, spc])
        return out_inds

    def to_scipy_model(self):
        """The converted scipy model is given as:
        
        param_dict: `{(parameter, gas/solid, stream, reaction, species): value}`
        def simulation(param_dict):
            p = list(param_dict.values())
            def derivative(c, x):
            def boundary(c_a, c_b):
            res = solve_bvp(derivative, boundary, x_init, c_init)
            res_dict = {"x": ..., "y": ...}
            return res_dict

        Returns:
            str: converted scipy model, format of the scipy model return is given as
                {
                    "x": {
                        "ind": ("param1", None, None, None, None),
                        "val": [...],
                    }, 
                    "y": {
                        "ind": [
                            ("param2", None, None, None, None),
                            ("param3", None, None, None, None)
                        ],
                        "val: [
                            [...],
                            [...]
                        ]
                    }
                }
        """

        # Validate reaction
        self.validate_rxn()

        # Model
        model = ScipyModel()
        # model.add_header(self.context)
        model.add_lib()

        # Parameter
        param_dict = self.extract_param_dict()
        model.add("param_dict = {", 0)
        for k, v in param_dict.items():
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
            
        ac_laws = pheno2law[self.context["desc"]["ac"]]
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
        for mt_pheno in self.context["desc"]["mt"]:
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
            raise ValueError("Multiple associated gas law associated with mass transport.")
        else:
            assoc_gas_law = assoc_gas_laws[0] if assoc_gas_laws else None
        if len(assoc_sld_laws) > 1:
            raise ValueError("Multiple associated solid law associated with mass transport.")
        else:
            assoc_sld_law = assoc_sld_laws[0] if assoc_sld_laws else None

        # c_g_star, c_s_star
        me_laws, me_vars = [], []
        for var in mt_vars:
            if var != "Concentration" and self.entity["var"][var]["laws"]:
                law = self.context["desc"]["param_law"][var]
                law_dict = self.entity["law"][law]
                if law_dict["pheno"] in self.context["desc"]["me"]:
                    me_laws.append(law)
                    me_vars.extend(law_dict["vars"])

        fp_laws, fp_vars = [], []
        # flow_velocity
        for var in ac_vars:
            for law in pheno2law[self.context["desc"]["fp"]]:
                if law in self.entity["var"][var]["laws"]:
                    fp_laws.append(law)
                    fp_vars.extend(law_dict["vars"])
        # mixing_time
        for var in mt_vars:
            if var != "Concentration" and self.entity["var"][var]["laws"]:
                law = self.context["desc"]["param_law"][var]
                law_dict = self.entity["law"][law]
                if law_dict["pheno"] == self.context["desc"]["fp"]:
                    fp_laws.append(law)
                    fp_vars.extend(law_dict["vars"])

        # film_thickness
        sub_fp_laws, sub_fp_vars = [], []
        for var in fp_vars:
            if self.entity["var"][var]["laws"]:
                law = self.context["desc"]["param_law"][var]
                law_dict = self.entity["law"][law]
                if law in pheno2law[self.context["desc"]["fp"]]:
                    sub_fp_laws.append(law)
                    sub_fp_vars.extend(law_dict["vars"])

        rxn_laws, rxn_vars = {}, {}
        for rxn, rxn_phenos in self.context["desc"]["rxn"].items():
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
            raise ValueError(f"Unknown operation type: {self.context['type']}")
        model.add("def simulate(param_dict):", 0)
        model.add("# parameter", 1)
        model.add("p = list(param_dict.values())", 1)

        # Parameter setup
        op_vars = [v for v in model_vars if self.entity["var"][v]["cls"] 
                    == "OperationParameter" and all([
                    d is None for d in self.entity["var"][v]["dims"]])]
        op_syms = [MMLExpression(self.entity["var"][v]
                                 ["sym"]).to_numpy() for v in op_vars]
        iul_var = self.entity["law"][ac_law]["int_up_lim"]
        iul_sym = MMLExpression(self.entity["var"][iul_var]["sym"]).to_numpy()
        keys = list(param_dict.keys())
        for var in model_vars:
            var_dict = self.entity["var"][var]
            sym = MMLExpression(var_dict["sym"]).to_numpy()
            dims = var_dict["dims"]
            
            if var_dict["cls"] == "Constant":
                model.add(f'{sym} = {var_dict["val"]}', 1)            
            if "Parameter" not in var_dict["cls"]:
                continue
            if var_dict["laws"]:
                continue

            if set(dims) == set([]):
                ind = keys.index((var, None, None, None, None))
                model.add(f'{sym} = p[{ind}]', 1)
            elif set(dims) == set(["Species"]):
                model.add(f"{sym} = np.zeros({nspc}, dtype=np.float64)", 1)
                for i, spc in enumerate(spcs):
                    ind = keys.index((var, None, None, None, spc))
                    model.add(f'{sym}[{i}] = p[{ind}]', 1)
            elif set(dims) == set(["Reaction"]):
                model.add(f"{sym} = np.zeros({nrxn}, dtype=np.float64)", 1)
                for i, rxn in enumerate(rxns):
                    if (var, None, None, rxn, None) in keys:
                        ind = keys.index((var, None, None, rxn, None))
                        model.add(f'{sym}[{i}] = p[{ind}]', 1)
            elif set(dims) == set(["Stream"]):
                model.add(f"{sym} = np.zeros({nstm}, dtype=np.float64)", 1)
                for i, stm in enumerate(stms):
                    ind = keys.index((var, None, stm, None, None))
                    model.add(f"{sym}[{i}] = p[{ind}]", 1)
            elif set(dims) == set(["Gas"]):
                model.add(f"{sym} = np.zeros({ngas}, dtype=np.float64)", 1)
                for i, gas in enumerate(gass):
                    ind = keys.index((var, gas, None, None, None))
                    model.add(f"{sym}[{i}] = p[{ind}]", 1)
            elif set(dims) == set(["Solid"]):
                model.add(f"{sym} = np.zeros({nsld}, dtype=np.float64)", 1)
                for i, sld in enumerate(slds):
                    ind = keys.index((var, sld, None, None, None))
                    model.add(f"{sym}[{i}] = p[{ind}]", 1)
            elif set(dims) == set(["Species", "Reaction"]):
                model.add(f"{sym} = np.zeros({nrxn, nspc}, dtype=np.float64)", 1)
                for i, rxn in enumerate(rxns):
                    for j, spc in enumerate(spcs):
                        if (var, None, None, rxn, spc) in keys:
                            ind = keys.index((var, None, None, rxn, spc))
                            model.add(f'{sym}[{i}, {j}] = p[{ind}]', 1)
            elif set(dims) == set(["Species", "Stream"]):
                model.add(f"{sym} = np.zeros({nstm, nspc}, dtype=np.float64)", 1)
                for i, stm in enumerate(stms):
                    for j, spc in enumerate(spcs):
                        if (var, None, stm, None, spc) in keys:
                            ind = keys.index((var, None, stm, None, spc))
                            model.add(f'{sym}[{i}, {j}] = p[{ind}]', 1)
            elif set(dims) == set(["Species", "Gas"]):
                model.add(f"{sym} = np.zeros({ngas, nspc}, dtype=np.float64)", 1)
                for i, gas in enumerate(gass):
                    for j, spc in enumerate(spcs):
                        if (var, gas, None, None, spc) in keys:
                            ind = keys.index((var, gas, None, None, spc))
                            model.add(f'{sym}[{i}, {j}] = p[{ind}]', 1)
            elif set(dims) == set(["Species", "Solid"]):
                model.add(f"{sym} = np.zeros({nsld, nspc}, dtype=np.float64)", 1)
                for i, sld in enumerate(slds):
                    for j, spc in enumerate(spcs):
                        if (var, sld, None, None, spc) in keys:
                            ind = keys.index((var, sld, None, None, spc))
                            model.add(f'{sym}[{i}, {j}] = p[{ind}]', 1)
            elif set(dims) == set(["Reaction", "Stream"]):
                model.add(f"{sym} = np.zeros({nstm, nrxn}, dtype=np.float64)", 1)
                for i, stm in enumerate(stms):
                    for j, rxn in enumerate(rxns):
                        if (var, None, stm, rxn, None) in keys:
                            ind = keys.index((var, None, stm, rxn, None))
                            model.add(f'{sym}[{i}, {j}] = p[{ind}]', 1)
            elif set(dims) == set(["Species", "Stream", "Gas"]):
                model.add(f"{sym} = np.zeros({ngas, nstm, nrxn}, dtype=np.float64)", 1)
                for i, gas in enumerate(gass):
                    for j, stm in enumerate(stms):
                        for k, spc in enumerate(spcs):
                            if (var, gas, stm, None, spc) in keys:
                                ind = keys.index((var, gas, stm, None, spc))
                                model.add(f'{sym}[{i}, {j}, {k}] = p[{ind}]', 1)
            elif set(dims) == set(["Species", "Stream", "Solid"]):
                model.add(f"{sym} = np.zeros({nsld, nstm, nrxn}, dtype=np.float64)", 1)
                for i, sld in enumerate(slds):
                    for j, stm in enumerate(stms):
                        for k, spc in enumerate(spcs):
                            if (var, sld, stm, None, spc) in keys:
                                ind = keys.index((var, sld, stm, None, spc))
                                model.add(f'{sym}[{i}, {j}, {k}] = p[{ind}]', 1)
            else:
                raise ValueError(f"Unknown parameter {var} with dimensions: {dims}")
            
            unit = self.entity["var"][var]["unit"]
            if unit:
                rto = self.entity["unit"][unit]["rto"]
                intcpt = self.entity["unit"][unit]["intcpt"]
                if self.context["type"] == "dynamic" and var in op_vars:
                    if rto:
                        model.add(f"{sym} = [_{sym} * {rto} for _{sym} in {sym}]", 1)
                    if intcpt:
                        model.add(f"{sym} = [_{sym} + {intcpt} for _{sym} in {sym}]", 1)
                else:
                    if rto:
                        model.add(f"{sym} *= {rto}", 1)
                    if intcpt:
                        model.add(f"{sym} += {intcpt}", 1)
        model.add("", 0)

        model.add("# dynamic parameter interpolation", 1)
        if self.context["type"] == "dynamic":
            model.add("interps = {}", 1)
            for op_sym in op_syms:
                if op_sym != iul_sym:
                    model.add(f"interps['{op_sym}'] = interp1d({iul_sym}, {op_sym})", 1)
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
        if self.context["desc"]["ac"] in ["Batch", "Continuous"]:
            ivar = self.entity["law"][ac_law]["int_var"]
            imml = self.entity["var"][ivar]["sym"]
            isym = MMLExpression(imml).to_numpy()
            dvar = self.entity["law"][ac_law]["diff_var"]
            dmml = self.entity["var"][dvar]["sym"]
            dsym = MMLExpression(dmml).to_numpy()
            model.add(f"def derivative({dsym}, {isym}):", 1)
            if self.context["type"] == "dynamic":
                for op_sym in op_syms:
                    if op_sym != iul_sym:
                        model.add(f"{op_sym} = interps['{op_sym}']({dsym})", 2)
            if fia:
                ivar_shape = (len(stms), len(spcs) * 2)
                ivar_num = len(stms) * len(spcs) * 2
            else:
                ivar_shape = (len(stms), len(spcs))
                ivar_num = len(stms) * len(spcs)
            if assoc_gas_law and ngas:
                gvar = self.entity["law"][assoc_gas_law]["int_var"]
                gmml = self.entity["var"][gvar]["sym"]
                gsym = MMLExpression(gmml).to_numpy()
                gind = f"[{ivar_num}:{ivar_num + ngas}]"
                model.add(f"{gsym} = np.array({isym}{gind}, dtype=np.float64)", 2)
            if assoc_sld_law and nsld:
                svar = self.entity["law"][assoc_sld_law]["int_var"]
                smml = self.entity["var"][svar]["sym"]
                ssym = MMLExpression(smml).to_numpy()
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
            if var_dict["cls"] != "PhysicsParameter":
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
                        codes = self.context["info"]["rxn"][rxn][sub_law]
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
                raise ValueError(f"Invalid dimensions for mass equilibrium parameter {var}: {dims}")
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
                        codes = self.context["info"]["me"][law][pha][stm][spc]
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
            vars = [var for var in vars if var != "Mass"]
            dims = ["Stream", "Species"]
            sizes = [dim2size[dim] for dim in dims]
            for ind in itertools.product(*[list(range(size)) for size in sizes]):
                ind_isym = self.index_fml(isym, [ivar], dims, ind)
                ind_fml = self.index_fml(fml, vars, dims, ind)
                ind_fml = self.index_fml(ind_fml, ["Mass"], ["Stream"], ind[:1])
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
                    vars = [var for var in vars if var != "Mass"]
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
                                    key = (gas_int_init_val, gas, None, None, spc)
                                    assoc_ivals.append(f"p[{keys.index(key)}]")
                                else:
                                    assoc_ivals.append(0)
                                dims = ["Gas", "Stream", "Species"]
                                ind = [i, j, k]
                                ind_fml = self.index_fml(fml, vars, dims, ind)
                                ind_fml = self.index_fml(
                                    ind_fml, ["Mass"], ["Stream"], ind[1:2])
                                model.add(f"d{gas_isym}[{i}, {j}, {k}] = {ind_fml}", 2)
                if self.entity["law"][mt_law]["assoc_sld_law"]:
                    assoc_sld_law = self.entity["law"][mt_law]["assoc_sld_law"]
                    sld_ivar = self.entity["law"][assoc_sld_law]["int_var"]
                    sld_isym = self.entity["var"][sld_ivar]["sym"]
                    sld_isym = MMLExpression(sld_isym).to_numpy()
                    fml = self.entity["law"][assoc_sld_law]["fml"]
                    fml = MMLExpression(fml).to_numpy()
                    vars = self.entity["law"][assoc_sld_law]["vars"]
                    vars = [var for var in vars if var != "Mass"]
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
                                    key = (sld_int_init_val, sld, None, None, spc)
                                    assoc_ivals.append(f"p[{keys.index(key)}]")
                                else:
                                    assoc_ivals.append(0)
                                dims = ["Solid", "Stream", "Species"]
                                ind = [i, j, k]
                                ind_fml = self.index_fml(fml, vars, dims, ind)
                                ind_fml = self.index_fml(
                                    ind_fml, ["Mass"], ["Stream"], ind[1:2])
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
                    f"{dsym}_eval = np.linspace(0, {iul_sym}, 201, dtype=np.float64)", 1
                )
                model.add(
                    f"res = solve_ivp(derivative, (0, {iul_sym}), "
                    f"{isym}_0, t_eval={dsym}_eval, method='LSODA', atol=1e-12)", 1
                )
                model.add(f"if res.success:", 1)
                model.add(f"if np.isnan(res.y).any():", 2)
                model.add(f"return None", 3)
                model.add(f"else:", 2)
            if self.context["type"] == "dynamic":
                model.add(f"t_span = {iul_sym}[-1] / {self.dynamic_segs}", 1)
                model.add("res = {'x': [], 'y': []}", 1)
                model.add("res['x'].append(0)", 1)
                model.add(f"res['y'].append({isym}_0.round(6).tolist())", 1)
                model.add(f"for i in range({self.dynamic_segs}):", 1)
                model.add(
                    "seg_res = solve_ivp(derivative, (t_span * i, t_span * (i+1)), "
                    f"{isym}_0, t_eval=[t_span * i, t_span * (i+1)], method='LSODA', "
                    "atol=1e-12)", 2
                )
                model.add("if np.isnan(seg_res.y).any():", 2)
                model.add("return None", 3)
                model.add("res['x'].append(t_span * (i+1))", 2)
                model.add(f"res['y'].append(seg_res.y[:, -1].round(6).tolist())", 2)
                model.add(f"{isym}_0 = seg_res.y[:, -1]", 2)
                model.add(f"res['x'] = np.array(res['x'])", 1)
                model.add(f"res['y'] = np.stack(res['y'], axis=-1)", 1)
                
        
        if fia:
            model.add(f"return [res.x.round(6), res.y.round(6)[:{nstm * nspc}], q]", 3)
            model.add(f"else:", 1)
            model.add(f"return None", 2)
        else:
            if self.context["type"] == "steady":
                iul_unit = self.entity["var"][iul_var]["unit"]
                if iul_unit and self.entity["unit"][iul_unit]["intcpt"]:
                    intcpt = self.entity["unit"][iul_unit]["intcpt"]
                    model.add(f"res.t -= {intcpt}", 3)
                if iul_unit and self.entity["unit"][iul_unit]["rto"]:
                    rto = self.entity["unit"][iul_unit]["rto"]
                    model.add(f"res.t /= {rto}", 3)
                # TODO
                # if self.context["desc"]["ac"] == "Continuous":
                #     model.add(f"return {{'x': {{'{dsym}': res.t.round(6).tolist()}}}}", 3)
                #     # model.add(f"return [res.t.round(6), res.y.round(6), q]", 3)
                if self.context["desc"]["ac"] == "Batch":
                    model.add("res_dict = {"
                        "'x': {'ind': None, 'val': None}, "
                        "'y': {'ind': [], 'val': []}, "
                    "}", 3)
                    model.add(f"res_dict['x']['ind'] = {(dvar, None, None, None, None)}", 3)
                    model.add(f"res_dict['x']['val'] = res.t.round(6).tolist()", 3)
                    out_ind = 0
                    for i, stm in enumerate(stms):
                        for j, spc in enumerate(spcs):
                            model.add(f"res_dict['y']['ind'].append({(ivar, None, stm, None, spc)})", 3)
                            model.add(f"res_dict['y']['val'].append(res.y[{out_ind}].round(6).tolist())", 3)
                            out_ind += 1
                    for j, spc in enumerate(spcs):
                        model.add(f"res_dict['y']['ind'].append({(ivar, None, 'Overall', None, spc)})", 3)
                        model.add(f"res_dict['y']['val'].append(res.y[:{nstm*nspc}].reshape("
                                  f"{nstm},{nspc},-1)[:,{j}].sum(axis=0).round(6).tolist())", 3)
                    if assoc_gas_law and ngas:
                        for i, gas in enumerate(gass):
                            for j, spc in enumerate(self.context["basic"]["gas"][gas]["spc"]):
                                model.add(f"res_dict['y']['ind'].append({(gvar, gas, None, None, spc)})", 3)
                                model.add(f"res_dict['y']['val'].append(res.y[{out_ind}].round(6).tolist())", 3)
                                out_ind += 1
                    if assoc_sld_law and nsld:
                        for i, sld in enumerate(slds):
                            for j, spc in enumerate(self.context["basic"]["sld"][sld]["spc"]):
                                model.add(f"res_dict['y']['ind'].append({(svar, sld, None, None, spc)})", 3)
                                model.add(f"res_dict['y']['val'].append(res.y[{out_ind}].round(6).tolist())", 3)
                                out_ind += 1
                    model.add("return res_dict", 3)
                model.add(f"else:", 1)
                model.add(f"return None", 2)
            if self.context["type"] == "dynamic":
                iul_unit = self.entity["var"][iul_var]["unit"]
                if iul_unit and self.entity["unit"][iul_unit]["intcpt"]:
                    intcpt = self.entity["unit"][iul_unit]["intcpt"]
                    model.add(f"res['x'] -= {intcpt}", 1)
                if iul_unit and self.entity["unit"][iul_unit]["rto"]:
                    rto = self.entity["unit"][iul_unit]["rto"]
                    model.add(f"res['x'] /= {rto}", 1)
                if self.context["desc"]["ac"] == "Batch":
                    model.add("res_dict = {"
                        "'x': {'ind': None, 'val': None}, "
                        "'y': {'ind': [], 'val': []}, "
                    "}", 1)
                    model.add(f"res_dict['x']['ind'] = {(dvar, None, None, None, None)}", 1)
                    model.add(f"res_dict['x']['val'] = res['x'].round(6).tolist()", 1)
                    out_ind = 0
                    for i, stm in enumerate(stms):
                        for j, spc in enumerate(spcs):
                            model.add(f"res_dict['y']['ind'].append({(ivar, None, stm, None, spc)})", 1)
                            model.add(f"res_dict['y']['val'].append(res['y'][{out_ind}].round(6).tolist())", 1)
                            out_ind += 1
                    for j, spc in enumerate(spcs):
                        model.add(f"res_dict['y']['ind'].append({(ivar, None, 'Overall', None, spc)})", 1)
                        model.add(f"res_dict['y']['val'].append(res['y'][:{nstm*nspc}].reshape("
                                  f"{nstm},{nspc},-1)[:,{j}].sum(axis=0).round(6).tolist())", 1)
                    if assoc_gas_law and ngas:
                        for i, gas in enumerate(gass):
                            for j, spc in enumerate(self.context["basic"]["gas"][gas]["spc"]):
                                model.add(f"res_dict['y']['ind'].append({(gvar, gas, None, None, spc)})", 1)
                                model.add(f"res_dict['y']['val'].append(res['y'][{out_ind}].round(6).tolist())", 1)
                                out_ind += 1
                    if assoc_sld_law and nsld:
                        for i, sld in enumerate(slds):
                            for j, spc in enumerate(self.context["basic"]["sld"][sld]["spc"]):
                                model.add(f"res_dict['y']['ind'].append({(svar, sld, None, None, spc)})", 1)
                                model.add(f"res_dict['y']['val'].append(res['y'][{out_ind}].round(6).tolist())", 1)
                                out_ind += 1
                    model.add("return res_dict", 1)
        
        return model.get_model()