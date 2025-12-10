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
                        # Use sets during construction for O(1) membership checks
                        "_fps_set": set(),
                        "_mts_set": set(),
                        "_mes_set": set(),
                    }
                if fp:
                    pheno_dict[p]["_fps_set"].add(fp)
                if mtp:
                    pheno_dict[p]["_mts_set"].add(mtp)
                if mep:
                    pheno_dict[p]["_mes_set"].add(mep)
        pheno_dict = dict(sorted(pheno_dict.items(), key=lambda x: x[0]))

        # print(f"Querying {self.h.pheno_classes}s from GraphDB: {self._last_pheno_sparql}")
        for p in list(pheno_dict.keys()):
            pheno_dict[p]["fps"] = sorted(pheno_dict[p].get("_fps_set", set()))
            pheno_dict[p]["mts"] = sorted(pheno_dict[p].get("_mts_set", set()))
            pheno_dict[p]["mes"] = sorted(pheno_dict[p].get("_mes_set", set()))
            if "_fps_set" in pheno_dict[p]:
                del pheno_dict[p]["_fps_set"]
            if "_mts_set" in pheno_dict[p]:
                del pheno_dict[p]["_mts_set"]
            if "_mes_set" in pheno_dict[p]:
                del pheno_dict[p]["_mes_set"]
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

        # Base ontology maps
        laws = self.h.query_law("mainpage")
        vars = self.h.query_var()

        # Precompute set-based indices for fast membership/union operations
        laws_by_pheno = {}
        vars_by_law = {}
        opt_vars_by_law = {}
        laws_by_var = {}
        for law, ld in laws.items():
            p = ld.get("pheno")
            if p:
                laws_by_pheno.setdefault(p, set()).add(law)
            vars_by_law[law] = set(ld.get("vars", []) or [])
            opt_vars_by_law[law] = set(ld.get("opt_vars", []) or [])
        for v, vd in vars.items():
            laws_by_var[v] = set(vd.get("laws", []) or [])

        vars_by_pheno = {}
        opt_vars_by_pheno = {}
        for p, lset in laws_by_pheno.items():
            vagg = set()
            voagg = set()
            for l in lset:
                vagg |= vars_by_law.get(l, set())
                voagg |= opt_vars_by_law.get(l, set())
            vars_by_pheno[p] = vagg
            opt_vars_by_pheno[p] = voagg

        # Accumulation-derived sets
        ac_vars = set(vars_by_pheno.get(ac, set())) if ac else set()
        ac_opt_vars = set(opt_vars_by_pheno.get(ac, set())) if ac else set()

        # FP vars influenced by AC vars
        fp_vars = set()
        if fp and ac_vars:
            ac_var_laws = set().union(*(laws_by_var.get(v, set()) for v in ac_vars))
            fp_laws = set(laws_by_pheno.get(fp, set()))
            fp_laws_from_ac = ac_var_laws & fp_laws
            if fp_laws_from_ac:
                fp_vars = set().union(*(vars_by_law.get(l, set()) for l in fp_laws_from_ac))

        # MT vars influenced by AC optional vars
        mt_vars = set()
        if mts and ac_opt_vars:
            ac_opt_var_laws = set().union(*(laws_by_var.get(v, set()) for v in ac_opt_vars))
            mt_laws_set = set().union(*(laws_by_pheno.get(m, set()) for m in mts))
            mt_laws_from_ac_opt = ac_opt_var_laws & mt_laws_set
            if mt_laws_from_ac_opt:
                mt_vars = set().union(*(vars_by_law.get(l, set()) for l in mt_laws_from_ac_opt))

        # ME vars influenced by MT vars
        me_vars = set()
        if mts and mes and mt_vars:
            mt_var_laws = set().union(*(laws_by_var.get(v, set()) for v in mt_vars))
            me_laws_set = set().union(*(laws_by_pheno.get(m, set()) for m in mes))
            me_laws_from_mt = mt_var_laws & me_laws_set
            if me_laws_from_mt:
                me_vars = set().union(*(vars_by_law.get(l, set()) for l in me_laws_from_mt))

        # Vars referenced directly by chosen parameter laws
        param_law_vars = set()
        if param_law:
            chosen = [l for l in param_law.values() if l in vars_by_law]
            if chosen:
                param_law_vars = set().union(*(vars_by_law.get(l, set()) for l in chosen))

        # Reaction variable neighborhoods (base + 2-hop)
        rxn_var_dict = {rxn: set() for rxn in rxn_dict}
        for rxn, rxn_phenos in rxn_dict.items():
            base_vars = set().union(*(vars_by_pheno.get(p, set()) for p in rxn_phenos)) if rxn_phenos else set()
            neighbor_laws = set().union(*(laws_by_var.get(v, set()) for v in base_vars)) if base_vars else set()
            neighbor_vars = set().union(*(vars_by_law.get(l, set()) for l in neighbor_laws)) if neighbor_laws else set()
            rxn_var_dict[rxn] = base_vars | neighbor_vars
        
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

        # Normalize filters
        ac = desc.get("ac")
        fp = desc.get("fp")
        mt_list = desc.get("mt") or []
        me_list = desc.get("me") or []

        # Base ontology maps
        vars = self.h.query_var()
        laws = self.h.query_law(mode="mainpage")

        # Build indices
        laws_by_pheno = {}
        vars_by_law = {}
        laws_by_var = {}
        for law, ld in laws.items():
            p = ld.get("pheno")
            if p:
                laws_by_pheno.setdefault(p, set()).add(law)
            vars_by_law[law] = set(ld.get("vars", []) or [])
        for v, vd in vars.items():
            laws_by_var[v] = set(vd.get("laws", []) or [])

        vars_by_pheno = {}
        for p, lset in laws_by_pheno.items():
            vagg = set()
            for l in lset:
                vagg |= vars_by_law.get(l, set())
            vars_by_pheno[p] = vagg

        param_law = {}

        def add_mapping(var, law_names):
            if not law_names:
                return
            lst = sorted(set(law_names))
            if var in param_law:
                param_law[var] = sorted(set(param_law[var] + lst))
            else:
                param_law[var] = lst

        # 1) FP laws subsidiary to MT
        if mt_list:
            mt_vars = set().union(*(vars_by_pheno.get(p, set()) for p in mt_list))
            for var in mt_vars:
                if var == "Concentration":
                    continue
                var_laws = laws_by_var.get(var, set())
                fp_laws_for_var = [l for l in var_laws if laws.get(l, {}).get("pheno") == fp]
                if fp_laws_for_var and var not in param_law:
                    add_mapping(var, fp_laws_for_var)

        # 2) FP laws subsidiary to FP
        if fp:
            fp_vars = set().union(*(vars_by_pheno.get(p, set()) for p in [fp]))
            for var in fp_vars:
                if var == "Concentration" or var in param_law:
                    continue
                var_laws = laws_by_var.get(var, set())
                fp_laws_for_var = [l for l in var_laws if laws.get(l, {}).get("pheno") == fp]
                if fp_laws_for_var:
                    add_mapping(var, fp_laws_for_var)

        # 3) ME laws filtered from MT
        if mt_list and me_list:
            mt_vars = set().union(*(vars_by_pheno.get(p, set()) for p in mt_list))
            for var in mt_vars:
                if var in param_law:
                    continue
                var_laws = laws_by_var.get(var, set())
                me_laws_for_var = [l for l in var_laws if laws.get(l, {}).get("pheno") in me_list]
                if me_laws_for_var:
                    add_mapping(var, me_laws_for_var)

        return {k: param_law[k] for k in sorted(param_law.keys())}

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

        # Base ontology maps
        laws = self.h.query_law("mainpage")
        vars = self.h.query_var()

        # Indices
        laws_by_pheno = {}
        vars_by_law = {}
        opt_vars_by_law = {}
        laws_by_var = {}
        for law, ld in laws.items():
            p = ld.get("pheno")
            if p:
                laws_by_pheno.setdefault(p, set()).add(law)
            vars_by_law[law] = set(ld.get("vars", []) or [])
            opt_vars_by_law[law] = set(ld.get("opt_vars", []) or [])
        for v, vd in vars.items():
            laws_by_var[v] = set(vd.get("laws", []) or [])

        vars_by_pheno = {}
        opt_vars_by_pheno = {}
        for p, lset in laws_by_pheno.items():
            vagg = set()
            voagg = set()
            for l in lset:
                vagg |= vars_by_law.get(l, set())
                voagg |= opt_vars_by_law.get(l, set())
            vars_by_pheno[p] = vagg
            opt_vars_by_pheno[p] = voagg

        # Accumulation-derived sets
        ac_vars = set(vars_by_pheno.get(ac, set())) if ac else set()
        ac_opt_vars = set(opt_vars_by_pheno.get(ac, set())) if ac else set()

        # FP vars influenced by AC vars
        fp_vars = set()
        if fp and ac_vars:
            ac_var_laws = set().union(*(laws_by_var.get(v, set()) for v in ac_vars)) if ac_vars else set()
            fp_law_set = set(laws_by_pheno.get(fp, set()))
            fp_laws_from_ac = ac_var_laws & fp_law_set
            if fp_laws_from_ac:
                fp_vars = set().union(*(vars_by_law.get(l, set()) for l in fp_laws_from_ac))

        # MT vars influenced by AC optional vars
        mt_vars = set()
        if mts and ac_opt_vars:
            ac_opt_var_laws = set().union(*(laws_by_var.get(v, set()) for v in ac_opt_vars))
            mt_law_set = set().union(*(laws_by_pheno.get(m, set()) for m in mts))
            mt_laws_from_ac_opt = ac_opt_var_laws & mt_law_set
            if mt_laws_from_ac_opt:
                mt_vars = set().union(*(vars_by_law.get(l, set()) for l in mt_laws_from_ac_opt))

        # ME vars influenced by MT vars
        me_vars = set()
        if mts and mes and mt_vars:
            mt_var_laws = set().union(*(laws_by_var.get(v, set()) for v in mt_vars))
            me_law_set = set().union(*(laws_by_pheno.get(m, set()) for m in mes))
            me_laws_from_mt = mt_var_laws & me_law_set
            if me_laws_from_mt:
                me_vars = set().union(*(vars_by_law.get(l, set()) for l in me_laws_from_mt))

        # Associated gas/solid vars via candidate MT laws
        assoc_gas_vars = set()
        assoc_sld_vars = set()
        if mts and ac_opt_vars:
            ac_opt_var_laws = set().union(*(laws_by_var.get(v, set()) for v in ac_opt_vars))
            mt_law_set = set().union(*(laws_by_pheno.get(m, set()) for m in mts))
            candidate_mt_laws = ac_opt_var_laws & mt_law_set
            if candidate_mt_laws:
                if gass:
                    for l in candidate_mt_laws:
                        agl = laws.get(l, {}).get("assoc_gas_law")
                        if agl and agl in vars_by_law:
                            assoc_gas_vars |= vars_by_law.get(agl, set())
                if slds:
                    for l in candidate_mt_laws:
                        asl = laws.get(l, {}).get("assoc_sld_law")
                        if asl and asl in vars_by_law:
                            assoc_sld_vars |= vars_by_law.get(asl, set())

        # Vars directly referenced by param_law
        param_law_vars = set()
        if param_law:
            chosen_laws = set(v for v in param_law.values() if v in vars_by_law)
            if chosen_laws:
                param_law_vars = set().union(*(vars_by_law.get(l, set()) for l in chosen_laws))

        # Reaction variable sets (base + 2-hop)
        rxn_var_dict = {rxn: set() for rxn in rxn_dict}
        for rxn, rxn_phenos in rxn_dict.items():
            base_vars = set().union(*(vars_by_pheno.get(p, set()) for p in rxn_phenos)) if rxn_phenos else set()
            neighbor_laws = set().union(*(laws_by_var.get(v, set()) for v in base_vars)) if base_vars else set()
            neighbor_vars = set().union(*(vars_by_law.get(l, set()) for l in neighbor_laws)) if neighbor_laws else set()
            rxn_var_dict[rxn] = base_vars | neighbor_vars
        
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

        # Precompute species lookups for containers to avoid repeated dict access
        stm_species = {stm: list(basic.get("stm", {}).get(stm, {}).get("spc", [])) for stm in stms}
        gas_species = {gas: list(basic.get("gas", {}).get(gas, {}).get("spc", [])) for gas in gass}
        sld_species = {sld: list(basic.get("sld", {}).get(sld, {}).get("spc", [])) for sld in slds}

        op_param = {}
        # Single pass over variables
        for desc_var in desc_vars:
            vinfo = vars[desc_var]
            if vinfo["laws"]:
                continue
            if vinfo["cls"] != "OperationParameter":
                continue

            dims_key = tuple(sorted(vinfo.get("dims", [])))
            if dims_key == ():
                op_param[(desc_var, None, None, None, None)] = None
            elif dims_key == ("Stream",):
                for stm in stms:
                    op_param[(desc_var, None, stm, None, None)] = None
            elif dims_key == ("Gas",):
                for gas in gass:
                    op_param[(desc_var, gas, None, None, None)] = None
            elif dims_key == ("Solid",):
                for sld in slds:
                    op_param[(desc_var, sld, None, None, None)] = None
            elif dims_key == ("Species", "Stream"):
                for stm in stms:
                    for spc in stm_species.get(stm, []):
                        op_param[(desc_var, None, stm, None, spc)] = None
            elif dims_key == ("Gas", "Species") or dims_key == ("Species", "Gas"):
                for gas in gass:
                    for spc in gas_species.get(gas, []):
                        op_param[(desc_var, gas, None, None, spc)] = None
            elif dims_key == ("Solid", "Species") or dims_key == ("Species", "Solid"):
                for sld in slds:
                    for spc in sld_species.get(sld, []):
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

        # Base ontology maps
        laws = self.h.query_law("mainpage")
        vars = self.h.query_var()

        # Build indices
        laws_by_pheno = {}
        vars_by_law = {}
        opt_vars_by_law = {}
        laws_by_var = {}
        for law, ld in laws.items():
            p = ld.get("pheno")
            if p:
                laws_by_pheno.setdefault(p, set()).add(law)
            vars_by_law[law] = set(ld.get("vars", []) or [])
            opt_vars_by_law[law] = set(ld.get("opt_vars", []) or [])
        for v, vd in vars.items():
            laws_by_var[v] = set(vd.get("laws", []) or [])

        vars_by_pheno = {}
        opt_vars_by_pheno = {}
        for p, lset in laws_by_pheno.items():
            vagg = set()
            voagg = set()
            for l in lset:
                vagg |= vars_by_law.get(l, set())
                voagg |= opt_vars_by_law.get(l, set())
            vars_by_pheno[p] = vagg
            opt_vars_by_pheno[p] = voagg

        # Accumulation-derived sets
        ac_vars = set(vars_by_pheno.get(ac, set())) if ac else set()
        ac_opt_vars = set(opt_vars_by_pheno.get(ac, set())) if ac else set()

        # FP vars influenced by AC vars
        fp_vars = set()
        if fp and ac_vars:
            ac_var_laws = set().union(*(laws_by_var.get(v, set()) for v in ac_vars))
            fp_laws_set = set(laws_by_pheno.get(fp, set()))
            fp_laws_from_ac = ac_var_laws & fp_laws_set
            if fp_laws_from_ac:
                fp_vars = set().union(*(vars_by_law.get(l, set()) for l in fp_laws_from_ac))

        # MT vars influenced by AC optional vars
        mt_vars = set()
        if mts and ac_opt_vars:
            ac_opt_var_laws = set().union(*(laws_by_var.get(v, set()) for v in ac_opt_vars))
            mt_laws_set = set().union(*(laws_by_pheno.get(m, set()) for m in mts))
            mt_laws_from_ac_opt = ac_opt_var_laws & mt_laws_set
            if mt_laws_from_ac_opt:
                mt_vars = set().union(*(vars_by_law.get(l, set()) for l in mt_laws_from_ac_opt))

        # ME vars influenced by MT vars
        me_vars = set()
        if mts and mes and mt_vars:
            mt_var_laws = set().union(*(laws_by_var.get(v, set()) for v in mt_vars))
            me_laws_set = set().union(*(laws_by_pheno.get(m, set()) for m in mes))
            me_laws_from_mt = mt_var_laws & me_laws_set
            if me_laws_from_mt:
                me_vars = set().union(*(vars_by_law.get(l, set()) for l in me_laws_from_mt))

        # Vars referenced directly by chosen parameter laws
        param_law_vars = set()
        if param_law:
            chosen = [l for l in param_law.values() if l in vars_by_law]
            if chosen:
                param_law_vars = set().union(*(vars_by_law.get(l, set()) for l in chosen))

        # Reaction variable neighborhoods
        rxn_var_dict = {rxn: set() for rxn in rxn_dict}
        for rxn, rxn_phenos in rxn_dict.items():
            base_vars = set().union(*(vars_by_pheno.get(p, set()) for p in rxn_phenos)) if rxn_phenos else set()
            neighbor_laws = set().union(*(laws_by_var.get(v, set()) for v in base_vars)) if base_vars else set()
            neighbor_vars = set().union(*(vars_by_law.get(l, set()) for l in neighbor_laws)) if neighbor_laws else set()
            rxn_var_dict[rxn] = base_vars | neighbor_vars
        
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
