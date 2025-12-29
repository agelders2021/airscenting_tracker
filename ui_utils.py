"""
Utility Functions for Air-Scenting Logger
Helper functions used throughout the application
"""
from getpass import getuser


def get_username():
    """Get the current system username"""
    try:
        return getuser()
    except:
        return "unknown"


def get_default_terrain_types():
    """Get the default terrain type list"""
    return [
        "Urban", "Rural", "Forest", "Scrub", "Desert", "Sandy", "Rocky", 
        "City park", "Meadow", "Dense brush", "Many cacti", "Stream", 
        "Roadway", "Marsh", "Mixed", "Industrial", "Residential"
    ]


def get_default_distraction_types():
    """Get the default distraction type list"""
    return [
        "Critter", "Horse", "Loud noise", "Motorcycle", "Hikers", 
        "Cow", "Vehicle"
    ]
