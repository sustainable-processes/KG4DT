import re
from openai import OpenAI


class ModelChatGPTAgent:
    """Model chatgpt agent for language querying using OpenAI API with preloaded knowledge graph."""

    def __init__(self, entity, model_chatgpt_request):
        self.entity = entity
        self.model_chatgpt_request = model_chatgpt_request

    def context(self):
        phenomenon_context = []
        formula_context = []

        for law, law_dict in self.entity["law"].items():
            phenomenon = law_dict["phenomenon"]
            if self.entity["phenomenon"][phenomenon]["class"] == "ChemicalReactionPhenomenon":
                formula = [law_dict["formula"]["concise_formula"] for law_dict in self.entity["law"].values() if law_dict["phenomenon"] == phenomenon][0]
                if not formula: continue
                formula = re.sub(r"\n", "", formula)
                formula = re.sub(r"\> *\<", "><", formula)
                phenomenon_type_assertation = " - **" + phenomenon.replace("_", " ") + "** is a reaction kinetics phenomenon."
                formula_assertation = " - The **" + phenomenon.replace("_", " ") + "** formula is " + formula
                if phenomenon_type_assertation not in phenomenon_context: phenomenon_context.append(phenomenon_type_assertation)
                if formula_assertation not in formula_context: formula_context.append(formula_assertation)

        common_molecular_transport_phenomena = []
        for rule, rule_dict in self.entity["rule"].items():
            if [d for d in rule_dict["context_descriptors"] if self.entity["context_descriptor"][d]["class"] == "StructureContextDescriptor"]: continue
            for phenomenon in rule_dict["phenomena"]:
                if self.entity["phenomenon"][phenomenon]["class"] == "MolecularTransportPhenomenon" and phenomenon not in common_molecular_transport_phenomena:
                    common_molecular_transport_phenomena.append(phenomenon)
        for law, law_dict in self.entity["law"].items():
            if law_dict["rule"]: continue
            phenomenon = law_dict["phenomenon"]
            if self.entity["phenomenon"][phenomenon]["class"] == "MolecularTransportPhenomenon" and phenomenon not in common_molecular_transport_phenomena:
                if not [rule for rule, rule_dict in self.entity["rule"].items() if phenomenon in rule_dict["phenomena"]]:
                    common_molecular_transport_phenomena.append(phenomenon)
        for descriptor in self.entity["context_descriptor"]:
            if self.entity["context_descriptor"][descriptor]["class"] != "StructureContextDescriptor": continue
            for phenomenon in common_molecular_transport_phenomena:
                formula = [law_dict["formula"]["concise_formula"] for law_dict in self.entity["law"].values() if law_dict["phenomenon"] == phenomenon][0]
                formula = re.sub(r"\n", "", formula)
                formula = re.sub(r"\> *\<", "><", formula)
                phenomenon_type_assertation = " - **" + phenomenon.replace("_", " ") + "** is a molecular transport phenomenon."
                phenomenon_assertation = " - " + descriptor.replace("_", " ") + " has molecular transport phenomenon **" + phenomenon.replace("_", " ") + "**."
                formula_assertation = " - The **" + phenomenon.replace("_", " ") + "** formula in " + descriptor.replace("_", " ") + " is " + formula
                if phenomenon_type_assertation not in phenomenon_context: phenomenon_context.append(phenomenon_type_assertation)
                if phenomenon_assertation not in phenomenon_context: phenomenon_context.append(phenomenon_assertation)
                if formula_assertation not in formula_context: formula_context.append(formula_assertation)
        for law, law_dict in self.entity["law"].items():
            rule = law_dict["rule"]
            if not rule: continue
            for descriptor in self.entity["rule"][rule]["context_descriptors"]:
                if self.entity["context_descriptor"][descriptor]["class"] != "StructureContextDescriptor": continue
                for phenomenon in self.entity["rule"][rule]["phenomena"]:
                    if self.entity["phenomenon"][phenomenon]["class"] == "MolecularTransportPhenomenon":
                        type_assertation = " - **" + phenomenon.replace("_", " ") + "** is a molecular transport phenomenon."
                        assertation = " - " + descriptor.replace("_", " ") + " has molecular transport phenomenon **" + phenomenon.replace("_", " ") + "**."
                        if type_assertation not in phenomenon_context: phenomenon_context.append(type_assertation)
                        if assertation not in phenomenon_context: phenomenon_context.append(assertation)
        
        return "\n".join(phenomenon_context + formula_context)

    def query(self):
        context = self.context()
        client = OpenAI(api_key=self.model_chatgpt_request["api_key"])
        content = "Known:\n" + context + "\n" + \
            "Reaction kinetics phenomena can be combined to describe a single reaction.\n" + \
            "Do not consider Arrhenius when the reaction is proceeded in a water bath.\n" + \
            "Usually do not consider **Instantenous** phenomenon.\n" + \
            "Answer in short length.\n" + \
            self.model_chatgpt_request["query"]
        chat_completion = client.chat.completions.create(messages=[{"role": "user", "content": content}], model="gpt-4o",)
        answer = chat_completion.choices[0].message.content
        response = {"answer": answer}
        return response
