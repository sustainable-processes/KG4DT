import re

import pubchempy as pcp
import requests
from bs4 import BeautifulSoup


class PhysicalPropertyAgent():
    """Physical property agent for querying information from public databases by API, including
    - PubChem: https://pubchem.ncbi.nlm.nih.gov
    - ChemSpider: http://www.chemspider.com
    - Wikipedia: https://en.wikipedia.org
    """

    def __init__(self, entity):
        self.entity = entity
        self.pubchem_url = entity["data_source"]["PubChem"]["url"]
        self.chemspider_search_url = entity["data_source"]["ChemSpider"]["url"].split("|")[1]
        self.chemspider_url = entity["data_source"]["ChemSpider"]["url"].split("|")[0]
        self.wikipedia_url = entity["data_source"]["Wikipedia"]["url"]
    

    def query_pubchem(self, names, properties):
        property_res = {name: {} for name in names}
        for name in names:
            compound = pcp.get_compounds(name, namespace="name")
            if not compound: continue
            compound = compound[0]
            property_res[name]["canonical_smiles"] = compound.canonical_smiles
            property_res[name]["property"] = {}
            for property in properties:
                pubchem_url = self.pubchem_url.replace("{cid}", str(compound.cid)).replace("{property}", property)
                pubchem_res = requests.get(pubchem_url).json()["Record"]["Section"][0]["Section"][0]["Section"][0]
                property_res[name]["property"][property] = [{
                    "reference": res["Reference"][0],
                    "value": res["Value"]["StringWithMarkup"][0]["String"].replace(r"\u00b0", "&deg;"),
                } for res in pubchem_res["Information"] 
                if "Reference" in res and "Value" in res and "StringWithMarkup" in res["Value"] and "Markup" not in res["Value"]["StringWithMarkup"][0]]
        return property_res
    

    def query_chemspider(self, names, properties):
        property_res = {name: {} for name in names}
        for name in names:
            compound = pcp.get_compounds(name, namespace="name")
            if not compound: continue
            compound = compound[0]
            property_res[name]["canonical_smiles"] = compound.canonical_smiles
            property_res[name]["property"] = {}
            chemspider_id = requests.get(
                self.chemspider_search_url.replace("{name}", name), 
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            ).json()["Records"][0]["ChemSpiderId"]
            for property in properties:
                chemspider_res = requests.get(
                    self.chemspider_url.replace("{cid}", str(chemspider_id)), 
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                ).json()
                datasource_names = []
                property_res[name]["property"][property] = []
                for res in chemspider_res[property + "Properties"]:
                    if "DatasourceName" in res and "ExternalUrl" in res and "LowValue" in res and "Unit" in res and \
                        res["DatasourceName"] in ["Sigma-Aldrich"] and res["DatasourceName"] not in datasource_names:
                        property_res[name]["property"][property].append({
                            "reference": res["DatasourceName"] + " " + res["ExternalUrl"],
                            "value": str(res["LowValue"]) + " " + res["Unit"],
                        })
                        datasource_names.append(res["DatasourceName"])
        return property_res
    

    def query_wikipedia(self, names, properties):
        property_res = {name: {} for name in names}
        for name in names:
            compound = pcp.get_compounds(name, namespace="name")
            if not compound: continue
            compound = compound[0]
            property_res[name]["canonical_smiles"] = compound.canonical_smiles
            property_res[name]["property"] = {}
            soup = BeautifulSoup(requests.get(self.wikipedia_url.replace("{name}", name)).text, features="lxml")
            trs = [tr for tr in soup.find_all("tr") if len(tr.find_all("td", recursive=False)) == 2]
            wikipedia_res = {}
            for tr in trs:
                parameter_dict = []
                if tr.select("td")[1].find("ul"):
                    for li in tr.select("td")[1].find_all("li")[:3]:
                        if ":" in li.text: continue
                        value = repr(li).strip().replace("\xa0", " ")
                        for sup in li.findChildren("sup" , recursive=False):
                            if sup.find("a"):
                                value = value.replace(repr(sup), "")
                        value = re.sub(r"<li[^<>]*>", "", value)
                        value = re.sub(r"</li>", "", value)
                        value = re.sub(r"<span[^<>]*>", "", value)
                        value = re.sub(r"</span>", "", value)
                        value = re.sub(r"<a[^<>]*>", "", value)
                        value = re.sub(r"</a>", "", value)
                        value = re.sub(r"<sup[^<>]*>[ \n]*</sup>", "", value)
                        value = value.strip()
                        if li.find("a"):
                            if li.find("a").attrs["href"].startswith("/"):
                                reference = ""
                            elif li.find("a").attrs["href"].startswith("#"):
                                reference = soup.find(id=li.find("a").attrs["href"][1:]).select("span")[1].text
                            else:
                                reference = li.find("a").attrs["href"]
                        else:
                            reference = ""
                        parameter_dict.append({"value": value, "reference": reference})
                else:
                    value = repr(tr.select("td")[1]).strip().replace("\xa0", " ")
                    for sup in tr.select("td")[1].findChildren("sup" , recursive=False):
                        if sup.find("a"):
                            value = value.replace(repr(sup), "")
                    value = re.sub(r"<td[^<>]*>", "", value)
                    value = re.sub(r"</td>", "", value)
                    value = re.sub(r"<span[^<>]*>", "", value)
                    value = re.sub(r"</span>", "", value)
                    value = re.sub(r"<a[^<>]*>", "", value)
                    value = re.sub(r"</a>", "", value)
                    value = re.sub(r"<sup[^<>]*>[ \n]*</sup>", "", value)
                    value = value.strip()
                    if tr.select("td")[1].find("a"):
                        if tr.select("td")[1].find("a").attrs["href"].startswith("/"):
                            reference = ""
                        elif tr.select("td")[1].find("a").attrs["href"].startswith("#"):
                            reference = soup.find(id=tr.select("td")[1].find("a").attrs["href"][1:]).select("span")[1].text
                        else:
                            reference = tr.select("td")[1].find("a").attrs["href"]
                    else:
                        reference = ""
                    parameter_dict.append({"value": value, "reference": reference})
                wikipedia_res[tr.select("td")[0].text.strip().replace("\xa0", " ")] = parameter_dict
            for property in properties:
                if property in wikipedia_res:
                    property_res[name]["property"][property] = wikipedia_res[property]
        return property_res
