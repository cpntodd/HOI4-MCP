"""
Vanilla HOI4 Database — indexes vanilla game files into a SQLite database
for fast, deterministic lookups. Eliminates AI hallucinations about vanilla IDs.

Usage as script: python -m hoi4_mcp.db.vanilla_index --vanilla-path /path/to/hoi4
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from ..clausewitz.parser import parse_file


# ---------------------------------------------------------------------------
# Database schema
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS vanilla_focuses (
    id TEXT PRIMARY KEY,
    tree_id TEXT,
    icon TEXT,
    x INTEGER,
    y INTEGER,
    prerequisite TEXT,
    mutually_exclusive TEXT,
    available TEXT,
    completion_reward TEXT,
    file TEXT,
    raw TEXT
);

CREATE TABLE IF NOT EXISTS vanilla_events (
    id TEXT PRIMARY KEY,
    namespace TEXT,
    type TEXT,
    title TEXT,
    description TEXT,
    is_triggered_only INTEGER,
    hide_window INTEGER,
    file TEXT,
    raw TEXT
);

CREATE TABLE IF NOT EXISTS vanilla_ideas (
    id TEXT PRIMARY KEY,
    category TEXT,
    picture TEXT,
    slot TEXT,
    modifier TEXT,
    file TEXT,
    raw TEXT
);

CREATE TABLE IF NOT EXISTS vanilla_decisions (
    id TEXT PRIMARY KEY,
    category TEXT,
    icon TEXT,
    cost INTEGER,
    file TEXT,
    raw TEXT
);

CREATE TABLE IF NOT EXISTS vanilla_technologies (
    id TEXT PRIMARY KEY,
    category TEXT,
    start_year INTEGER,
    research_cost REAL,
    prerequisites TEXT,
    file TEXT,
    raw TEXT
);

CREATE TABLE IF NOT EXISTS vanilla_characters (
    id TEXT PRIMARY KEY,
    name TEXT,
    roles TEXT,
    file TEXT,
    raw TEXT
);

CREATE TABLE IF NOT EXISTS vanilla_countries (
    tag TEXT PRIMARY KEY,
    file TEXT,
    capital INTEGER,
    ruling_party TEXT,
    raw TEXT
);

CREATE TABLE IF NOT EXISTS vanilla_modifiers (
    key TEXT PRIMARY KEY,
    description TEXT
);

CREATE INDEX IF NOT EXISTS idx_focuses_tree ON vanilla_focuses(tree_id);
CREATE INDEX IF NOT EXISTS idx_events_ns ON vanilla_events(namespace);
CREATE INDEX IF NOT EXISTS idx_ideas_cat ON vanilla_ideas(category);
CREATE INDEX IF NOT EXISTS idx_tech_cat ON vanilla_technologies(category);
"""


# ---------------------------------------------------------------------------
# Known vanilla modifiers (from SKILL.md reference)
# ---------------------------------------------------------------------------

VANILLA_MODIFIERS = {
    # =========================================================================
    # Stability & Political
    # =========================================================================
    "stability_factor": "Stability percentage modifier",
    "stability_weekly": "Weekly stability change (flat)",
    "war_support_factor": "War support percentage modifier",
    "war_support_weekly": "Weekly war support change (flat)",
    "political_power_factor": "Political power gain percentage modifier",
    "political_power_cost": "Flat PP cost modifier (negative = cheaper)",
    "political_power_gain": "Flat daily political power gain",
    "command_power_gain_mult": "Command power gain multiplier",
    "command_power_gain": "Flat daily command power gain",
    "drift_defence_factor": "Ideology drift defense percentage",
    "communism_drift": "Daily communism drift (flat)",
    "fascism_drift": "Daily fascism drift (flat)",
    "democratic_drift": "Daily democratic drift (flat)",
    "neutrality_drift": "Daily neutrality drift (flat)",
    "political_advisor_cost_factor": "Political advisor PP cost",
    "political_advisor_cost": "Flat political advisor cost modifier",
    "conscription_factor": "Conscription law recruitment percentage",
    "weekly_manpower": "Weekly manpower gain",
    "mobilization_speed": "Mobilization speed",
    "justify_war_goal_time": "War goal justification time modifier",
    "justify_war_goal_when_in_major_war_time": "War goal justification time when at major war",
    "guarantee_cost": "Guarantee cost modifier",
    "create_faction_threat_factor": "Easier faction creation vs threatening nations",
    "minimum_surrender_limit": "Minimum surrender progress threshold",
    "surrender_limit": "Surrender progress threshold",
    "extra_trade_supply_receiver": "Extra trade as supply receiver",
    "trade_opinion_factor": "Trade deal acceptance modifier",

    # =========================================================================
    # Production & Economy
    # =========================================================================
    "production_factory_efficiency_gain_factor": "Factory output efficiency gain",
    "production_factory_max_efficiency_factor": "Maximum factory efficiency cap",
    "production_factory_start_efficiency_factor": "Starting factory efficiency",
    "production_speed_buildings_factor": "Construction speed modifier",
    "production_speed_arms_factory_factor": "Military factory construction speed",
    "production_speed_industrial_complex_factor": "Civilian factory construction speed",
    "production_speed_dockyard_factor": "Dockyard output speed",
    "production_speed_naval_dockyard_factor": "Naval dockyard construction speed",
    "production_speed_refinery_factor": "Refinery construction speed",
    "production_speed_military_factory_factor": "Military factory construction speed",
    "line_change_production_efficiency_factor": "Production efficiency retention on line change",
    "industrial_capacity_factory": "Raw factory count (flat)",
    "industrial_capacity_dockyard": "Raw dockyard count (flat)",
    "consumer_goods_factor": "Consumer goods factor (negative reduces)",
    "production_lack_of_resource_penalty_factor": "Resource shortage penalty reduction",
    "production_resource_factor": "Resource gain efficiency",
    "production_oil_factor": "Oil production modifier",
    "global_building_slots_factor": "Building slots modifier",
    "production_speed_infrastructure_factor": "Infrastructure construction speed",
    "production_speed_air_base_factor": "Air base construction speed",
    "production_speed_naval_base_factor": "Naval base construction speed",
    "production_speed_rocket_site_factor": "Rocket site construction speed",
    "production_speed_radar_station_factor": "Radar station construction speed",
    "production_speed_nuclear_reactor_factor": "Nuclear reactor construction speed",
    "production_speed_anti_air_building_factor": "AA building construction speed",
    "production_speed_synthetic_refinery_factor": "Synthetic refinery construction speed",
    "production_speed_fuel_silo_factor": "Fuel silo construction speed",
    "infrastructure_construction_effect": "Infrastructure construction bonus",
    "conversion_speed_building_factor": "Building conversion speed modifier",
    "research_speed_factor": "Global research speed percentage",
    "research_speed_industry_factor": "Industrial research speed",
    "research_speed_electronics_factor": "Electronics research speed",
    "research_speed_land_doctrine_factor": "Land doctrine research speed",
    "research_speed_naval_doctrine_factor": "Naval doctrine research speed",
    "research_speed_air_doctrine_factor": "Air doctrine research speed",
    "research_speed_engineering_factor": "Engineering research speed",
    "research_speed_rocketry_factor": "Rocketry research speed",
    "research_speed_nuclear_factor": "Nuclear research speed",
    "research_speed_jet_technology_factor": "Jet technology research speed",
    "research_speed_armor_factor": "Armor research speed",
    "research_speed_naval_factor": "Naval research speed",
    "research_speed_air_factor": "Air research speed",
    "tech_sharing_bonus_factor": "Technology sharing bonus from allies",
    "license_purchase_cost": "License production cost modifier",
    "license_production_speed": "License production speed modifier",
    "equipment_conversion_speed": "Equipment conversion speed",
    "equipment_conversion_cost": "Equipment conversion cost modifier",
    "fuel_gain_factor": "Fuel gain per oil modifier",
    "fuel_gain_factor_from_states": "Fuel gain from owned states",
    "fuel_cost_factor": "Fuel cost modifier for units",
    "max_fuel": "Maximum fuel storage",
    "max_fuel_factor": "Maximum fuel storage multiplier",
    "fuel_k_factor": "Fuel usage modifier",

    # =========================================================================
    # Resources
    # =========================================================================
    "steel_gain_factor": "Steel resource gain",
    "aluminium_gain_factor": "Aluminium resource gain",
    "rubber_gain_factor": "Rubber resource gain",
    "tungsten_gain_factor": "Tungsten resource gain",
    "chromium_gain_factor": "Chromium resource gain",
    "oil_gain_factor": "Oil resource gain",
    "excavation_tech_factor": "Excavation technology mining efficiency",

    # =========================================================================
    # Military — Army
    # =========================================================================
    "army_morale_factor": "Division morale (org recovery rate)",
    "army_org_factor": "Maximum organization percentage",
    "army_org_regain": "Organization regain rate",
    "army_attack_factor": "Division attack percentage",
    "army_defence_factor": "Division defense percentage",
    "army_speed_factor": "Division movement speed",
    "army_core_attack_factor": "Attack on core territory",
    "army_core_defence_factor": "Defense on core territory",
    "breakthrough_factor": "Division breakthrough stat",
    "soft_attack_factor": "Soft attack modifier",
    "hard_attack_factor": "Hard attack modifier",
    "piercing_factor": "Piercing modifier",
    "hardness_factor": "Hardness modifier",
    "armor_factor": "Armor value modifier",
    "max_organisation": "Maximum org for all divisions",
    "max_planning_factor": "Planning bonus cap",
    "planning_speed": "Planning speed",
    "dig_in_speed_factor": "Entrenchment speed",
    "land_reinforce_rate": "Reinforcement speed",
    "land_night_attack": "Night attack penalty reduction (land)",
    "supply_consumption_factor": "Supply consumption (negative reduces)",
    "experience_gain_army_factor": "Army XP gain rate",
    "experience_gain_army_unit_factor": "Division XP gain rate",
    "army_fuel_consumption_factor": "Fuel consumption for army units",
    "reliability_factor": "Equipment reliability",
    "winter_attrition_factor": "Winter attrition modifier",
    "heat_attrition_factor": "Heat attrition modifier",
    "acclimatization_cold_climate_gain_factor": "Cold acclimatization speed",
    "acclimatization_hot_climate_gain_factor": "Hot acclimatization speed",
    "attrition": "Equipment attrition",
    "training_time_army_factor": "Army training time modifier",
    "training_time_factor": "All training time modifier",
    "minimum_training_level": "Minimum training level",
    "military_factory_refund_factor": "Military factory refund on disband",
    "army_armor_speed_factor": "Armored unit speed",
    "army_armor_attack_factor": "Armored unit attack",
    "army_armor_defence_factor": "Armored unit defense",
    "army_artillery_attack_factor": "Artillery attack",
    "army_artillery_defence_factor": "Artillery defense",
    "army_infantry_attack_factor": "Infantry attack",
    "army_infantry_defence_factor": "Infantry defense",
    "special_forces_attack_factor": "Special forces attack",
    "special_forces_defence_factor": "Special forces defense",
    "special_forces_cap": "Special forces battalion limit",
    "special_forces_min": "Minimum special forces battalions",
    "cavalry_attack_factor": "Cavalry attack",
    "cavalry_defence_factor": "Cavalry defense",
    "motorized_attack_factor": "Motorized/mechanized attack",
    "motorized_defence_factor": "Motorized/mechanized defense",
    "army_org_loss_when_moving": "Organization loss when moving",
    "org_loss_when_moving": "Org lost during movement",
    "recon_factor": "Reconnaissance bonus",
    "entrenchment_speed_factor": "Entrenchment build speed",
    "combat_width_factor": "Combat width modifier",
    "military_police_effect_factor": "Military police suppression bonus",
    "resistance_suppression_factor": "Resistance suppression efficiency",
    "no_supply_grace": "Hours before supply penalty",

    # =========================================================================
    # Military — Manpower
    # =========================================================================
    "manpower_factor": "Recruitable population percentage",
    "manpower_deployment_distance": "Manpower deployment distance modifier",
    "conscription": "Conscription percentage",
    "training_time": "Training time modifier",
    "manpower_gain": "Flat weekly manpower gain",

    # =========================================================================
    # Military — Air
    # =========================================================================
    "air_attack_factor": "Air attack percentage",
    "air_defence_factor": "Air defense percentage",
    "air_agility_factor": "Air agility percentage",
    "air_maximum_speed_factor": "Aircraft maximum speed",
    "air_range_factor": "Aircraft range modifier",
    "air_detection": "Air detection percentage",
    "air_mission_efficiency": "All air mission efficiency",
    "air_superiority_efficiency": "Air superiority mission efficiency",
    "air_interception_efficiency": "Interception mission efficiency",
    "air_close_air_support_efficiency": "CAS mission efficiency",
    "air_strategic_bomber_efficiency": "Strategic bombing efficiency",
    "air_nav_efficiency": "Naval bombing mission efficiency",
    "air_air_superiority_efficiency": "Air superiority efficiency",
    "air_cas_efficiency": "Close air support efficiency",
    "air_intercept_efficiency": "Interception efficiency",
    "air_strategic_bombing_efficiency": "Strategic bombing efficiency",
    "air_ace_generation_chance_factor": "Ace generation chance",
    "air_accidents_factor": "Air accident chance",
    "air_weather_penalty_factor": "Weather penalty for air missions",
    "air_night_penalty_factor": "Night penalty for air missions",
    "fighter_attack_factor": "Fighter attack",
    "fighter_defence_factor": "Fighter defense",
    "fighter_agility_factor": "Fighter agility",
    "heavy_fighter_attack_factor": "Heavy fighter attack",
    "heavy_fighter_defence_factor": "Heavy fighter defense",
    "heavy_fighter_agility_factor": "Heavy fighter agility",
    "cas_attack_factor": "CAS ground attack",
    "cas_defence_factor": "CAS defense",
    "cas_agility_factor": "CAS agility",
    "tac_bomber_attack_factor": "Tactical bomber attack",
    "tac_bomber_defence_factor": "Tactical bomber defense",
    "nav_bomber_attack_factor": "Naval bomber attack",
    "nav_bomber_defence_factor": "Naval bomber defense",
    "nav_bomber_agility_factor": "Naval bomber agility",
    "strat_bomber_attack_factor": "Strategic bomber attack",
    "strat_bomber_defence_factor": "Strategic bomber defense",
    "strat_bomber_agility_factor": "Strategic bomber agility",
    "ground_attack_factor": "CAS ground attack percentage",
    "air_ground_attack_factor": "Air-to-ground attack",
    "air_naval_attack_factor": "Air-to-naval attack",
    "air_fuel_consumption_factor": "Aircraft fuel use",
    "air_bombing_targetting_factor": "Strategic bombing targeting precision",
    "air_home_defence_factor": "Home air defense multiplier",
    "strategic_bomber_defence": "Strategic bomber air defense stat",
    "experience_gain_air_factor": "Air XP gain rate",
    "experience_gain_air_unit_factor": "Air wing XP gain rate",
    "air_training_accident_factor": "Air training accident chance",
    "air_volunteer_limit": "Air volunteer limit",

    # =========================================================================
    # Military — Navy
    # =========================================================================
    "naval_speed_factor": "Ship speed percentage",
    "naval_detection": "Naval detection percentage",
    "naval_hit_chance": "Naval hit chance percentage",
    "naval_morale_factor": "Naval morale percentage",
    "naval_damage_factor": "Naval damage output percentage",
    "naval_retreat_chance": "Naval retreat chance",
    "naval_retreat_speed": "Naval retreat speed",
    "naval_spotting": "Naval spotting",
    "naval_strike_attack": "Naval strike attack",
    "naval_invasion_capacity": "Naval invasion capacity",
    "naval_invasion_preparation_speed": "Naval invasion planning speed",
    "naval_invasion_efficiency": "Naval invasion efficiency",
    "naval_detection_factor": "Naval detection modifier",
    "naval_coordination": "Naval coordination for fleet actions",
    "naval_accuracy": "Naval accuracy",
    "naval_max_range": "Naval maximum range",
    "naval_max_range_factor": "Naval maximum range modifier",
    "naval_anti_air_attack_factor": "Naval AA attack",
    "submarine_attack_factor": "Submarine attack",
    "submarine_defence_factor": "Submarine defense",
    "submarine_detection": "Submarine detection",
    "submarine_speed_factor": "Submarine speed modifier",
    "convoy_escort_efficiency": "Convoy escort efficiency",
    "convoy_raiding_efficiency": "Convoy raiding efficiency",
    "naval_mine_sweeping": "Mine sweeping efficiency",
    "naval_mine_laying": "Mine laying efficiency",
    "naval_repair_speed_factor": "Ship repair speed",
    "naval_refit_speed": "Ship refit speed",
    "naval_invasion_defence": "Naval invasion defense",
    "amphibious_invasion_defence": "Amphibious invasion defense",
    "amphibious_invasion_speed": "Amphibious invasion speed",
    "amphibious_invasion": "Amphibious invasion bonus",
    "shore_bombardment_bonus": "Shore bombardment bonus",
    "naval_fuel_consumption_factor": "Naval fuel consumption",
    "naval_mission_efficiency": "All naval mission efficiency",
    "carrier_air_agility_factor": "Carrier aircraft agility",
    "carrier_air_attack_factor": "Carrier aircraft attack",
    "carrier_air_defence_factor": "Carrier aircraft defense",
    "carrier_air_range_factor": "Carrier aircraft range",
    "carrier_sortie_efficiency": "Carrier sortie efficiency",
    "carrier_capacity_factor": "Carrier deck capacity modifier",
    "naval_torpedo_attack_factor": "Torpedo attack",
    "naval_torpedo_hit_chance_factor": "Torpedo hit chance",
    "naval_depth_charge_attack_factor": "Depth charge attack",
    "naval_evasion_factor": "Naval evasion modifier",
    "naval_armor_factor": "Naval armor modifier",
    "naval_anti_air_factor": "Naval anti-air modifier",
    "experience_gain_navy_factor": "Navy XP gain rate",
    "experience_gain_navy_unit_factor": "Ship XP gain rate",
    "navy_fuel_consumption_factor": "Navy fuel consumption",
    "sortie_efficiency": "Carrier sortie efficiency",
    "naval_steiners_attack_factor": "Naval attack (direct stat modifier)",
    "naval_defence_factor": "Naval defense (direct stat modifier)",

    # =========================================================================
    # Diplomacy & Foreign Policy
    # =========================================================================
    "opinion_gain_monthly_factor": "Monthly opinion drift",
    "opinion_gain_monthly_same_ideology_factor": "Monthly opinion with same ideology",
    "opinion_gain_monthly_different_ideology_factor": "Monthly opinion with different ideology",
    "trade_deal_opinion_factor": "Trade deal acceptance score",
    "lend_lease_tension": "Tension from lend-lease",
    "send_volunteers_tension": "Tension from volunteers",
    "send_volunteer_factor": "Volunteer limit percentage",
    "send_volunteers_size": "Volunteer division cap",
    "expeditionary_force_factor": "Expeditionary force limit",
    "supply_factor": "Supply to allies percentage",
    "faction_trade_tension": "Tension required for faction trade",
    "guarantee_tension": "Tension required for guarantee",
    "join_faction_tension": "Tension required to join faction",
    "embargo_tension": "Tension required for embargo",
    "war_goal_tension": "Tension required for war goal",
    "declare_war_tension": "Tension required to declare war",
    "diplomatic_relation_factor": "Diplomatic relation improvement",
    "alliance_cost": "Alliance cost modifier",
    "foreign_subversive_activites": "Foreign subversive activities efficiency",
    "boost_ideology_cost_factor": "Ideology boosting PP cost",
    "boost_ideology": "Ideology boosting effectiveness",
    "diplomatic_action_cost": "Diplomatic action cost modifier",
    "subversive_activites_upkeep": "Subversive activities upkeep modifier",
    "civil_war_involvement_tension": "Tension required for civil war involvement",
    "puppet_cost_factor": "Puppet cost modifier",
    "stage_coup_cost": "Stage coup cost modifier",
    "stage_coup_tension": "Tension required to stage coup",
    "naval_treaty_adherent": "Naval treaty adherence bonus",

    # =========================================================================
    # Occupation & Resistance
    # =========================================================================
    "resistance_target": "Resistance target in occupied states",
    "resistance_growth_speed": "Resistance growth speed",
    "resistance_decay_speed": "Resistance decay speed",
    "resistance_damage_to_garrison": "Damage to garrison from resistance",
    "compliance_growth_speed": "Compliance growth speed",
    "compliance_growth_factor": "Compliance growth multiplier",
    "compliance_decay_speed": "Compliance decay speed",
    "garrison_manpower_need": "Garrison manpower requirement",
    "garrison_damage": "Garrison damage modifier",
    "garrison_penetration": "Garrison penetration (resistance suppression)",
    "garrison_strength": "Garrison strength modifier",
    "occupation_cost": "Occupation cost modifier",
    "non_core_manpower": "Non-core manpower percentage",
    "damage_to_garrison": "Damage taken by garrison units",

    # =========================================================================
    # Intelligence & Espionage
    # =========================================================================
    "intel_max_from_fighting": "Intel gained from combat",
    "intel_network_gain": "Intel network gain speed",
    "intel_network_strength": "Intel network strength",
    "decryption_power_factor": "Decryption power",
    "encryption_power_factor": "Encryption power",
    "operation_token_factor": "Operation token availability",
    "operation_outcome_factor": "Operation outcome modifier",
    "operation_cost_factor": "Operation cost modifier",
    "operation_planning_speed": "Operation planning speed",
    "agent_recruitment_time": "Agent recruitment time",
    "agent_slot": "Operative slot count",
    "agency_upgrade_time": "Agency upgrade time",
    "agency_creation_time": "Agency creation time",
    "civilian_intel_factor": "Civilian intel to others",
    "army_intel_factor": "Army intel to others",
    "air_intel_factor": "Air intel to others",
    "navy_intel_factor": "Navy intel to others",
    "intel_from_air_missions_factor": "Intel from air missions",
    "capture_enemy_equipment_factor": "Enemy equipment capture rate",
    "own_intel_factor": "Own intel defense modifier",
    "network_national_coverage": "Intel network national coverage",
    "strengthen_intelligence_agency_effect": "Intel agency strength",

    # =========================================================================
    # Decision & Mission
    # =========================================================================
    "decision_cost_factor": "Decision cost modifier",
    "decision_cooldown_factor": "Decision cooldown modifier",
    "decision_slot": "Decision slot count modifier",
    "mission_cost_factor": "Mission cost modifier",

    # =========================================================================
    # State / Province
    # =========================================================================
    "local_factory_sabotage": "Factory sabotage vulnerability",
    "local_resources": "Local resource gain",
    "local_manpower": "Local manpower modifier",
    "local_building_slots": "Local building slots modifier",
    "local_supplies": "Local supply capacity",
    "local_non_core_manpower": "Local non-core manpower",
    "state_maintenance_cost_factor": "State maintenance cost modifier",
    "local_resistance_suppression_factor": "Local resistance suppression",
    "local_compliance_gain": "Local compliance gain",

    # =========================================================================
    # General / Misc
    # =========================================================================
    "global_tension": "Global tension contribution",
    "tension_factor": "Tension generation factor",
    "world_tension_factor": "World tension generation",
    "legitimacy_factor": "Government legitimacy modifier",
    "legitimacy_weekly": "Weekly legitimacy change",
    "inflation_factor": "Inflation modifier",
    "inflation_weekly": "Weekly inflation change",
    "civil_war_support": "Civil war support modifier",
    "nuclear_production_factor": "Nuclear bomb production speed",
    "nuclear_bomb_damage_factor": "Nuclear bomb damage",
    "rocket_production_factor": "Rocket production speed",
    "rocket_attack_factor": "Rocket attack effectiveness",
    "synth_oil_factor": "Synthetic oil refinery output",
    "fuel_silo_capacity_factor": "Fuel silo capacity modifier",
    "conscription_law_factor": "Conscription law recruitable % multiplier",
    "economic_law_factor": "Economic law modifier",
    "trade_law_factor": "Trade law modifier",

    # =========================================================================
    # Unit-specific stats (often used in equipment/tech)
    # =========================================================================
    "infantry_equipment_reliability": "Infantry equipment reliability",
    "artillery_attack": "Artillery soft attack",
    "artillery_defence": "Artillery defense",
    "antitank_attack": "Anti-tank hard attack",
    "antitank_defence": "Anti-tank defense",
    "antiair_attack": "Anti-air attack",
    "light_armor_attack": "Light tank attack",
    "light_armor_defence": "Light tank defense",
    "medium_armor_attack": "Medium tank attack",
    "medium_armor_defence": "Medium tank defense",
    "heavy_armor_attack": "Heavy tank attack",
    "heavy_armor_defence": "Heavy tank defense",
    "modern_armor_attack": "Modern tank attack",
    "modern_armor_defence": "Modern tank defense",
    "mechanized_attack_factor": "Mechanized attack",
    "mechanized_defence_factor": "Mechanized defense",
    "motorised_infantry_attack_factor": "Motorized infantry attack",
    "motorised_infantry_defence_factor": "Motorized infantry defense",

    # =========================================================================
    # Designer-spirit specific (NSB / BBA / AAT)
    # =========================================================================
    "land_doctrine_research_bonus": "Land doctrine research bonus (flat)",
    "naval_doctrine_research_bonus": "Naval doctrine research bonus (flat)",
    "air_doctrine_research_bonus": "Air doctrine research bonus (flat)",
    "political_power_gain_factor": "Political power gain multiplier",
    "production_speed_equipment_factor": "Equipment production speed",
    "production_speed_small_arms_factor": "Small arms production speed",
    "production_speed_artillery_factor": "Artillery production speed",
    "production_speed_tank_factor": "Tank production speed",
    "production_speed_aircraft_factor": "Aircraft production speed",
    "production_speed_ship_factor": "Ship production speed",
    "production_speed_motorized_factor": "Motorized equipment production speed",
    "equipment_capture_factor": "Equipment capture rate modifier",
    "max_planning": "Maximum planning bonus (flat)",
    "sortie_efficiency_factor": "Carrier sortie efficiency",
    "dig_in_speed": "Entrenchment speed (flat)",
    "winter_attrition": "Winter attrition",
    "heat_attrition": "Heat attrition",
    "terrain_adaptation_factor": "Terrain adaptation speed",
    "river_crossing_factor": "River crossing penalty modifier",
    "amphibious_landing_factor": "Amphibious landing penalty modifier",
    "paradrop_attack_factor": "Paratrooper attack",
    "paradrop_defence_factor": "Paratrooper defense",
    "night_attack_factor": "Night attack modifier",
    "night_defence_factor": "Night defense modifier",
    "enemy_air_superiority_penalty_factor": "Enemy air superiority penalty reduction",
}


# ---------------------------------------------------------------------------
# DB Builder
# ---------------------------------------------------------------------------

class VanillaDBBuilder:
    """Parses vanilla HOI4 game files and indexes them into SQLite."""

    def __init__(self, vanilla_path: str | Path, db_path: str | Path | None = None):
        self.vanilla_path = Path(vanilla_path)
        if not self.vanilla_path.exists():
            raise FileNotFoundError(f"Vanilla HOI4 path does not exist: {vanilla_path}")

        if db_path is None:
            db_path = Path.home() / ".hoi4_mcp" / "vanilla.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._create_schema()

    def _create_schema(self) -> None:
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def _txt_files(self, subdir: str) -> list[Path]:
        full = self.vanilla_path / subdir
        return sorted(full.rglob("*.txt")) if full.exists() else []

    def index_focuses(self) -> int:
        """Index all vanilla focus trees."""
        count = 0
        self.conn.execute("DELETE FROM vanilla_focuses")
        for fp in self._txt_files("common/national_focus"):
            parsed = parse_file(fp)
            for key, value in parsed.data.items():
                if key == "focus_tree" and isinstance(value, dict):
                    tree_id = str(value.get("id", fp.stem))
                    foci = value.get("focus", {})
                    if isinstance(foci, dict):
                        self._insert_focus(foci, tree_id, fp)
                        count += 1
                    elif isinstance(foci, list):
                        for f in foci:
                            if isinstance(f, dict):
                                self._insert_focus(f, tree_id, fp)
                                count += 1
        self.conn.commit()
        return count

    def _insert_focus(self, focus_data: dict, tree_id: str, filepath: Path) -> None:
        fid = str(focus_data.get("id", ""))
        if not fid:
            return
        self.conn.execute(
            """INSERT OR REPLACE INTO vanilla_focuses 
               (id, tree_id, icon, x, y, prerequisite, mutually_exclusive, 
                available, completion_reward, file, raw)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                fid,
                tree_id,
                str(focus_data.get("icon", "")),
                focus_data.get("x", 0),
                focus_data.get("y", 0),
                json.dumps(focus_data.get("prerequisite", {})),
                json.dumps(focus_data.get("mutually_exclusive", {})),
                json.dumps(focus_data.get("available", {})),
                json.dumps(focus_data.get("completion_reward", {})),
                str(filepath.relative_to(self.vanilla_path)),
                json.dumps(focus_data),
            )
        )

    def index_events(self) -> int:
        """Index all vanilla events."""
        count = 0
        self.conn.execute("DELETE FROM vanilla_events")
        for fp in self._txt_files("events"):
            parsed = parse_file(fp)
            for ns in parsed.namespaces:
                for key, value in parsed.data.items():
                    if key in ("country_event", "news_event", "state_event", 
                               "unit_event", "decision_event"):
                        if isinstance(value, dict) and "id" in value:
                            eid = str(value["id"])
                            self.conn.execute(
                                """INSERT OR REPLACE INTO vanilla_events
                                   (id, namespace, type, title, description,
                                    is_triggered_only, hide_window, file, raw)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                (
                                    eid,
                                    ns,
                                    key,
                                    str(value.get("title", "")),
                                    str(value.get("desc", "")),
                                    1 if value.get("is_triggered_only") == "yes" else 0,
                                    1 if value.get("hide_window") == "yes" else 0,
                                    str(fp.relative_to(self.vanilla_path)),
                                    json.dumps(value),
                                )
                            )
                            count += 1
        self.conn.commit()
        return count

    def index_ideas(self) -> int:
        """Index all vanilla ideas/spirits/advisors."""
        count = 0
        self.conn.execute("DELETE FROM vanilla_ideas")
        for fp in self._txt_files("common/ideas"):
            parsed = parse_file(fp)
            for cat_key, cat_val in parsed.data.items():
                if isinstance(cat_val, dict):
                    for idea_key, idea_val in cat_val.items():
                        if isinstance(idea_val, dict):
                            self.conn.execute(
                                """INSERT OR REPLACE INTO vanilla_ideas
                                   (id, category, picture, slot, modifier, file, raw)
                                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                (
                                    str(idea_key),
                                    str(cat_key),
                                    str(idea_val.get("picture", "")),
                                    str(idea_val.get("slot", "")),
                                    json.dumps(idea_val.get("modifier", {})),
                                    str(fp.relative_to(self.vanilla_path)),
                                    json.dumps(idea_val),
                                )
                            )
                            count += 1
        self.conn.commit()
        return count

    def index_technologies(self) -> int:
        """Index all vanilla technologies."""
        count = 0
        self.conn.execute("DELETE FROM vanilla_technologies")
        for fp in self._txt_files("common/technology"):
            parsed = parse_file(fp)
            if "technologies" in parsed.data:
                techs = parsed.data["technologies"]
                if isinstance(techs, dict):
                    for tech_key, tech_val in techs.items():
                        if isinstance(tech_val, dict):
                            self.conn.execute(
                                """INSERT OR REPLACE INTO vanilla_technologies
                                   (id, category, start_year, research_cost,
                                    prerequisites, file, raw)
                                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                (
                                    str(tech_key),
                                    str(tech_val.get("category", "")),
                                    tech_val.get("start_year", 1936),
                                    tech_val.get("research_cost", 0.0),
                                    json.dumps(tech_val.get("allow_branch", {})),
                                    str(fp.relative_to(self.vanilla_path)),
                                    json.dumps(tech_val),
                                )
                            )
                            count += 1
        self.conn.commit()
        return count

    def index_countries(self) -> int:
        """Index country history files."""
        count = 0
        self.conn.execute("DELETE FROM vanilla_countries")
        for fp in self._txt_files("history/countries"):
            parsed = parse_file(fp)
            # Extract tag from filename: "TAG - name.txt"
            tag = fp.stem.split(" - ")[0].strip().upper()
            if len(tag) == 3:
                self.conn.execute(
                    """INSERT OR REPLACE INTO vanilla_countries
                       (tag, file, capital, ruling_party, raw)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        tag,
                        str(fp.relative_to(self.vanilla_path)),
                        parsed.data.get("capital", 0),
                        str(parsed.data.get("set_politics", {}).get("ruling_party", "") if isinstance(parsed.data.get("set_politics"), dict) else ""),
                        json.dumps(parsed.data),
                    )
                )
                count += 1
        self.conn.commit()
        return count

    def index_modifiers(self) -> int:
        """Load known vanilla modifiers from the built-in reference."""
        self.conn.execute("DELETE FROM vanilla_modifiers")
        for key, desc in VANILLA_MODIFIERS.items():
            self.conn.execute(
                "INSERT OR REPLACE INTO vanilla_modifiers (key, description) VALUES (?, ?)",
                (key, desc)
            )
        self.conn.commit()
        return len(VANILLA_MODIFIERS)

    def index_decisions(self) -> int:
        """Index all vanilla decisions."""
        count = 0
        self.conn.execute("DELETE FROM vanilla_decisions")
        for fp in self._txt_files("common/decisions"):
            parsed = parse_file(fp)
            for cat_key, cat_val in parsed.data.items():
                if isinstance(cat_val, dict):
                    for dec_key, dec_val in cat_val.items():
                        if isinstance(dec_val, dict):
                            self.conn.execute(
                                """INSERT OR REPLACE INTO vanilla_decisions
                                   (id, category, icon, cost, file, raw)
                                   VALUES (?, ?, ?, ?, ?, ?)""",
                                (
                                    str(dec_key),
                                    str(cat_key),
                                    str(dec_val.get("icon", "")),
                                    dec_val.get("cost", 0),
                                    str(fp.relative_to(self.vanilla_path)),
                                    json.dumps(dec_val),
                                )
                            )
                            count += 1
        self.conn.commit()
        return count

    def index_characters(self) -> int:
        """Index all vanilla characters."""
        count = 0
        self.conn.execute("DELETE FROM vanilla_characters")
        for fp in self._txt_files("common/characters"):
            parsed = parse_file(fp)
            char_data = parsed.data.get("characters", {})
            if isinstance(char_data, dict):
                for char_id, char_val in char_data.items():
                    if isinstance(char_val, dict):
                        roles = []
                        if "country_leader" in char_val:
                            roles.append("country_leader")
                        if "advisor" in char_val:
                            roles.append("advisor")
                        if "corps_commander" in char_val:
                            roles.append("corps_commander")
                        self.conn.execute(
                            """INSERT OR REPLACE INTO vanilla_characters
                               (id, name, roles, file, raw)
                               VALUES (?, ?, ?, ?, ?)""",
                            (
                                str(char_id),
                                str(char_val.get("name", "")),
                                json.dumps(roles),
                                str(fp.relative_to(self.vanilla_path)),
                                json.dumps(char_val),
                            )
                        )
                        count += 1
        self.conn.commit()
        return count

    def build_all(self) -> dict[str, int]:
        """Run all indexers. Returns counts per category."""
        return {
            "focuses": self.index_focuses(),
            "events": self.index_events(),
            "ideas": self.index_ideas(),
            "decisions": self.index_decisions(),
            "characters": self.index_characters(),
            "technologies": self.index_technologies(),
            "countries": self.index_countries(),
            "modifiers": self.index_modifiers(),
        }

    def close(self) -> None:
        self.conn.close()


# ---------------------------------------------------------------------------
# DB Queries (used by MCP tool)
# ---------------------------------------------------------------------------

class VanillaLookup:
    """Query interface for the vanilla HOI4 SQLite database."""

    def __init__(self, db_path: str | Path | None = None):
        if db_path is None:
            db_path = Path.home() / ".hoi4_mcp" / "vanilla.db"
        self.db_path = Path(db_path)
        self.conn: sqlite3.Connection | None = None

    def _ensure_connected(self) -> sqlite3.Connection:
        if self.conn is None:
            if not self.db_path.exists():
                raise FileNotFoundError(
                    f"Vanilla database not found at {self.db_path}. "
                    "Run 'index-vanilla --vanilla-path /path/to/hoi4' first."
                )
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row
        return self.conn

    def lookup_focus(self, focus_id: str) -> dict[str, Any] | None:
        """Look up a vanilla focus by ID."""
        conn = self._ensure_connected()
        row = conn.execute(
            "SELECT * FROM vanilla_focuses WHERE id = ?", (focus_id,)
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    def lookup_event(self, event_id: str) -> dict[str, Any] | None:
        """Look up a vanilla event by ID (e.g., 'germany.1')."""
        conn = self._ensure_connected()
        row = conn.execute(
            "SELECT * FROM vanilla_events WHERE id = ?", (event_id,)
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    def lookup_idea(self, idea_key: str) -> dict[str, Any] | None:
        """Look up a vanilla idea/spirit/advisor by key."""
        conn = self._ensure_connected()
        row = conn.execute(
            "SELECT * FROM vanilla_ideas WHERE id = ?", (idea_key,)
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    def lookup_technology(self, tech_key: str) -> dict[str, Any] | None:
        """Look up a vanilla technology by key."""
        conn = self._ensure_connected()
        row = conn.execute(
            "SELECT * FROM vanilla_technologies WHERE id = ?", (tech_key,)
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    def lookup_country(self, tag: str) -> dict[str, Any] | None:
        """Look up a vanilla country by tag."""
        conn = self._ensure_connected()
        row = conn.execute(
            "SELECT * FROM vanilla_countries WHERE tag = ?", (tag.upper(),)
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    def lookup_modifier(self, modifier_key: str) -> dict[str, Any] | None:
        """Look up a known vanilla modifier by key."""
        conn = self._ensure_connected()
        row = conn.execute(
            "SELECT * FROM vanilla_modifiers WHERE key = ?", (modifier_key,)
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    def lookup_decision(self, decision_key: str) -> dict[str, Any] | None:
        """Look up a vanilla decision by key."""
        conn = self._ensure_connected()
        row = conn.execute(
            "SELECT * FROM vanilla_decisions WHERE id = ?", (decision_key,)
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    def lookup_character(self, character_id: str) -> dict[str, Any] | None:
        """Look up a vanilla character by ID."""
        conn = self._ensure_connected()
        row = conn.execute(
            "SELECT * FROM vanilla_characters WHERE id = ?", (character_id,)
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    def search_focuses(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search focus IDs by substring."""
        conn = self._ensure_connected()
        rows = conn.execute(
            "SELECT id, tree_id, icon, file FROM vanilla_focuses WHERE id LIKE ? LIMIT ?",
            (f"%{query}%", limit)
        ).fetchall()
        return [dict(r) for r in rows]

    def search_events(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search event IDs by substring."""
        conn = self._ensure_connected()
        rows = conn.execute(
            "SELECT id, namespace, type, title, file FROM vanilla_events WHERE id LIKE ? LIMIT ?",
            (f"%{query}%", limit)
        ).fetchall()
        return [dict(r) for r in rows]

    def search_ideas(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search idea keys by substring."""
        conn = self._ensure_connected()
        rows = conn.execute(
            "SELECT id, category, slot, picture, file FROM vanilla_ideas WHERE id LIKE ? LIMIT ?",
            (f"%{query}%", limit)
        ).fetchall()
        return [dict(r) for r in rows]

    def search_modifiers(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        """Search vanilla modifier keys and descriptions by substring.

        Searches both the modifier key name and the description text.
        Use this to discover the correct modifier name for an effect you want.
        """
        conn = self._ensure_connected()
        rows = conn.execute(
            "SELECT key, description FROM vanilla_modifiers "
            "WHERE key LIKE ? OR description LIKE ? "
            "ORDER BY key LIMIT ?",
            (f"%{query}%", f"%{query}%", limit)
        ).fetchall()
        return [dict(r) for r in rows]

    def search_decisions(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search decision keys by substring."""
        conn = self._ensure_connected()
        rows = conn.execute(
            "SELECT id, category, icon, cost, file FROM vanilla_decisions WHERE id LIKE ? LIMIT ?",
            (f"%{query}%", limit)
        ).fetchall()
        return [dict(r) for r in rows]

    def search_characters(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search character IDs/names by substring."""
        conn = self._ensure_connected()
        rows = conn.execute(
            "SELECT id, name, roles, file FROM vanilla_characters WHERE id LIKE ? OR name LIKE ? LIMIT ?",
            (f"%{query}%", f"%{query}%", limit)
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI to build the vanilla database."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Index vanilla HOI4 game files into a SQLite database for fast lookups."
    )
    parser.add_argument(
        "--vanilla-path", required=True,
        help="Path to the HOI4 game install directory (e.g., ~/.steam/steam/steamapps/common/Hearts of Iron IV)"
    )
    parser.add_argument(
        "--db-path", default=None,
        help="Path to store the SQLite database (default: ~/.hoi4_mcp/vanilla.db)"
    )
    args = parser.parse_args()

    print(f"Indexing vanilla HOI4 from: {args.vanilla_path}")
    builder = VanillaDBBuilder(args.vanilla_path, args.db_path)
    counts = builder.build_all()
    builder.close()

    print("\nIndexing complete:")
    for category, count in counts.items():
        print(f"  {category}: {count} entries")
    print(f"\nDatabase saved to: {builder.db_path}")


if __name__ == "__main__":
    main()
