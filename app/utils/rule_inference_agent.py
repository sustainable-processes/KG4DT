class RuleInferenceAgent():
    def __init__(self, entity, graphdb_hander):
        self.entity = entity
        self.graphdb_handler = graphdb_hander
    def infer(self, data):
        descriptors = data["key"]
        inference_result = []
        for sample_data in data["value"]:
            sample_inference_result = []
            for rule, rule_dict in self.graphdb_handler.query_rule().items():
                if set(descriptors).issuperset(set(rule_dict["context_descriptors"])):
                    sparql = rule_dict["sparql"]
                    for descriptor, value in zip(descriptors, sample_data):
                        sparql = sparql.replace("{" + descriptor + "}", value)
                    try:
                        if self.graphdb_handler.cur.execute(sparql).split("\r\n")[1] == "true":
                            sample_inference_result.append(rule)
                    except:
                        pass
            inference_result.append(sample_inference_result)
        return inference_result
