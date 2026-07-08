import re
import numpy as np


def strCaseCmp(str1, str2):
    return str1.casefold() == str2.casefold()


def classifyLine(line):
    if line.startswith("**"):
        return "comment"
    elif line.startswith("*"):
        return "keyword"
    else:
        return "data"


def parseKeywordLine(line):
    """ parse keyword line and return definition as dict
    Args:
        line: keyword line
    Returns:
        defDict: definition with lower case keys
    """
    defDict = {}

    sanitizedLine = re.sub(r"[\n\t\s]*", "", line)
    splitLine = sanitizedLine.split(",")

    defDict["keyword"] = splitLine.pop(0)[1:]
    defDict.update(dict([item.split("=") for item in splitLine]))

    defDict = {key.casefold(): value for key, value in defDict.items()}

    return defDict


def keywordLineFromDefDict(defDict):
    line = "*"
    line += defDict.pop("keyword")

    for key, value in defDict.items():
        line += ", "
        line += key.upper()
        line += "="
        line += value

    line += "\n"

    return line


def setElementDefinition(lines, elSet, properties):
    currKey = ""
    for i1, line in enumerate(lines):
        lineType = classifyLine(line)
        if lineType == "keyword":
            defDict = parseKeywordLine(line)
            currKey = defDict["keyword"]

            if currKey.casefold() == "element" and defDict["elset"] == elSet:
                defDict.update(properties)

            lines[i1] = keywordLineFromDefDict(defDict)
        else:
            pass


def copyElementDefinition(lines, setName, newName, offset=900000):
    keywordIdx = None
    keywordLines = []
    dataLines = []
    commentLines = []
    currKey = ""
    for i1, line in enumerate(lines):
        lineType = classifyLine(line)

        if lineType == "data":
            dataLines.append(i1)

        elif lineType == "keyword":
            keywordLines.append(i1)

            defDict = parseKeywordLine(line)
            currKey = defDict["keyword"]

            if currKey.casefold() == "element" and defDict.get("elset") == setName:
                keywordIdx = i1

        elif lineType == "comment":
            commentLines.append(i1)

    if not keywordIdx:
        raise(Exception(f"Error occured while processing set '{setName}'"))

    keywordLines = np.array(keywordLines)
    dataLines = np.array(dataLines)

    aux = np.array(keywordLines) - keywordIdx
    nextKeywordIdx = keywordLines[np.where(aux > 0, aux, np.inf).argmin()]

    dataLineIdxsToCopy = dataLines[
        np.logical_and(
            np.array(dataLines) - keywordIdx > 0,
            np.array(dataLines) - nextKeywordIdx < 0,
        )
    ]
    insertIdx = dataLineIdxsToCopy[-1] + 1

    for idx in np.flip(dataLineIdxsToCopy, axis=None):
        line = lines[idx]
        sanitizedLine = re.sub(r"[\n\t\s]*", "", line)
        splitLine = sanitizedLine.split(",")

        elNumber = int(splitLine.pop(0)) + offset
        nodeNumbers = [int(item) for item in splitLine]
        insertLine = ",".join([f"{item:8}" for item in [elNumber] + nodeNumbers]) + "\n"

        lines.insert(insertIdx, insertLine)

    defDict = parseKeywordLine(lines[keywordIdx])
    defDict["elset"] = newName
    lines.insert(insertIdx, keywordLineFromDefDict(defDict))

    return


inpFile = "./concrete.inp"
outFile = "./modified/concrete.inp"
with open(inpFile, "r") as fIn, open(outFile, "w+") as fOut:
    lines = fIn.readlines()
    copyElementDefinition(lines, "dummy", "concrete")
    # # GCDP
    setElementDefinition(lines, "dummy", dict(type="C3D20R"))
    setElementDefinition(lines, "concrete", dict(type="U004"))    
    # # GMCDP
    # setElementDefinition(lines, "concrete", dict(type="U020"))
    # setElementDefinition(lines, "concrete2", dict(type="U020"))

    fOut.writelines(lines)

inpFile = "./steel.inp"
outFile = "./modified/steel.inp"
with open(inpFile, "r") as fIn, open(outFile, "w+") as fOut:
    lines = fIn.readlines()
    setElementDefinition(lines, "anchor", dict(type="C3D8"))
    setElementDefinition(lines, "plate", dict(type="C3D8"))
    setElementDefinition(lines, "mortar", dict(type="COH3D8"))
    fOut.writelines(lines)

