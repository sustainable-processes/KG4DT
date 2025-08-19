import os


class Config:
    # Base directory
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    # GraphDB
    GRAPHDB_HOST = os.getenv("GRAPHDB_HOST", "127.0.0.1")
    GRAPHDB_PORT = os.getenv("GRAPHDB_PORT", "7200")
    GRAPHDB_USER = os.getenv("GRAPHDB_USER", "admin")
    GRAPHDB_PASSWORD = os.getenv("GRAPHDB_PASSWORD", "root")
    GRAPHDB_DB = os.getenv("GRAPHDB_DB", "ontomo")

    # Assets
    ASSETS_ROOT = os.getenv('ASSETS_ROOT', '/static/assets')

    # RDF prefix
    PREFIX_RDF = "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>"
    PREFIX_ONTOMO = ("PREFIX ontomo: <https://raw.githubusercontent.com/"
                     "sustainable-processes/KG4DT/refs/heads/dev-alkyne-hydrogenation/ontology/OntoMo.owl#>")
    PREFIX = "\n".join([PREFIX_RDF, PREFIX_ONTOMO, ""])

    # Phenomenon
    PHENOMENON_CLASSES = [
        "Accumulation",
        "FlowPattern",
        "MassTransportPhenomenon",
        "MassEquilibriumPhenomenon",
        "ReactionPhenomenon",
    ]

    # Model variable
    MODEL_VARIABLE_CLASSES = [
        "Constant",
        "RateVariable",
        "StateVariable",
        "FlowParameter",
        "PhysicsParameter",
        "ReactionParameter",
        "OperationParameter",
        "StructureParameter",
        "MassTransportParameter",
    ]

    # Data source
    DATA_SOURCE_CLASSES = [
        "PhysicsDataSource",
        "MiscibilityDataSource",
    ]

    # Descriptor
    DESCRIPTOR_CLASSES = [
        "TimeDescriptor",
        "SpaceDescriptor",
        "EnergyDescriptor",
        "StructureDescriptor",
        "SubstanceDescriptor",
        "InformationDescriptor",
    ]


class DebugConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_dict = {
    'Debug': DebugConfig,
    'Production': ProductionConfig,
}
