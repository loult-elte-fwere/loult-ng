#!/usr/bin/python3
import csv

"""Script utilisé pour extraire les noms communs dans le lexique complet téléchargé chez
http://lexique.org/telLexique.php"""

FULL_LEXIQUE_FILEPATH = "lexique_full.txt"
FILTERED_COMMON_NAMES_FILPATH = "noms_communs.txt"

if __name__ == "__main__":
    freq_fields = ['7_freqlemfilms2', '8_freqlemlivres', '9_freqfilms2', '10_freqlivres']

    with open(FULL_LEXIQUE_FILEPATH, "r") as lexique_file, open(FILTERED_COMMON_NAMES_FILPATH, "w") as filtered_file:
        csv_reader = csv.DictReader(lexique_file, delimiter='\t')
        csv_writer = csv.DictWriter(filtered_file, delimiter ='\t', fieldnames=["ortho", "genre", "nombre", "freq"])
        csv_writer.writeheader()
        all_freqs = []
        for row in csv_reader:
            if row["4_cgram"] == "NOM":
                # avg_freq = sum([float(row[field]) for field in freq_fields]) / 4
                # all_freqs.append(avg_freq)
                # if avg_freq > 0.205:
                if row["1_ortho"] != row["3_lemme"]:
                    csv_writer.writerow({"ortho" : row["1_ortho"],
                                         "genre" : row["5_genre"],
                                         "nombre" : row["6_nombre"],
                                         "freq" : avg_freq})
        all_freqs.sort(reverse=True)
        print(all_freqs[30000])
