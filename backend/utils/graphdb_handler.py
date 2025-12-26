import re
import pygraphdb
from .mml_expression import MMLExpression
from .phenomenon_service import PhenomenonService


class GraphdbHandler:
    """
    Class to handle connection with graphdb for querying and convert ontologies to dict.

    SPARQL template is used to query graphdb.
    """
    
    def __init__(self, config):
        self.host =                         config.GRAPHDB_HOST
        self.port =                         config.GRAPHDB_PORT
        self.user =                         config.GRAPHDB_USER
        self.password =                     config.GRAPHDB_PASSWORD
        self.db =                           config.GRAPHDB_DB

        # RDF prefix
        self.prefix =                       config.PREFIX

        # Ontology classes
        self.src_classes =                  config.DATA_SOURCE_CLASSES
        self.var_classes =                  config.MODEL_VARIABLE_CLASSES
        self.desc_classes =                 config.DESCRIPTOR_CLASSES
        self.pheno_classes =                config.PHENOMENON_CLASSES
        self.template_classes =             config.TEMPLATE_CLASSES

        self.conn = pygraphdb.connect(self.host, self.port, self.user, self.password, self.db)
        self.cur = self.conn.cursor()

        # Internal log for SPARQL queries executed by query_pheno
        # Access via get_pheno_sparql() after calling query_pheno()
        self._last_pheno_sparql = []

        # Phenomenon service (delegation for helper queries)
        self.pheno_service = PhenomenonService(self)

    def query(self, mode=None):
        """Queries GraphDB and returns model ontology in a dictionary.

        Args:
            mode: Parameter passed to `query_law` for formula format.

        Returns:
            dict: A dictionary of model ontology components.
        """
        return {
            "dim": self.query_dim(),
            "law": self.query_law(mode),
            "src": self.query_src(),
            "var": self.query_var(),
            # "desc": self.query_desc(),
            "unit": self.query_unit(),
            # "rule": self.query_rule(),
            "pheno": self.query_pheno(),
        }

    def query_dim(self):
        """Queries Dimensions from GraphDB.

        Returns:
            dict: A dictionary of Dimensions.
        """
        dim_dict = {}
        sparql = f"{self.prefix}select ?d where {{?d rdf:type ontomo:Dimension. }}"

        sparql_res = self.cur.execute(sparql)
        for res in sparql_res.split("\r\n")[1:-1]:
            dim = res.split("#")[1]
            dim_dict[dim] = {"cls": "Dimension"}
        dim_dict = dict(sorted(dim_dict.items(), key=lambda x: x[0]))
        return dim_dict

    def query_law(self, mode):
        """Queries Laws from GraphDB.

        Returns:
            dict: A dictionary of Laws.
        """
        law_dict = {}
        sparql = (
            f"{self.prefix}"
            "select ?l ?f ?v ?d ?r ?p ?ov ?dv ?ul ?iv ?mv ?agl ?asl ?fia where {"
            "?l rdf:type ontomo:Law. "
            "?l ontomo:hasFormula ?f. "
            "?l ontomo:hasModelVariable ?v. "
            "optional{{?l ontomo:hasDOI ?d. }}"
            "optional{{?l ontomo:hasRule ?r. }}"
            "optional{{?l ontomo:isAssociatedWith ?p. }}"
            "optional{{?l ontomo:hasOptionalModelVariable ?ov. }}"
            "optional{{?l ontomo:hasDifferentialModelVariable ?dv. }}"
            "optional{{?l ontomo:hasIntegralUpperLimit ?ul. }}"
            "optional{{?l ontomo:hasIntegralInitialValue ?iv. }}"
            "optional{{?l ontomo:hasIntegralModelVariable ?mv. }}"
            "optional{{?l ontomo:hasAssociatedGasLaw ?agl. }}"
            "optional{{?l ontomo:hasAssociatedSolidLaw ?asl. }}"
            "optional{{?l ontomo:hasFormulaIntegratedWithAccumulation ?fia. }}"
            "}"
        )
        sparql_res = self.cur.execute(sparql)
        for res in sparql_res.split("\r\n")[1:-1]:
            l, f, v, d, r, p, ov, dv, ul, iv, mv, agl, asl, fia = re.split(
                r",(?![a-zA-Z0]\<\/mtext\>)", res)
            l = l.split("#")[1]
            v = v.split("#")[1]
            p = p.split("#")[1] if p else None
            r = r.split("#")[1] if r else None
            ov = ov.split("#")[1] if ov else None
            dv = dv.split("#")[1] if dv else None
            ul = ul.split("#")[1] if ul else None
            iv = iv.split("#")[1] if iv else None
            mv = mv.split("#")[1] if mv else None
            agl = agl.split("#")[1] if agl else None
            asl = asl.split("#")[1] if asl else None
            if l not in law_dict:
                law_dict[l] = {
                    "cls": "Law",
                    "doi": None,
                    "fml": None,
                    "rule": None,
                    "pheno": None,
                    "diff_var": None,
                    "int_up_lim": None,
                    "int_init_val": None,
                    "int_var": None,
                    "assoc_gas_law": None,
                    "assoc_sld_law": None,
                    "fml_int_with_accum": None,
                    "vars": [],
                    "opt_vars": [],
                }
            f = re.sub(r'("*)"', r'\1', f[1:-1])
            f = re.sub(r" xmlns=[^\>]*", "", f)
            if mode == "sidebar":
                f = MMLExpression(f).to_sidebar_mml()
            if mode == "mainpage":
                f = MMLExpression(f).to_mainpage_mml()
            if fia:
                fia = re.sub(r'("*)"', r'\1', fia[1:-1])
                fia = re.sub(r" xmlns=[^\>]*", "", fia)
            law_dict[l]["fml"] = f
            if d:
                law_dict[l]["doi"] = d
            if r:
                law_dict[l]["rule"] = r
            if p:
                law_dict[l]["pheno"] = p
            if dv:
                law_dict[l]["diff_var"] = dv
            if ul:
                law_dict[l]["int_up_lim"] = ul
            if iv:
                law_dict[l]["int_init_val"] = iv
            if mv:
                law_dict[l]["int_var"] = mv
            if agl:
                law_dict[l]["assoc_gas_law"] = agl
            if asl:
                law_dict[l]["assoc_sld_law"] = asl
            if fia:
                law_dict[l]["fml_int_with_accum"] = fia
            if v not in law_dict[l]["vars"]:
                law_dict[l]["vars"].append(v)
            if ov and ov not in law_dict[l]["opt_vars"]:
                law_dict[l]["opt_vars"].append(ov)
        law_dict = dict(sorted(law_dict.items(), key=lambda x: x[0]))
        for l in law_dict:
            law_dict[l]["vars"] = sorted(law_dict[l]["vars"])
            law_dict[l]["opt_vars"] = sorted(law_dict[l]["opt_vars"])
        return law_dict

    def query_src(self):
        """Queries DataSources from GraphDB.

        Returns:
            dict: A dictionary of DataSources.
        """
        src_dict = {}
        for src_class in self.src_classes:
            sparql = (
                f"{self.prefix}"
                "select ?s ?url where {"
                f"?s rdf:type ontomo:{src_class}. "
                f"?s ontomo:hasURL ?url. "
                "}"
            )
            sparql_res = self.cur.execute(sparql)
            for res in sparql_res.split("\r\n")[1:-1]:
                s, url = re.split(r",(?![a-zA-Z0]\<\/mtext\>)", res)
                s = s.split("#")[1]
                src_dict[s] = {
                    "cls": src_class,
                    "url": url,
                }
        src_dict = dict(sorted(src_dict.items(), key=lambda x: x[0]))
        return src_dict

    def query_var(self):
        """Queries ModelVariables from GraphDB.

        Returns:
            dict: A dictionary of ModelVariables.
        """
        var_dict = {}
        for var_class in self.var_classes:
            sparql = (
                f"{self.prefix}"
                "select ?v ?s ?u ?d ?l ?val where {"
                f"?v rdf:type ontomo:{var_class}. "
                f"?v ontomo:hasSymbol ?s. "
                f"optional{{?v ontomo:hasValue ?val}}. "
                f"optional{{?v ontomo:hasUnit ?u}}. "
                f"optional{{?v ontomo:hasDimension ?d}}. "
                f"optional{{?v ontomo:hasLaw ?l}}. "
                "}"
            )
            sparql_res = self.cur.execute(sparql)
            for res in sparql_res.split("\r\n")[1:-1]:
                v, s, u, d, l, val = re.split(r",(?![a-zA-Z0]\<\/mtext\>)", res)
                v = v.split("#")[1]
                u = u.split("#")[1] if u else None
                d = d.split("#")[1] if d else None
                l = l.split("#")[1] if l else None
                s = re.sub(r'("*)"', r'\1', s[1:-1])
                s = re.sub(r" xmlns=[^\>]*", "", s)
                d = " ".join(d.split("_")[:-1]) if d else d
                val = float(val) if val else None
                if v not in var_dict:
                    var_dict[v] = {
                        "cls": var_class,
                        "sym": None,
                        "val": None,
                        "unit": None,
                        "dims": [],
                        "laws": [],
                    }
                var_dict[v]["sym"] = s
                if val:
                    var_dict[v]["val"] = val
                if u:
                    var_dict[v]["unit"] = u
                if d and d not in var_dict[v]["dims"]:
                    var_dict[v]["dims"].append(d)
                if l and l not in var_dict[v]["laws"]:
                    var_dict[v]["laws"].append(l)
        var_dict = dict(sorted(var_dict.items(), key=lambda x: x[0]))
        for v in var_dict:
            var_dict[v]["dims"] = sorted(var_dict[v]["dims"])
            var_dict[v]["laws"] = sorted(var_dict[v]["laws"])
        return var_dict

    def query_desc(self):
        """Queries Descriptors from GraphDB.

        Returns:
            dict: A dictionary of Descriptors.
        """
        desc_dict = {}
        for desc_class in self.desc_classes:
            sparql = (
                f"{self.prefix}"
                "select ?d ?s ?u where {"
                f"?d rdf:type ontomo:{desc_class}. "
                f"optional{{?d ontomo:hasSymbol ?s}}. "
                f"optional{{?d ontomo:hasUnit ?u}}. "
                "}"
            )
            sparql_res = self.cur.execute(sparql)
            for res in sparql_res.split("\r\n")[1:-1]:
                d, s, u = re.split(r",(?![a-zA-Z0]\<\/mtext\>)", res)
                d = d.split("#")[-1]
                u = u.split("#")[-1]
                s = re.sub(r'("*)"', r'\1', s[1:-1])
                s = re.sub(r" xmlns=[^\>]*", "", s)
                if d not in desc_dict:
                    desc_dict[d] = {
                        "cls": desc_class,
                        "sym": None,
                        "unit": None,
                    }
                if s:
                    desc_dict[d]["sym"] = s
                if u:
                    desc_dict[d]["unit"] = u
        desc_dict = dict(sorted(desc_dict.items(), key=lambda x: x[0]))
        return desc_dict

    def query_unit(self):
        """Queries Units from GraphDB.

        Returns:
            dict: A dictionary of Units.
        """
        unit_dict = {}
        sparql = (
            f"{self.prefix}"
            "select ?u ?s ?m ?r ?i where {"
            f"?u rdf:type ontomo:Unit. "
            f"optional{{?u ontomo:hasSymbol ?s}}. "
            f"optional{{?u ontomo:hasMetric ?m}}. "
            f"optional{{?u ontomo:hasRatio ?r}}. " \
            f"optional{{?u ontomo:hasIntercept ?i}}. " \
            "}"
        )
        sparql_res = self.cur.execute(sparql)
        for res in sparql_res.split("\r\n")[1:-1]:
            u, s, m, r, i = re.split(r",(?![a-zA-Z0]\<\/mtext\>)", res)
            u = u.split("#")[1]
            m = m.split("#")[1] if m else None
            s = re.sub(r'("*)"', r'\1', s[1:-1])
            s = re.sub(r" xmlns=[^\>]*", "", s)
            r = float(r) if r else None
            i = float(i) if i else None
            if u not in unit_dict:
                unit_dict[u] = {
                    "cls": "Unit",
                    "sym": None,
                    "metr": None,
                    "rto": None,
                    "intcpt": None,
                }
            unit_dict[u]["sym"] = s
            if m:
                unit_dict[u]["metr"] = m
            if r:
                unit_dict[u]["rto"] = r
            if i:
                unit_dict[u]["intcpt"] = i
        unit_dict = dict(sorted(unit_dict.items(), key=lambda x: x[0]))
        return unit_dict

    def query_rule(self):
        """Queries Rules from GraphDB.

        Returns:
            dict: A dictionary of Rules.
        """
        rule_dict = {}
        sparql = (
            f"{self.prefix}"
            "select ?r ?d ?p ?doi ?s where {"
            "?r rdf:type ontomo:Rule. "
            "?r ontomo:hasDescriptor ?d. "
            "?r ontomo:isAssociatedWith ?p. "
            "optional{?r ontomo:hasDOI ?doi}. "
            "?r ontomo:hasSPARQL ?s. "
            "}"
        )
        sparql_res = self.cur.execute(sparql)
        for res in sparql_res.split("\r\n")[1:-1]:
            r, d, p, doi = re.split(r",(?![a-zA-Z0]\<\/mtext\>)", res)[:4]
            r = r.split("#")[-1]
            d = d.split("#")[-1]
            p = p.split("#")[-1]
            doi = doi.split("#")[-1]
            s = ",".join(re.split(r",(?![a-zA-Z0]\<\/mtext\>)", res)[4:])[1:-1]
            if r not in rule_dict:
                rule_dict[r] = {
                    "doi": None,
                    "pheno": None,
                    "sparql": None,
                    "descs": [],
                }
            rule_dict[r]["pheno"] = p
            rule_dict[r]["sparql"] = s
            if doi:
                rule_dict[r]["doi"] = doi
            if d and d not in rule_dict[r]["descs"]:
                rule_dict[r]["descs"].append(d)
        rule_dict = dict(sorted(rule_dict.items(), key=lambda x: x[0]))
        for r in rule_dict:
            rule_dict[r]["descs"] = sorted(rule_dict[r]["descs"])
        return rule_dict

    def query_role(self):
        """Queries Roles from GraphDB.

        Returns:
            list: A list of species roles in reaction.
        """
        roles = []
        sparql = (
            f"{self.prefix}"
            "select ?r where {"
            "?r rdf:type ontomo:SpeciesRole. "
            "}"
        )
        sparql_res = self.cur.execute(sparql)
        for res in sparql_res.split("\r\n")[1:-1]:
            r = re.split(r",(?![a-zA-Z0]\<\/mtext\>)", res)[0]
            r = r.split("#")[-1]
            if r not in roles:
                roles.append(r)
        roles = sorted(roles)
        return roles

    def query_pheno(self):
        """Delegates to PhenomenonService.query_pheno"""
        return self.pheno_service.query_pheno()

    def query_ac(self):
        """Delegates to PhenomenonService.query_ac"""
        return self.pheno_service.query_ac()

    def query_fp_by_ac(self, ac):
        """Delegates to PhenomenonService.query_fp_by_ac"""
        return self.pheno_service.query_fp_by_ac(ac)

    def query_mt_by_fp(self, fp):
        """Delegates to PhenomenonService.query_mt_by_fp"""
        return self.pheno_service.query_mt_by_fp(fp)

    def query_me_by_mt(self, mt):
        """Delegates to PhenomenonService.query_me_by_mt"""
        return self.pheno_service.query_me_by_mt(mt)

    def query_param_law(self, desc):
        """Delegates to PhenomenonService.query_param_law"""
        return self.pheno_service.query_param_law(desc)

    def query_rxn(self):
        """Delegates to PhenomenonService.query_reactions"""
        return self.pheno_service.query_rxn()

    def query_info(self, context):
        """Delegates to PhenomenonService.query_info"""
        return self.pheno_service.query_info(context)

    def query_symbol(self, unit):
        return self.pheno_service.query_symbol(unit)

    def query_op_param(self, context=None):
        """Delegates to PhenomenonService.query_op_param"""
        return self.pheno_service.query_op_param(context)

    def query_cal_param(self, context=None):
        """Delegates to PhenomenonService.query_cal_param"""
        return self.pheno_service.query_cal_param(context)

    def query_context_template(self):
        """Queries context templates from GraphDB.

        Returns:
            dict: A dictionary of context templates.
        """
        context_template_dict = {}
        
        for t in self.template_classes:
            sparql = (
                f"{self.prefix}"
                "select ?c ?p ?ss ?os where {"
                f"?c rdf:type ontomo:{t}Context. "
                "optional{{?c ontomo:hasPhenomenon ?p. }}"
                "optional{{?c ontomo:hasStructureSection ?ss. }}"
                "optional{{?c ontomo:hasOperationSection ?os. }}"
                "}"
            )
            sparql_res = self.cur.execute(sparql)
            for res in sparql_res.split("\r\n")[1:-1]:
                c, p, ss, os  = re.split(r",(?![a-zA-Z0]\<\/mtext\>)", res)
                c = c.split("#")[-1].replace("_Context", "")
                t = t.split("#")[-1].replace("Context", "")
                p = p.split("#")[-1]
                ss = ss.split("#")[-1]
                os = os.split("#")[-1]
                if c not in context_template_dict:
                    context_template_dict[c] = {"type": t}
                if p:
                    context_template_dict[c]["accumulation"] = p
                if ss:
                    context_template_dict[c]["st"] = {}
                if os:
                    context_template_dict[c]["op"] = {}

        sparql = (
            f"{self.prefix}"
            "select ?c ?s ?d ?v ?lb ?ub ?o ?do ?u ?us where {"
            "?c rdf:type ontomo:Context. "
            "?s rdf:type ontomo:ContextSection. "
            "?c ontomo:hasStructureSection ?s. "
            "?d rdf:type ontomo:Descriptor. "
            "?s ontomo:hasDescriptor ?d. "
            "optional{{?d ontomo:hasDefaultValue ?v.}} "
            "optional{{?d ontomo:hasLowerBound ?lb.}} "
            "optional{{?d ontomo:hasUpperBound ?ub.}} "
            "optional{{?d ontomo:hasOption ?o.}} "
            "optional{{?d ontomo:hasDefaultOption ?do.}} "
            "optional{{?d ontomo:hasUnit ?u. ?u ontomo:hasSymbol ?us. filter(bound(?u) && bound(?us))}}"
            "}"
        )
        sparql_res = self.cur.execute(sparql)
        for res in sparql_res.split("\r\n")[1:-1]:
            c, s, d, v, lb, ub, o, do, u, us = re.split(r",(?![a-zA-Z0]\<\/mtext\>)", res)
            c = c.split("#")[-1].replace("_Context", "")
            s = s.split("#")[-1]
            d = d.split("#")[-1]
            v = v.split("#")[-1]
            lb = lb.split("#")[-1]
            ub = ub.split("#")[-1]
            o = o.split("#")[-1]
            do = do.split("#")[-1]
            u = u.split("#")[-1]
            if d not in context_template_dict[c]["st"]:
                context_template_dict[c]["st"][d] = {}
            if v:
                if v != "true":
                    context_template_dict[c]["st"][d]["type"] = "value"
                    context_template_dict[c]["st"][d]["default"] = float(v)
                else:
                    context_template_dict[c]["st"][d]["type"] = "bool"
                    context_template_dict[c]["st"][d]["default"] = True
            elif lb and ub:
                context_template_dict[c]["st"][d]["type"] = "range"
                context_template_dict[c]["st"][d]["lower_bound"] = float(lb)
                context_template_dict[c]["st"][d]["upper_bound"] = float(ub)
            elif o:
                context_template_dict[c]["st"][d]["type"] = "option"
                if "options" not in context_template_dict[c]["st"][d]:
                    context_template_dict[c]["st"][d]["options"] = [o]
                else:
                    context_template_dict[c]["st"][d]["options"].append(o)
            else:
                context_template_dict[c]["st"][d]["type"] = "value"
            if do:
                context_template_dict[c]["st"][d]["default_option"] = do
            if u:
                context_template_dict[c]["st"][d]["unit"] = u
            if us:
                us = re.sub(r'("*)"', r'\1', us[1:-1])
                us = re.sub(r" xmlns=[^\>]*", "", us)
                context_template_dict[c]["st"][d]["unit_symbol"] = us

        sparql = (
            f"{self.prefix}"
            "select ?c ?s ?d ?v ?lb ?ub ?o ?do ?u ?us where {"
            "?c rdf:type ontomo:Context. "
            "?s rdf:type ontomo:ContextSection. "
            "?c ontomo:hasOperationSection ?s. "
            "?d rdf:type ontomo:Descriptor. "
            "?s ontomo:hasDescriptor ?d. "
            "optional{{?d ontomo:hasDefaultValue ?v.}} "
            "optional{{?d ontomo:hasLowerBound ?lb.}} "
            "optional{{?d ontomo:hasUpperBound ?ub.}} "
            "optional{{?d ontomo:hasOption ?o.}} "
            "optional{{?d ontomo:hasDefaultOption ?do.}} "
            "optional{{?d ontomo:hasUnit ?u. ?u ontomo:hasSymbol ?us. filter(bound(?u) && bound(?us))}}"
            "}"
        )
        sparql_res = self.cur.execute(sparql)
        for res in sparql_res.split("\r\n")[1:-1]:
            c, s, d, v, lb, ub, o, do, u, us = re.split(r",(?![a-zA-Z0]\<\/mtext\>)", res)
            c = c.split("#")[-1].replace("_Context", "")
            s = s.split("#")[-1]
            d = d.split("#")[-1]
            v = v.split("#")[-1]
            lb = lb.split("#")[-1]
            ub = ub.split("#")[-1]
            o = o.split("#")[-1]
            do = do.split("#")[-1]
            u = u.split("#")[-1]
            if d not in context_template_dict[c]["op"]:
                context_template_dict[c]["op"][d] = {}
            if v:
                if v != "true":
                    context_template_dict[c]["op"][d]["type"] = "value"
                    context_template_dict[c]["op"][d]["default"] = float(v)
                else:
                    context_template_dict[c]["op"][d]["type"] = "bool"
                    context_template_dict[c]["op"][d]["default"] = True
            elif lb and ub:
                context_template_dict[c]["op"][d]["type"] = "range"
                context_template_dict[c]["op"][d]["lower_bound"] = float(lb)
                context_template_dict[c]["op"][d]["upper_bound"] = float(ub)
            elif o:
                context_template_dict[c]["op"][d]["type"] = "option"
                if "options" not in context_template_dict[c]["op"][d]:
                    context_template_dict[c]["op"][d]["options"] = [o]
                else:
                    context_template_dict[c]["op"][d]["options"].append(o)
            else:
                context_template_dict[c]["op"][d]["type"] = "value"
            if do:
                context_template_dict[c]["op"][d]["default_option"] = do
            if u:
                context_template_dict[c]["op"][d]["unit"] = u
            if us:
                us = re.sub(r'("*)"', r'\1', us[1:-1])
                us = re.sub(r" xmlns=[^\>]*", "", us)
                context_template_dict[c]["op"][d]["unit_symbol"] = us

        context_template_dict = dict(sorted(context_template_dict.items(), key=lambda x: x[0]))
        for c in context_template_dict:
            for s in context_template_dict[c]:
                if isinstance(context_template_dict[c][s], list):
                    context_template_dict[c][s] = sorted(context_template_dict[c][s])
                if isinstance(context_template_dict[c][s], dict):
                    context_template_dict[c][s] = dict(sorted(context_template_dict[c][s].items(), key=lambda x: x[0]))
        return context_template_dict

    def get_pheno_sparql(self):
        """Return the list of SPARQL queries executed by the last call to query_pheno().
        This allows users to copy/paste the exact queries into GraphDB Workbench.
        If query_pheno() has not been called yet, returns an empty list.
        """
        return list(getattr(self, "_last_pheno_sparql", []) or [])

    def close(self):
        self.conn.close()
