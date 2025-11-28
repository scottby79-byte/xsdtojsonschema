# XSD to JSON Schema Converter

Ce programme Python analyse un ou plusieurs fichiers de schéma XML (XSD) et génère un fichier JSON Schema correspondant. Il prend en charge les imports et inclusions XSD, résout les références aux types et éléments globaux, et traduit les constructions XSD standard (types complexes, types simples, éléments, attributs, groupes, etc.) en concepts JSON Schema équivalents (objets, propriétés, types, énumérations, motifs, etc.).
L'objectif est de fournir un schéma JSON utilisable pour valider des documents JSON qui représentent l'équivalent structurel des documents XML conformes au XSD original.

L'application est hebergé sur Render.com : https://xsdtojsonschema.onrender.com/

## Fonctionnalités et Support XSD

## 🛠️ Concepts XSD Mappés

Le tableau ci-dessous détaille les concepts XSD pris en charge et leur traduction en JSON Schema (Draft-07) :

| Concept XSD | Traduction JSON Schema | Détails de la mise en œuvre |
| :--- | :--- | :--- |
| **Structure** | | |
| `xs:complexType` | `"type": "object"`, `"properties"` | Définitions enregistrées dans `#/definitions`. |
| `xs:element` | Propriété (`"properties"`) ou `$ref` | Gère les références et les définitions inline. |
| `xs:sequence`, `xs:all` | `"properties"` et `"required"` | Définissent l'ordre des propriétés, la validation se concentre sur la présence. |
| `xs:choice` | **`"oneOf"`** | Liste des options possibles (avec les corrections d'imbrication). |
| `xs:group` | Fusion des propriétés ou **`"oneOf"`** (si le groupe contient un choix) | Gère la fusion de contenu dans le contexte parent. |
| **Types Simples** | | |
| Types Numériques/Chaînes | Mappage exhaustif des types XSD intégrés | Utilisation de `XSD_TO_JSON_TYPE_MAP` pour la conversion des types de base. |
| `xs:list` | `"type": "array"`, `"items"` | Gère les listes de types simples XSD. |
| `xs:union` | `"type": [...]` ou `"oneOf"` | Gère les unions de types XSD. |
| **Restrictions** | | |
| `xs:restriction` (Facettes) | `"enum"`, `"pattern"`, `"minLength"`, `"maximum"`, etc. | Traduction des contraintes de validation. |
| **Métadonnées** | | |
| `xs:annotation/documentation` | `"description"` | Ajout de la documentation directement dans le schéma JSON. |
| `fixed` / `default` | `"const"` / `"default"` | Conversion de la valeur au type JSON cible. |
| **Attributs** | | |
| `xs:attribute` | `"properties"` de l'objet parent. | Gère `use="required"` et la résolution des références d'attributs. |
| `xs:anyAttribute` | `"additionalProperties": true` | Permet des attributs non spécifiés. |


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

## ⚖️ Licence

Ce projet est sous la **Licence MIT**. Voir le fichier `LICENSE` pour plus de détails.
