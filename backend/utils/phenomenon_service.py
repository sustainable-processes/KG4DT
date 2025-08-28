import re as _re

class PhenomenonService:
    """
    Encapsulates phenomenon-related query helpers for GraphDB.

    This service is composed into GraphdbHandler and uses its cursor/prefix/query API.
    """

    def __init__(self, handler):
        # handler is expected to provide: cur, prefix, query(), and optionally _last_pheno_sparql
        self.h = handler

    def query_phenomenon_ac(self, ac):
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

        flow_patterns = set()
        for res in sparql_res.split("\r\n")[1:-1]:
            try:
                _, flow_pattern = res.split(",")
            except ValueError:
                parts = res.split(",")
                flow_pattern = parts[1] if len(parts) > 1 else ""
            flow_pattern = flow_pattern.split("#")[-1]
            if flow_pattern:
                flow_patterns.add(flow_pattern)

        return sorted(flow_patterns)

    def query_mass_transfer_by_flow_pattern(self, fp):
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

    def query_mass_equilibrium_by_mass_transfer(self, mt):
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
            "select ?mtp ?eq where {" \
            f"?mtp rdf:type ontomo:MolecularTransportPhenomenon. " \
            f"FILTER(regex(str(?mtp), '#{mt_str}$', 'i')). " \
            f"?d rdf:type ontomo:Law. " \
            f"?d ontomo:isAssociatedWith ?mtp. " \
            f"?d ontomo:isAssociatedWith ?eq. " \
            f"?eq rdf:type ontomo:PhysicalEquilibriumPhenomenon. " \
            "}"

        try:
            sparql_res = self.h.cur.execute(sparql)
        except Exception:
            return []

        equilibria = set()
        for res in sparql_res.split("\r\n")[1:-1]:
            parts = res.split(",")
            eq_iri = parts[1] if len(parts) > 1 else ""
            eq_name = eq_iri.split("#")[-1]
            if eq_name:
                equilibria.add(eq_name)

        return sorted(equilibria)

    def query_param_law(self, filters):
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
            esc = [_re.escape(n) for n in names]
            return "|".join(esc)

        if ac_list:
            p = _regex_union(ac_list)
            union_blocks.append(
                "{"
                f"?d ontomo:isAssociatedWith ?phen_ac. "
                f"?phen_ac rdf:type ontomo:Accumulation. "
                f"FILTER(regex(str(?phen_ac), '#({p})$', 'i')). "
                "}"
            )
        if fp_list:
            p = _regex_union(fp_list)
            union_blocks.append(
                "{"
                f"?d ontomo:isAssociatedWith ?phen_fp. "
                f"?phen_fp rdf:type ontomo:FlowPattern. "
                f"FILTER(regex(str(?phen_fp), '#({p})$', 'i')). "
                "}"
            )
        if mt_list:
            p = _regex_union(mt_list)
            union_blocks.append(
                "{"
                f"?d ontomo:isAssociatedWith ?phen_mt. "
                f"?phen_mt rdf:type ontomo:MolecularTransportPhenomenon. "
                f"FILTER(regex(str(?phen_mt), '#({p})$', 'i')). "
                "}"
            )
        if me_list:
            p = _regex_union(me_list)
            union_blocks.append(
                "{"
                f"?d ontomo:isAssociatedWith ?phen_me. "
                f"?phen_me rdf:type ontomo:PhysicalEquilibriumPhenomenon. "
                f"FILTER(regex(str(?phen_me), '#({p})$', 'i')). "
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

    def query_reactions(self, filters=None):
        """
        Retrieve reactions and their associated kinetic law names.
        filters: optional dict with keys 'ac', 'fp', 'mt', 'me' (string or list) to constrain Laws via isAssociatedWith,
                 and optional 'param_law' to constrain by specific law name(s).
        - filters['param_law'] may be:
            - dict { parameter_name: law_name }
            - list [law_name, ...]
            - string law_name
        Returns: dict { reaction_local_name: [law_name, ...] }
        """
        if filters is None:
            filters = {}
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

        law_list = []
        pl = filters.get("param_law")
        if isinstance(pl, dict):
            law_list = _norm(list(pl.values()))
        elif isinstance(pl, (list, tuple)):
            law_list = _norm(list(pl))
        elif pl is not None:
            law_list = _norm(pl)

        union_blocks = []

        def _regex_union(names):
            esc = [_re.escape(n) for n in names]
            return "|".join(esc)

        if ac_list:
            p = _regex_union(ac_list)
            union_blocks.append(
                "{"
                f"?d ontomo:isAssociatedWith ?phen_ac. "
                f"?phen_ac rdf:type ontomo:Accumulation. "
                f"FILTER(regex(str(?phen_ac), '#({p})$', 'i')). "
                "}"
            )
        if fp_list:
            p = _regex_union(fp_list)
            union_blocks.append(
                "{"
                f"?d ontomo:isAssociatedWith ?phen_fp. "
                f"?phen_fp rdf:type ontomo:FlowPattern. "
                f"FILTER(regex(str(?phen_fp), '#({p})$', 'i')). "
                "}"
            )
        if mt_list:
            p = _regex_union(mt_list)
            union_blocks.append(
                "{"
                f"?d ontomo:isAssociatedWith ?phen_mt. "
                f"?phen_mt rdf:type ontomo:MolecularTransportPhenomenon. "
                f"FILTER(regex(str(?phen_mt), '#({p})$', 'i')). "
                "}"
            )
        if me_list:
            p = _regex_union(me_list)
            union_blocks.append(
                "{"
                f"?d ontomo:isAssociatedWith ?phen_me. "
                f"?phen_me rdf:type ontomo:PhysicalEquilibriumPhenomenon. "
                f"FILTER(regex(str(?phen_me), '#({p})$', 'i')). "
                "}"
            )

        sparql = self.h.prefix + \
            "select ?rxn ?d where {" \
            f"?rxn rdf:type ontomo:ChemicalReactionPhenomenon. " \
            f"?d rdf:type ontomo:Law. " \
            f"?d ontomo:isAssociatedWith ?rxn. "

        if union_blocks:
            sparql += "(" + " UNION ".join(union_blocks) + ") . "

        if law_list:
            p = _regex_union(law_list)
            sparql += f"FILTER(regex(str(?d), '#({p})$', 'i')). "

        sparql += "}"

        try:
            sparql_res = self.h.cur.execute(sparql)
        except Exception:
            return {}

        mapping = {}
        for line in sparql_res.split("\r\n")[1:-1]:
            parts = line.split(",")
            if len(parts) < 2:
                continue
            rxn_iri, law_iri = parts[0], parts[1]
            rxn_name = rxn_iri.split("#")[-1]
            law_name = law_iri.split("#")[-1]
            if not rxn_name or not law_name:
                continue
            laws = mapping.setdefault(rxn_name, set())
            laws.add(law_name)

        return {k: sorted(list(v)) for k, v in sorted(mapping.items(), key=lambda x: x[0])}

    def query_accumulators(self):
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
        result = set()
        for line in sparql_res.split("\r\n")[1:-1]:
            try:
                _, name = line.split("#")
            except ValueError:
                parts = line.split("#")
                name = parts[-1] if parts else ""
            name = name.strip()
            if name:
                result.add(name)
        return sorted(result)

    def query_information(self, filters):
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
        if not isinstance(filters, dict):
            filters = {}

        def _norm_list(v):
            if v is None:
                return []
            if isinstance(v, (list, tuple)):
                items = v
            else:
                items = [v]
            out = []
            for x in items:
                if x is None:
                    continue
                s = str(x).strip()
                if s:
                    out.append(s)
            return out

        phen_filters = {}
        for k in ("ac", "fp", "mt", "me"):
            if k in filters and filters[k] is not None:
                phen_filters[k] = filters[k]

        param_law_input = filters.get("param_law")
        param_law_map = {}
        if isinstance(param_law_input, dict):
            param_law_map = {str(k): str(v) for k, v in param_law_input.items() if k and v}
        elif param_law_input is not None:
            law_names = set(_norm_list(param_law_input))
            if law_names:
                entity = self.h.query()
                for var, meta in (entity.get("var", {}) or {}).items():
                    laws = set(meta.get("laws", []) or [])
                    inter = laws & law_names
                    if inter:
                        chosen = sorted(list(inter))[0]
                        param_law_map[var] = chosen
            else:
                param_law_map = {}
        else:
            param_law_map = self.query_param_law(phen_filters) or {}

        rxn_input = filters.get("rxn")
        rxn_laws = {}
        if isinstance(rxn_input, dict):
            for r, laws in rxn_input.items():
                rxn_laws[str(r)] = _norm_list(laws)
        elif rxn_input is not None:
            requested_rxns = set(_norm_list(rxn_input))
            if requested_rxns:
                all_map = self.query_reactions({**phen_filters, "param_law": param_law_map or filters.get("param_law")}) or {}
                rxn_laws = {r: laws for r, laws in all_map.items() if r in requested_rxns}
        else:
            rxn_laws = self.query_reactions({**phen_filters, "param_law": param_law_map or filters.get("param_law")}) or {}

        entity = self.h.query()
        vars_meta = entity.get("var", {}) or {}

        info = {}

        st = {}
        for var, meta in vars_meta.items():
            if meta.get("class") == "ReactorParameter" and meta.get("val") is not None:
                st[var] = meta.get("val")
        if st:
            info["st"] = st

        mt_info = {}
        selected_params = set(param_law_map.keys()) if param_law_map else set(
            [v for v, m in vars_meta.items() if m.get("class") == "MolecularTransportParameter"]
        )
        for var in sorted(selected_params):
            meta = vars_meta.get(var)
            if not meta:
                continue
            if meta.get("class") != "MolecularTransportParameter":
                continue
            val = meta.get("val")
            if val is not None:
                mt_info[var] = val
        if mt_info:
            info["mt"] = mt_info

        rxn_info = {}
        for rxn, laws in sorted((rxn_laws or {}).items(), key=lambda x: x[0]):
            details = {}
            law_set = set(laws or [])
            for var, meta in vars_meta.items():
                if meta.get("class") != "ReactionParameter":
                    continue
                dims = meta.get("dims") or []
                if set(dims) != {"Reaction"}:
                    continue
                v_laws = set(meta.get("laws", []) or [])
                if law_set and not (v_laws & law_set):
                    continue
                val = meta.get("val")
                if val is not None:
                    details[var] = val
            rxn_info[rxn] = details
        if rxn_info:
            info["rxn"] = rxn_info

        return info

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
            f"FILTER(regex(str(?u), '#{_re.escape(unit_str)}$', 'i')). " \
            "}"

        try:
            sparql_res = self.h.cur.execute(sparql)
        except Exception:
            return None

        # Expect CSV-like lines with header, then rows: u,s
        for res in sparql_res.split("\r\n")[1:-1]:
            parts = _re.split(r",(?![a-zA-Z0]\<\/mtext\>)", res)
            if not parts:
                continue
            s = parts[1] if len(parts) > 1 else None
            if not s:
                # No symbol bound for this row
                continue
            # Clean quotes and xmlns just like query_unit does
            try:
                s_clean = _re.sub(r'("*)"', r'\1', s[1:-1])
                s_clean = _re.sub(r" xmlns=[^\>]*", "", s_clean)
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
            esc = [_re.escape(n) for n in names]
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
