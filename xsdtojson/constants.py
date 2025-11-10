# Namespace XSD
XSD_NAMESPACE = "{http://www.w3.org/2001/XMLSchema}"

# Mapping des types XSD vers les types JSON Schema
XSD_TO_JSON_TYPE_MAP = {
    # Types numériques
    f"{XSD_NAMESPACE}byte": "integer",
    f"{XSD_NAMESPACE}decimal": "number",
    f"{XSD_NAMESPACE}float": "number",
    f"{XSD_NAMESPACE}double": "number",
    f"{XSD_NAMESPACE}int": "integer",
    f"{XSD_NAMESPACE}integer": "integer",
    f"{XSD_NAMESPACE}long": "integer",
    f"{XSD_NAMESPACE}negativeInteger": "integer",
    f"{XSD_NAMESPACE}nonNegativeInteger": "integer",
    f"{XSD_NAMESPACE}nonPositiveInteger": "integer",
    f"{XSD_NAMESPACE}positiveInteger": "integer",
    f"{XSD_NAMESPACE}short": "integer",
    f"{XSD_NAMESPACE}unsignedLong": "integer",
    f"{XSD_NAMESPACE}unsignedInt": "integer",
    f"{XSD_NAMESPACE}unsignedShort": "integer",
    f"{XSD_NAMESPACE}unsignedByte": "integer",

    # Types booléens
    f"{XSD_NAMESPACE}boolean": "boolean",

    # Types chaîne de caractères
    f"{XSD_NAMESPACE}string": "string",
    f"{XSD_NAMESPACE}normalizedString": "string",
    f"{XSD_NAMESPACE}token": "string",
    f"{XSD_NAMESPACE}base64Binary": "string", # Représenté comme une chaîne encodée
    f"{XSD_NAMESPACE}hexBinary": "string",    # Représenté comme une chaîne encodée
    f"{XSD_NAMESPACE}anyURI": "string",
    f"{XSD_NAMESPACE}QName": "string",
    f"{XSD_NAMESPACE}NOTATION": "string",
    f"{XSD_NAMESPACE}ID": "string",
    f"{XSD_NAMESPACE}IDREF": "string",
    f"{XSD_NAMESPACE}IDREFS": "array", # Liste de chaînes
    f"{XSD_NAMESPACE}ENTITY": "string",
    f"{XSD_NAMESPACE}ENTITIES": "array", # Liste de chaînes
    f"{XSD_NAMESPACE}NCName": "string",
    f"{XSD_NAMESPACE}NMTOKEN": "string",
    f"{XSD_NAMESPACE}NMTOKENS": "array", # Liste de chaînes
    f"{XSD_NAMESPACE}Name": "string",
    f"{XSD_NAMESPACE}language": "string",
    f"{XSD_NAMESPACE}anySimpleType": {}, # Peut être n'importe quoi, souvent traité comme 'string' ou 'object'

    # Types date/heure
    f"{XSD_NAMESPACE}date": "string",  # Format: "YYYY-MM-DD"
    f"{XSD_NAMESPACE}dateTime": "string", # Format: "YYYY-MM-DDThh:mm:ss" ou "YYYY-MM-DDThh:mm:ssZ"
    f"{XSD_NAMESPACE}dateTimeStamp": "string", # Format: "YYYY-MM-DDThh:mm:ss" avec fuseau horaire
    f"{XSD_NAMESPACE}time": "string",  # Format: "hh:mm:ss"
    f"{XSD_NAMESPACE}gYearMonth": "string", # Format: "YYYY-MM"
    f"{XSD_NAMESPACE}gYear": "string",    # Format: "YYYY"
    f"{XSD_NAMESPACE}gMonthDay": "string", # Format: "--MM-DD"
    f"{XSD_NAMESPACE}gDay": "string",     # Format: "---DD"
    f"{XSD_NAMESPACE}gMonth": "string",   # Format: "--MM--"

    # Types de durée (peuvent être complexes à mapper directement, souvent traités comme string)
    f"{XSD_NAMESPACE}duration": "string",
    f"{XSD_NAMESPACE}dayTimeDuration": "string",
    f"{XSD_NAMESPACE}yearMonthDuration": "string",
}