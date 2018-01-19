from urllib import request
from zipfile import ZipFile
from io import BytesIO
from os import makedirs

BASE_URL = "http://tcts.fpms.ac.be/synthesis/mbrola/dba/"
MBROLA_FOLDER = "/usr/share/mbrola/"

FR_FILES = ["fr1/fr1-990204.zip",
            "fr2/fr2-980806.zip",
            "fr3/fr3-990324.zip",
            "fr4/fr4-990521.zip",
            "fr5/fr5-991020.zip",
            "fr6/fr6-010330.zip",
            "fr7/fr7-010330.zip"]

if __name__ == "__main__":
    for file in FR_FILES:
        print("Downloading file %s" % file)
        zipfile = request.urlopen(BASE_URL + file).read()
        filename = file.split("-")[0]
        print("Extracting file")
        with ZipFile(BytesIO(zipfile), "r") as zfile:
            if "fr4" in filename:
                try:
                    makedirs(MBROLA_FOLDER + "fr4/")
                except:
                    pass
                zfile.extract("fr4", MBROLA_FOLDER + "fr4/")
            else:
                zfile.extract(filename, MBROLA_FOLDER)

    print("All done!")