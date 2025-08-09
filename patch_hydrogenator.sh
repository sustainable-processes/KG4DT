python utils/patch_rdf.py --in_rdf ontology/OntoMo.owl --out_rdf ontology/OntoMo1.owl --json ontology/json/Gas_Dissolution_Saturate_Concentration_Law_with_Gas-Liquid_Mass_Transfer.json
python utils/patch_rdf.py --in_rdf ontology/OntoMo1.owl --out_rdf ontology/OntoMo2.owl --json ontology/json/Gas-Liquid_Volumetric_Mass_Transfer_Rate_Law_with_Gas-Liquid_Mass_Transfer.json
python utils/patch_rdf.py --in_rdf ontology/OntoMo2.owl --out_rdf ontology/OntoMo3.owl --json ontology/json/Solid_Dissolution_Saturate_Concentration_Law_with_Solid-Liquid_Mass_Transfer.json
python utils/patch_rdf.py --in_rdf ontology/OntoMo3.owl --out_rdf ontology/OntoMo4.owl --json ontology/json/Solid-Liquid_Volumetric_Mass_Transfer_Rate_Law_with_Solid-Liquid_Mass_Transfer.json
