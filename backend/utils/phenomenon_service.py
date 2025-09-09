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
        basic = context["basic"] if "basic" in context else {}
        desc = context["desc"] if "desc" in context else {}

        spcs = basic["spc"] if "spc" in basic else []
        rxns = basic["rxn"] if "rxn" in basic else []
        stms = basic["stm"] if "stm" in basic else []
        gass = basic["gas"] if "gas" in basic else []
        slds = basic["sld"] if "sld" in basic else []

        ac = desc["ac"] if "ac" in desc else None
        fp = desc["fp"] if "fp" in desc else None
        mts = desc["mt"] if "mt" in desc else []
        mes = desc["me"] if "me" in desc else []
        param_law = desc["param_law"] if "param_law" in desc else {}
        rxn_dict = desc["rxn"] if "rxn" in desc else {}

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
        
        info_vars = set()
        info_vars.update(ac_vars)
        info_vars.update(fp_vars)
        info_vars.update(mt_vars)
        info_vars.update(me_vars)
        info_vars.update(param_law_vars)
        for rxn_vars in rxn_var_dict.values():
            info_vars.update(rxn_vars)

        info = {}
        # structure parameter
        info["st"] = {}
        for info_var in info_vars:
            if vars[info_var]["laws"]:
                continue
            if vars[info_var]["cls"] == "StructureParameter":
                if set(vars[info_var]["dims"]) == set([]):
                    info["st"][info_var] = None
        
        # species parameter
        info["spc"] = {}
        for info_var in info_vars:
            if vars[info_var]["laws"]:
                continue
            if vars[info_var]["cls"] == "PhysicsParameter":
                if set(vars[info_var]["dims"]) == set(["Species"]):
                    info["spc"][info_var] = {}
                    for spc in spcs:
                        info["spc"][info_var][spc] = None

        # stream
        info["stm"] = {}
        for info_var in info_vars:
            if vars[info_var]["laws"]:
                continue
            if vars[info_var]["cls"] == "PhysicsParameter":
                if set(vars[info_var]["dims"]) == set(["Stream"]):
                    info["stm"][info_var] = {}
                    for stm in stms:
                        info["stm"][info_var][stm] = None

        # gas
        info["gas"] = {}
        for info_var in info_vars:
            if vars[info_var]["laws"]:
                continue
            if vars[info_var]["cls"] == "PhysicsParameter":
                if set(vars[info_var]["dims"]) == set(["Gas"]):
                    info["gas"][info_var] = {}
                    for gas in gass:
                        info["gas"][info_var][gas] = None
        
        # solid
        info["sld"] = {}
        for info_var in info_vars:
            if vars[info_var]["laws"]:
                continue
            if vars[info_var]["cls"] == "PhysicsParameter":
                if set(vars[info_var]["dims"]) == set(["Solid"]):
                    info["sld"][info_var] = {}
                    for sld in slds:
                        info["sld"][info_var][sld] = None

        # mass transport parameter
        info["mt"] = {}
        for info_var in info_vars:
            if vars[info_var]["laws"]:
                continue
            if vars[info_var]["cls"] == "MassTransportParameter":
                if set(vars[info_var]["dims"]) == set([]):
                    info["mt"][info_var] = None
                if set(vars[info_var]["dims"]) == set(["Gas", "Stream", "Species"]):
                    info["mt"][info_var] = {}
                    for gas in gass:
                        if not basic["gas"][gas]:
                            continue
                        info["mt"][info_var][gas] = {}
                        for stm in stms:
                            info["mt"][info_var][gas][stm] = {}
                            for spc in basic["gas"][gas]["spc"]:
                                info["mt"][info_var][gas][stm][spc] = None
                if set(vars[info_var]["dims"]) == set(["Solid", "Stream", "Species"]):
                    info["mt"][info_var] = {}
                    for sld in slds:
                        if not basic["sld"][sld]:
                            continue
                        info["mt"][info_var][sld] = {}
                        for stm in stms:
                            info["mt"][info_var][sld][stm] = {}
                            for spc in basic["sld"][sld]["spc"]:
                                info["mt"][info_var][sld][stm][spc] = None

        # mass equilibrium parameter
        info["me"] = {}
        for info_var in info_vars:
            if vars[info_var]["laws"]:
                continue
            if vars[info_var]["cls"] == "PhysicsParameter":
                if set(vars[info_var]["dims"]) == set(["Gas", "Stream", "Species"]):
                    info["me"][info_var] = {}
                    for gas in gass:
                        if not basic["gas"][gas]:
                            continue
                        info["me"][info_var][gas] = {}
                        for stm in stms:
                            info["me"][info_var][gas][stm] = {}
                            for spc in basic["gas"][gas]["spc"]:
                                info["me"][info_var][gas][stm][spc] = None
                if set(vars[info_var]["dims"]) == set(["Solid", "Stream", "Species"]):
                    info["me"][info_var] = {}
                    for sld in slds:
                        if not basic["sld"][sld]:
                            continue
                        info["me"][info_var][sld] = {}
                        for stm in stms:
                            info["me"][info_var][sld][stm] = {}
                            for spc in basic["sld"][sld]["spc"]:
                                info["me"][info_var][sld][stm][spc] = None
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
        for info_var in info_vars:
            if vars[info_var]["laws"]:
                continue
            if vars[info_var]["cls"] == "ReactionParameter":
                if set(vars[info_var]["dims"]) == set(["Stream", "Reaction"]):
                    info["rxn"][info_var] = {}
                    for stm in stms:
                        info["rxn"][info_var][stm] = {}
                        for rxn in rxns:
                            if info_var not in rxn_var_dict[rxn]:
                                continue
                            info["rxn"][info_var][stm][rxn] = None
                if set(vars[info_var]["dims"]) == set(["Reaction", "Species"]):
                    if info_var == "Stoichiometric_Coefficient":
                        continue
                    info["rxn"][info_var] = {}
                    for rxn in rxns:
                        if info_var not in rxn_var_dict[rxn]:
                            continue
                        info["rxn"][info_var][rxn] = {}
                        lhs = rxn.split(" > ")[0]
                        lhs_spcs = [s.split(" ")[-1] for s in lhs.split(" + ")]
                        for spc in lhs_spcs:
                            info["rxn"][info_var][rxn][spc] = None
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

    def query_param(self, filters):
        """
        Retrieve parameter -> law mapping for Laws associated with provided phenomena.
        filters: dict with optional keys 'ac', 'fp', 'mt', 'me'; values may be string or list of strings.
        Returns: dict { parameter_name: law_name }
        """
        if not isinstance(filters, dict):
            return {}

        def _norm(v):
            if v is None:
                return []
            if isinstance(v, list):
                items = v
            else:
                items = [v]
            out = []
            for s in items:
                if s is None:
                    continue
                s2 = str(s).strip()
                if s2:
                    out.append(s2)
            return out

        ac_list = _norm(filters.get("ac"))
        fp_list = _norm(filters.get("fp"))
        mt_list = _norm(filters.get("mt"))
        me_list = _norm(filters.get("me"))

        if not (ac_list or fp_list or mt_list or me_list):
            return {}

        union_blocks = []

        def _regex_union(names):
            esc = [re.escape(n) for n in names]
            return "|".join(esc)

        if ac_list:
            p = _regex_union(ac_list)
            union_blocks.append(
                "{"
                f"?d ontomo:isAssociatedWith ?ac. "
                f"?ac rdf:type ontomo:Accumulation. "
                f"FILTER(regex(str(?ac), '#({p})$', 'i')). "
                "}"
            )
        if fp_list:
            p = _regex_union(fp_list)
            union_blocks.append(
                "{"
                f"?d ontomo:isAssociatedWith ?fp. "
                f"?fp rdf:type ontomo:FlowPattern. "
                f"FILTER(regex(str(?fp), '#({p})$', 'i')). "
                "}"
            )
        if mt_list:
            p = _regex_union(mt_list)
            union_blocks.append(
                "{"
                f"?d ontomo:isAssociatedWith ?mt. "
                f"?mt rdf:type ontomo:MassTransportPhenomenon. "
                f"FILTER(regex(str(?mt), '#({p})$', 'i')). "
                "}"
            )
        if me_list:
            p = _regex_union(me_list)
            union_blocks.append(
                "{"
                f"?d ontomo:isAssociatedWith ?me. "
                f"?me rdf:type ontomo:MassEquilibriumPhenomenon. "
                f"FILTER(regex(str(?me), '#({p})$', 'i')). "
                "}"
            )

        param_types = [
            "FlowParameter",
            "ReactorParameter",
            "ReactionParameter",
            "PhysicalParameter",
            "OperatingParameter",
            "MolecularTransportParameter",
        ]
        values_param_types = " ".join([f"ontomo:{t}" for t in param_types])

        sparql = self.h.prefix + \
            "select ?v ?d where {" \
            f"?d rdf:type ontomo:Law. " \
            f"{{ ?d ontomo:hasModelVariable ?v }} UNION {{ ?d ontomo:hasOptionalModelVariable ?v }}. " \
            f"?v rdf:type ?pt. VALUES ?pt {{{values_param_types}}}. "

        if union_blocks:
            sparql += "(" + " UNION ".join(union_blocks) + ") . "

        sparql += "}"

        try:
            sparql_res = self.h.cur.execute(sparql)
        except Exception:
            return {}

        mapping = {}
        for res in sparql_res.split("\r\n")[1:-1]:
            parts = res.split(",")
            if len(parts) < 2:
                continue
            var_iri, law_iri = parts[0], parts[1]
            var_name = var_iri.split("#")[-1]
            law_name = law_iri.split("#")[-1]
            if not var_name or not law_name:
                continue
            if var_name in mapping:
                if law_name < mapping[var_name]:
                    mapping[var_name] = law_name
            else:
                mapping[var_name] = law_name

        return dict(sorted(mapping.items(), key=lambda x: x[0]))

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

    def query_operation_parameters(self, filters=None):
        """
        Retrieve the set of variable local names that are OperationParameter or StructureParameter
        connected to Laws via hasModelVariable/hasOptionalModelVariable, constrained by optional filters:
          - ac, fp, mt, me, rxn: phenomenon names matched case-insensitively on IRI tail
          - param_law: law name(s) matched case-insensitively on IRI tail
        Returns: set of variable names (Python set for uniqueness)
        """

        if filters is None:
            filters = {}
        if not isinstance(filters, dict):
            return set()

        def _norm(v):
            if v is None:
                return []
            if isinstance(v, (list, tuple)):
                items = v
            else:
                items = [v]
            out = []
            for s in items:
                if s is None:
                    continue
                s2 = str(s).strip()
                if s2:
                    out.append(s2)
            return out

        ac_list = _norm(filters.get("ac"))
        fp_list = _norm(filters.get("fp"))
        mt_list = _norm(filters.get("mt"))
        me_list = _norm(filters.get("me"))
        rxn_list = _norm(filters.get("rxn"))

        # Normalize param_law to list of names
        pl = filters.get("param_law")
        if isinstance(pl, dict):
            law_list = _norm(list(pl.values()))
        else:
            law_list = _norm(pl)

        # If no filters at all, reject (per API expectation)
        if not (ac_list or fp_list or mt_list or me_list or rxn_list or law_list):
            return set()

        def _regex_union(names):
            esc = [re.escape(n) for n in names]
            return "|".join(esc)

        # Build UNION blocks for phenomena constraints
        union_blocks = []
        if ac_list:
            p = _regex_union(ac_list)
            union_blocks.append(
                "{"
                "?d ontomo:isAssociatedWith ?phen_ac. "
                "?phen_ac rdf:type ontomo:Accumulation. "
                f"FILTER(regex(str(?phen_ac), '#({p})$', 'i')). "
                "}"
            )
        if fp_list:
            p = _regex_union(fp_list)
            union_blocks.append(
                "{"
                "?d ontomo:isAssociatedWith ?phen_fp. "
                "?phen_fp rdf:type ontomo:FlowPattern. "
                f"FILTER(regex(str(?phen_fp), '#({p})$', 'i')). "
                "}"
            )
        if mt_list:
            p = _regex_union(mt_list)
            # Prefer MassTransportPhenomenon per config
            union_blocks.append(
                "{"
                "?d ontomo:isAssociatedWith ?phen_mt. "
                "?phen_mt rdf:type ontomo:MassTransportPhenomenon. "
                f"FILTER(regex(str(?phen_mt), '#({p})$', 'i')). "
                "}"
            )
        if me_list:
            p = _regex_union(me_list)
            union_blocks.append(
                "{"
                "?d ontomo:isAssociatedWith ?phen_me. "
                "?phen_me rdf:type ontomo:MassEquilibriumPhenomenon. "
                f"FILTER(regex(str(?phen_me), '#({p})$', 'i')). "
                "}"
            )
        if rxn_list:
            p = _regex_union(rxn_list)
            # Support both ReactionPhenomenon and ChemicalReactionPhenomenon
            union_blocks.append(
                "{"
                "?d ontomo:isAssociatedWith ?phen_rxn. "
                "?phen_rxn rdf:type ?rxnType. VALUES ?rxnType { ontomo:ReactionPhenomenon ontomo:ChemicalReactionPhenomenon }. "
                f"FILTER(regex(str(?phen_rxn), '#({p})$', 'i')). "
                "}"
            )

        values_param_types = "ontomo:OperationParameter ontomo:StructureParameter"

        sparql = self.h.prefix + \
            "select ?v where {" \
            "?d rdf:type ontomo:Law. " \
            "{ ?d ontomo:hasModelVariable ?v } UNION { ?d ontomo:hasOptionalModelVariable ?v }. " \
            "?v rdf:type ?pt. VALUES ?pt { " + values_param_types + " }. "

        if union_blocks:
            sparql += "(" + " UNION ".join(union_blocks) + ") . "

        if law_list:
            p = _regex_union(law_list)
            sparql += f"FILTER(regex(str(?d), '#({p})$', 'i')). "

        sparql += "}"

        try:
            res = self.h.cur.execute(sparql)
        except Exception:
            return set()

        vars_set = set()
        for line in res.split("\r\n")[1:-1]:
            v = line.split(",")[0]
            name = v.split("#")[-1]
            if name:
                vars_set.add(name)
        return vars_set
