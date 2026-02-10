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


    def get_compound(self, item):
        search_item = re.sub(r"<[^<>]*>", "", item)
        compounds = []
        try:
            compounds.extend(pcp.get_compounds(search_item, namespace="formula"))
        except:
            try:
                compounds.extend(pcp.get_compounds(search_item, namespace="name"))
            except:
                pass

        if compounds:
            return compounds[0]
        else:
            return "-"


    def query_rmg(self, solution):
        pool = ThreadPool(8)
        solv_compounds = pool.map(self.get_compound, solution["solvents"])
        solu_compounds = pool.map(self.get_compound, solution["solutes"])
        pool.close()
        solv_smis = [compound.connectivity_smiles if isinstance(compound, pcp.Compound) else "-" for compound in solv_compounds]
        solu_smis = [compound.connectivity_smiles if isinstance(compound, pcp.Compound) else "-" for compound in solu_compounds]
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
        soup = BeautifulSoup(requests.get(url).text, features="lxml")
        solubility = [tr.find_all("td")[11].text for tr in soup.find_all("tr")[1:]]
        solubility = [
            [
                str(round(10 ** float(solubility[i * len(solu_compounds) + j]), 3)) if solubility[i * len(solu_compounds) + j] != "-" else "-"
                for j in range(len(solu_compounds))
            ] for i in range(len(solv_compounds))
        ]
        solute_solubility = {"value": solubility, "reference": url}
        return solute_solubility