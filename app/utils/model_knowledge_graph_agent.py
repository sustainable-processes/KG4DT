class ModelKnowledgeGraphAgent:
    """Agent for generating knowledge graph data for display and interaction.
    """

    def __init__(self, entity):
        """_summary_

        Args:
            entity (dict): OntoMo entity derived from GraphdbHandler.
        """
        self.entity = entity

    def law2label(self, law):
        if "by" in law:
            return law.split("_with_")[0].replace("_", " ") + "\n" + law.split("_with_")[1].split("_by_")[0].replace("_", " ") + "\nby " + law.split("_by_")[1].replace("_", " ")
        else:
            return law.split("_with_")[0].replace("_", " ") + "\n" + law.split("_with_")[1].split("_by_")[0].replace("_", " ")
        # if "by" in law:
        #     return law.split("_with_")[0].replace("_", " ") + " by " + law.split("_by_")[1].replace("_", " ") + "\n(" + law.split("_with_")[1].split("_by_")[0].replace("_", " ") + ")"
        # else:
        #     return law.split("_with_")[0].replace("_", " ") + "\n(" + law.split("_with_")[1].replace("_", " ") + ")"

    def to_knowledge_graph_data(self):
        nodes = []
        edges = []
        node2id = {}
        node_id = 0
        edge_id = 0
        for model_variable in self.entity["model_variable"]:
            nodes.append({
                "id": node_id,
                "label": model_variable.replace("_", ""),
                "group": 0,
            })
            node2id[model_variable] = node_id
            node_id += 1
        for law in self.entity["law"]:
            nodes.append({
                "id": node_id,
                "label": self.law2label(law),
                "group": 1,
            })
            node2id[law] = node_id
            node_id += 1
        for definition in self.entity["definition"]:
            nodes.append({
                "id": node_id,
                "label": definition.replace("_", ""),
                "group": 1,
            })
            node2id[definition] = node_id
            node_id += 1
        # for phenomenon in self.entity["phenomenon"]:
        #     nodes.append({
        #         "id": node_id,
        #         "label": phenomenon.replace("_", ""),
        #         "group": 2,
        #     })
        #     node2id[phenomenon.replace("_", "")] = node_id
        #     node_id += 1
        
        for model_variable in self.entity["model_variable"]:
            for law in self.entity["model_variable"][model_variable]["laws"]:
                edges.append({
                    "id": edge_id,
                    "from": node2id[model_variable],
                    "to": node2id[law],
                    "label": "hasLaw",
                    "arrows": "to",
                    "color": {"inherit": "from"},
                })
                edge_id += 1
            if self.entity["model_variable"][model_variable]["definition"]:
                definition = self.entity["model_variable"][model_variable]["definition"]
                edges.append({
                    "id": edge_id,
                    "from": node2id[model_variable],
                    "to": node2id[definition],
                    "label": "hasDefinition",
                    "arrows": "to",
                    "color": {"inherit": "from"},
                })
                edge_id += 1
        for law in self.entity["law"]:
            # if self.entity["law"][law]["phenomenon"]:
            #     edges.append({
            #         "from": node2id[law.replace("_with_", "\n(").replace("_", "") + ")"],
            #         "to": node2id[self.entity["law"][law]["phenomenon"].replace("_", "")],
            #         "label": "hasPhenomenon",
            #         "arrows": "to",
            #     })
            if self.entity["law"][law]["phenomenon"] == "Instantaneous": continue
            for model_variable in self.entity["law"][law]["model_variables"]:
                edges.append({
                    "id": edge_id,
                    "from": node2id[law],
                    "to": node2id[model_variable],
                    "label": "hasModelVariable",
                    "arrows": "to",
                    "color": {"inherit": "from"},
                })
                edge_id += 1
            for model_variable in self.entity["law"][law]["optional_model_variables"]:
                edges.append({
                    "id": edge_id,
                    "from": node2id[law],
                    "to": node2id[model_variable],
                    "dashes": True,
                    "label": "hasOptionalModelVariable",
                    "arrows": "to",
                    "color": {"inherit": "from"},
                })
                edge_id += 1
            if self.entity["law"][law]["differential_model_variable"]:
                edges.append({
                    "id": edge_id,
                    "from": node2id[law],
                    "to": node2id[self.entity["law"][law]["differential_model_variable"]],
                    "dashes": True,
                    "label": "hasDifferentialModelVariable",
                    "arrows": "to",
                    "color": {"inherit": "from"},
                })
                edge_id += 1
        for definition in self.entity["definition"]:
            for model_variable in self.entity["definition"][definition]["model_variables"]:
                edges.append({
                    "id": edge_id,
                    "from": node2id[definition],
                    "to": node2id[model_variable],
                    "label": "hasModelVariable",
                    "arrows": "to",
                    "color": {"inherit": "from"},
                })
                edge_id += 1

        data = {
            "node": nodes,
            "edge": edges,
        }
        return data