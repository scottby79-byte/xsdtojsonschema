# XSD to JSON Schema Converter

Ce programme Python xsdtojson.py analyse un ou plusieurs fichiers de schéma XML (XSD) et génère un fichier JSON Schema correspondant. Il prend en charge les imports et inclusions XSD, résout les références aux types et éléments globaux, et traduit les constructions XSD standard (types complexes, types simples, éléments, attributs, groupes, etc.) en concepts JSON Schema équivalents (objets, propriétés, types, énumérations, motifs, etc.).
L'objectif est de fournir un schéma JSON utilisable pour valider des documents JSON qui représentent l'équivalent structurel des documents XML conformes au XSD original.


## Fonctionnalités et Support XSD

Ce convertisseur prend en charge une gamme significative de constructions XSD de la spécification W3C XML Schema, les mappant aux fonctionnalités de JSON Schema (Draft 07).

### Types de base et Facettes

#### Mappage de Types Standard : 

Traduction des types intégrés XSD (xs:string, xs:int, xs:float, xs:boolean, xs:date, xs:dateTime, etc.) vers leurs équivalents JSON Schema (string, integer, number, boolean).

#### xs:simpleType
##### xs:restriction
- enumeration : Mappé à la propriété enum.
- minInclusive, maxInclusive : Mappés à minimum et maximum.
- minExclusive, maxExclusive : Mappés à exclusiveMinimum et exclusiveMaximum.
- length, minLength, maxLength : Mappés à minLength et maxLength pour les chaînes.
- pattern : Mappé à la propriété pattern.
##### xs:list
Converti en un type array avec un items basé sur le itemType du XSD.
##### xs:union
Mappé à la propriété oneOf de JSON Schema.

### Éléments et Attributs

#### xs:element
Conversion des définitions d'éléments globaux et locaux.
Prise en charge des attributs name, type, et ref pour les éléments.
Gestion de minOccurs et maxOccurs pour déterminer la cardinalité (minItems, maxItems pour les tableaux) et les champs required.
Prise en charge de l'attribut nillable (ajoute null au tableau des types JSON Schema).
Mappage des attributs fixed et default aux propriétés const et default de JSON Schema.
#### xs:attribute
Conversion des définitions d'attributs locaux.
Prise en charge de name, type, et ref pour les attributs.
Gestion de l'attribut use (optional, required).
Mappage des attributs fixed et default.
#### xs:any et xs:anyAttribute
Mappés à additionalProperties: true, permettant des propriétés/attributs non définis dans le schéma.

### Structures complexes
#### xs:complexType
- Convertit les types complexes en objets JSON Schema.
- xs:sequence et xs:all : Les éléments internes sont mappés aux propriétés de l'objet.
- xs:choice : Mappé à la propriété oneOf de JSON Schema, représentant un choix exclusif entre plusieurs sous-schémas.
- Gestion des attributs et groupes d'attributs définis ou référencés au sein d'un complexType.

### Références et Définitions
#### Références Globales
Résout les références (ref attributs) aux éléments, attributs, groupes de modèles (xs:group) et groupes d'attributs (xs:attributeGroup) définis globalement.
#### Définitions Réutilisables
Les types complexes et simples globaux sont convertis en définitions (#/definitions) dans le JSON Schema de sortie pour la réutilisation et la lisibilité, sauf si l'option --no-ref est utilisée.
#### xs:group (model groups)
Les groupes de modèles référencés sont résolus et leurs éléments internes sont fusionnés dans le schéma de l'objet parent.
#### xs:attributeGroup
Les groupes d'attributs référencés sont résolus et leurs attributs sont fusionnés dans le schéma des propriétés de l'objet parent.

### Documentation
#### xs:annotation et xs:documentation
Le contenu de xs:documentation est extrait et utilisé comme description dans le JSON Schema généré.

### Traitement des Fichiers XSD
Support des Imports/Includes : L'analyseur XSD (XSDParser) gère récursivement les directives xs:import et xs:include, résolvant les chemins relatifs et utilisant un mappage de namespaces connus (XSD_SCHEMALOCATION_MAP) pour les schémas sans schemaLocation.
Analyse de Répertoire : Peut analyser un répertoire entier de fichiers XSD ou un fichier XSD principal spécifique.

## Limitations

Bien que le convertisseur couvre de nombreuses constructions XSD, certaines fonctionnalités complexes ou spécifiques à XML ne peuvent pas être directement mappées ou ne sont pas implémentées :
### Ordre des Propriétés
JSON Schema ne garantit pas l'ordre des propriétés des objets, donc l'ordre défini par xs:sequence n'est pas préservé dans le JSON Schema.
### Contenu Mixte (mixed="true")
L'attribut mixed="true" sur les types complexes n'est pas directement supporté par JSON Schema, qui se concentre sur les données structurées.
### Facettes non mappées entièrement
- totalDigits et fractionDigits sont reconnus mais ne sont pas entièrement traduits en équivalents JSON Schema. totalDigits est partiellement utilisé pour déterminer les limites d'un entier.
- whiteSpace n'a pas d'équivalent direct en JSON Schema.
### Contraintes de Clé (xs:key, xs:keyref, xs:unique)
Les mécanismes de validation basés sur des clés ou des unicité (souvent liés à XPath) ne sont pas mappables en JSON Schema.
### Assertions (xs:assert)
Les assertions complexes de XSD 1.1 ne peuvent pas être traduites en JSON Schema.
### Groupes de Substitution (xs:substitutionGroup)
Non directement pris en charge. Un élément de substitution pourrait être représenté par un oneOf manuel, mais ce n'est pas automatisé.
### Types et Éléments Abstraits (abstract="true")
L'attribut abstract n'est pas directement pris en compte dans la génération du JSON Schema.
### Spécificité de xs:any/xs:anyAttribute
additionalProperties: true est une interprétation générique ; les attributs comme processContents="skip|lax|strict" ne sont pas traduits.
### Groupes de Modèles/Attributs en ligne
Les groupes définis directement dans un complexType sans référence (<xs:group><xs:element ... /></xs:group>) ne sont pas directement supportés pour la fusion et nécessitent d'être définis globalement avec une référence.

## Installation de python

https://www.python.org/downloads/windows/ 
    
1) Prendre la version avec installer et l'installer dans c:\programmes

2) Si vous executez le script Python depuis git-bash, ajoutez les variables d'environnements suivantes pour executer python, pip et le projet (/C/programmes/Python/Python313/Scripts:/C/programmes/Python/Python313) dans votre fichier bash.bashrc (c:\programmes\Git\etc\bash.bashrc) :

```
export PYTHONPATH=${PYTHONPATH}:/c/Workspaces/WK_VSC_Python/xsdtojsonschema
export PATH=$PATH:/C/programmes/Python/Python313/Scripts:/C/programmes/Python/Python313
```
## Installation des modules Python depuis Git Bash

Pour l'execution en ligne de commande

```
pip install lxml
pip install Flask
pip install python-dotenv
pip install Werkzeug
```

## Structure du Projet

Le programme est structuré en plusieurs modules pour une meilleure maintenabilité et lisibilité :

```
xsdtojsonschema/
├── templates
|   ├── index.html                # Formulaire web pour executer la conversion
├── xsdtojson.py                  # CLI pour exécuter la conversion
├── webapp.py                     # Webapp Python
└── xsdtojson/
    ├── __init__.py               # Rend 'xsdtojson' un package Python
    ├── constants.py              # Contient les constantes comme le namespace XSD et les mappages de types
    ├── file_utils.py             # Fonctions utilitaires liées aux opérations sur les fichiers
    ├── json_schema_converter.py  # Logique principale de conversion XSD en JSON Schema
    └── xsd_parser.py             # Analyseur de fichiers XSD, gère les imports/inclusions
```


## Execution :

### WebAPP en Local

```
python webapp.py
```

Acceder à l'outil de convertion depuis l'url : http://127.0.0.1:8080

### WebAPP sous Docker

Un Dockerfile permet de démarrer l'application dans un container Docker au sein d'un serveur HTTP WSGI Gunicorn

```
docker build --tag 'xsdtojsonschema' .

docker run -p 8080:8080 --detach 'xsdtojsonschema'
```

Acceder à l'outil de convertion depuis l'url : http://127.0.0.1:8080

### CLI

```bash
python xsdtojson.py <INPUT_PATH> [OPTIONS]
 
Arguments :
<INPUT_PATH>: Chemin vers le fichier XSD principal ou le répertoire contenant l'arborescence des fichiers XSD.

Options :
-m --main-xsd <FILENAME>: (Obligatoire si INPUT_PATH est un répertoire) Spécifie le nom du fichier XSD principal à partir duquel commencer la conversion. Exemple : root.xsd.
-o --output <FILEPATH>: Spécifie le chemin vers le fichier de sortie JSON Schema. Si non fourni, le nom du fichier de sortie sera <nom_fichier_xsd_principal>.json dans le répertoire courant.
-p --pretty: Formate le JSON de sortie avec une indentation pour une meilleure lisibilité.
--no-ref: Désactive l'utilisation des références ($ref) vers les définitions. Lorsque cette option est présente, les définitions des types complexes sont directement incluses (inlined) à chaque endroit où elles sont utilisées, plutôt que d'être stockées dans la section definitions et référencées.
```

Exemple : 

1) S'il s'agit d'un schéma xsd sans aucune dépendances (sans import ou include) :

```
python xsdtojson.py ./tests/in/ApplicationData.xsd -o ./tests/out/ApplicationData.xsd.json -p --no-ref
```

2) S'il s'agit d'un schéma xsd avec des interdépendances avec d'autres schémas (import et/ou include) :

Supposons que vous ayez une structure comme :
```
my_xsd_project/
├── main.xsd
├── common/
│   └── types.xsd
└── models/
    └── order.xsd
```

```
python xsdtojson.py my_xsd_project/ -m main.xsd -o ./tests/out/output_schema.json -p
```

Un autre exemple :
```
python xsdtojson.py ./tests/in/ -m ApplicationData.xsd -o ./tests/out/ApplicationData.xsd.no-ref.json -p --no-ref
```