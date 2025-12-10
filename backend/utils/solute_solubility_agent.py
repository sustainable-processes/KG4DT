import pubchempy as pcp
import requests
from bs4 import BeautifulSoup
import re
from multiprocessing.pool import ThreadPool


class SoluteSolubilityAgent():
    """Agent for predicting solute solubility of species in chemical processes.
    - RMG-py: https://rmg.mit.edu/database/solvation/searchSolubility
    """
    
    def __init__(self, entity):
        self.entity = entity
        self.rmg_url = "https://rmg.mit.edu/database/solvation/searchSolubility/" \
            "solv={solv}__solu={solu}__T={temperature}__refSolv={ref_solv}__refS={ref_s}__refT={ref_t}__Hsub={h_sub}__Cpg={c_pg}__Cps={c_ps}"
        # In-memory cache for PubChem lookups; reuse a single HTTP session
        self._compound_cache = {}
        self._session = requests.Session()
        self._timeout = (5, 20)  # (connect, read) seconds


    def get_compound(self, item):
        # Normalize and cache to avoid repeated PubChem queries
        search_item = re.sub(r"<[^<>]*>", "", str(item or "")).strip()
        key = search_item.lower()
        if not key:
            return "-"
        if key in self._compound_cache:
            return self._compound_cache[key]

        compounds = []
        try:
            compounds.extend(pcp.get_compounds(search_item, namespace="formula"))
        except Exception:
            try:
                compounds.extend(pcp.get_compounds(search_item, namespace="name"))
            except Exception:
                compounds = []

        res = compounds[0] if compounds else "-"
        self._compound_cache[key] = res
        return res


    def query_rmg(self, solution):
        pool = ThreadPool(8)
        solv_compounds = pool.map(self.get_compound, solution["solvents"])
        solu_compounds = pool.map(self.get_compound, solution["solutes"])
        pool.close()
        solv_smis = [compound.canonical_smiles if isinstance(compound, pcp.Compound) else "-" for compound in solv_compounds]
        solu_smis = [compound.canonical_smiles if isinstance(compound, pcp.Compound) else "-" for compound in solu_compounds]
        if "temperature" not in solution:
            temperature = 298
        else:
            temperature = solution["temperature"]
        solv_span = "_".join(["_".join([solv_smi] * len(solu_compounds)) for solv_smi in solv_smis])
        solu_span = "_".join(["_".join(solu_smis)] * len(solv_compounds))
        temperature_span = "_".join([str(temperature)] * (len(solu_compounds) * len(solv_compounds)))
        none_span = "_".join(["None"] * (len(solu_compounds) * len(solv_compounds)))
        url = self.rmg_url.replace("{solv}", solv_span).replace("{solu}", solu_span).replace("{temperature}", temperature_span) \
            .replace("{ref_solv}", none_span).replace("{ref_s}", none_span).replace("{ref_t}", none_span) \
            .replace("{h_sub}", none_span).replace("{c_pg}", none_span).replace("{c_ps}", none_span) \
            .replace("#", "%23")
        print(url)
        resp = self._session.get(url, timeout=self._timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, features="lxml")
        solubility = [tr.find_all("td")[11].text for tr in soup.find_all("tr")[1:]]
        solubility = [
            [
                str(round(10 ** float(solubility[i * len(solu_compounds) + j]), 3)) if solubility[i * len(solu_compounds) + j] != "-" else "-"
                for j in range(len(solu_compounds))
            ] for i in range(len(solv_compounds))
        ]
        solute_solubility = {"value": solubility, "reference": url}
        return solute_solubility