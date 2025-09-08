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

    def query_information(self, basic, desc):
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
        if not isinstance(basic, dict):
            basic = {}
        if not isinstance(desc, dict):
            desc = {}

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

        info = {}
        laws = self.h.query_law()
        vars = self.h.query_var()

        ac_vars, ac_opt_vars = [], []
        for law_dict in laws.values():
            if law_dict["pheno"] == ac:
                for var in law_dict["vars"]:
                    if var not in ac_vars:
                        ac_vars.append(var)
                for var in law_dict["opt_vars"]:
                    if var not in ac_opt_vars:
                        ac_opt_vars.append(var)
        
        fp_vars = []
        for law, law_dict in laws.items():
            if any([law in vars[var]["laws"] for var in ac_vars]):
                if law_dict["pheno"] == fp:
                    for var in law_dict["vars"]:
                        if var not in fp_vars:
                            fp_vars.append(var)
        
        mt_vars = []
        for law, law_dict in laws.items():
            if any([law in vars[var]["laws"] for var in ac_opt_vars]):
                if law_dict["pheno"] in mts:
                    for var in law_dict["vars"]:
                        if var not in mt_vars:
                            mt_vars.append(var)

        me_vars = []
        for law, law_dict in laws.items():
            if any([law in vars[var]["laws"] for var in mt_vars]):
                if law_dict["pheno"] in mes:
                    for var in law_dict["vars"]:
                        if var not in me_vars:
                            me_vars.append(var)
        # TODO
        # for law in param_law.values():

        # def _norm_list(v):
        #     if v is None:
        #         return []
        #     if isinstance(v, (list, tuple)):
        #         items = v
        #     else:
        #         items = [v]
        #     out = []
        #     for x in items:
        #         if x is None:
        #             continue
        #         s = str(x).strip()
        #         if s:
        #             out.append(s)
        #     return out

        # param_law_input = filters.get("param_law")
        # param_law_map = {}
        # if isinstance(param_law_input, dict):
        #     param_law_map = {str(k): str(v) for k, v in param_law_input.items() if k and v}
        # elif param_law_input is not None:
        #     law_names = set(_norm_list(param_law_input))
        #     if law_names:
        #         entity = self.h.query()
        #         for var, meta in (entity.get("var", {}) or {}).items():
        #             laws = set(meta.get("laws", []) or [])
        #             inter = laws & law_names
        #             if inter:
        #                 chosen = sorted(list(inter))[0]
        #                 param_law_map[var] = chosen
        #     else:
        #         param_law_map = {}
        # else:
        #     param_law_map = self.query_param_law(pheno_filters) or {}

        # rxn_input = filters.get("rxn")
        # rxn_laws = {}
        # if isinstance(rxn_input, dict):
        #     for r, laws in rxn_input.items():
        #         rxn_laws[str(r)] = _norm_list(laws)
        # elif rxn_input is not None:
        #     requested_rxns = set(_norm_list(rxn_input))
        #     if requested_rxns:
        #         all_map = self.query_rxns({**pheno_filters, "param_law": param_law_map or filters.get("param_law")}) or {}
        #         rxn_laws = {r: laws for r, laws in all_map.items() if r in requested_rxns}
        # else:
        #     rxn_laws = self.query_rxns({**pheno_filters, "param_law": param_law_map or filters.get("param_law")}) or {}

        # entity = self.h.query()
        # vars_meta = entity.get("var", {}) or {}

        # info = {}

        # st = {}
        # for var, meta in vars_meta.items():
        #     if meta.get("class") == "ReactorParameter" and meta.get("val") is not None:
        #         st[var] = meta.get("val")
        # if st:
        #     info["st"] = st

        # mt_info = {}
        # selected_params = set(param_law_map.keys()) if param_law_map else set(
        #     [v for v, m in vars_meta.items() if m.get("class") == "MassTransportParameter"]
        # )
        # for var in sorted(selected_params):
        #     meta = vars_meta.get(var)
        #     if not meta:
        #         continue
        #     if meta.get("class") != "MassTransportParameter":
        #         continue
        #     val = meta.get("val")
        #     if val is not None:
        #         mt_info[var] = val
        # if mt_info:
        #     info["mt"] = mt_info

        # rxn_info = {}
        # for rxn, laws in sorted((rxn_laws or {}).items(), key=lambda x: x[0]):
        #     details = {}
        #     law_set = set(laws or [])
        #     for var, meta in vars_meta.items():
        #         if meta.get("class") != "ReactionParameter":
        #             continue
        #         dims = meta.get("dims") or []
        #         if set(dims) != {"Reaction"}:
        #             continue
        #         v_laws = set(meta.get("laws", []) or [])
        #         if law_set and not (v_laws & law_set):
        #             continue
        #         val = meta.get("val")
        #         if val is not None:
        #             details[var] = val
        #     rxn_info[rxn] = details
        # if rxn_info:
        #     info["rxn"] = rxn_info

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
