import re

class PhenomenonService:
    """
    Encapsulates phenomenon-related query helpers for GraphDB.

    This service is composed into GraphdbHandler and uses its cursor/prefix/query API.
    """

    def __init__(self, handler):
        # handler is expected to provide: cur, prefix, query(), and optionally _last_pheno_sparql
        self.h = handler

    def query_pheno(self):
        """Queries Phenomena from GraphDB.

        Returns:
            dict: A dictionary of Phenomena.

        Side-effect:
            Records all SPARQL queries executed for this method. Retrieve them with get_pheno_sparql().
        """
        # Reset SPARQL log for this run
        self._last_pheno_sparql = []

        pheno_dict = {}
        for pheno_class in self.h.pheno_classes:
            sparql = (
                f"{self.h.prefix}"
                "select ?p ?fp ?mtp ?mep where {"
                f"?p rdf:type ontomo:{pheno_class}. "
                "optional{?p ontomo:relatesToFlowPattern ?fp}. "
                "optional{?p ontomo:relatesToMassTransportPhenomenon ?mtp}. "
                "optional{?p ontomo:relatesToMassEquilibriumPhenomenon ?mep}. "
                "}"
            )
            # Log the query for external use (e.g., copy/paste into GraphDB workbench)
            self._last_pheno_sparql.append(sparql)


            sparql_res = self.h.cur.execute(sparql)
            for res in sparql_res.split("\r\n")[1:-1]:
                p, fp, mtp, mep = re.split(r",(?![a-zA-Z0]\<\/mtext\>)", res)
                p = p.split("#")[1]
                fp = fp.split("#")[1] if fp else None
                mtp = mtp.split("#")[1] if mtp else None
                mep = mep.split("#")[1] if mep else None
                if p not in pheno_dict:
                    pheno_dict[p] = {
                        "cls": pheno_class,
                        "fps": [],
                        "mts": [],
                        "mes": [],
                    }
                if fp and fp not in pheno_dict[p]["fps"]:
                    pheno_dict[p]["fps"].append(fp)
                if mtp and mtp not in pheno_dict[p]["mts"]:
                    pheno_dict[p]["mts"].append(mtp)
                if mep and mep not in pheno_dict[p]["mes"]:
                    pheno_dict[p]["mes"].append(mep)
        pheno_dict = dict(sorted(pheno_dict.items(), key=lambda x: x[0]))

        # print(f"Querying {self.h.pheno_classes}s from GraphDB: {self._last_pheno_sparql}")
        for p in pheno_dict:
            pheno_dict[p]["fps"] = sorted(pheno_dict[p]["fps"])
            pheno_dict[p]["mts"] = sorted(pheno_dict[p]["mts"])
            pheno_dict[p]["mes"] = sorted(pheno_dict[p]["mes"])
        return pheno_dict

    def query_ac(self):
        """
        Return a sorted list of Accumulation individuals (e.g., 'Batch', 'Continuous').
        """
        sparql = self.h.prefix + \
            "select ?p where {" \
            f"?p rdf:type ontomo:Accumulation. " \
            "}"
        try:
            sparql_res = self.h.cur.execute(sparql)
        except Exception:
            return []
        acs = set()
        for line in sparql_res.split("\r\n")[1:-1]:
            try:
                _, ac = line.split("#")
            except ValueError:
                parts = line.split("#")
                ac = parts[-1] if parts else ""
            ac = ac.strip()
            if ac:
                acs.add(ac)
        return sorted(acs)

    def query_fp_by_ac(self, ac):
        """
        Query all FlowPattern individuals related to a specific Accumulation individual.
        The input `ac` is expected to indicate which Accumulation individual to filter, e.g.,
        "Batch" or "Continuous". Matching is case-insensitive.

        Returns a sorted list of FlowPattern local names.
        """
        if ac is None:
            return []

        ac_str = str(ac).strip()
        if not ac_str:
            return []

        sparql = self.h.prefix + \
            "select ?p ?rp where {" \
            f"?p rdf:type ontomo:Accumulation. " \
            f"optional{{?p ontomo:relatesToFlowPattern ?rp}}. " \
            f"FILTER(regex(str(?p), '#{ac_str}$', 'i')). " \
            "}"

        try:
            sparql_res = self.h.cur.execute(sparql)
        except Exception:
            return []

        fps = set()
        for res in sparql_res.split("\r\n")[1:-1]:
            try:
                _, fp = res.split(",")
            except ValueError:
                parts = res.split(",")
                fp = parts[1] if len(parts) > 1 else ""
            fp = fp.split("#")[-1]
            if fp:
                fps.add(fp)

        return sorted(fps)

    def query_mt_by_fp(self, fp):
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

        sparql = self.h.prefix + \
            "select ?fp ?mt where {" \
            f"?fp rdf:type ontomo:FlowPattern. " \
            f"optional{{?fp ontomo:relatesToMassTransportPhenomenon ?mt}}. " \
            f"FILTER(regex(str(?fp), '#{fp_str}$', 'i')). " \
            "}"

        try:
            sparql_res = self.h.cur.execute(sparql)
        except Exception:
            return []

        mass_transfers = set()
        for res in sparql_res.split("\r\n")[1:-1]:
            try:
                _, mt_iri = res.split(",")
            except ValueError:
                parts = res.split(",")
                mt_iri = parts[1] if len(parts) > 1 else ""
            mt_name = mt_iri.split("#")[-1]
            if mt_name:
                mass_transfers.add(mt_name)
        return sorted(mass_transfers)

    def query_me_by_mt(self, mt):
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

        sparql = self.h.prefix + \
            "select ?mt ?me where {" \
            f"?mt rdf:type ontomo:MassTransportPhenomenon. " \
            f"FILTER(regex(str(?mt), '#{mt_str}$', 'i')). " \
            f"?me rdf:type ontomo:MassEquilibriumPhenomenon. " \
            f"?mt ontomo:relatesToMassEquilibriumPhenomenon ?me. " \
            "}"

        try:
            sparql_res = self.h.cur.execute(sparql)
        except Exception:
            return []

        mes = set()
        for res in sparql_res.split("\r\n")[1:-1]:
            parts = res.split(",")
            me = parts[1] if len(parts) > 1 else ""
            me = me.split("#")[-1]
            if me:
                mes.add(me)

        return sorted(mes)

    def query_rxn(self):
        """
        Return a sorted list of ReactionPhenomenon individuals (e.g., 'Arrhenius', 'Plain_Rate_Constant').
        """
        sparql = self.h.prefix + \
            "select ?p where {" \
            f"?p rdf:type ontomo:ReactionPhenomenon. " \
            "}"
        try:
            sparql_res = self.h.cur.execute(sparql)
        except Exception:
            return []
        rxns = set()
        for line in sparql_res.split("\r\n")[1:-1]:
            try:
                _, rxn = line.split("#")
            except ValueError:
                parts = line.split("#")
                rxn = parts[-1] if parts else ""
            rxn = rxn.strip()
            if rxn:
                rxns.add(rxn)
        return sorted(rxns)

    def query_info(self, context):
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
        basic = context.get("basic", {})
        desc = context.get("desc", {})

        spcs = basic.get("spc", [])
        rxns = basic.get("rxn", [])
        stms = basic.get("stm", [])
        gass = basic.get("gas", [])
        slds = basic.get("sld", [])

        ac = desc.get("ac", None)
        fp = desc.get("fp", None)
        mts = desc.get("mt", [])
        mes = desc.get("me", [])
        param_law = desc.get("param_law", {})
        rxn_dict = desc.get("rxn", {})

        laws = self.h.query_law("mainpage")
        vars = self.h.query_var()

        ac_vars, ac_opt_vars = set(), set()
        for law_dict in laws.values():
            if law_dict["pheno"] == ac:
                for var in law_dict["vars"]:
                    ac_vars.add(var)
                for var in law_dict["opt_vars"]:
                    ac_opt_vars.add(var)
        
        fp_vars = set()
        for law, law_dict in laws.items():
            if any([law in vars[var]["laws"] for var in ac_vars]):
                if law_dict["pheno"] == fp:
                    for var in law_dict["vars"]:
                        fp_vars.add(var)
        
        mt_vars = set()
        for law, law_dict in laws.items():
            if any([law in vars[var]["laws"] for var in ac_opt_vars]):
                if law_dict["pheno"] in mts:
                    for var in law_dict["vars"]:
                        mt_vars.add(var)

        me_vars = set()
        for law, law_dict in laws.items():
            if any([law in vars[var]["laws"] for var in mt_vars]):
                if law_dict["pheno"] in mes:
                    for var in law_dict["vars"]:
                        me_vars.add(var)

        param_law_vars = set()
        for law in param_law.values():
            law_dict = laws[law]
            for var in law_dict["vars"]:
                param_law_vars.add(var)
        
        rxn_var_dict = {rxn: set() for rxn in rxn_dict}
        for rxn, rxn_phenos in rxn_dict.items():
            for law, law_dict in laws.items():
                if law_dict["pheno"] in rxn_phenos:
                    for var in law_dict["vars"]:
                        rxn_var_dict[rxn].add(var)
                        for var_law in vars[var]["laws"]:
                            for var_law_var in laws[var_law]["vars"]:
                                rxn_var_dict[rxn].add(var_law_var)
        
        desc_vars = set()
        desc_vars.update(ac_vars)
        desc_vars.update(fp_vars)
        desc_vars.update(mt_vars)
        desc_vars.update(me_vars)
        desc_vars.update(param_law_vars)
        for rxn_vars in rxn_var_dict.values():
            desc_vars.update(rxn_vars)
        desc_vars = sorted(desc_vars)

        info = {}
        # structure parameter
        info["st"] = {}
        for desc_var in desc_vars:
            if vars[desc_var]["laws"]:
                continue
            if vars[desc_var]["cls"] == "StructureParameter":
                if set(vars[desc_var]["dims"]) == set([]):
                    info["st"][desc_var] = None
        
        # species parameter
        info["spc"] = {}
        for desc_var in desc_vars:
            if vars[desc_var]["laws"]:
                continue
            if vars[desc_var]["cls"] == "PhysicsParameter":
                if set(vars[desc_var]["dims"]) == set(["Species"]):
                    info["spc"][desc_var] = {}
                    for spc in spcs:
                        info["spc"][desc_var][spc] = None

        # stream
        info["stm"] = {}
        for desc_var in desc_vars:
            if vars[desc_var]["laws"]:
                continue
            if vars[desc_var]["cls"] == "PhysicsParameter":
                if set(vars[desc_var]["dims"]) == set(["Stream"]):
                    info["stm"][desc_var] = {}
                    for stm in stms:
                        info["stm"][desc_var][stm] = None

        # gas
        info["gas"] = {}
        for desc_var in desc_vars:
            if vars[desc_var]["laws"]:
                continue
            if vars[desc_var]["cls"] == "PhysicsParameter":
                if set(vars[desc_var]["dims"]) == set(["Gas"]):
                    info["gas"][desc_var] = {}
                    for gas in gass:
                        info["gas"][desc_var][gas] = None
        
        # solid
        info["sld"] = {}
        for desc_var in desc_vars:
            if vars[desc_var]["laws"]:
                continue
            if vars[desc_var]["cls"] == "PhysicsParameter":
                if set(vars[desc_var]["dims"]) == set(["Solid"]):
                    info["sld"][desc_var] = {}
                    for sld in slds:
                        info["sld"][desc_var][sld] = None

        # mass transport parameter
        info["mt"] = {}
        for desc_var in desc_vars:
            if vars[desc_var]["laws"]:
                continue
            if vars[desc_var]["cls"] == "MassTransportParameter":
                if set(vars[desc_var]["dims"]) == set([]):
                    info["mt"][desc_var] = None
                if set(vars[desc_var]["dims"]) == set(["Gas", "Stream", "Species"]):
                    info["mt"][desc_var] = {}
                    for gas in gass:
                        if not basic["gas"][gas]:
                            continue
                        info["mt"][desc_var][gas] = {}
                        for stm in stms:
                            info["mt"][desc_var][gas][stm] = {}
                            for spc in basic["gas"][gas]["spc"]:
                                info["mt"][desc_var][gas][stm][spc] = None
                if set(vars[desc_var]["dims"]) == set(["Solid", "Stream", "Species"]):
                    info["mt"][desc_var] = {}
                    for sld in slds:
                        if not basic["sld"][sld]:
                            continue
                        info["mt"][desc_var][sld] = {}
                        for stm in stms:
                            info["mt"][desc_var][sld][stm] = {}
                            for spc in basic["sld"][sld]["spc"]:
                                info["mt"][desc_var][sld][stm][spc] = None

        # mass equilibrium parameter
        info["me"] = {}
        for desc_var in desc_vars:
            if vars[desc_var]["laws"]:
                continue
            if vars[desc_var]["cls"] == "PhysicsParameter":
                if set(vars[desc_var]["dims"]) == set(["Gas", "Stream", "Species"]):
                    info["me"][desc_var] = {}
                    for gas in gass:
                        if not basic["gas"][gas]:
                            continue
                        info["me"][desc_var][gas] = {}
                        for stm in stms:
                            info["me"][desc_var][gas][stm] = {}
                            for spc in basic["gas"][gas]["spc"]:
                                info["me"][desc_var][gas][stm][spc] = None
                if set(vars[desc_var]["dims"]) == set(["Solid", "Stream", "Species"]):
                    info["me"][desc_var] = {}
                    for sld in slds:
                        if not basic["sld"][sld]:
                            continue
                        info["me"][desc_var][sld] = {}
                        for stm in stms:
                            info["me"][desc_var][sld][stm] = {}
                            for spc in basic["sld"][sld]["spc"]:
                                info["me"][desc_var][sld][stm][spc] = None
        for var, var_dict in vars.items():
            if set(var_dict["dims"]) == set(["Solid", "Stream", "Species"]):
                for law in var_dict["laws"]:
                    law_dict = laws[law]
                    if law_dict["pheno"] not in mes:
                        continue
                    if law_dict["fml"]["detail_formula"] and "specifically defined" \
                        in law_dict["fml"]["detail_formula"]:
                        if law not in info["me"]:
                            info["me"][law] = {}
                        for sld in slds:
                            if sld not in info["me"][law]:
                                info["me"][law][sld] = {}
                            for stm in stms:
                                if stm not in info["me"][law][sld]:
                                    info["me"][law][sld][stm] = {}
                                for spc in basic["sld"][sld]["spc"]:
                                    info["me"][law][sld][stm][spc] = None

        # reaction parameter
        info["rxn"] = {}
        for desc_var in desc_vars:
            if vars[desc_var]["laws"]:
                continue
            if vars[desc_var]["cls"] == "ReactionParameter":
                if set(vars[desc_var]["dims"]) == set(["Stream", "Reaction"]):
                    info["rxn"][desc_var] = {}
                    for stm in stms:
                        info["rxn"][desc_var][stm] = {}
                        for rxn in rxns:
                            if desc_var not in rxn_var_dict[rxn]:
                                continue
                            info["rxn"][desc_var][stm][rxn] = None
                if set(vars[desc_var]["dims"]) == set(["Reaction", "Species"]):
                    if desc_var == "Stoichiometric_Coefficient":
                        continue
                    info["rxn"][desc_var] = {}
                    for rxn in rxns:
                        if desc_var not in rxn_var_dict[rxn]:
                            continue
                        info["rxn"][desc_var][rxn] = {}
                        lhs = rxn.split(" > ")[0]
                        lhs_spcs = [s.split(" ")[-1] for s in lhs.split(" + ")]
                        for spc in lhs_spcs:
                            info["rxn"][desc_var][rxn][spc] = None
        for rxn, rxn_phenos in rxn_dict.items():
            for var, var_dict in vars.items():
                for law in var_dict["laws"]:
                    law_dict = laws[law]
                    if law_dict["pheno"] in rxn_phenos:
                        if law_dict["fml"]["detail_formula"] and "specifically defined" \
                            in law_dict["fml"]["detail_formula"]:
                            if law_dict["pheno"] not in info["rxn"]:
                                info["rxn"][law_dict["pheno"]] = {}
                            info["rxn"][law_dict["pheno"]][rxn] = None

        return info

    def query_param_law(self, desc):
        """
        Retrieve parameter -> law mapping for Laws associated with provided phenomena.
        desc: dict with optional keys 'ac', 'fp', 'mt', 'me'; values may be string or list of strings.
        Returns: dict { parameter_name: law_name }
        """
        if not isinstance(desc, dict):
            return {}
        
        param_law = {}
        vars = self.h.query_var()
        laws = self.h.query_law(mode="mainpage")

        # flow pattern laws subsidiary to mass transport
        for law_dict in laws.values():
            if law_dict["pheno"] not in desc["mt"]:
                continue
            for var in law_dict["vars"]:
                if var == "Concentration":
                    continue
                if var in param_law or not vars[var]["laws"]:
                    continue
                var_laws = []
                for var_law in vars[var]["laws"]:
                    if laws[var_law]["pheno"] == desc["fp"]:
                        var_laws.append(var_law)
                if var_laws:
                    param_law[var] = var_laws

        # flow pattern laws subsidiary to flow pattern
        for law_dict in laws.values():
            if law_dict["pheno"] != desc["fp"]:
                continue
            for var in law_dict["vars"]:
                if var == "Concentration":
                    continue
                if var in param_law or not vars[var]["laws"]:
                    continue
                var_laws = []
                for var_law in vars[var]["laws"]:
                    if laws[var_law]["pheno"] == desc["fp"]:
                        var_laws.append(var_law)
                if var_laws:
                    param_law[var] = var_laws
        
        # mass equilibrium laws
        for law_dict in laws.values():
            if law_dict["pheno"] not in desc["mt"]:
                continue
            for var in law_dict["vars"]:
                if var in param_law or not vars[var]["laws"]:
                    continue
                var_laws = []
                for var_law in vars[var]["laws"]:
                    if laws[var_law]["pheno"] in desc["me"]:
                        var_laws.append(var_law)
                if var_laws:
                    param_law[var] = var_laws

        return dict(sorted(param_law.items(), key=lambda x: x[0]))

    def query_symbol(self, unit):
        """
        Given a Unit local name (e.g., "meter", "second", "mol_per_L"),
        query GraphDB for its ontomo:hasSymbol and return a cleaned symbol string.
        Matching is case-insensitive on the IRI tail.
        Returns: str symbol or None if not found.
        """
        if unit is None:
            return None
        unit_str = str(unit).strip()
        if not unit_str:
            return None

        sparql = self.h.prefix + \
            "select ?u ?s where {" \
            f"?u rdf:type ontomo:Unit. " \
            f"optional{{?u ontomo:hasSymbol ?s}}. " \
            f"FILTER(regex(str(?u), '#{re.escape(unit_str)}$', 'i')). " \
            "}"

        try:
            sparql_res = self.h.cur.execute(sparql)
        except Exception:
            return None

        # Expect CSV-like lines with header, then rows: u,s
        for res in sparql_res.split("\r\n")[1:-1]:
            parts = re.split(r",(?![a-zA-Z0]\<\/mtext\>)", res)
            if not parts:
                continue
            s = parts[1] if len(parts) > 1 else None
            if not s:
                # No symbol bound for this row
                continue
            # Clean quotes and xmlns just like query_unit does
            try:
                s_clean = re.sub(r'("*)"', r'\1', s[1:-1])
                s_clean = re.sub(r" xmlns=[^\>]*", "", s_clean)
            except Exception:
                s_clean = s
            if s_clean:
                return s_clean
        return None

    def query_op_param(self, context=None):
        """
        Retrieve the set of variable local names that are OperationParameter
        connected to Laws via hasModelVariable/hasOptionalModelVariable, constrained by optional filters:
          - ac, fp, mt, me, rxn: phenomenon names matched case-insensitively on IRI tail
          - param_law: law name(s) matched case-insensitively on IRI tail
        Returns: set of variable names (Python set for uniqueness)
        """

        if context is None:
            context = {}
        if not isinstance(context, dict):
            return set()

        
        basic = context.get("basic", {})
        desc = context.get("desc", {})

        spcs = basic.get("spc", [])
        rxns = basic.get("rxn", [])
        stms = basic.get("stm", [])
        gass = basic.get("gas", [])
        slds = basic.get("sld", [])

        ac = desc.get("ac", None)
        fp = desc.get("fp", None)
        mts = desc.get("mt", [])
        mes = desc.get("me", [])
        param_law = desc.get("param_law", {})
        rxn_dict = desc.get("rxn", {})

        laws = self.h.query_law("mainpage")
        vars = self.h.query_var()

        ac_vars, ac_opt_vars = set(), set()
        for law_dict in laws.values():
            if law_dict["pheno"] == ac:
                for var in law_dict["vars"]:
                    ac_vars.add(var)
                for var in law_dict["opt_vars"]:
                    ac_opt_vars.add(var)
        
        fp_vars = set()
        for law, law_dict in laws.items():
            if any([law in vars[var]["laws"] for var in ac_vars]):
                if law_dict["pheno"] == fp:
                    for var in law_dict["vars"]:
                        fp_vars.add(var)
        
        mt_vars = set()
        for law, law_dict in laws.items():
            if any([law in vars[var]["laws"] for var in ac_opt_vars]):
                if law_dict["pheno"] in mts:
                    for var in law_dict["vars"]:
                        mt_vars.add(var)

        me_vars = set()
        for law, law_dict in laws.items():
            if any([law in vars[var]["laws"] for var in mt_vars]):
                if law_dict["pheno"] in mes:
                    for var in law_dict["vars"]:
                        me_vars.add(var)
        
        assoc_gas_vars = set()
        for law, law_dict in laws.items():
            for ac_opt_var in ac_opt_vars:
                if law in vars[ac_opt_var]["laws"]:
                    if law_dict["pheno"] in mts:
                        assoc_gas_law = law_dict["assoc_gas_law"]
                        if assoc_gas_law and basic["gas"]:
                            for var in laws[assoc_gas_law]["vars"]:
                                assoc_gas_vars.add(var)
        
        assoc_sld_vars = set()
        for law, law_dict in laws.items():
            for ac_opt_var in ac_opt_vars:
                if law in vars[ac_opt_var]["laws"]:
                    if law_dict["pheno"] in mts:
                        assoc_sld_law = law_dict["assoc_sld_law"]
                        if assoc_sld_law and basic["sld"]:
                            for var in laws[assoc_sld_law]["vars"]:
                                assoc_sld_vars.add(var)

        param_law_vars = set()
        for law in param_law.values():
            law_dict = laws[law]
            for var in law_dict["vars"]:
                param_law_vars.add(var)
        
        rxn_var_dict = {rxn: set() for rxn in rxn_dict}
        for rxn, rxn_phenos in rxn_dict.items():
            for law, law_dict in laws.items():
                if law_dict["pheno"] in rxn_phenos:
                    for var in law_dict["vars"]:
                        rxn_var_dict[rxn].add(var)
                        for var_law in vars[var]["laws"]:
                            for var_law_var in laws[var_law]["vars"]:
                                rxn_var_dict[rxn].add(var_law_var)
        
        desc_vars = set()
        desc_vars.update(ac_vars)
        desc_vars.update(fp_vars)
        desc_vars.update(mt_vars)
        desc_vars.update(me_vars)
        desc_vars.update(assoc_gas_vars)
        desc_vars.update(assoc_sld_vars)
        desc_vars.update(param_law_vars)
        for rxn_vars in rxn_var_dict.values():
            desc_vars.update(rxn_vars)
        desc_vars = sorted(desc_vars)

        op_param = {}
        for desc_var in desc_vars:
            if vars[desc_var]["laws"]:
                continue
            if vars[desc_var]["cls"] == "OperationParameter":
                if set(vars[desc_var]["dims"]) == set([]):
                    op_param[(desc_var, None, None, None, None)] = None

        for desc_var in desc_vars:
            if vars[desc_var]["laws"]:
                continue
            if vars[desc_var]["cls"] == "OperationParameter":
                if set(vars[desc_var]["dims"]) == set(["Stream"]):
                    for stm in stms:
                        op_param[(desc_var, None, stm, None, None)] = None

        for desc_var in desc_vars:
            if vars[desc_var]["laws"]:
                continue
            if vars[desc_var]["cls"] == "OperationParameter":
                if set(vars[desc_var]["dims"]) == set(["Gas"]):
                    for gas in gass:
                        op_param[(desc_var, gas, None, None, None)] = None

        for desc_var in desc_vars:
            if vars[desc_var]["laws"]:
                continue
            if vars[desc_var]["cls"] == "OperationParameter":
                if set(vars[desc_var]["dims"]) == set(["Solid"]):
                    for sld in slds:
                        op_param[(desc_var, sld, None, None, None)] = None

        for desc_var in desc_vars:
            if vars[desc_var]["laws"]:
                continue
            if vars[desc_var]["cls"] == "OperationParameter":
                if set(vars[desc_var]["dims"]) == set(["Species", "Stream"]):
                    for stm in stms:
                        for spc in basic["stm"][stm]["spc"]:
                            op_param[(desc_var, None, stm, None, spc)] = None

        for desc_var in desc_vars:
            if vars[desc_var]["laws"]:
                continue
            if vars[desc_var]["cls"] == "OperationParameter":
                if set(vars[desc_var]["dims"]) == set(["Species", "Gas"]):
                    for gas in gass:
                        for spc in basic["gas"][gas]["spc"]:
                            op_param[(desc_var, gas, None, None, spc)] = None

        for desc_var in desc_vars:
            if vars[desc_var]["laws"]:
                continue
            if vars[desc_var]["cls"] == "OperationParameter":
                if set(vars[desc_var]["dims"]) == set(["Species", "Solid"]):
                    for sld in slds:
                        for spc in basic["sld"][sld]["spc"]:
                            op_param[(desc_var, sld, None, None, spc)] = None

        return op_param
    
    def query_cal_param(self, context=None):
        """
        Retrieve the set of variable local names that are ReactionParamter/MassTransferParameter
        connected to Laws via hasModelVariable/hasOptionalModelVariable, constrained by optional filters:
          - ac, fp, mt, me, rxn: phenomenon names matched case-insensitively on IRI tail
          - param_law: law name(s) matched case-insensitively on IRI tail
        Returns: set of variable names (Python set for uniqueness)
        """

        if context is None:
            context = {}
        if not isinstance(context, dict):
            return set()

        
        basic = context.get("basic", {})
        desc = context.get("desc", {})

        spcs = basic.get("spc", [])
        rxns = basic.get("rxn", [])
        stms = basic.get("stm", [])
        gass = basic.get("gas", [])
        slds = basic.get("sld", [])

        ac = desc.get("ac", None)
        fp = desc.get("fp", None)
        mts = desc.get("mt", [])
        mes = desc.get("me", [])
        param_law = desc.get("param_law", {})
        rxn_dict = desc.get("rxn", {})

        laws = self.h.query_law("mainpage")
        vars = self.h.query_var()

        ac_vars, ac_opt_vars = set(), set()
        for law_dict in laws.values():
            if law_dict["pheno"] == ac:
                for var in law_dict["vars"]:
                    ac_vars.add(var)
                for var in law_dict["opt_vars"]:
                    ac_opt_vars.add(var)
        
        fp_vars = set()
        for law, law_dict in laws.items():
            if any([law in vars[var]["laws"] for var in ac_vars]):
                if law_dict["pheno"] == fp:
                    for var in law_dict["vars"]:
                        fp_vars.add(var)
        
        mt_vars = set()
        for law, law_dict in laws.items():
            if any([law in vars[var]["laws"] for var in ac_opt_vars]):
                if law_dict["pheno"] in mts:
                    for var in law_dict["vars"]:
                        mt_vars.add(var)

        me_vars = set()
        for law, law_dict in laws.items():
            if any([law in vars[var]["laws"] for var in mt_vars]):
                if law_dict["pheno"] in mes:
                    for var in law_dict["vars"]:
                        me_vars.add(var)

        param_law_vars = set()
        for law in param_law.values():
            law_dict = laws[law]
            for var in law_dict["vars"]:
                param_law_vars.add(var)
        
        rxn_var_dict = {rxn: set() for rxn in rxn_dict}
        for rxn, rxn_phenos in rxn_dict.items():
            for law, law_dict in laws.items():
                if law_dict["pheno"] in rxn_phenos:
                    for var in law_dict["vars"]:
                        rxn_var_dict[rxn].add(var)
                        for var_law in vars[var]["laws"]:
                            for var_law_var in laws[var_law]["vars"]:
                                rxn_var_dict[rxn].add(var_law_var)
        
        desc_vars = set()
        desc_vars.update(ac_vars)
        desc_vars.update(fp_vars)
        desc_vars.update(mt_vars)
        desc_vars.update(me_vars)
        desc_vars.update(param_law_vars)
        for rxn_vars in rxn_var_dict.values():
            desc_vars.update(rxn_vars)
        desc_vars = sorted(desc_vars)

        cal_param = {}
        for desc_var in desc_vars:
            if vars[desc_var]["laws"]:
                continue
            if vars[desc_var]["cls"] in ["ReactionParameter", "MassTransportParameter"]:
                if set(vars[desc_var]["dims"]) == set([]):
                    cal_param[(desc_var, None, None, None, None)] = None

        for desc_var in desc_vars:
            if vars[desc_var]["laws"]:
                continue
            if vars[desc_var]["cls"] in ["ReactionParameter", "MassTransportParameter"]:
                if set(vars[desc_var]["dims"]) == set(["Reaction", "Stream"]):
                    for stm in stms:
                        for rxn in basic["stm"][stm]["rxn"]:
                            if desc_var in rxn_var_dict[rxn]:
                                cal_param[(desc_var, None, stm, rxn, None)] = None

        for desc_var in desc_vars:
            if vars[desc_var]["laws"]:
                continue
            if vars[desc_var]["cls"] in ["ReactionParameter", "MassTransportParameter"]:
                if set(vars[desc_var]["dims"]) == set(["Species", "Stream", "Gas"]):
                    for stm in stms:
                        for gas in gass:
                            for spc in basic["gas"][gas]["spc"]:
                                cal_param[(desc_var, gas, stm, None, spc)] = None

        for desc_var in desc_vars:
            if vars[desc_var]["laws"]:
                continue
            if vars[desc_var]["cls"] in ["ReactionParameter", "MassTransportParameter"]:
                if set(vars[desc_var]["dims"]) == set(["Species", "Stream", "Solid"]):
                    for stm in stms:
                        for sld in slds:
                            for spc in basic["sld"][sld]["spc"]:
                                cal_param[(desc_var, sld, stm, None, spc)] = None

        return cal_param
