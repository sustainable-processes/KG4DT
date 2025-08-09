import re
import json
import rdflib
import argparse
from mml_expression import MMLExpression


prefix_rdf = "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>"

domain = (
    "https://raw.githubusercontent.com/sustainable-processes/KG4DT/refs/heads/"
    "dev-alkyne-hydrogenation/ontology"
)
ns_ontomo = f"{domain}/OntoMo.owl#"
ns_system = f"{domain}/OntoCAPE/upper_level/system.owl#"
ns_si_unit = f"{domain}/OntoCAPE/supporting_concepts/SI_unit/SI_unit.owl#"
ns_process = f"{domain}/OntoCAPE/chemical_process_system/CPS_function/process.owl#"
ns_behavior = f"{domain}/OntoCAPE/chemical_process_system/CPS_behavior/behavior.owl#"
ns_process_model = f"{domain}/OntoCAPE/model/process_model.owl#"
ns_mathematical_model = f"{domain}/OntoCAPE/model/mathematical_model.owl#"

unit_classes = ["SI_BaseUnit", "SI_DerivedUnit"]
pheno_classes = [
    "Accumulation",
    "FlowPattern",
    "MolecularTransportPhenomenon",
    "ChemicalReactionPhenomenon",
]
variable_classes = [
    "Constant",
    "RateVariable",
    "StateVariable",
    "FlowParameter",
    "ReactorParameter",
    "OperatingParameter",
    "PhysicalParameter",
    "ReactionParameter",
    "MolecularTransportParameter",
]
variable_dimensions = ["Species", "Reaction", "Stream", "Solvent"]


def patch_pheno(rdf, patch):
    phenos = []
    for pheno_class in pheno_classes:
        sparql = (
            f"{prefix_rdf}\n"
            f"SELECT ?p\n"
            "WHERE {\n"
            f"    ?p rdf:type <{ns_behavior}{pheno_class}> .\n"
            "}"
        )
        sparql_res = rdf.query(sparql)
        for res in sparql_res:
            phenos.append(str(res[0]).split("#")[1])

    patch_phenos = [pheno_dict["name"] for pheno_dict in patch["Phenomenon"]]

    for pheno_dict in patch["Phenomenon"][::-1]:
        assert (
            pheno_dict["class"] in pheno_classes
        ), f"Unknown phenomenon class {pheno_dict['class']}"
        if pheno_dict["name"] == "Continuous":
            pheno_ns = ns_process
        else:
            pheno_ns = ns_ontomo
        sparql = (
            f"{prefix_rdf}\n"
            f"SELECT ?fp ?mtp\n"
            "WHERE {\n"
            f"    ?p rdf:type <{ns_behavior}{pheno_dict['class']}> .\n"
            f"    optional{{?p <{ns_ontomo}relatesToFlowPattern> ?fp .}}\n"
            "    optional"
            f"{{?p <{ns_ontomo}relatesToMolecularTransportPhenomenon> ?mtp .}}\n"
            f"    BIND(<{pheno_ns}{pheno_dict['name']}> AS ?p)\n"
            "}"
        )
        sparql_res = rdf.query(sparql)
        flow_patterns = []
        molecular_transport_phenos = []
        for res in sparql_res:
            if res[0]:
                flow_pattern = str(res[0]).split("#")[1]
                if flow_pattern not in flow_patterns:
                    flow_patterns.append(flow_pattern)
            if res[1]:
                molecular_transport_pheno = str(res[1]).split("#")[1]
                if molecular_transport_pheno not in molecular_transport_phenos:
                    molecular_transport_phenos.append(molecular_transport_pheno)
        for pheno in flow_patterns:
            assert (
                pheno in phenos or pheno in patch_phenos
            ), f"Flow pattern {pheno} not defined"
        for pheno in molecular_transport_phenos:
            assert (
                pheno in phenos or pheno in patch_phenos
            ), f"Molecular transport phenomenon {pheno} not defined"
        flow_pattern_sparql = "".join(
            [
                f"    ?p <{ns_ontomo}relatesToFlowPattern> <{ns_ontomo}{fp}> .\n"
                for fp in pheno_dict["flow_patterns"]
            ]
        )
        molecular_transport_pheno_sparql = "".join(
            [
                f"    ?p <{ns_ontomo}relatesToMolecularTransportPhenomenon> "
                f"<{ns_ontomo}{mtp}> .\n"
                for mtp in pheno_dict["molecular_transport_phenomena"]
            ]
        )
        sparql = (
            f"{prefix_rdf}\n"
            "INSERT {\n"
            f"    ?p rdf:type <{ns_behavior}{pheno_dict['class']}> .\n"
            f"{flow_pattern_sparql}"
            f"{molecular_transport_pheno_sparql}"
            "}\n"
            "WHERE {\n"
            f"    BIND(<{pheno_ns}{pheno_dict['name']}> AS ?p)\n"
            "}"
        )
        rdf.update(sparql)


def patch_unit(rdf, patch):
    for unit_dict in patch["Unit"]:
        assert (
            unit_dict["class"] in unit_classes
        ), f"Unknown unit class {unit_dict['class']}"
        unit_symbol = unit_dict["symbol"]
        unit_symbol = re.sub("\n", "", unit_symbol)
        unit_symbol = re.sub(r"\> *\<", "><", unit_symbol)
        unit_symbol = re.sub(r" *\< *", "<", unit_symbol)
        unit_symbol = re.sub(r" *\> *", ">", unit_symbol)
        sparql = (
            f"{prefix_rdf}\n"
            f"SELECT ?s\n"
            "WHERE {\n"
            f"    BIND(<{ns_ontomo}{unit_dict['name']}> AS ?u)\n"
            f"    ?u rdf:type <{ns_si_unit}{unit_dict['class']}> .\n"
            f"    ?u <{ns_ontomo}hasSymbol> ?s .\n"
            "}"
        )
        sparql_res = rdf.query(sparql)
        if list(sparql_res):
            sparql_symbol = str(list(sparql_res)[0][0])
            sparql_symbol = re.sub("xmlns=[^>]*", "", sparql_symbol)
            sparql_symbol = re.sub("\n", "", sparql_symbol)
            sparql_symbol = re.sub(r"\> *\<", "><", sparql_symbol)
            sparql_symbol = re.sub(r" *\< *", "<", sparql_symbol)
            sparql_symbol = re.sub(r" *\> *", ">", sparql_symbol)
            assert sparql_symbol == unit_symbol, (
                f"Inconsistent unit symbol for {unit_dict['name']}: "
                f"{unit_dict['symbol']}"
            )
        else:
            sparql = (
                f"{prefix_rdf}\n"
                "INSERT {\n"
                f"    ?u rdf:type <{ns_si_unit}{unit_dict['class']}> .\n"
                f'    ?u <{ns_ontomo}hasSymbol> "{unit_symbol}"^^rdf:XMLLiteral .\n'
                "}\n"
                "WHERE {\n"
                f"    BIND(<{ns_ontomo}{unit_dict['name']}> AS ?u)\n"
                "}"
            )
            rdf.update(sparql)


def patch_variable(rdf, patch):
    units = []
    sparql = (
        f"{prefix_rdf}\n"
        f"SELECT ?u\n"
        "WHERE {\n"
        f"    {{?u rdf:type <{ns_si_unit}SI_BaseUnit>}} UNION "
        f"{{?u rdf:type <{ns_si_unit}SI_DerivedUnit>}} .\n"
        "}"
    )
    sparql_res = rdf.query(sparql)
    for res in sparql_res:
        unit = str(res[0]).split("#")[1]
        units.append(unit)

    for variable_dict in patch["Variable"]:
        assert (
            variable_dict["class"] in variable_classes
        ), f"Unknown variable class {variable_dict['class']}"
        assert (
            variable_dict["unit"] is None or variable_dict["unit"] in units
        ), f"Unknown variable unit {variable_dict['unit']}"
        assert set(variable_dict["dimensions"]).issubset(
            set(variable_dimensions)
        ), f"Unknown variable dimension {variable_dict['dimensions']}"
        if variable_dict["class"] in ["Constant"]:
            variable_ns = ns_mathematical_model
        else:
            variable_ns = ns_ontomo
        sparql = (
            f"{prefix_rdf}\n"
            f"SELECT ?v\n"
            "WHERE {\n"
            f"    BIND(<{ns_ontomo}{variable_dict['name']}> AS ?v)\n"
            f"    ?v rdf:type <{variable_ns}{variable_dict['class']}> .\n"
            "}"
        )
        sparql_res = rdf.query(sparql)
        if sparql_res:
            unit = None
            dimensions = []
            sparql = (
                f"{prefix_rdf}\n"
                f"SELECT ?s ?u ?d\n"
                "WHERE {\n"
                f"    <{ns_ontomo}{variable_dict['name']}> "
                f"<{ns_ontomo}hasSymbol> ?s .\n"
                f"    optional{{<{ns_ontomo}{variable_dict['name']}> "
                f"<{ns_system}hasUnitOfMeasure> ?u .}}\n"
                f"    optional{{<{ns_ontomo}{variable_dict['name']}> "
                f"<{ns_system}hasDimension> ?d .}}\n"
                "}"
            )
            sparql_res = rdf.query(sparql)
            for res in sparql_res:
                symbol = re.sub("xmlns=[^>]*", "", str(res[0]))
                symbol = re.sub("\n", "", symbol)
                symbol = re.sub(r"\> *\<", "><", symbol)
                symbol = re.sub(r" *\< *", "<", symbol)
                symbol = re.sub(r" *\> *", ">", symbol)
                if res[1]:
                    unit = str(res[1]).split("#")[1]
                if res[2]:
                    dimension = str(res[2]).split("#")[1].split("_")[0]
                    dimensions.append(dimension)
            assert (
                unit == variable_dict["unit"]
            ), f"Inconsistent unit for {variable_dict['name']}: {variable_dict['unit']}"
            assert set(dimensions) == set(variable_dict["dimensions"]), (
                f"Inconsistent dimensions for {variable_dict['name']}:"
                f"{variable_dict['dimensions']}"
            )
        else:
            dimension_sparql = "".join(
                [
                    f"    ?v <{ns_system}hasDimension> "
                    f"<{ns_ontomo}{dimension}_Dimension> .\n"
                    for dimension in variable_dict["dimensions"]
                ]
            )
            unit_sparql = (
                f"    ?v <{ns_system}hasUnitOfMeasure> "
                f"<{ns_ontomo}{variable_dict['unit']}> .\n"
                if variable_dict["unit"]
                else ""
            )
            symbol = variable_dict["symbol"]
            symbol = re.sub("\n", "", symbol)
            symbol = re.sub(r"\> *\<", "><", symbol)
            symbol = re.sub(r" *\< *", "<", symbol)
            symbol = re.sub(r" *\> *", ">", symbol)
            try:
                MMLExpression(symbol.replace("\\\"", "\"")).to_numpy()
            except:
                print(f"MathML parsing error for {variable_dict['name']}: {symbol}")
            sparql = (
                f"{prefix_rdf}\n"
                "INSERT {\n"
                f"    ?v rdf:type <{variable_ns}{variable_dict['class']}> .\n"
                f'    ?v <{ns_ontomo}hasSymbol> "{symbol}"^^rdf:XMLLiteral .\n'
                f"{unit_sparql}"
                f"{dimension_sparql}"
                "}\n"
                "WHERE {\n"
                f"    BIND(<{ns_ontomo}{variable_dict['name']}> AS ?v)\n"
                "}"
            )
            rdf.update(sparql)


def patch_law(rdf, patch):
    law_dict = patch["Law"]
    variable_dict = [
        variable_dict
        for variable_dict in patch["Variable"]
        if variable_dict["law"] == law_dict["name"]
    ]
    assert len(variable_dict) == 1, "Json file is only allowed to add one law"
    variable_dict = variable_dict[0]

    phenos = []
    for pheno_class in pheno_classes:
        sparql = (
            f"{prefix_rdf}\n"
            f"SELECT ?p\n"
            "WHERE {\n"
            f"    ?p rdf:type <{ns_behavior}{pheno_class}> .\n"
            "}"
        )
        sparql_res = rdf.query(sparql)
        for res in sparql_res:
            phenos.append(str(res[0]).split("#")[1])
    assert (
        law_dict["phenomenon"] in phenos
    ), f"Unknown law phenomenon: {law_dict['phenomenon']}"

    variables = []
    for variable_class in variable_classes:
        if variable_class in ["ModelVariable", "Constant"]:
            variable_ns = ns_mathematical_model
        else:
            variable_ns = ns_ontomo
        sparql = (
            f"{prefix_rdf}\n"
            f"SELECT ?v\n"
            "WHERE {\n"
            f"    ?v rdf:type <{variable_ns}{variable_class}> .\n"
            "}"
        )
        sparql_res = rdf.query(sparql)
        for res in sparql_res:
            variables.append((str(res[0]), variable_class))
    for variable in law_dict["variables"]:
        assert variable in [
            v[0].split("#")[1] for v in variables
        ], f"Unknown law variable: {variable}"
    variables = [
        variable[0]
        for variable in variables
        if variable[0].split("#")[1]
        in [variable_dict["name"] for variable_dict in patch["Variable"]]
        or variable[1] == "Constant"
    ]

    formula = law_dict["formula"]
    formula = re.sub("\n", "", formula)
    formula = re.sub(r"\> *\<", "><", formula)
    formula = re.sub(r" *\< *", "<", formula)
    formula = re.sub(r" *\> *", ">", formula)
    try:
        MMLExpression(formula.replace("\\\"", "\"")).to_numpy()
    except:
        print(f"MathML parsing error for {law_dict['name']}: {formula}")

    variable_sparql = "".join(
        [
            f"    ?l <{ns_mathematical_model}hasModelVariable> <{variable}> .\n"
            for variable in variables
        ]
    )
    doi_sparql = (
        f"    ?l <{ns_ontomo}hasDOI> \"{law_dict['DOI']}\"^^rdf:string .\n"
        if law_dict["DOI"]
        else ""
    )
    sparql = (
        f"{prefix_rdf}\n"
        "INSERT {\n"
        f"    ?l rdf:type <{ns_process_model}Law> .\n"
        f"{doi_sparql}"
        f'    ?l <{ns_ontomo}hasFormula> "{formula}"^^rdf:XMLLiteral .\n'
        f"    ?l <{ns_process_model}isAssociatedWith> "
        f"<{ns_behavior}{law_dict['phenomenon']}> .\n"
        f"{variable_sparql}"
        f"    <{ns_ontomo}{variable_dict['name']}> <{ns_ontomo}hasLaw> ?l .\n"
        "}\n"
        "WHERE {\n"
        f"    BIND(<{ns_ontomo}{law_dict['name']}> AS ?l)\n"
        "}"
    )
    rdf.update(sparql)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--in_rdf", help="Path of the input RDF file of model ontology")
    parser.add_argument(
        "--out_rdf", help="Path of the output RDF file of model ontology"
    )
    parser.add_argument(
        "--json", help="Path of the JSON file of components to be added"
    )
    args = parser.parse_args()

    # load input model ontology
    rdf = rdflib.Graph()
    rdf.parse(args.in_rdf, format="xml")

    # add json to model ontology
    with open(args.json, "r") as f:
        patch = json.load(f)
        patch_pheno(rdf, patch)
        patch_unit(rdf, patch)
        patch_variable(rdf, patch)
        patch_law(rdf, patch)

    # save output model ontology
    assert args.in_rdf != args.out_rdf, "Overwriting RDF file is not allowed"
    rdf.serialize(args.out_rdf, format="pretty-xml")
