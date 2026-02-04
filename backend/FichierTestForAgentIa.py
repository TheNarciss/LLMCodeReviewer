import time
import random
import math
import sys
from datetime import datetime

# Constantes globales
GRAVITY = 9.81
ORBIT_VELOCITY = 7800
MISSION_TYPES = ["Exploration", "Satellite", "Supply", "Rescue"]

def check_system_integrity(system_list):
    # Fonction globale simple
    integrity = 100
    for system in system_list:
        if random.random() < 0.05:
            integrity -= 15
    return max(0, integrity)

def complex_fuel_calculation(mass, distance):
    # Une fonction avec un peu de maths pour l'AST
    base_fuel = (mass * distance) / 1000
    correction = math.sqrt(base_fuel) * random.uniform(0.9, 1.1)
    return base_fuel + correction

class SpaceError(Exception):
    pass

class Astronaut:
    def __init__(self, name, role, experience_years):
        self.name = name
        self.role = role
        self.experience = experience_years
        self.status = "Active"

    def train(self, hours):
        self.experience += (hours / 1000)
        
    def __repr__(self):
        return f"Astronaut({self.name}, {self.role})"

class Rocket:
    # Variable de classe
    total_rockets_built = 0

    def __init__(self, name, model, capacity):
        self.name = name
        self.model = model
        self.capacity = capacity
        self.fuel_level = 0
        self.is_launched = False
        Rocket.total_rockets_built += 1

    @classmethod
    def get_fleet_count(cls):
        return cls.total_rockets_built

    def refuel(self, amount):
        if self.fuel_level + amount > 100:
            self.fuel_level = 100
        else:
            self.fuel_level += amount

    def engine_check(self):
        # Simulation d'une vérification complexe
        status = True
        if self.fuel_level < 10:
            status = False
        return status

class Mission:
    def __init__(self, mission_id, target):
        self.id = mission_id
        self.target = target
        self.rocket = None
        self.crew = []
        self.status = "Planned"
        self.logs = []

    def assign_rocket(self, rocket):
        if isinstance(rocket, Rocket):
            self.rocket = rocket
        else:
            raise SpaceError("Invalid equipment assigned")

    def add_crew_member(self, astronaut):
        if len(self.crew) < self.rocket.capacity:
            self.crew.append(astronaut)
        else:
            print(f"Rocket full! Cannot add {astronaut.name}")

    def calculate_trajectory_heavy(self):
        """
        CETTE FONCTION EST VOLONTAIREMENT LENTE POUR TESTER LE PROFILER.
        Elle fait des calculs inutiles pour consommer du CPU.
        """
        print(f"Calculating trajectory for mission {self.id}...")
        result = 0
        # Boucle lourde pour le profiling (~0.5 à 1 seconde)
        for i in range(2000000):
            result += math.sqrt(i) * math.sin(i)
        return result

    def launch(self):
        if not self.rocket:
            return False
        
        self.logs.append(f"Initiating launch sequence for {self.rocket.name}")
        
        # Vérification pré-lancement
        integrity = check_system_integrity(["Engine", "Navigation", "LifeSupport"])
        if integrity < 80:
            self.status = "Aborted"
            self.logs.append("Critical system failure detected")
            return False

        # Appel de la fonction lourde
        trajectory = self.calculate_trajectory_heavy()
        
        if self.rocket.fuel_level > 90:
            self.rocket.is_launched = True
            self.status = "In Orbit"
            self.logs.append(f"Launch successful. Orbit: {trajectory:.2f}")
            return True
        else:
            self.logs.append("Insufficient fuel")
            return False

class MissionControl:
    def __init__(self, location):
        self.location = location
        self.missions = {}

    def register_mission(self, mission):
        self.missions[mission.id] = mission

    def run_simulation(self):
        print(f"--- Mission Control Center: {self.location} ---")
        success_count = 0
        
        for m_id, mission in self.missions.items():
            print(f"Processing Mission {m_id} -> Target: {mission.target}")
            
            # Préparation fusée
            mission.rocket.refuel(100)
            
            # Tentative lancement
            result = mission.launch()
            
            if result:
                success_count += 1
                print(f"  [SUCCESS] {mission.rocket.name} is flying.")
            else:
                print(f"  [FAILURE] Mission aborted: {mission.logs[-1]}")
                
        return success_count

# --- SECTION DE TEST / EXÉCUTION ---
if __name__ == "__main__":
    # Création du centre de contrôle
    houston = MissionControl("Houston, TX")

    # Création des astronautes
    astro1 = Astronaut("Neil", "Commander", 15)
    astro2 = Astronaut("Buzz", "Pilot", 12)
    astro3 = Astronaut("Yuri", "Specialist", 8)

    # Création des fusées
    falcon = Rocket("Falcon-9", "v1.2", 4)
    starship = Rocket("Starship", "SN20", 20)
    soyuz = Rocket("Soyuz", "MS-15", 3)

    # Création Mission 1 : Mars
    m1 = Mission("M-001", "Mars")
    m1.assign_rocket(starship)
    m1.add_crew_member(astro1)
    m1.add_crew_member(astro2)
    houston.register_mission(m1)

    # Création Mission 2 : ISS Supply
    m2 = Mission("ISS-Resupply", "ISS")
    m2.assign_rocket(falcon)
    # Pas d'équipage pour le cargo
    houston.register_mission(m2)

    # Création Mission 3 : Moon (va échouer par manque de fuel simulé manuellement)
    m3 = Mission("Artemis-1", "Moon")
    m3.assign_rocket(soyuz)
    m3.add_crew_member(astro3)
    # On vide le réservoir manuellement pour provoquer une erreur logique
    m3.rocket.fuel_level = 50 
    houston.register_mission(m3)

    # Lancement global
    start_time = time.time()
    successes = houston.run_simulation()
    end_time = time.time()

    print("\n" + "="*30)
    print(f"Simulation Report")
    print(f"Total Missions: {len(houston.missions)}")
    print(f"Successful: {successes}")
    print(f"Fleet Size: {Rocket.get_fleet_count()}")
    print(f"Simulation Time: {end_time - start_time:.4f}s")
    print("="*30)