import re
import json
import rdflib
import argparse
from backend.app.utils.mml_expression import MMLExpression
from backend.app.config import Config
# import rdflib.parser.Parser

prefix_rdf = "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>"
ontomo = (
    "https://raw.githubusercontent.com/sustainable-processes/KG4DT/refs/heads/"
    "dev-alkyne-hydrogenation/ontology/OntoMo.owl#"
)

pheno_classes = Config.PHENOMENON_CLASSES
var_classes = Config.MODEL_VARIABLE_CLASSES
dim_classes = ["Species", "Reaction", "Stream", "Solvent", "Time", "Gas", "Solid"]
unit_classes = ["Unit"]

def patch_pheno(rdf, patch):
    phenos = []
    for pheno_class in pheno_classes:
        sparql = (
            f"{prefix_rdf}"
            f"SELECT ?p\n"
            "WHERE {\n"
            f"    ?p rdf:type <{ontomo}{pheno_class}> .\n"
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
        sparql = (
            f"{prefix_rdf}\n"
            f"SELECT ?fp ?mtp\n"
            "WHERE {\n"
            f"    ?p rdf:type <{ontomo}{pheno_dict['class']}> .\n"
            f"    optional{{?p <{ontomo}relatesToFlowPattern> ?fp .}}\n"
            f"    optional{{?p <{ontomo}relatesToMassTransportPhenomenon> ?mtp .}}\n"
            f"    BIND(<{ontomo}{pheno_dict['name']}> AS ?p)\n"
            "}"
        )
        sparql_res = rdf.query(sparql)
        flow_pats = []
        mt_phenos = []
        for res in sparql_res:
            if res[0]:
                flow_pat = str(res[0]).split("#")[1]
                if flow_pat not in flow_pats:
                    flow_pats.append(flow_pat)
            if res[1]:
                mt_pheno = str(res[1]).split("#")[1]
                if mt_pheno not in mt_phenos:
                    mt_phenos.append(mt_pheno)
        for flow_pat in flow_pats:
            assert (
                flow_pat in phenos or flow_pat in patch_phenos
            ), f"FlowPattern {flow_pat} not defined"
        for mt_pheno in mt_phenos:
            assert (
                mt_pheno in phenos or mt_pheno in patch_phenos
            ), f"MassTransportPhenomenon {mt_pheno} not defined"
        flow_pat_sparql = "\n".join(
            [
                f"    ?p <{ontomo}relatesToFlowPattern> <{ontomo}{flow_pat}> ."
                for flow_pat in pheno_dict["flow_pats"]
            ]
        )
        mt_pheno_sparql = "\n".join(
            [
                f"    ?p <{ontomo}relatesToMassTransportPhenomenon> "
                f"<{ontomo}{mt_pheno}> ."
                for mt_pheno in pheno_dict["mt_phenos"]
            ]
        )
        sparql = (
            f"{prefix_rdf}\n"
            "INSERT {\n"
            f"    ?p rdf:type <{ontomo}{pheno_dict['class']}> .\n"
            f"{flow_pat_sparql}\n"
            f"{mt_pheno_sparql}\n"
            "}\n"
            "WHERE {\n"
            f"    BIND(<{ontomo}{pheno_dict['name']}> AS ?p)\n"
            "}"
        )
        rdf.update(sparql)


def patch_unit(rdf, patch):
    for unit_dict in patch["Unit"]:
        assert (
            unit_dict["class"] in unit_classes
        ), f"Unknown unit class {unit_dict['class']}"
        unit_sym = unit_dict["sym"]
        unit_sym = re.sub("\n", "", unit_sym)
        unit_sym = re.sub(r" *\< *", "<", unit_sym)
        unit_sym = re.sub(r" *\> *", ">", unit_sym)
        sparql = (
            f"{prefix_rdf}\n"
            f"SELECT ?s\n"
            "WHERE {\n"
            f"    BIND(<{ontomo}{unit_dict['name']}> AS ?u)\n"
            f"    ?u rdf:type <{ontomo}Unit> .\n"
            f"    ?u <{ontomo}hasSymbol> ?s .\n"
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
                f"{prefix_rdf}\n"
                "INSERT {\n"
                f"    ?u rdf:type <{ontomo}Unit> .\n"
                f'    ?u <{ontomo}hasSymbol> "{unit_sym}"^^rdf:XMLLiteral .\n'
                "}\n"
                "WHERE {\n"
                f"    BIND(<{ontomo}{unit_dict['name']}> AS ?u)\n"
                "}"
            )
            rdf.update(sparql)


def patch_var(rdf, patch):
    units = []
    sparql = (
        f"{prefix_rdf}\n"
        f"SELECT ?u\n"
        "WHERE {\n"
        f"    ?u rdf:type <{ontomo}Unit> .\n"
        "}"
    )
    sparql_res = rdf.query(sparql)
    for res in sparql_res:
        unit = str(res[0]).split("#")[1]
        units.append(unit)

    for var_dict in patch["Variable"]:
        assert (var_dict["class"] in var_classes
        ), f"Unknown variable class {var_dict['class']}"
        assert (
            var_dict["unit"] is None or var_dict["unit"] in units
        ), f"Unknown variable unit {var_dict['unit']}"
        assert set(var_dict["dims"]).issubset(
            set(dim_classes)), f"Unknown variable dimension {var_dict['dims']}"
        sparql = (
            f"{prefix_rdf}\n"
            f"SELECT ?v\n"
            "WHERE {\n"
            f"    BIND(<{ontomo}{var_dict['name']}> AS ?v)\n"
            f"    ?v rdf:type <{ontomo}Unit> .\n"
            "}"
        )
        sparql_res = rdf.query(sparql)
        if sparql_res:
            unit = None
            dims = []
            sparql = (
                f"{prefix_rdf}\n"
                f"SELECT ?s ?u ?d\n"
                "WHERE {\n"
                f"    <{ontomo}{var_dict['name']}> <{ontomo}hasSymbol> ?s .\n"
                f"    optional{{<{ontomo}{var_dict['name']}> "
                f"<{var_dict}hasUnit> ?u .}}\n"
                f"    optional{{<{ontomo}{var_dict['name']}> "
                f"<{var_dict}hasDimension> ?d .}}\n"
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
                f"    ?v <{ontomo}hasDimension> <{ontomo}{dim}_Dimension> ."
                for dim in var_dict["dims"]
            ])
            unit_sparql = (
                f"    ?v <{ontomo}hasUnit> <{ontomo}{var_dict['unit']}> .\n" 
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
                f"{prefix_rdf}\n"
                "INSERT {\n"
                f"    ?v rdf:type <{ontomo}{var_dict['class']}> .\n"
                f'    ?v <{ontomo}hasSymbol> "{sym}"^^rdf:XMLLiteral .\n'
                f"{unit_sparql}"
                f"{dim_sparql}"
                "}\n"
                "WHERE {\n"
                f"    BIND(<{ontomo}{var_dict['name']}> AS ?v)\n"
                "}"
            )
            rdf.update(sparql)


def patch_law(rdf, patch):
    law_dict = patch["Law"]
    var_dict = [var_dict for var_dict in patch["Variable"]
                if var_dict["law"] == law_dict["name"]]
    assert len(var_dict) == 1, "Json file is only allowed to add one law"
    var_dict = var_dict[0]

    phenos = []
    for pheno_class in pheno_classes:
        sparql = (
            f"{prefix_rdf}\n"
            f"SELECT ?p\n"
            "WHERE {\n"
            f"    ?p rdf:type <{ontomo}{pheno_class}> .\n"
            "}"
        )
        sparql_res = rdf.query(sparql)
        for res in sparql_res:
            phenos.append(str(res[0]).split("#")[1])
    assert law_dict["pheno"] in phenos, f"Unknown law phenomenon: {law_dict['pheno']}"

    vars = []
    for var_class in var_classes:
        sparql = (
            f"{prefix_rdf}\n"
            f"SELECT ?v\n"
            "WHERE {\n"
            f"    ?v rdf:type <{ontomo}{var_class}> .\n"
            "}"
        )
        sparql_res = rdf.query(sparql)
        for res in sparql_res:
            vars.append((str(res[0]), var_class))
    for var in law_dict["vars"]:
        assert var in [v[0].split("#")[1] for v in vars], f"Unknown law variable: {var}"
    vars = [
        var[0] for var in vars if (var[0].split("#")[1] in [var_dict["name"] 
        for var_dict in patch["Variable"]] or var[1] == "Constant") and 
        var[0].split("#")[1] in patch["Law"]["vars"]
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
        f"    ?l <{ontomo}hasModelVariable> <{var}> ." for var in vars
    ])
    doi_sparql = (
        f"    ?l <{ontomo}hasDOI> \"{law_dict['doi']}\"^^rdf:string .\n"
        if law_dict["doi"] else ""
    )
    sparql = (
        f"{prefix_rdf}\n"
        "INSERT {\n"
        f"    ?l rdf:type <{ontomo}Law> .\n"
        f"{doi_sparql}"
        f'    ?l <{ontomo}hasFormula> "{fml}"^^rdf:XMLLiteral .\n'
        f"    ?l <{ontomo}isAssociatedWith> <{ontomo}{law_dict['pheno']}> .\n"
        f"{var_sparql}"
        f"    <{ontomo}{var_dict['name']}> <{ontomo}hasLaw> ?l .\n"
        "}\n"
        "WHERE {\n"
        f"    BIND(<{ontomo}{law_dict['name']}> AS ?l)\n"
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
        patch_law(rdf, patch)

    # save output model ontology
    assert args.in_rdf != args.out_rdf, "Overwriting RDF file is not allowed"
    rdf_str = rdf.serialize(None, format="pretty-xml")
    rdf_str = re.sub(r"\<OntoMo:", "<", rdf_str)
    rdf_str = re.sub(r"\</OntoMo:", "</", rdf_str)
    rdf_str = re.sub(r"\<math[^\>]*\>", "<math>", rdf_str)
    with open(args.out_rdf, "w") as f:
        f.write(rdf_str)
