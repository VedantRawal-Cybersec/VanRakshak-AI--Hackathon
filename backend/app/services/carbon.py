from app.models import CarbonRequest

def estimate(req: CarbonRequest):
    # Common reporting convention: carbon fraction approximated at 0.47 of dry biomass; CO2/C = 44/12.
    biomass = req.area_ha * req.biomass_t_per_ha
    carbon = biomass * 0.47
    co2e = carbon * (44/12)
    u=req.uncertainty_pct/100
    return {
        "area_ha":req.area_ha,
        "biomass_t":round(biomass,2),
        "carbon_t":round(carbon,2),
        "co2e_t":round(co2e,2),
        "co2e_range_t":[round(co2e*(1-u),2),round(co2e*(1+u),2)],
        "label":"AI_ESTIMATE",
        "assumptions":["carbon fraction = 0.47 of dry biomass","CO2/C conversion = 44/12","biomass density must come from a cited dataset such as GEDI or local inventory"]
    }
