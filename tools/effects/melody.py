
"""Tools for melodies used in phonems"""
from typing import List

au_clair_de_la_lune = ["C4"] * 3 + ["D4", "E4", "C4", "D4", "E4", "D4"]

chord_progressions =[
    ["C", "Am", "F", "G"],
    ["D", "Bm", "G", "A"],
    ["G", "Em", "C", "D"],
    ["C", "Am", "D", "G"],
    ["D", "Bm", "Em", "A"],
    ["G", "Em", "Am", "D"],
    ["C", "Em", "F", "G"],
    ["G", "Bm", "C", "D"],
    ["C", "F", "C", "G"],
    ["A", "D", "A", "E"],
]

chords_ratios = {
    "major" : [0, 3, 6],
    "minor" : [0, 2, 6],
}


def get_freqs(fundamental : int, ratios : List[int]):
    return [int(round(fundamental * (1 + r/12))) for r in ratios]


def get_harmonies(note_pitch, chord_type="major") -> List[int]:
    return get_freqs(note_pitch, chords_ratios[chord_type])