import re
import pygraphdb
from .mml_expression import MMLExpression


class GraphdbHandler:
    """
    Class to handle connection with graphdb for querying and convert ontologies to dict.

    SPARQL template is used to query graphdb.
    """
    
    def __init__(self, config):
        self.host =                         config.GRAPHDB_HOST
        self.port =                         config.GRAPHDB_PORT
        self.user =                         config.GRAPHDB_USER
        self.password =                     config.GRAPHDB_PASSWORD
        self.db =                           config.GRAPHDB_DB
        self.prefix =                       config.PREFIX
        self.phenomenon_classes =           config.PHENOMENON_CLASSES
        self.model_variable_classes =       config.MODEL_VARIABLE_CLASSES
        self.data_source_classes =          config.DATA_SOURCE_CLASSES
        self.context_descriptor_classes =   config.CONTEXT_DESCRIPTOR_CLASSES
        self.ns_dict =                      config.NS_DICT
        self.conn = pygraphdb.connect(self.host, self.port, self.user, self.password, self.db)
        self.cur = self.conn.cursor()


    def query(self, mode=None):
        phenomenon = self.query_phenomenon()
        model_dimension = self.query_model_dimension()
        model_variable = self.query_model_variable()
        definition = self.query_definition(mode)
        law = self.query_law(mode)
        unit = self.query_unit()
        data_source = self.query_data_source()
        context_descriptor = self.query_context_descriptor()
        rule = self.query_rule()
        return {
            "phenomenon": phenomenon,
            "model_dimension": model_dimension,
            "model_variable": model_variable,
            "definition": definition,
            "law": law,
            "unit": unit,
            "data_source": data_source,
            "context_descriptor": context_descriptor,
            "rule": rule,
        }


    def query_phenomenon(self):
        phenomena = {}
        for subclass in self.phenomenon_classes:
            sparql = self.prefix + \
                "select ?p where {" \
                f"?p rdf:type {self.ns_dict[subclass]}:{subclass}. " \
                "}"
            sparql_res = self.cur.execute(sparql)
            for phenomenon in sparql_res.split("\r\n")[1:-1]:
                ns, phenomenon = phenomenon.split("#")
                phenomena[phenomenon] = {
                    "ns": ns,
                    "class": subclass,
                    "flow_patterns": [],
                    "molecular_transport_phenomena": [],
                }

        sparql = self.prefix + \
            "select ?p ?rp where {" \
            f"?p rdf:type {self.ns_dict['Accumulation']}:Accumulation. " \
            f"optional{{?p {self.ns_dict['relatesToFlowPattern']}:relatesToFlowPattern ?rp}}. " \
            "}"
        sparql_res = self.cur.execute(sparql)
        for res in sparql_res.split("\r\n")[1:-1]:
            phenomenon, flow_pattern = res.split(",")
            phenomenon = phenomenon.split("#")[-1]
            flow_pattern = flow_pattern.split("#")[-1]
            if flow_pattern != "" and flow_pattern not in phenomena[phenomenon]["flow_patterns"]:
                phenomena[phenomenon]["flow_patterns"].append(flow_pattern)

        sparql = self.prefix + \
            "select ?p ?rp where {" \
            f"?p rdf:type {self.ns_dict['FlowPattern']}:FlowPattern. " \
            f"optional{{?p {self.ns_dict['relatesToMolecularTransportPhenomenon']}:relatesToMolecularTransportPhenomenon ?rp}}. " \
            "}"
        sparql_res = self.cur.execute(sparql)
        for res in sparql_res.split("\r\n")[1:-1]:
            phenomenon, molecular_transport_phenomenon = res.split(",")
            phenomenon = phenomenon.split("#")[-1]
            molecular_transport_phenomenon = molecular_transport_phenomenon.split("#")[-1]
            if molecular_transport_phenomenon != "" and molecular_transport_phenomenon not in phenomena[phenomenon]["molecular_transport_phenomena"]:
                phenomena[phenomenon]["molecular_transport_phenomena"].append(molecular_transport_phenomenon)
        
        phenomena = dict(sorted(phenomena.items(), key=lambda x: x[0]))
        for phenomenon in phenomena:
            phenomena[phenomenon]["flow_patterns"] = sorted(phenomena[phenomenon]["flow_patterns"])
            phenomena[phenomenon]["molecular_transport_phenomena"] = sorted(phenomena[phenomenon]["molecular_transport_phenomena"])
        return phenomena


    def query_model_dimension(self):
        dimensions = {}
        sparql = self.prefix + \
            "select ?d where {" \
            f"?d rdf:type {self.ns_dict['ModelDimension']}:ModelDimension. " \
            "}"
        sparql_res = self.cur.execute(sparql)
        for dimension in sparql_res.split("\r\n")[1:-1]:
            ns, dimension = dimension.split("#")
            dimensions[dimension] = {
                "ns": ns,
                "class": "ModelDimension", 
            }
        dimensions = dict(sorted(dimensions.items(), key=lambda x: x[0]))
        return dimensions


    def query_definition(self, mode):
        definitions = {}
        
        sparql = self.prefix + \
            "select ?d where {" \
            f"?d rdf:type {self.ns_dict['Definition']}:Definition. " \
            "}"
        sparql_res = self.cur.execute(sparql)
        for definition in sparql_res.split("\r\n")[1:-1]:
            ns, definition = definition.split("#")
            definitions[definition] = {
                "ns": ns,
                "class": "Definition", 
                "model_variables": [],
            }
        
        sparql = self.prefix + \
            "select ?d ?ml ?v where {" \
            f"?d rdf:type {self.ns_dict['Definition']}:Definition. " \
            f"?d {self.ns_dict['hasFormula']}:hasFormula ?ml. " \
            f"?d {self.ns_dict['hasModelVariable']}:hasModelVariable ?v. " \
            "}"
        sparql_res = self.cur.execute(sparql)
        for res in sparql_res.split("\r\n")[1:-1]:
            definition, formula, model_variable = res.split(",")
            definition = definition.split("#")[-1]
            formula = re.sub(r'("*)"', r'\1', formula)
            formula = re.sub(r' xmlns=".*"', "", formula)
            if mode == "sidebar":
                formula = MMLExpression(formula).to_sidebar_mml()
            if mode == "mainpage":
                formula = MMLExpression(formula).to_mainpage_mml()
            definitions[definition]["formula"] = formula
            model_variable = model_variable.split("#")[-1]
            if model_variable not in definitions[definition]["model_variables"]:
                definitions[definition]["model_variables"].append(model_variable)
        
        definitions = dict(sorted(definitions.items(), key=lambda x: x[0]))
        for definition in definitions:
            definitions[definition]["model_variables"] = sorted(definitions[definition]["model_variables"])
        return definitions
        

    def query_law(self, mode):
        laws = {}
        
        sparql = self.prefix + \
            "select ?d where {" \
            f"?d rdf:type {self.ns_dict['Law']}:Law. " \
            "}"
        sparql_res = self.cur.execute(sparql)
        for law in sparql_res.split("\r\n")[1:-1]:
            ns, law = law.split("#")
            laws[law] = {
                "ns": ns,
                "class": "Law", 
                "rule": None, 
                "doi": None,
                "formula": None, 
                "phenomenon": None,
                "model_variables": [],
                "optional_model_variables": [],
                "differential_model_variable": None,
                "differential_upper_limit": None,
                "differential_initial_value": None,
                "formula_integrated_with_accumulation": None, 
            }

        sparql = self.prefix + \
            "select ?d ?ml ?p ?r ?doi ?v ?ov ?dv ?ul ?iv ?aml where {" \
            f"?d rdf:type {self.ns_dict['Law']}:Law. " \
            f"?d {self.ns_dict['hasFormula']}:hasFormula ?ml. " \
            f"?d {self.ns_dict['isAssociatedWith']}:isAssociatedWith ?p. " \
            f"optional{{?d {self.ns_dict['hasRule']}:hasRule ?r}}. " \
            f"optional{{?d {self.ns_dict['hasDOI']}:hasDOI ?doi}}. " \
            f"optional{{?d {self.ns_dict['hasModelVariable']}:hasModelVariable ?v}}. " \
            f"optional{{?d {self.ns_dict['hasOptionalModelVariable']}:hasOptionalModelVariable ?ov}}. " \
            f"optional{{?d {self.ns_dict['hasDifferentialModelVariable']}:hasDifferentialModelVariable ?dv}}. " \
            f"optional{{?d {self.ns_dict['hasDifferentialUpperLimit']}:hasDifferentialUpperLimit ?ul}}. " \
            f"optional{{?d {self.ns_dict['hasDifferentialInitialValue']}:hasDifferentialInitialValue ?iv}}. " \
            f"optional{{?d {self.ns_dict['hasFormulaIntegratedWithAccumulation']}:hasFormulaIntegratedWithAccumulation ?aml}}. " \
            "}"
        sparql_res = self.cur.execute(sparql)
        for res in sparql_res.split("\r\n")[1:-1]:
            law, formula, phenomenon, rule, doi, model_variable, optional_model_variable, differential_model_variable, \
                differential_upper_limit, differential_initial_value, formula_integrated_with_accumulation = res.split(",")
            law = law.split("#")[-1]
            phenomenon = phenomenon.split("#")[-1]
            rule = rule.split("#")[-1]
            doi = doi.split("#")[-1]
            model_variable = model_variable.split("#")[-1]
            optional_model_variable = optional_model_variable.split("#")[-1]
            differential_model_variable = differential_model_variable.split("#")[-1]
            differential_upper_limit = differential_upper_limit.split("#")[-1]
            differential_initial_value = differential_initial_value.split("#")[-1]
            formula = re.sub(r'("*)"', r'\1', formula)
            formula = re.sub(r' xmlns=".*"', "", formula)
            formula_integrated_with_accumulation = re.sub(r'("*)"', r'\1', formula_integrated_with_accumulation)
            formula_integrated_with_accumulation = re.sub(r' xmlns=".*"', "", formula_integrated_with_accumulation)
            if mode == "sidebar":
                formula = MMLExpression(formula).to_sidebar_mml()
            if mode == "mainpage":
                formula = MMLExpression(formula).to_mainpage_mml()
            laws[law]["formula"] = formula
            laws[law]["phenomenon"] = phenomenon
            if model_variable != "" and model_variable not in laws[law]["model_variables"]:
                laws[law]["model_variables"].append(model_variable)
            if optional_model_variable != "" and optional_model_variable not in laws[law]["optional_model_variables"]:
                laws[law]["optional_model_variables"].append(optional_model_variable)
            if rule != "":
                laws[law]["rule"] = rule
            if doi != "":
                laws[law]["doi"] = doi
            if differential_model_variable != "":
                laws[law]["differential_model_variable"] = differential_model_variable
            if differential_upper_limit != "":
                laws[law]["differential_upper_limit"] = differential_upper_limit
            if differential_initial_value != "":
                laws[law]["differential_initial_value"] = differential_initial_value
            if formula_integrated_with_accumulation != "":
                laws[law]["formula_integrated_with_accumulation"] = formula_integrated_with_accumulation

        laws = dict(sorted(laws.items(), key=lambda x: x[0]))
        for law in laws:
            laws[law]["model_variables"] = sorted(laws[law]["model_variables"])
            laws[law]["optional_model_variables"] = sorted(laws[law]["optional_model_variables"])
        return laws


    def query_model_variable(self):
        model_variables = {}
        
        for subclass in self.model_variable_classes:
            sparql = self.prefix + \
                "select ?v where {" \
                f"?v rdf:type {self.ns_dict[subclass]}:{subclass}. " \
                "}"
            sparql_res = self.cur.execute(sparql)
            for variable in sparql_res.split("\r\n")[1:-1]:
                ns, variable = variable.split("#")
                model_variables[variable] = {
                    "ns": ns,
                    "class": subclass,
                    "symbol": None,
                    "value": None,
                    "unit": None,
                    "dimensions": [],
                    "definition": None, 
                    "laws": [],
                }
        
            sparql = self.prefix + \
                "select ?v ?ml ?val ?d ?l ?df ?u where {" \
                f"?v rdf:type {self.ns_dict[subclass]}:{subclass}. " \
                f"?v {self.ns_dict['hasSymbol']}:hasSymbol ?ml. " \
                f"optional{{?v {self.ns_dict['hasValue']}:hasValue ?val}}. " \
                f"optional{{?v {self.ns_dict['hasDimension']}:hasDimension ?d}}. " \
                f"optional{{?v {self.ns_dict['hasDefinition']}:hasDefinition ?df}}. " \
                f"optional{{?v {self.ns_dict['hasLaw']}:hasLaw ?l}}. " \
                f"optional{{?v {self.ns_dict['hasUnitOfMeasure']}:hasUnitOfMeasure ?u}}. " \
                "}"
            sparql_res = self.cur.execute(sparql)
            for res in sparql_res.split("\r\n")[1:-1]:
                variable, symbol, value, dimension, law, definition, unit = res.split(",")
                variable = variable.split("#")[-1]
                symbol = re.sub(r'("*)"', r'\1', symbol)
                symbol = re.sub(r' xmlns="[^"]*"', "", symbol)
                symbol = re.sub(r'\n *', "", symbol)
                value = float(value.split("#")[-1]) if value else None
                dimension = " ".join(dimension.split("#")[-1].split("_")[:-1])
                law = law.split("#")[-1]
                model_variables[variable]["value"] = value
                model_variables[variable]["symbol"] = symbol
                definition = definition.split("#")[-1]
                unit = unit.split("#")[-1]
                if dimension != "" and dimension not in model_variables[variable]["dimensions"]:
                    model_variables[variable]["dimensions"].append(dimension)
                if law != "" and law not in model_variables[variable]["laws"]:
                    model_variables[variable]["laws"].append(law)
                if definition != "":
                    model_variables[variable]["definition"] = definition
                if unit != "":
                    model_variables[variable]["unit"] = unit

        model_variables = dict(sorted(model_variables.items(), key=lambda x: x[0]))
        for model_variable in model_variables:
            model_variables[model_variable]["laws"] = sorted(model_variables[model_variable]["laws"])
            model_variables[model_variable]["dimensions"] = sorted(model_variables[model_variable]["dimensions"])
        return model_variables


    def query_unit(self):
        units = {}
        sparql = self.prefix + \
            "select ?u where {" \
            f"VALUES ?type {{{self.ns_dict['SI_BaseUnit']}:SI_BaseUnit {self.ns_dict['SI_DerivedUnit']}:SI_DerivedUnit}}. " \
            f"?u rdf:type ?type. " \
            "}"
        sparql_res = self.cur.execute(sparql)
        for unit in sparql_res.split("\r\n")[1:-1]:
            ns, unit = unit.split("#")
            units[unit] = {
                "ns": ns,
                "class": None, 
                "symbol": None, 
                "standard_unit": None,
                "ratio_to_standard_unit": None,
            }

        sparql = self.prefix + \
            "select ?u ?t ?s ?su ?r where {" \
            f"VALUES ?t {{{self.ns_dict['SI_BaseUnit']}:SI_BaseUnit {self.ns_dict['SI_DerivedUnit']}:SI_DerivedUnit}}. " \
            f"?u rdf:type ?t. " \
            f"optional{{?u {self.ns_dict['hasSymbol']}:hasSymbol ?s}}. " \
            f"optional{{?u {self.ns_dict['hasStandardUnitOfMeasure']}:hasStandardUnitOfMeasure ?su}}. " \
            f"optional{{?u {self.ns_dict['hasRatioToStandardUnitOfMeasure']}:hasRatioToStandardUnitOfMeasure ?r}}. " \
            "}"
        sparql_res = self.cur.execute(sparql)
        for res in sparql_res.split("\r\n")[1:-1]:
            unit, type, symbol, standard_unit, ratio_to_standard_unit = res.split(",")
            unit = unit.split("#")[-1]
            type = type.split("#")[-1]
            symbol = re.sub(r'("*)"', r'\1', symbol)
            symbol = re.sub(r' xmlns="[^"]*"', "", symbol)
            symbol = re.sub(r'\n *', "", symbol)
            standard_unit = standard_unit.split("#")[-1]
            ratio_to_standard_unit = ratio_to_standard_unit.split("#")[-1]
            units[unit]["class"] = type
            if symbol != "":
                units[unit]["symbol"] = symbol
            if standard_unit != "":
                units[unit]["standard_unit"] = standard_unit
            if ratio_to_standard_unit != "":
                units[unit]["ratio_to_standard_unit"] = float(ratio_to_standard_unit)

        units = dict(sorted(units.items(), key=lambda x: x[0]))
        return units


    def query_data_source(self):
        data_sources = {}

        for subclass in self.data_source_classes:
            sparql = self.prefix + \
                "select ?v where {" \
                f"?v rdf:type {self.ns_dict[subclass]}:{subclass}. " \
                "}"
            sparql_res = self.cur.execute(sparql)
            for data_source in sparql_res.split("\r\n")[1:-1]:
                ns, data_source = data_source.split("#")
                data_sources[data_source] = {
                    "ns": ns,
                    "class": subclass,
                    "url": None,
                }

            sparql = self.prefix + \
                "select ?ds ?url where {" \
                f"?ds rdf:type {self.ns_dict[subclass]}:{subclass}. " \
                f"?ds {self.ns_dict['hasURL']}:hasURL ?url. " \
                "}"
            sparql_res = self.cur.execute(sparql)
            for res in sparql_res.split("\r\n")[1:-1]:
                data_source, url = res.split(",")
                data_source = data_source.split("#")[-1]
                url = url.split("#")[-1]
                data_sources[data_source]["url"] = url

        data_sources = dict(sorted(data_sources.items(), key=lambda x: x[0]))
        return data_sources


    def query_context_descriptor(self):
        context_descriptors = {}

        for subclass in self.context_descriptor_classes:
            sparql = self.prefix + \
                "select ?d where {" \
                f"?d rdf:type {self.ns_dict[subclass]}:{subclass}. " \
                "}"
            sparql_res = self.cur.execute(sparql)
            for context_descriptor in sparql_res.split("\r\n")[1:-1]:
                ns, context_descriptor = context_descriptor.split("#")
                context_descriptors[context_descriptor] = {
                    "ns": ns,
                    "class": subclass,
                    "symbol": None,
                    "unit": None,
                }
            
            sparql = self.prefix + \
                "select ?d ?s ?u where {" \
                f"?d rdf:type {self.ns_dict[subclass]}:{subclass}. " \
                f"optional{{?d {self.ns_dict['hasSymbol']}:hasSymbol ?s}}. " \
                f"optional{{?d {self.ns_dict['hasUnitOfMeasure']}:hasUnitOfMeasure ?u}}. " \
                "}"
            sparql_res = self.cur.execute(sparql)
            for res in sparql_res.split("\r\n")[1:-1]:
                context_descriptor, symbol, unit = res.split(",")
                context_descriptor = context_descriptor.split("#")[-1]
                symbol = re.sub(r'("*)"', r'\1', symbol)
                symbol = re.sub(r' xmlns="[^"]*"', "", symbol)
                symbol = re.sub(r'\n *', "", symbol)
                unit = unit.split("#")[-1]
                if symbol != "":
                    context_descriptors[context_descriptor]["symbol"] = symbol
                if unit != "":
                    context_descriptors[context_descriptor]["unit"] = unit

        context_descriptors = dict(sorted(context_descriptors.items(), key=lambda x: x[0]))
        return context_descriptors


    def query_rule(self):
        rules = {}

        sparql = self.prefix + \
        "select ?r where {" \
        f"?r rdf:type {self.ns_dict['Rule']}:{'Rule'}. " \
        "}"
        sparql_res = self.cur.execute(sparql)
        for rule in sparql_res.split("\r\n")[1:-1]:
            ns, rule = rule.split("#")
            rules[rule] = {
                "ns": ns,
                "class": "Rule",
                "phenomena": [],
                "context_descriptors": [],
                "sparql": None,
                "doi": None,
            }
        
        sparql = self.prefix + \
            "select ?r ?d ?p ?doi ?s where {" \
            f"?r rdf:type {self.ns_dict['Rule']}:Rule. " \
            f"?r {self.ns_dict['hasContextDescriptor']}:hasContextDescriptor ?d. " \
            f"?r {self.ns_dict['isAssociatedWith']}:isAssociatedWith ?p. " \
            f"?r {self.ns_dict['hasSPARQL']}:hasSPARQL ?s. " \
            f"optional{{?r {self.ns_dict['hasDOI']}:hasDOI ?doi}}. " \
            "}"
        sparql_res = self.cur.execute(sparql)
        for res in sparql_res.split("\r\n")[1:-1]:
            rule, context_descriptor, phenomenon, doi = res.split(",")[:4]
            sparql = ",".join(res.split(",")[4:])[1:-1]
            rule = rule.split("#")[-1]
            context_descriptor = context_descriptor.split("#")[-1]
            phenomenon = phenomenon.split("#")[-1]
            if context_descriptor != "" and context_descriptor not in rules[rule]["context_descriptors"]:
                rules[rule]["context_descriptors"].append(context_descriptor)
            if phenomenon != "" and phenomenon not in rules[rule]["phenomena"]:
                rules[rule]["phenomena"].append(phenomenon)
            rules[rule]["doi"] = doi if doi else "None"
            rules[rule]["sparql"] = sparql

        rules = dict(sorted(rules.items(), key=lambda x: x[0]))
        for rule in rules:
            rules[rule]["phenomena"] = sorted(rules[rule]["phenomena"])
            rules[rule]["context_descriptors"] = sorted(rules[rule]["context_descriptors"])
        return rules


    def query_phenomenon_ac(self, ac):
        """
        Query all FlowPattern individuals related to a specific Accumulation individual.
        The input `ac` is expected to indicate which Accumulation individual to filter, e.g.,
        "Batch" or "Continuous". Matching is case-insensitive.

        Returns a sorted list of FlowPattern local names.
        """
        if ac is None:
            return []

        # Normalize input (accepts 'batch'/'continuous' and similar variants)
        ac_str = str(ac).strip()
        if not ac_str:
            return []

        # Build SPARQL using configured prefixes/namespaces and pygraphdb cursor
        sparql = self.prefix + \
            "select ?p ?rp where {" \
            f"?p rdf:type {self.ns_dict['Accumulation']}:Accumulation. " \
            f"optional{{?p {self.ns_dict['relatesToFlowPattern']}:relatesToFlowPattern ?rp}}. " \
            f"FILTER(regex(str(?p), '#{ac_str}$', 'i')). " \
            "}"

        try:
            sparql_res = self.cur.execute(sparql)
        except Exception:
            # If cursor-based execution fails for any reason, return empty to keep API stable
            return []

        flow_patterns = set()
        # Expect CSV-like lines: header, then "<p>,<rp>"; handle empty right part
        for res in sparql_res.split("\r\n")[1:-1]:
            try:
                phenomenon, flow_pattern = res.split(",")
            except ValueError:
                # In case the backend returns a single column or malformed line
                parts = res.split(",")
                phenomenon = parts[0] if parts else ""
                flow_pattern = parts[1] if len(parts) > 1 else ""
            flow_pattern = flow_pattern.split("#")[-1]
            if flow_pattern:
                flow_patterns.add(flow_pattern)

        return sorted(flow_patterns)

    def query_mass_transfer_by_flow_pattern(self, fp):
        """
        Given a FlowPattern individual name (e.g., "Annular_Microflow"),
        return all related MolecularTransportPhenomenon local names (mass transfer phenomena).
        Matching of the flow pattern is case-insensitive against the IRI tail.
        """
        if fp is None:
            return []
        fp_str = str(fp).strip()
        if not fp_str:
            return []

        sparql = self.prefix + \
            "select ?fp ?mt where {" \
            f"?fp rdf:type {self.ns_dict['FlowPattern']}:FlowPattern. " \
            f"optional{{?fp {self.ns_dict['relatesToMolecularTransportPhenomenon']}:relatesToMolecularTransportPhenomenon ?mt}}. " \
            f"FILTER(regex(str(?fp), '#{fp_str}$', 'i')). " \
            "}"

        try:
            sparql_res = self.cur.execute(sparql)
        except Exception:
            return []

        mass_transfers = set()
        for res in sparql_res.split("\r\n")[1:-1]:
            try:
                fp_iri, mt_iri = res.split(",")
            except ValueError:
                parts = res.split(",")
                mt_iri = parts[1] if len(parts) > 1 else ""
            mt_name = mt_iri.split("#")[-1]
            if mt_name:
                mass_transfers.add(mt_name)
        return sorted(mass_transfers)

    def query_mass_equilibrium_by_mass_transfer(self, mt):
        """
        Given a MolecularTransportPhenomenon individual name (e.g., "Engulfment" or "mass_diffusion"),
        return all related PhysicalEquilibriumPhenomenon local names ("mass equilibrium") by traversing
        Laws that are associated with both the given MTP and a PhysicalEquilibriumPhenomenon.
        Matching of the MTP is case-insensitive against the IRI tail.
        """
        if mt is None:
            return []
        mt_str = str(mt).strip()
        if not mt_str:
            return []

        sparql = self.prefix + \
            "select ?mtp ?eq where {" \
            f"?mtp rdf:type {self.ns_dict['MolecularTransportPhenomenon']}:MolecularTransportPhenomenon. " \
            f"FILTER(regex(str(?mtp), '#{mt_str}$', 'i')). " \
            f"?d rdf:type {self.ns_dict['Law']}:Law. " \
            f"?d {self.ns_dict['isAssociatedWith']}:isAssociatedWith ?mtp. " \
            f"?d {self.ns_dict['isAssociatedWith']}:isAssociatedWith ?eq. " \
            f"?eq rdf:type {self.ns_dict['PhysicalEquilibriumPhenomenon']}:PhysicalEquilibriumPhenomenon. " \
            "}"

        try:
            sparql_res = self.cur.execute(sparql)
        except Exception:
            return []

        equilibria = set()
        for res in sparql_res.split("\r\n")[1:-1]:
            parts = res.split(",")
            eq_iri = parts[1] if len(parts) > 1 else ""
            eq_name = eq_iri.split("#")[-1]
            if eq_name:
                equilibria.add(eq_name)

        return sorted(equilibria)
 
    def query_param_law(self, filters):
        """
        Retrieve parameter -> law mapping for Laws associated with provided phenomena.
        filters: dict with optional keys 'ac', 'fp', 'mt', 'me'; values may be string or list of strings.
        Returns: dict { parameter_name: law_name }
        """

        ## Dr Ryan
        if not isinstance(filters, dict):
            return {}

        # Normalize filter values to lists of non-empty strings
        def _norm(v):
            if v is None:
                return []
            if isinstance(v, list):
                items = v
            else:
                items = [v]
            out = []
            for s in items:
                if s is None:
                    continue
                s2 = str(s).strip()
                if s2:
                    out.append(s2)
            return out

        ac_list = _norm(filters.get("ac"))
        fp_list = _norm(filters.get("fp"))
        mt_list = _norm(filters.get("mt"))
        me_list = _norm(filters.get("me"))

        if not (ac_list or fp_list or mt_list or me_list):
            return {}

        # Build UNION blocks for each provided phenomenon group
        union_blocks = []
        def _regex_union(names):
            # Build a single regex that matches any of the names at IRI tail
            esc = [re.escape(n) for n in names]
            pattern = "|".join(esc)
            return pattern

        if ac_list:
            pattern = _regex_union(ac_list)
            union_blocks.append(
                "{"
                f"?d {self.ns_dict['isAssociatedWith']}:isAssociatedWith ?phen_ac. "
                f"?phen_ac rdf:type {self.ns_dict['Accumulation']}:Accumulation. "
                f"FILTER(regex(str(?phen_ac), '#({pattern})$', 'i')). "
                "}"
            )
        if fp_list:
            pattern = _regex_union(fp_list)
            union_blocks.append(
                "{"
                f"?d {self.ns_dict['isAssociatedWith']}:isAssociatedWith ?phen_fp. "
                f"?phen_fp rdf:type {self.ns_dict['FlowPattern']}:FlowPattern. "
                f"FILTER(regex(str(?phen_fp), '#({pattern})$', 'i')). "
                "}"
            )
        if mt_list:
            pattern = _regex_union(mt_list)
            union_blocks.append(
                "{"
                f"?d {self.ns_dict['isAssociatedWith']}:isAssociatedWith ?phen_mt. "
                f"?phen_mt rdf:type {self.ns_dict['MolecularTransportPhenomenon']}:MolecularTransportPhenomenon. "
                f"FILTER(regex(str(?phen_mt), '#({pattern})$', 'i')). "
                "}"
            )
        if me_list:
            pattern = _regex_union(me_list)
            union_blocks.append(
                "{"
                f"?d {self.ns_dict['isAssociatedWith']}:isAssociatedWith ?phen_me. "
                f"?phen_me rdf:type {self.ns_dict['PhysicalEquilibriumPhenomenon']}:PhysicalEquilibriumPhenomenon. "
                f"FILTER(regex(str(?phen_me), '#({pattern})$', 'i')). "
                "}"
            )

        # Parameter variable classes
        param_types = [
            "FlowParameter",
            "ReactorParameter",
            "ReactionParameter",
            "PhysicalParameter",
            "OperatingParameter",
            "MolecularTransportParameter",
        ]
        values_param_types = " ".join([f"{self.ns_dict[t]}:{t}" for t in param_types])

        sparql = self.prefix + \
            "select ?v ?d where {" \
            f"?d rdf:type {self.ns_dict['Law']}:Law. " \
            f"{{ ?d {self.ns_dict['hasModelVariable']}:hasModelVariable ?v }} UNION {{ ?d {self.ns_dict['hasOptionalModelVariable']}:hasOptionalModelVariable ?v }}. " \
            f"?v rdf:type ?pt. VALUES ?pt {{{values_param_types}}}. "

        # Add phenomenon association constraints via UNION of provided groups (ANY of them)
        if union_blocks:
            sparql += "(" + " UNION ".join(union_blocks) + ") . "

        sparql += "}"

        try:
            sparql_res = self.cur.execute(sparql)
        except Exception:
            return {}

        mapping = {}
        # Expect lines: header then rows of two columns v,d
        for res in sparql_res.split("\r\n")[1:-1]:
            parts = res.split(",")
            if len(parts) < 2:
                continue
            var_iri, law_iri = parts[0], parts[1]
            var_name = var_iri.split("#")[-1]
            law_name = law_iri.split("#")[-1]
            if not var_name or not law_name:
                continue
            # Deterministic selection: keep lexicographically smallest law if multiple
            if var_name in mapping:
                if law_name < mapping[var_name]:
                    mapping[var_name] = law_name
            else:
                mapping[var_name] = law_name

        return dict(sorted(mapping.items(), key=lambda x: x[0]))

    def query_reactions(self, filters=None):
        """
        Retrieve reactions and their associated kinetic law names.
        filters: optional dict with keys 'ac', 'fp', 'mt', 'me' (string or list) to constrain Laws via isAssociatedWith,
                 and optional 'param_law' to constrain by specific law name(s).
        - filters['param_law'] may be:
            - dict { parameter_name: law_name }
            - list [law_name, ...]
            - string law_name
        Returns: dict { reaction_local_name: [law_name, ...] }
        """
        if filters is None:
            filters = {}
        if not isinstance(filters, dict):
            return {}

        # Normalize filters to lists
        def _norm(v):
            if v is None:
                return []
            if isinstance(v, list):
                items = v
            else:
                items = [v]
            out = []
            for s in items:
                if s is None:
                    continue
                s2 = str(s).strip()
                if s2:
                    out.append(s2)
            return out

        ac_list = _norm(filters.get("ac"))
        fp_list = _norm(filters.get("fp"))
        mt_list = _norm(filters.get("mt"))
        me_list = _norm(filters.get("me"))

        # Extract law-name filters from 'param_law'
        law_list = []
        pl = filters.get("param_law")
        if isinstance(pl, dict):
            law_list = _norm(list(pl.values()))
        elif isinstance(pl, (list, tuple)):
            law_list = _norm(list(pl))
        elif pl is not None:
            law_list = _norm(pl)

        # UNION constraints for provided phenomena
        union_blocks = []
        def _regex_union(names):
            esc = [re.escape(n) for n in names]
            return "|".join(esc)

        if ac_list:
            p = _regex_union(ac_list)
            union_blocks.append(
                "{"
                f"?d {self.ns_dict['isAssociatedWith']}:isAssociatedWith ?phen_ac. "
                f"?phen_ac rdf:type {self.ns_dict['Accumulation']}:Accumulation. "
                f"FILTER(regex(str(?phen_ac), '#({p})$', 'i')). "
                "}"
            )
        if fp_list:
            p = _regex_union(fp_list)
            union_blocks.append(
                "{"
                f"?d {self.ns_dict['isAssociatedWith']}:isAssociatedWith ?phen_fp. "
                f"?phen_fp rdf:type {self.ns_dict['FlowPattern']}:FlowPattern. "
                f"FILTER(regex(str(?phen_fp), '#({p})$', 'i')). "
                "}"
            )
        if mt_list:
            p = _regex_union(mt_list)
            union_blocks.append(
                "{"
                f"?d {self.ns_dict['isAssociatedWith']}:isAssociatedWith ?phen_mt. "
                f"?phen_mt rdf:type {self.ns_dict['MolecularTransportPhenomenon']}:MolecularTransportPhenomenon. "
                f"FILTER(regex(str(?phen_mt), '#({p})$', 'i')). "
                "}"
            )
        if me_list:
            p = _regex_union(me_list)
            union_blocks.append(
                "{"
                f"?d {self.ns_dict['isAssociatedWith']}:isAssociatedWith ?phen_me. "
                f"?phen_me rdf:type {self.ns_dict['PhysicalEquilibriumPhenomenon']}:PhysicalEquilibriumPhenomenon. "
                f"FILTER(regex(str(?phen_me), '#({p})$', 'i')). "
                "}"
            )

        sparql = self.prefix + \
            "select ?rxn ?d where {" \
            f"?rxn rdf:type {self.ns_dict['ChemicalReactionPhenomenon']}:ChemicalReactionPhenomenon. " \
            f"?d rdf:type {self.ns_dict['Law']}:Law. " \
            f"?d {self.ns_dict['isAssociatedWith']}:isAssociatedWith ?rxn. "

        if union_blocks:
            sparql += "(" + " UNION ".join(union_blocks) + ") . "

        # Constrain by specific kinetic law names if provided
        if law_list:
            p = _regex_union(law_list)
            sparql += f"FILTER(regex(str(?d), '#({p})$', 'i')). "

        sparql += "}"

        try:
            sparql_res = self.cur.execute(sparql)
        except Exception:
            return {}

        mapping = {}
        for line in sparql_res.split("\r\n")[1:-1]:
            parts = line.split(",")
            if len(parts) < 2:
                continue
            rxn_iri, law_iri = parts[0], parts[1]
            rxn_name = rxn_iri.split("#")[-1]
            law_name = law_iri.split("#")[-1]
            if not rxn_name or not law_name:
                continue
            laws = mapping.setdefault(rxn_name, set())
            laws.add(law_name)

        # Convert sets to sorted lists
        return {k: sorted(list(v)) for k, v in sorted(mapping.items(), key=lambda x: x[0])}
 
    def query_accumulators(self):
        """
        Return a sorted list of Accumulation individuals (e.g., 'Batch', 'Continuous').
        """
        sparql = self.prefix + \
            "select ?p where {" \
            f"?p rdf:type {self.ns_dict['Accumulation']}:Accumulation. " \
            "}"
        try:
            sparql_res = self.cur.execute(sparql)
        except Exception:
            return []
        result = set()
        for line in sparql_res.split("\r\n")[1:-1]:
            try:
                ns, name = line.split("#")
            except ValueError:
                parts = line.split("#")
                name = parts[-1] if parts else ""
            name = name.strip()
            if name:
                result.add(name)
        return sorted(result)

    def query_information(self, filters):
        """
        Build a best-effort "information" object from the ontology based on provided filters.
        filters: dict with optional keys {ac, fp, mt, me, param_law, rxn}.
        Returns a dict shaped like:
          {
            "st": { <ReactorParameter>: <value>, ... },
            "mt": { <MolecularTransportParameter>: <value>, ... },
            "rxn": { <ReactionName>: { <ReactionParameter>: <value>, ... }, ... }
          }
        Only sections with content are included.
        """

        ## Dr Ryan
        if not isinstance(filters, dict):
            filters = {}

        # Helper to normalize various inputs to lists
        def _norm_list(v):
            if v is None:
                return []
            if isinstance(v, (list, tuple)):
                items = v
            else:
                items = [v]
            out = []
            for x in items:
                if x is None:
                    continue
                s = str(x).strip()
                if s:
                    out.append(s)
            return out

        # Compose a filters dict for helper queries
        phen_filters = {}
        for k in ("ac", "fp", "mt", "me"):
            if k in filters and filters[k] is not None:
                phen_filters[k] = filters[k]

        # Determine parameter->law map
        param_law_input = filters.get("param_law")
        param_law_map = {}
        if isinstance(param_law_input, dict):
            # Already in desired form
            param_law_map = {str(k): str(v) for k, v in param_law_input.items() if k and v}
        elif param_law_input is not None:
            # list/string of law names: infer parameters whose variables reference these laws
            law_names = set(_norm_list(param_law_input))
            if law_names:
                # Use entity to find variables tied to these laws
                entity = self.query()
                for var, meta in entity.get("model_variable", {}).items():
                    laws = set(meta.get("laws", []) or [])
                    if laws & law_names:
                        # choose a deterministic law name (alphabetically smallest in intersection)
                        chosen = sorted(list(laws & law_names))[0]
                        param_law_map[var] = chosen
            else:
                param_law_map = {}
        else:
            # Derive from phenomena selection
            param_law_map = self.query_param_law(phen_filters) or {}

        # Determine reaction -> laws mapping
        rxn_input = filters.get("rxn")
        rxn_laws = {}
        if isinstance(rxn_input, dict):
            # Ensure values are list
            for r, laws in rxn_input.items():
                rxn_laws[str(r)] = _norm_list(laws)
        elif rxn_input is not None:
            # If a list/string of reaction names given, fetch laws for those reactions via query_reactions
            requested_rxns = set(_norm_list(rxn_input))
            if requested_rxns:
                all_map = self.query_reactions({**phen_filters, "param_law": param_law_map or filters.get("param_law")}) or {}
                rxn_laws = {r: laws for r, laws in all_map.items() if r in requested_rxns}
        else:
            rxn_laws = self.query_reactions({**phen_filters, "param_law": param_law_map or filters.get("param_law")}) or {}

        # Gather variables and metadata
        entity = locals().get('entity') or self.query()
        vars_meta = entity.get("model_variable", {})

        info = {}

        # st: reactor parameters with available values
        st = {}
        for var, meta in vars_meta.items():
            if meta.get("class") == "ReactorParameter" and meta.get("value") is not None:
                st[var] = meta.get("value")
        if st:
            info["st"] = st

        # mt: molecular transport parameters with available values, prioritizing those selected by param_law
        mt_info = {}
        selected_params = set(param_law_map.keys()) if param_law_map else set(
            [v for v, m in vars_meta.items() if m.get("class") == "MolecularTransportParameter"]
        )
        for var in sorted(selected_params):
            meta = vars_meta.get(var)
            if not meta:
                continue
            if meta.get("class") != "MolecularTransportParameter":
                continue
            val = meta.get("value")
            if val is not None:
                mt_info[var] = val
        if mt_info:
            info["mt"] = mt_info

        # rxn: for each reaction, include ReactionParameter values with dimensions == ["Reaction"]
        rxn_info = {}
        for rxn, laws in sorted((rxn_laws or {}).items(), key=lambda x: x[0]):
            details = {}
            law_set = set(laws or [])
            for var, meta in vars_meta.items():
                if meta.get("class") != "ReactionParameter":
                    continue
                dims = meta.get("dimensions") or []
                if set(dims) != {"Reaction"}:
                    # skip solvent/species dependent parameters in this best-effort extractor
                    continue
                # If we have reaction-specific association via variable laws intersecting reaction laws
                v_laws = set(meta.get("laws", []) or [])
                if law_set and not (v_laws & law_set):
                    continue
                val = meta.get("value")
                if val is not None:
                    details[var] = val
            rxn_info[rxn] = details
        if rxn_info:
            info["rxn"] = rxn_info

        return info

    def close(self):
        self.conn.close()