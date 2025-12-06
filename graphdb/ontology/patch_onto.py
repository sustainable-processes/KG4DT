import re
import json
import rdflib
import argparse
from mml_expression import MMLExpression


PREFIX_RDF = "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>"
PREFIX_ONTOMO = (
    "PREFIX ontomo: <https://raw.githubusercontent.com/sustainable-processes/KG4DT/refs"
    "/heads/main/ontology/OntoMo.owl#>"
)
PREFIX_SYSTEM = (
    "PREFIX system: <https://raw.githubusercontent.com/sustainable-processes/KG4DT/refs"
    "/heads/main/ontology/OntoCAPE/upper_level/system.owl#>"
)
PREFIX_SIUNIT = (
    "PREFIX SI_unit: <https://raw.githubusercontent.com/sustainable-processes/KG4DT/"
    "refs/heads/main/ontology/OntoCAPE/supporting_concepts/SI_unit/SI_unit.owl#>"
)
PREFIX_BEHAVIOR = (
    "PREFIX behavior: <https://raw.githubusercontent.com/sustainable-processes/KG4DT/"
    "refs/heads/main/ontology/OntoCAPE/chemical_process_system/CPS_behavior/"
    "behavior.owl#>"
)
PREFIX_PROCESS_MODEL = (
    "PREFIX process_model: <https://raw.githubusercontent.com/sustainable-processes/"
    "KG4DT/refs/heads/main/ontology/OntoCAPE/model/process_model.owl#>"
)
PREFIX_MATHEMATICAL_MODEL = (
    "PREFIX mathematical_model: <https://raw.githubusercontent.com/"
    "sustainable-processes/KG4DT/refs/heads/main/ontology/OntoCAPE/model/"
    "mathematical_model.owl#>"
)
PREFIX = "\n".join([
    PREFIX_RDF, PREFIX_ONTOMO, PREFIX_SYSTEM, PREFIX_SIUNIT, PREFIX_BEHAVIOR, 
    PREFIX_PROCESS_MODEL, PREFIX_MATHEMATICAL_MODEL, ""
])

pheno_classes = [
    "Accumulation", 
    "MolecularTransportPhenomenon", 
    "FlowPattern", 
    "ChemicalReactionPhenomenon"
]
unit_classes = [
    "SI_BaseUnit", 
    "SI_DerivedUnit"
]
var_classes = [
    "Constant", 
    "RateVariable", 
    "StateVariable",
    "FlowParameter", 
    "ReactorParameter", 
    "ReactionParameter", 
    "PhysicalParameter", 
    "OperatingParameter", 
    "MolecularTransportParameter", 
]
dim_classes = [
    "Species", 
    "Reaction", 
    "Stream", 
    "Solvent", 
    "Gas", 
    "Solid"
]
desc_classes = [
    "EnergyContextDescriptor", 
    "InformationContextDescriptor", 
    "SpaceContextDescriptor", 
    "StructureContextDescriptor", 
    "SubstanceContextDescriptor", 
    "TimeContextDescriptor"
]

def patch_pheno(rdf, patch):
    phenos = []
    for pheno_class in pheno_classes:
        sparql = (
            f"{PREFIX}"
            f"SELECT ?p\n"
            "WHERE {\n"
            f"    ?p rdf:type behavior:{pheno_class} .\n"
            "}"
        )
        sparql_res = rdf.query(sparql)
        for res in sparql_res:
            phenos.append(str(res[0]).split("#")[1])

    patch_phenos = [pheno_dict["name"] for pheno_dict in patch["Phenomenon"]]

    for pheno_dict in patch["Phenomenon"][::-1]:
        assert (
            pheno_dict["cls"] in pheno_classes
        ), f"Unknown phenomenon class {pheno_dict['cls']}"
        sparql = (
            f"{PREFIX}\n"
            f"SELECT ?fp ?mtp\n"
            "WHERE {\n"
            f"    ?p rdf:type behavior:{pheno_dict['cls']} .\n"
            f"    optional{{?p ontomo:relatesToFlowPattern ?fp .}}\n"
            f"    optional{{?p ontomo:relatesToMassTransportPhenomenon ?mtp .}}\n"
            f"    BIND(ontomo:{pheno_dict['name']} AS ?p)\n"
            "}"
        )
        sparql_res = rdf.query(sparql)
        fps = []
        mts = []
        for res in sparql_res:
            if res[0]:
                fp = str(res[0]).split("#")[1]
                if fp not in fps:
                    fps.append(fp)
            if res[1]:
                mt = str(res[1]).split("#")[1]
                if mt not in mts:
                    mts.append(mt)
        for fp in fps:
            assert fp in phenos or fp in patch_phenos, f"FlowPattern {fp} not defined"
        for mt in mts:
            assert mt in phenos or mt in patch_phenos, \
                f"MassTransportPhenomenon {mt} not defined"
        fp_sparql = "\n".join(
            [
                f"    ?p ontomo:relatesToFlowPattern ontomo:{fp} ."
                for fp in pheno_dict["fps"]
            ]
        )
        mt_sparql = "\n".join(
            [
                f"    ?p ontomo:relatesToMassTransportPhenomenon ontomo:{mt} ."
                for mt in pheno_dict["mts"]
            ]
        )
        sparql = (
            f"{PREFIX}\n"
            "INSERT {\n"
            f"    ?p rdf:type behavior:{pheno_dict['cls']} .\n"
            f"{fp_sparql}\n"
            f"{mt_sparql}\n"
            "}\n"
            "WHERE {\n"
            f"    BIND(ontomo:{pheno_dict['name']} AS ?p)\n"
            "}"
        )
        rdf.update(sparql)


def patch_unit(rdf, patch):
    for unit_dict in patch["Unit"]:
        assert unit_dict["cls"] in unit_classes, f"Unknown unit class {unit_dict['cls']}"
        unit_sym = unit_dict["sym"]
        unit_sym = re.sub("\n", "", unit_sym)
        unit_sym = re.sub(r" *\< *", "<", unit_sym)
        unit_sym = re.sub(r" *\> *", ">", unit_sym)
        sparql = (
            f"{PREFIX}\n"
            f"SELECT ?s\n"
            "WHERE {\n"
            f"    BIND(ontomo:{unit_dict['name']} AS ?u)\n"
            f"    ?u rdf:type SI_unit:{unit_dict['cls']} .\n"
            f"    ?u ontomo:hasSymbol ?s .\n"
            "}"
        )
        sparql_res = rdf.query(sparql)
        if list(sparql_res):
            sparql_sym = str(list(sparql_res)[0][0])
            sparql_sym = re.sub("xmlns=[^>]*", "", sparql_sym)
            sparql_sym = re.sub("\n", "", sparql_sym)
            sparql_sym = re.sub(r" *\< *", "<", sparql_sym)
            sparql_sym = re.sub(r" *\> *", ">", sparql_sym)
            assert sparql_sym == sparql_sym, (
                f"Inconsistent unit symbol for {unit_dict['name']}: {unit_dict['sym']}"
            )
        else:
            sparql = (
                f"{PREFIX}\n"
                "INSERT {\n"
                f"    ?u rdf:type ontomo:{unit_dict['name']} .\n"
                f'    ?u ontomo:hasSymbol "{unit_sym}"^^rdf:XMLLiteral .\n'
                "}\n"
                "WHERE {\n"
                f"    BIND(ontomo:{unit_dict['name']} AS ?u)\n"
                "}"
            )
            rdf.update(sparql)


def patch_var(rdf, patch):
    units = []
    sparql = (
        f"{PREFIX}\n"
        f"SELECT ?u\n"
        "WHERE {\n"
        "    "
        f"{' UNION '.join([f'{{?u rdf:type SI_unit:{c} .}}' for c in unit_classes])}\n"
        "}"
    )
    sparql_res = rdf.query(sparql)
    for res in sparql_res:
        unit = str(res[0]).split("#")[1]
        units.append(unit)

    for var_dict in patch["Variable"]:
        assert (var_dict["cls"] in var_classes
        ), f"Unknown variable class {var_dict['cls']}"
        assert (
            var_dict["unit"] is None or var_dict["unit"] in units
        ), f"Unknown variable unit {var_dict['unit']}"
        assert set(var_dict["dims"]).issubset(
            set(dim_classes)), f"Unknown variable dimension {var_dict['dims']}"
        sparql = (
            f"{PREFIX}\n"
            f"SELECT ?v\n"
            "WHERE {\n"
            f"    BIND(ontomo:{var_dict['name']} AS ?v)\n"
            f"    ?v rdf:type ontomo:{var_dict['cls']} .\n"
            "}"
        )
        sparql_res = rdf.query(sparql)
        if sparql_res:
            unit = None
            dims = []
            sparql = (
                f"{PREFIX}\n"
                f"SELECT ?s ?u ?d\n"
                "WHERE {\n"
                f"    ontomo:{var_dict['name']} ontomo:hasSymbol ?s .\n"
                f"    optional{{ontomo:{var_dict['name']} system:hasUnitOfMeasure ?u .}}\n"
                f"    optional{{ontomo:{var_dict['name']} system:hasDimension ?d .}}\n"
                "}"
            )
            sparql_res = rdf.query(sparql)
            for res in sparql_res:
                sym = re.sub("xmlns=[^>]*", "", str(res[0]))
                sym = re.sub("\n", "", sym)
                sym = re.sub(r" *\< *", "<", sym)
                sym = re.sub(r" *\> *", ">", sym)
                if res[1]:
                    unit = str(res[1]).split("#")[1]
                if res[2]:
                    dim = str(res[2]).split("#")[1].split("_")[0]
                    dims.append(dim)
            assert unit == var_dict["unit"], \
                f"Inconsistent unit for {var_dict['name']}: {var_dict['unit']}"
            assert set(dims) == set(var_dict["dims"]), \
                f"Inconsistent dimensions for {var_dict['name']}: {var_dict['dims']}"
        else:
            dim_sparql = "\n".join([
                f"    ?v system:hasDimension ontomo:{dim}_Dimension ."
                for dim in var_dict["dims"]
            ])
            unit_sparql = (
                f"    ?v system:hasUnitOfMeasure SI_unit:{var_dict['unit']} .\n" 
                if var_dict["unit"] else ""
            )
            sym = var_dict["sym"]
            sym = re.sub("\n", "", sym)
            sym = re.sub(r" *\< *", "<", sym)
            sym = re.sub(r" *\> *", ">", sym)
            try:
                MMLExpression(sym.replace("\\\"", "\"")).to_numpy()
            except:
                print(f"MathML parsing error for {var_dict['name']}: {sym}")
            sparql = (
                f"{PREFIX}\n"
                "INSERT {\n"
                f"    ?v rdf:type ontomo:{var_dict['cls']} .\n"
                f'    ?v ontomo:hasSymbol "{sym}"^^rdf:XMLLiteral .\n'
                f"{unit_sparql}"
                f"{dim_sparql}"
                "}\n"
                "WHERE {\n"
                f"    BIND(ontomo:{var_dict['name']} AS ?v)\n"
                "}"
            )
            rdf.update(sparql)


def patch_desc(rdf, patch):
    if "ContextDescriptor" not in patch:
        return
    units = []
    sparql = (
        f"{PREFIX}\n"
        f"SELECT ?u\n"
        "WHERE {\n"
        "    "
        f"{' UNION '.join([f'{{?u rdf:type SI_unit:{c} .}}' for c in unit_classes])}\n"
        "}"
    )
    sparql_res = rdf.query(sparql)
    for res in sparql_res:
        unit = str(res[0]).split("#")[1]
        units.append(unit)

    for desc_dict in patch["ContextDescriptor"]:
        assert (desc_dict["cls"] in desc_classes
        ), f"Unknown context descriptor class {desc_dict['cls']}"
        assert (
            desc_dict["unit"] is None or desc_dict["unit"] in units
        ), f"Unknown variable unit {desc_dict['unit']}"
        sparql = (
            f"{PREFIX}\n"
            f"SELECT ?v\n"
            "WHERE {\n"
            f"    BIND(ontomo:{desc_dict['name']} AS ?v)\n"
            f"    ?v rdf:type ontomo:{desc_dict['cls']} .\n"
            "}"
        )
        sparql_res = rdf.query(sparql)
        if sparql_res:
            unit = None
            dims = []
            sparql = (
                f"{PREFIX}\n"
                f"SELECT ?s ?u ?d\n"
                "WHERE {\n"
                f"    ontomo:{desc_dict['name']} ontomo:hasSymbol ?s .\n"
                f"    optional{{ontomo:{desc_dict['name']} system:hasUnitOfMeasure ?u .}}\n"
                "}"
            )
            sparql_res = rdf.query(sparql)
            for res in sparql_res:
                sym = re.sub("xmlns=[^>]*", "", str(res[0]))
                sym = re.sub("\n", "", sym)
                sym = re.sub(r" *\< *", "<", sym)
                sym = re.sub(r" *\> *", ">", sym)
                if res[1]:
                    unit = str(res[1]).split("#")[1]
                if res[2]:
                    dim = str(res[2]).split("#")[1].split("_")[0]
                    dims.append(dim)
            assert unit == desc_dict["unit"], \
                f"Inconsistent unit for {desc_dict['name']}: {desc_dict['unit']}"
        else:
            unit_sparql = (
                f"    ?v sysmte:hasUnit SI_unit:{desc_dict['unit']} .\n" 
                if desc_dict["unit"] else ""
            )
            sym = desc_dict["sym"]
            sym = re.sub("\n", "", sym)
            sym = re.sub(r" *\< *", "<", sym)
            sym = re.sub(r" *\> *", ">", sym)
            try:
                MMLExpression(sym.replace("\\\"", "\"")).to_numpy()
            except:
                print(f"MathML parsing error for {desc_dict['name']}: {sym}")
            sparql = (
                f"{PREFIX}\n"
                "INSERT {\n"
                f"    ?v rdf:type ontomo:{desc_dict['cls']} .\n"
                f'    ?v ontomo:hasSymbol "{sym}"^^rdf:XMLLiteral .\n'
                f"{unit_sparql}"
                "}\n"
                "WHERE {\n"
                f"    BIND(ontomo:{desc_dict['name']} AS ?v)\n"
                "}"
            )
            rdf.update(sparql)


def patch_rule(rdf, patch):
    if "Rule" not in patch:
        return
    rule_dict = patch["Rule"]
    assert isinstance(rule_dict, dict), "Json file is only allowed to add one law"

    phenos = []
    for pheno_class in pheno_classes:
        sparql = (
            f"{PREFIX}\n"
            f"SELECT ?p\n"
            "WHERE {\n"
            f"    ?p rdf:type behavior:{pheno_class} .\n"
            "}"
        )
        sparql_res = rdf.query(sparql)
        for res in sparql_res:
            phenos.append(str(res[0]).split("#")[1])
    assert set(rule_dict["phenos"]).issubset(set(phenos)), \
        f"Unknown rule phenomenons included: {rule_dict['pheno']}"

    descs = []
    for desc_class in desc_classes:
        sparql = (
            f"{PREFIX}\n"
            f"SELECT ?d\n"
            "WHERE {\n"
            f"    ?d rdf:type ontomo:{desc_class} .\n"
            "}"
        )
        sparql_res = rdf.query(sparql)
        for res in sparql_res:
            descs.append(str(res[0]).split("#")[1])
    for desc in rule_dict["descs"]:
        assert desc in descs, f"Unknown context descriptor: {desc}"

    desc_sparql = "\n".join([
        f"    ?r ontomo:hasContextDescriptor ontomo:{desc} ." for desc in rule_dict["descs"]
    ])
    pheno_sparql = "\n".join([
        f"    ?r process_model:isAssociatedWith ontomo:{pheno} ." for pheno in rule_dict["phenos"]
    ])
    doi_sparql = (
        f"    ?r ontomo:hasDOI \"{rule_dict['doi']}\"^^rdf:string .\n"
        if rule_dict["doi"] else ""
    )
    sparql = (
        f"{PREFIX}\n"
        "INSERT {\n"
        f"    ?r rdf:type ontomo:Rule .\n"
        f"{doi_sparql}\n"
        f"{pheno_sparql}\n"
        f"{desc_sparql}\n"
        f'    ?r ontomo:hasSPARQL """{"".join(rule_dict["sparql"])}"""^^rdf:string .\n'
        "}\n"
        "WHERE {\n"
        f"    BIND(ontomo:{rule_dict['name']} AS ?r)\n"
        "}"
    )
    rdf.update(sparql)


def patch_law(rdf, patch):
    law_dict = patch["Law"]
    assert isinstance(law_dict, dict), "Json file is only allowed to add one law"
    var_dict = [var_dict for var_dict in patch["Variable"]
                if var_dict["law"] == law_dict["name"]]
    assert len(var_dict) == 1, "Json file is only allowed to add one law"
    var_dict = var_dict[0]

    phenos = []
    for pheno_class in pheno_classes:
        sparql = (
            f"{PREFIX}\n"
            f"SELECT ?p\n"
            "WHERE {\n"
            f"    ?p rdf:type behavior:{pheno_class} .\n"
            "}"
        )
        sparql_res = rdf.query(sparql)
        for res in sparql_res:
            phenos.append(str(res[0]).split("#")[1])
    assert law_dict["pheno"] in phenos, f"Unknown law phenomenon: {law_dict['pheno']}"

    vars = []
    for var_class in var_classes:
        sparql = (
            f"{PREFIX}\n"
            f"SELECT ?v\n"
            "WHERE {\n"
            f"    ?v rdf:type ontomo:{var_class} .\n"
            "}"
        )
        sparql_res = rdf.query(sparql)
        for res in sparql_res:
            vars.append((str(res[0]), var_class))
    for var in law_dict["vars"]:
        assert var in [v[0].split("#")[1] for v in vars], f"Unknown law variable: {var}"
    vars = [
        var[0].split("#")[1] for var in vars if (var[0].split("#")[1] in 
        [var_dict["name"] for var_dict in patch["Variable"]] or 
        var[1] == "Constant") and var[0].split("#")[1] in patch["Law"]["vars"]
    ]

    fml = law_dict["fml"]
    fml = re.sub("\n", "", fml)
    fml = re.sub(r" *\< *", "<", fml)
    fml = re.sub(r" *\> *", ">", fml)
    try:
        MMLExpression(fml.replace("\\\"", "\"")).to_numpy()
    except:
        print(f"MathML parsing error for {law_dict['name']}: {fml}")

    var_sparql = "\n".join([
        f"    ?l mathematical_model:hasModelVariable ontomo:{var} ." for var in vars
    ])
    doi_sparql = (
        f"    ?l ontomo:hasDOI \"{law_dict['doi']}\"^^rdf:string .\n"
        if law_dict["doi"] else ""
    )
    rule_sparql = (
        f"    ?l ontomo:hasRule ontomo:{patch['Rule']['name']} .\n" 
        if "Rule" in patch else ""
    )
    sparql = (
        f"{PREFIX}\n"
        "INSERT {\n"
        f"    ?l rdf:type process_model:Law .\n"
        f"{doi_sparql}"
        f'    ?l ontomo:hasFormula "{fml}"^^rdf:XMLLiteral .\n'
        f"    ?l process_model:isAssociatedWith ontomo:{law_dict['pheno']} .\n"
        f"{var_sparql}\n"
        f"{rule_sparql}\n"
        f"    ontomo:{var_dict['name']} ontomo:hasLaw ?l .\n"
        "}\n"
        "WHERE {\n"
        f"    BIND(process_model:{law_dict['name']} AS ?l)\n"
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
        patch_var(rdf, patch)
        patch_desc(rdf, patch)
        patch_rule(rdf, patch)
        patch_law(rdf, patch)

    # save output model ontology
    assert args.in_rdf != args.out_rdf, "Overwriting RDF file is not allowed"
    rdf_str = rdf.serialize(None, format="pretty-xml")
    with open(args.out_rdf, "w") as f:
        f.write(rdf_str)
