import numpy as np


class SolventMiscibilityAgent():
    """Solvent miscibility agent for determining miscibility by table data, including
    - Sigma Aldrich: https://www.sigmaaldrich.com/GB/en/technical-documents/technical-article/analytical-chemistry/purification/solvent-miscibility-table
    """

    def __init__(self, entity, solvent_miscibility_table_path):
        self.entity = entity or {}
        # Normalize data source lookup
        self._sources = self.entity.get("data_source") or self.entity.get("src") or {}
        with open(solvent_miscibility_table_path) as f:
            self.solvents = [solvent.lower() for solvent in f.readline().split(",")[1:]]
        self.solvent_miscibility_table = np.loadtxt(solvent_miscibility_table_path, delimiter=",", skiprows=1, usecols=range(1, len(self.solvents)+1), dtype=np.int32)

    def _sigma_url(self):
        entry = self._sources.get("SigmaAldrich") or self._sources.get("sigmaaldrich")
        return (entry or {}).get("url") or "https://www.sigmaaldrich.com/GB/en/technical-documents/technical-article/analytical-chemistry/purification/solvent-miscibility-table"

    def query_sigmaaldrich(self, solvents):
        solvents = [solvent.lower() for solvent in solvents]
        if len(solvents) == 1:
            return [f"Chemical process with only single solvent: {solvents[0]}", ""]
        if len(solvents) > 2:
            return [f"Unknown miscibility on {len(solvents)} solvents: {', '.join(solvents)}", ""]
        if solvents[0] not in self.solvents or solvents[1] not in self.solvents:
            return [f"Unknown miscibility: {', '.join(solvents)}", ""]
        else:
            url = self._sigma_url()
            if self.solvent_miscibility_table[self.solvents.index(solvents[0])][self.solvents.index(solvents[1])] == 1:
                return [f"Miscible: {', '.join(solvents)}", url]
            else:
                return [f"Immiscible: {', '.join(solvents)}", url]
