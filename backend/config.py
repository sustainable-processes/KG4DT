import os


class Config:
    basedir = os.path.abspath(os.path.dirname(__file__))
    GRAPHDB_HOST =      os.getenv("GRAPHDB_HOST", "127.0.0.1")
    GRAPHDB_PORT =      os.getenv("GRAPHDB_PORT", "7200")
    GRAPHDB_USER =      os.getenv("GRAPHDB_USER", "admin")
    GRAPHDB_PASSWORD =  os.getenv("GRAPHDB_PASSWORD", "root")
    GRAPHDB_DB =        os.getenv("GRAPHDB_DB", "ontomo")
    ASSETS_ROOT =       os.getenv('ASSETS_ROOT', '/static/assets')

    PREFIX_RDF =                "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>"
    PREFIX_ONTOMO =             "PREFIX ontomo: <file:/ontology/OntoMo.owl#>"
    PREFIX_SYSTEM =             "PREFIX system: <file:/ontology/OntoCAPE/upper_level/system.owl#>"
    PREFIX_SIUNIT =             "PREFIX SI_unit: <file:/ontology/OntoCAPE/supporting_concepts/SI_unit/SI_unit.owl#>"
    PREFIX_BEHAVIOR =           "PREFIX behavior: <file:/ontology/OntoCAPE/chemical_process_system/CPS_behavior/behavior.owl#>"
    PREFIX_PROCESS_MODEL =      "PREFIX process_model: <file:/ontology/OntoCAPE/model/process_model.owl#>"
    PREFIX_MATHEMATICAL_MODEL = "PREFIX mathematical_model: <file:/ontology/OntoCAPE/model/mathematical_model.owl#>"
    PREFIX = "\n".join([PREFIX_RDF, PREFIX_ONTOMO, PREFIX_SYSTEM, PREFIX_SIUNIT, PREFIX_BEHAVIOR, PREFIX_PROCESS_MODEL, PREFIX_MATHEMATICAL_MODEL, ""])

    PHENOMENON_CLASSES = [
        "Accumulation", 
        "MolecularTransportPhenomenon",
        "FlowPattern", 
        "ChemicalReactionPhenomenon", 
    ]
    MODEL_VARIABLE_CLASSES = [
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
    DATA_SOURCE_CLASSES = [
        "PhysicalPropertyDataSource", 
        "SolventMiscibilityDataSource", 
    ]
    CONTEXT_DESCRIPTOR_CLASSES = [
        "EnergyContextDescriptor", 
        "InformationContextDescriptor",
        "SpaceContextDescriptor",
        "StructureContextDescriptor",
        "SubstanceContextDescriptor",
        "TimeContextDescriptor",
    ]
    NS_DICT = {
        # class
        "FlowParameter":                            "ontomo",
        "ReactorParameter":                         "ontomo",
        "PhysicalParameter":                        "ontomo",
        "ReactionParameter":                        "ontomo",
        "OperatingParameter":                       "ontomo",
        "MolecularTransportParameter":              "ontomo",
        "Definition":                               "ontomo",
        "RateVariable":                             "ontomo",
        "StateVariable":                            "ontomo",
        "ModelDimension":                           "ontomo",
        "Law":                                      "process_model",
        "Constant":                                 "mathematical_model", 
        "FlowPattern":                              "behavior", 
        "Accumulation":                             "behavior",
        "ChemicalReactionPhenomenon":               "behavior", 
        "MolecularTransportPhenomenon":             "behavior",
        "PhysicalEquilibriumPhenomenon":            "behavior",
        "SI_BaseUnit":                              "SI_unit",
        "SI_DerivedUnit":                           "SI_unit",
        "PhysicalPropertyDataSource":               "ontomo",
        "SolventMiscibilityDataSource":             "ontomo",
        "EnergyContextDescriptor":                  "ontomo",
        "InformationContextDescriptor":             "ontomo",
        "SpaceContextDescriptor":                   "ontomo",
        "StructureContextDescriptor":               "ontomo",
        "SubstanceContextDescriptor":               "ontomo",
        "TimeContextDescriptor":                    "ontomo",
        "Rule":                                     "ontomo",
        # object property
        "hasLaw":                                   "ontomo",
        "hasRule":                                  "ontomo",
        "hasDefinition":                            "ontomo",
        "hasOptionalModelVariable":                 "ontomo",
        "hasDifferentialModelVariable":             "ontomo",
        "hasDifferentialUpperLimit":                "ontomo",
        "hasDifferentialInitialValue":              "ontomo",
        "hasDimension":                             "system",
        "isAssociatedWith":                         "process_model",
        "hasModelVariable":                         "mathematical_model",
        "hasStandardUnitOfMeasure":                 "ontomo",
        "hasUnitOfMeasure":                         "system",
        "hasContextDescriptor":                     "ontomo",
        "relatesToFlowPattern":                     "ontomo",
        "relatesToMolecularTransportPhenomenon":    "ontomo",
        # data property
        "hasDOI":                                   "ontomo",
        "hasURL":                                   "ontomo",
        "hasSymbol":                                "ontomo",
        "hasValue":                                 "ontomo",
        "hasSPARQL":                                "ontomo",
        "hasFormula":                               "ontomo",
        "hasRatioToStandardUnitOfMeasure":          "ontomo",
        "hasFormulaIntegratedWithAccumulation":     "ontomo",
    }


class DebugConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_dict = {
    'Debug'     : DebugConfig, 
    'Production': ProductionConfig, 
}
