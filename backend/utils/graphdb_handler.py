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
    

    def query_model_me(self, mt):
        print(mt)
        # "mt": ["sdfdsf", "sdfsdfsd", "sdfsdf"]

        return "as"

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


    def close(self):
        self.conn.close()