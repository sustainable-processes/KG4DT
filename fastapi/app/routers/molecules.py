from __future__ import annotations

import logging
from urllib.parse import quote
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/molecule", tags=["molecules"])
_rdkit_logging_disabled = False


class ResolveRequest(BaseModel):
    """Request to resolve a chemical identifier to SMILES."""

    identifier: str = Field(
        ...,
        description="Chemical identifier (SMILES or InChI).",
    )
    preset: Optional[str] = Field(
        None,
        description="Reserved for compatibility; ignored by local resolver.",
    )


class ResolveResponse(BaseModel):
    """Response with resolved SMILES and properties."""

    resolved: bool
    smiles: Optional[str] = None
    source: str  # smiles, inchi, not_found, empty, error
    canonical_smiles: Optional[str] = None
    molecular_formula: Optional[str] = None
    molecular_weight: Optional[float] = None
    error: Optional[str] = None


@router.post("/resolve", response_model=ResolveResponse)
async def resolve_chemical(request: ResolveRequest) -> ResolveResponse:
    """Resolve a chemical identifier to SMILES via RDKit + PubChem fallback."""
    try:
        from rdkit import Chem, RDLogger
        from rdkit.Chem import Descriptors, rdMolDescriptors

        global _rdkit_logging_disabled
        if not _rdkit_logging_disabled:
            # Suppress RDKit SMILES parse errors when we intentionally try fallbacks.
            RDLogger.DisableLog("rdApp.error")
            _rdkit_logging_disabled = True

        identifier = request.identifier.strip() if request.identifier else ""
        if not identifier:
            return ResolveResponse(
                resolved=False,
                source="empty",
                error="Identifier is empty",
            )

        mol = Chem.MolFromSmiles(identifier)
        source = "smiles"

        if mol is None and identifier.startswith("InChI="):
            source = "inchi"
            try:
                from rdkit.Chem import inchi
                mol = inchi.MolFromInchi(identifier, sanitize=True)
            except Exception:
                mol = None

        if mol is None:
            mol, source = _resolve_via_cactus(identifier)

        if mol is None:
            mol, source = _resolve_via_pubchem(identifier)

        if mol is None:
            return ResolveResponse(
                resolved=False,
                source=source or "not_found",
                error=f"Could not resolve identifier '{identifier}'",
            )

        smiles = Chem.MolToSmiles(mol, canonical=False)
        canonical = Chem.MolToSmiles(mol, canonical=True)
        formula = rdMolDescriptors.CalcMolFormula(mol)
        mw = Descriptors.MolWt(mol)

        return ResolveResponse(
            resolved=True,
            smiles=smiles,
            source=_format_source(source),
            canonical_smiles=canonical,
            molecular_formula=formula,
            molecular_weight=round(mw, 2),
        )

    except Exception as e:
        logger.error("Resolution error for '%s': %s", request.identifier, e)
        return ResolveResponse(
            resolved=False,
            source="error",
            error=f"Resolution error: {str(e)}",
        )


def _resolve_via_pubchem(identifier: str) -> tuple[Optional["Chem.Mol"], str]:
    """Resolve via PubChem when local SMILES/InChI parsing fails."""
    try:
        import pubchempy as pcp
    except Exception as e:
        logger.error("PubChemPy not available: %s", e)
        return None, "pubchem_unavailable"

    from rdkit import Chem

    namespaces = ["name", "registry", "inchi", "inchikey", "smiles"]
    property_keys = ["CanonicalSMILES", "IsomericSMILES", "SMILES", "ConnectivitySMILES"]

    for namespace in namespaces:
        try:
            props = pcp.get_properties(property_keys, identifier, namespace)
        except Exception as e:
            logger.warning("PubChem lookup failed for %s=%s: %s", namespace, identifier, e)
            continue

        if not props:
            continue

        entry = props[0]
        smiles = None
        for key in property_keys:
            if entry.get(key):
                smiles = entry[key]
                break

        if not smiles:
            continue

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            continue

        return mol, f"pubchem:{namespace}"

    return None, "not_found"


def _resolve_via_cactus(identifier: str) -> tuple[Optional["Chem.Mol"], str]:
    """Resolve via the CACTUS/CIR service."""
    try:
        import httpx
        from rdkit import Chem
    except Exception as e:
        logger.error("CACTUS lookup unavailable: %s", e)
        return None, "cactus_unavailable"

    url = f"https://cactus.nci.nih.gov/chemical/structure/{quote(identifier)}/smiles"
    try:
        response = httpx.get(url, timeout=10.0)
    except Exception as e:
        logger.warning("CACTUS lookup failed for %s: %s", identifier, e)
        return None, "cactus_error"

    if response.status_code != 200:
        return None, "not_found"

    smiles = response.text.strip()
    if not smiles:
        return None, "not_found"

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None, "not_found"

    return mol, "cactus"


def _format_source(source: str) -> str:
    if not source:
        return "chemresolve:unknown"
    if source.startswith("pubchem:"):
        source = "pubchem"
    return f"chemresolve:{source}"


@router.get("/svg")
async def render_molecule_svg(
    smiles: str = Query(..., description="SMILES string to render"),
    width: int = Query(300, ge=50, le=1000),
    height: int = Query(200, ge=50, le=1000),
    highlight: Optional[str] = Query(None, description="Atom indices to highlight (comma-separated)"),
):
    """Render a molecule as SVG using RDKit."""
    try:
        from rdkit import Chem
        from rdkit.Chem import Draw

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid SMILES: Could not parse molecule",
            )

        highlight_atoms = []
        if highlight:
            try:
                highlight_atoms = [int(x.strip()) for x in highlight.split(",")]
            except ValueError:
                highlight_atoms = []

        drawer = Draw.MolDraw2DSVG(width, height)
        if highlight_atoms:
            drawer.DrawMolecule(mol, highlightAtoms=highlight_atoms)
        else:
            drawer.DrawMolecule(mol)
        drawer.FinishDrawing()
        svg = drawer.GetDrawingText()

        return Response(content=svg, media_type="image/svg+xml")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("SVG rendering error: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Rendering error: {str(e)}",
        )


@router.get("/reaction-svg")
async def render_reaction_svg(
    rxn_smiles: str = Query(..., description="Reaction SMILES to render"),
    width: int = Query(800, ge=200, le=2000),
    height: int = Query(200, ge=100, le=800),
):
    """Render a reaction as SVG using RDKit."""
    try:
        from rdkit.Chem import Draw, rdChemReactions

        rxn = rdChemReactions.ReactionFromSmarts(rxn_smiles, useSmiles=True)
        if rxn is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid reaction SMILES",
            )

        drawer = Draw.MolDraw2DSVG(width, height)
        drawer.DrawReaction(rxn)
        drawer.FinishDrawing()
        svg = drawer.GetDrawingText()

        return Response(content=svg, media_type="image/svg+xml")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Reaction SVG rendering error: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Rendering error: {str(e)}",
        )
