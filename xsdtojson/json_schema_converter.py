from lxml import etree
from xsdtojson.constants import XSD_NAMESPACE, XSD_TO_JSON_TYPE_MAP
from xsdtojson.xsd_parser import XSDParser
from typing import Any, Dict, List, Optional, Tuple, Union

# Alias pour la lisibilité
XSD_NS = XSD_NAMESPACE

class XSDToJsonSchemaConverter:
    """
    Convertit les éléments XSD et les types complexes en JSON Schema.
    
    Gère:
    - Les séquences (xs:sequence), les choix (xs:choice) et les éléments optionnels.
    - La résolution des références de types, d'éléments, de groupes et d'attributs globaux.
    - La traduction des types simples XSD, incluant les listes, les unions et les restrictions.
    """
    def __init__(self, xsd_parser: XSDParser, inline_definitions: bool = False):
        # Le parseur XSD pour la résolution des imports et des références.
        self.xsd_parser = xsd_parser
        # Stocke les définitions de types et d'éléments globaux pour les références $ref.
        self.json_schema_definitions: Dict[str, dict] = {} 
        # Indicateur pour insérer les définitions en ligne plutôt que d'utiliser $ref.
        self._inline_definitions = inline_definitions


    # --- Méthodes d'aide pour le parsing et la résolution ---
    
    def _get_json_type(self, xsd_type_qname: str, element_node_or_root: etree.Element) -> Union[str, dict]:
        """ 
        Retourne le type JSON correspondant au type XSD donné. 
        Gère les types intégrés XSD (ex: xs:string -> string).
        """
        # ... (Logique de résolution de type XSD vers JSON Schema) ...
        if xsd_type_qname in XSD_TO_JSON_TYPE_MAP.values():
            return xsd_type_qname

        if ":" in xsd_type_qname:
            prefix, local_name = xsd_type_qname.split(":")
            
            ns_map = element_node_or_root.nsmap if element_node_or_root is not None else {}
            if not ns_map and hasattr(element_node_or_root, 'getroottree') and element_node_or_root.getroottree() is not None:
                ns_map = element_node_or_root.getroottree().getroot().nsmap
           
            resolved_uri = ns_map.get(prefix)
           
            if resolved_uri == XSD_NS.strip("{}"):
                full_xsd_type_uri = f"{XSD_NS}{local_name}"
                if full_xsd_type_uri in XSD_TO_JSON_TYPE_MAP:
                    return XSD_TO_JSON_TYPE_MAP[full_xsd_type_uri]
                else:
                    return "string" 
            else:
                return xsd_type_qname 

        full_xsd_type_uri_no_prefix = f"{XSD_NS}{xsd_type_qname}"
        if full_xsd_type_uri_no_prefix in XSD_TO_JSON_TYPE_MAP:
            return XSD_TO_JSON_TYPE_MAP[full_xsd_type_uri_no_prefix]

        return xsd_type_qname


    def _get_search_roots(self, current_xsd_root: etree.Element, qname_prefix: Optional[str], qname_local_name: str) -> List[etree.Element]:
        """ 
        Utilise le parseur pour trouver les racines XSD pertinentes (gestion des imports et includes). 
        """        
        return self.xsd_parser.get_relevant_roots_for_qname(current_xsd_root, qname_prefix, qname_local_name)


    def _resolve_type(self, type_qname: str, current_xsd_root: etree.Element) -> dict:
        """ 
        Résout un type XSD défini par l'utilisateur (complexType ou simpleType) 
        et le convertit en $ref ou en schéma inline.
        """
        # ... (Logique de recherche et de conversion/stockage dans self.json_schema_definitions) ...
        prefix, local_type_name = (type_qname.split(":") if ":" in type_qname else (None, type_qname))

        found_node = None
        found_in_root = None
        context_root = current_xsd_root

        for r_elem in self._get_search_roots(context_root, prefix, local_type_name):
            # Chercher ComplexType et SimpleType
            for complex_type_node in r_elem.findall(f"{XSD_NS}complexType"):
                if complex_type_node.get("name") == local_type_name:
                    found_node = complex_type_node
                    found_in_root = r_elem
                    break
            if found_node is not None: break
            for simple_type_node in r_elem.findall(f"{XSD_NS}simpleType"):
                if simple_type_node.get("name") == local_type_name:
                    found_node = simple_type_node
                    found_in_root = r_elem
                    break
            if found_node is not None: break
        
        if found_node is None:
            return {"type": "string"}

        definition_key = local_type_name

        if self._inline_definitions:
            if etree.QName(found_node).localname == "complexType":
                return self._parse_complex_type(found_node, found_in_root)
            else: 
                return self._parse_simple_type(found_node, found_in_root)
        else:
            if definition_key not in self.json_schema_definitions:
                if etree.QName(found_node).localname == "complexType":
                    self.json_schema_definitions[definition_key] = self._parse_complex_type(found_node, found_in_root)
                else: 
                    self.json_schema_definitions[definition_key] = self._parse_simple_type(found_node, found_in_root)
            return {"$ref": f"#/definitions/{definition_key}"}


    def _get_type_schema(self, type_qname: str, current_node: etree.Element, current_xsd_root: etree.Element) -> dict:
        """ 
        Fonction utilitaire qui cherche d'abord les types XSD intégrés, puis les types définis par l'utilisateur. 
        """
        json_type = self._get_json_type(type_qname, current_node)
        if isinstance(json_type, str) and json_type not in XSD_TO_JSON_TYPE_MAP.values():
            return self._resolve_type(json_type, current_xsd_root)
        else:
            return {"type": json_type}


    def _convert_value_to_json_type(self, value_str: str, json_schema_part: dict) -> Any:
        """ 
        Convertit une valeur string XSD (pour 'fixed' ou 'default') en type JSON approprié 
        (int, float, bool) basé sur le schéma cible.
        """
        # ... (Logique de conversion de valeur) ...
        target_json_type = None
        if "type" in json_schema_part:
            type_info = json_schema_part["type"]
            if isinstance(type_info, list):
                for t in ["integer", "number", "boolean", "string"]:
                    if t in type_info:
                        target_json_type = t
                        break
                if target_json_type is None: target_json_type = "string"
            elif isinstance(type_info, str):
                target_json_type = type_info
        else:
            target_json_type = "string"

        if target_json_type == "integer":
            try: return int(value_str)
            except ValueError: pass
        elif target_json_type == "number":
            try: return float(value_str)
            except ValueError: pass
        elif target_json_type == "boolean":
            return value_str.lower() == "true" or value_str == "1"
        
        return value_str


    def _resolve_global_attribute(self, attribute_ref_qname: str, current_xsd_root: etree.Element) -> Optional[Tuple[str, dict, str]]:
        """ 
        Résout une référence à un attribut global (xs:attribute ref="..."). 
        """
        # ... (Logique de résolution d'attribut global) ...
        prefix, local_attribute_name = (attribute_ref_qname.split(":") if ":" in attribute_ref_qname else (None, attribute_ref_qname))
        
        found_node = None
        context_root = current_xsd_root

        for r_elem in self._get_search_roots(context_root, prefix, local_attribute_name):
            for attribute_node in r_elem.findall(f"{XSD_NS}attribute"):
                if attribute_node.get("name") == local_attribute_name:
                    found_node = attribute_node
                    break
            if found_node is not None: break
        
        if found_node is None:
            return local_attribute_name, {"type": "string"}, "optional"

        use = found_node.get("use", "optional") 
        parsed_attr_info = self._parse_attribute_node(found_node, current_xsd_root)
        if parsed_attr_info:
            return parsed_attr_info[0], parsed_attr_info[1], use 
        return None


    def _parse_attribute_node(self, attribute_node: etree.Element, current_xsd_root: etree.Element) -> Optional[Tuple[str, dict, str]]:
        """ 
        Parse un nœud xs:attribute, gérant les références, les types et les contraintes (use, fixed, default). 
        """
        # ... (Logique de parsing d'attribut) ...
        attr_name = attribute_node.get("name")
        attr_type_raw = attribute_node.get("type")
        attr_ref = attribute_node.get("ref")
        use = attribute_node.get("use", "optional")
        fixed_value = attribute_node.get("fixed")
        default_value = attribute_node.get("default")

        attr_schema = {}

        if attr_ref:
            resolved_attr_info = self._resolve_global_attribute(attr_ref, current_xsd_root)
            if resolved_attr_info:
                resolved_name, resolved_type_schema, resolved_use = resolved_attr_info
                attr_name = resolved_name
                attr_schema = resolved_type_schema
                if use == "optional" and resolved_use == "required": use = "required"
                elif use == "optional": use = resolved_use
            else: attr_schema["type"] = "string"
        elif attr_type_raw:
            attr_schema = self._get_type_schema(attr_type_raw, attribute_node, current_xsd_root)
        else:
            attr_schema["type"] = "string"

        annotation_node = attribute_node.find(f"{XSD_NS}annotation")
        if annotation_node is not None:
            documentation_node = annotation_node.find(f"{XSD_NS}documentation")
            if documentation_node is not None and documentation_node.text:
                attr_schema["description"] = documentation_node.text.strip()

        if fixed_value is not None:
            attr_schema["const"] = self._convert_value_to_json_type(fixed_value, attr_schema)
        elif default_value is not None:
            attr_schema["default"] = self._convert_value_to_json_type(default_value, attr_schema)

        if attr_name:
            return (attr_name, attr_schema, use)
        return None
    

    def _parse_simple_type(self, simple_type_node: etree.Element, current_xsd_root: etree.Element, parent_element_name: Optional[str] = None) -> dict:
        """ 
        Parse un xs:simpleType, gérant les restrictions (enum, pattern, PLAGES et LONGUEURS), 
        les listes et les unions. 
        """
        schema: Dict[str, Any] = {}
        
        restriction_node = simple_type_node.find(f"{XSD_NS}restriction")
        if restriction_node is not None:
            base_qname = restriction_node.get("base")
            if base_qname:
                base_schema = self._get_type_schema(base_qname, simple_type_node, current_xsd_root)
                schema.update(base_schema)
            
            for child in restriction_node.iterchildren():
                tag_name = etree.QName(child).localname
                value = child.get("value") # Récupérer la valeur de la contrainte (facet)

                if tag_name == "enumeration":
                    if "enum" not in schema: schema["enum"] = []
                    # Conversion de la valeur au type JSON approprié
                    enum_value = self._convert_value_to_json_type(value, schema) 
                    if enum_value is not None:
                        schema["enum"].append(enum_value)
                
                elif tag_name == "pattern":
                    schema["pattern"] = value

                # --- GESTION DES FACETS DE LONGUEUR (pour types string ou array/list) ---
                # XSD length -> JSON minLength et maxLength
                elif tag_name == "length" and value is not None:
                    try:
                        length = int(value)
                        schema["minLength"] = length
                        schema["maxLength"] = length
                    except ValueError: pass
                
                # XSD minLength -> JSON minLength
                elif tag_name == "minLength" and value is not None:
                    try:
                        schema["minLength"] = int(value)
                    except ValueError: pass
                    
                # XSD maxLength -> JSON maxLength
                elif tag_name == "maxLength" and value is not None:
                    try:
                        schema["maxLength"] = int(value)
                    except ValueError: pass

                # --- GESTION DES FACETS DE PLAGE (pour types numériques) ---
                # XSD minInclusive -> JSON minimum (inclut la valeur)
                elif tag_name == "minInclusive" and value is not None:
                    # Utiliser le convertisseur pour garantir le bon type (int/float)
                    schema["minimum"] = self._convert_value_to_json_type(value, schema)
                    
                # XSD maxInclusive -> JSON maximum (inclut la valeur)
                elif tag_name == "maxInclusive" and value is not None:
                    schema["maximum"] = self._convert_value_to_json_type(value, schema)

                # --- GESTION DES FACETS DE CHIFFRES (totalDigits/fractionDigits) ---
                # Ces facets nécessitent une logique de conversion complexe en pattern RegEx 
                # en JSON Schema (Draft-07). Nous les ignorons ici pour la simplicité.
                elif tag_name == "totalDigits" and value is not None:
                    pass
                elif tag_name == "fractionDigits" and value is not None:
                    pass

        list_node = simple_type_node.find(f"{XSD_NS}list")
        if list_node is not None:
            item_type_qname = list_node.get("itemType")
            if item_type_qname:
                item_schema = self._get_type_schema(item_type_qname, simple_type_node, current_xsd_root)
                schema["type"] = "array"
                schema["items"] = item_schema
            else:
                inline_type = list_node.find(f"{XSD_NS}simpleType")
                if inline_type is not None:
                     schema["type"] = "array"
                     schema["items"] = self._parse_simple_type(inline_type, current_xsd_root)

        union_node = simple_type_node.find(f"{XSD_NS}union")
        if union_node is not None:
            member_types_raw = union_node.get("memberTypes")
            union_schemas = []
            
            if member_types_raw:
                member_types = member_types_raw.split()
                for qname in member_types:
                    union_schemas.append(self._get_type_schema(qname, simple_type_node, current_xsd_root))

            for inline_type in union_node.findall(f"{XSD_NS}simpleType"):
                union_schemas.append(self._parse_simple_type(inline_type, current_xsd_root))

            simple_types = [s["type"] for s in union_schemas if s.get("type") and isinstance(s["type"], str)]
            
            if simple_types:
                schema["type"] = list(set(simple_types))
            elif union_schemas:
                 schema["oneOf"] = union_schemas

        annotation_node = simple_type_node.find(f"{XSD_NS}annotation")
        if annotation_node is not None:
            documentation_node = annotation_node.find(f"{XSD_NS}documentation")
            if documentation_node is not None and documentation_node.text:
                schema["description"] = documentation_node.text.strip()
                
        if "type" not in schema and "enum" not in schema and "oneOf" not in schema:
            schema["type"] = "string" 

        return schema


    def _resolve_attribute_group(self, group_ref_qname: str, current_xsd_root: etree.Element) -> Tuple[dict, List[str]]:
        """ 
        Résout une référence xs:attributeGroup, en fusionnant les attributs et les contraintes 'required'. 
        """
        # ... (Logique de résolution de groupe d'attributs) ...
        prefix, local_group_name = (group_ref_qname.split(":") if ":" in group_ref_qname else (None, group_ref_qname))

        found_node = None
        
        for r_elem in self._get_search_roots(current_xsd_root, prefix, local_group_name):
            for group_node in r_elem.findall(f"{XSD_NS}attributeGroup"):
                if group_node.get("name") == local_group_name:
                    found_node = group_node
                    break
            if found_node is not None: break
        
        if found_node is None:
            return {}, []

        properties = {}
        required = []

        for attr_node in found_node.findall(f"{XSD_NS}attribute"):
            parsed_attr = self._parse_attribute_node(attr_node, current_xsd_root)
            if parsed_attr:
                attr_name, attr_schema, use = parsed_attr
                properties[attr_name] = attr_schema
                if use == "required":
                    required.append(attr_name)

        for attr_group_ref in found_node.findall(f"{XSD_NS}attributeGroup"):
            nested_ref_name = attr_group_ref.get("ref")
            if nested_ref_name:
                nested_props, nested_reqs = self._resolve_attribute_group(nested_ref_name, current_xsd_root)
                properties.update(nested_props)
                required.extend(nested_reqs)
                 
        return properties, required

    # --- Méthodes utilitaires ---
    
    def _parse_element_for_content(self, element_node: etree.Element, current_xsd_root: etree.Element) -> Tuple[dict, Optional[str], int]:
        """ 
        Extrait le schéma, le nom final, et minOccurs d'un nœud element. 
        Utilisé pour le contenu d'une séquence ou d'un choix.
        """
        # ... (Logique de parsing d'élément pour le contenu) ...
        element_name = element_node.get("name")
        element_ref = element_node.get("ref")
        final_element_name = element_name
        if not final_element_name and element_ref:
            final_element_name = element_ref.split(":")[-1]
            
        min_occurs = int(element_node.get("minOccurs", "1"))
        
        if final_element_name:
            property_schema = self._parse_element(element_node, current_xsd_root) 
            return property_schema, final_element_name, min_occurs
        
        return {}, None, 0


    def _merge_properties_non_overwriting(self, target_properties: Dict[str, dict], source_properties: Dict[str, dict]):
        """ 
        Met à jour target_properties avec source_properties sans écraser les clés existantes. 
        Utilisé pour fusionner des propriétés dans les options oneOf.
        """
        for prop_name, prop_schema in source_properties.items():
            if prop_name not in target_properties:
                target_properties[prop_name] = prop_schema
    
    
    # --- MÉTHODE CRUCIALE : GESTION DE LA SÉQUENCE ET DES CHOIX ---

    def _process_sequence_content(self, parent_node: etree.Element, current_xsd_root: etree.Element) -> Tuple[Dict[str, dict], List[str], Optional[List[dict]]]:
        """
        Traite le contenu d'un xs:sequence ou xs:all. Gère l'accumulation de propriétés
        simples et la combinaison avec des 'oneOf' (choix ou groupes de choix).
        """
        current_properties: Dict[str, dict] = {}
        current_required: List[str] = []
        oneOf_options: List[dict] = []
        
        # Indique si un oneOf a déjà été initialisé.
        is_combining = False 

        for child_node in parent_node.iterchildren():
            if child_node.tag is etree.Comment or child_node.tag is etree.ProcessingInstruction:
                continue

            tag_name = etree.QName(child_node).localname

            # --- 1. Gestion des ÉLÉMENTS simples ---
            if tag_name == "element":
                element_schema, final_element_name, min_occurs = self._parse_element_for_content(child_node, current_xsd_root)
                if not final_element_name: continue
                
                if is_combining:
                    # Ajout à TOUTES les options oneOf existantes
                    for option in oneOf_options:
                        if final_element_name not in option.get("properties", {}):
                            option.get("properties", {})[final_element_name] = element_schema
                            if min_occurs > 0:
                                if "required" not in option: option["required"] = []
                                option["required"].append(final_element_name)
                else:
                    # Accumulation simple
                    current_properties[final_element_name] = element_schema
                    if min_occurs > 0:
                        current_required.append(final_element_name)
                            
            # --- 2. Gestion des GROUPES de modèles (simples ou oneOf) ---
            elif tag_name == "group":
                group_ref_name = child_node.get("ref")
                if group_ref_name:
                    group_schema = self._resolve_model_group(group_ref_name, current_xsd_root)
                    
                    # Résolution du $ref pour obtenir les propriétés réelles
                    resolved_group_schema = group_schema
                    if "$ref" in group_schema:
                        ref_name = group_schema["$ref"].split("/")[-1]
                        if hasattr(self, 'json_schema_definitions') and ref_name in self.json_schema_definitions:
                            resolved_group_schema = self.json_schema_definitions[ref_name]
                    
                    group_options = resolved_group_schema.get("oneOf", [])
                    group_props = resolved_group_schema.get("properties", {})
                    group_reqs = resolved_group_schema.get("required", [])


                    if group_options:
                        # Cas 2a: Le groupe lui-même est un Choix (oneOf)
                        is_combining = True
                        
                        if oneOf_options:
                            # COMBINAISON (Choix * Choix) - Multiplie les options existantes par les nouvelles options du groupe
                            new_oneOf_options = []
                            
                            for existing_opt in oneOf_options:
                                existing_props = existing_opt.get("properties", {})
                                existing_reqs = existing_opt.get("required", [])

                                for new_group_opt in group_options:
                                    # Cloner et fusionner
                                    combined_properties = existing_props.copy()
                                    combined_required = existing_reqs.copy()
                                    
                                    # Merge new group properties/required into existing_opt clone
                                    self._merge_properties_non_overwriting(combined_properties, new_group_opt.get("properties", {}))
                                    combined_required.extend(new_group_opt.get("required", []))
                                    
                                    new_oneOf_options.append({
                                        "type": "object",
                                        "properties": combined_properties,
                                        "required": combined_required,
                                    })
                            
                            oneOf_options = new_oneOf_options # Remplacer l'ancien oneOf par le nouveau combiné
                        
                        else:
                            # Initialisation ou Combinaison de propriétés simples (précédentes) avec ce nouveau choix
                            if not current_properties and not current_required:
                                oneOf_options.extend(group_options)
                            else:
                                for group_opt in group_options:
                                    combined_properties = current_properties.copy()
                                    combined_properties.update(group_opt.get("properties", {})) 
                                    
                                    combined_required = current_required.copy()
                                    combined_required.extend(group_opt.get("required", []))
                                    
                                    oneOf_options.append({
                                        "type": "object",
                                        "properties": combined_properties,
                                        "required": combined_required,
                                    })
                                
                                # Les propriétés accumulées PRÉCÉDENTES sont transférées et effacées.
                                current_properties = {}
                                current_required = []


                    elif group_props:
                        # Cas 2b: Le groupe est une SÉQUENCE/ALL SIMPLE : fusion des propriétés
                        
                        if is_combining:
                            # Fusion dans TOUTES les options oneOf existantes
                            for option in oneOf_options:
                                # Fusion non-écrasante des propriétés
                                self._merge_properties_non_overwriting(option.get("properties", {}), group_props)
                                # Ajout des requis
                                if "required" in option:
                                     option["required"].extend(group_reqs)
                                else:
                                     option["required"] = group_reqs

                        else:
                            # Fusion simple (pas de oneOf actif)
                            current_properties.update(group_props)
                            current_required.extend(group_reqs)
                        
            # --- 3. Gestion du CHOIX ---
            elif tag_name == "choice":
                # Le xs:choice force le mode 'combining'
                is_combining = True
                choice_schema_list = self._parse_choice(child_node, current_xsd_root)
                
                if oneOf_options:
                    # APLATISSEMENT (Choix successifs)
                    oneOf_options.extend(choice_schema_list) 
                else:
                    # Initialisation ou Combinaison de propriétés simples (précédentes) avec le choix
                    if not current_properties and not current_required:
                        oneOf_options.extend(choice_schema_list)
                    else:
                        for choice_opt in choice_schema_list:
                            combined_properties = current_properties.copy()
                            combined_properties.update(choice_opt.get("properties", {}))
                            
                            combined_required = current_required.copy()
                            combined_required.extend(choice_opt.get("required", []))
                            
                            oneOf_options.append({
                                "type": "object",
                                "properties": combined_properties,
                                "required": combined_required,
                            })

                    # Les propriétés accumulées PRÉCÉDENTES sont transférées et effacées.
                    current_properties = {}
                    current_required = []

            # --- 4. Gestion de 'xs:any' ---
            elif tag_name == "any":
                 if not is_combining:
                     current_properties["additionalProperties"] = True
                 else:
                     for option in oneOf_options:
                         option["additionalProperties"] = True
            
        # --- 5. Nettoyage Final ---
        if oneOf_options:
            for option in oneOf_options:
                # Nettoyage des tableaux 'required' vides
                if "required" in option and not option["required"]:
                    del option["required"]
                # S'assurer que chaque option a 'type: object'
                if "type" not in option:
                    option["type"] = "object"

        return current_properties, current_required, oneOf_options if oneOf_options else None


    def _parse_complex_type(self, complex_type_node: etree.Element, current_xsd_root: etree.Element, parent_element_name: Optional[str] = None) -> dict:
        """ 
        Parse un xs:complexType. 
        
        Correction: Ajout d'une logique de secours pour forcer la résolution du contenu 
        du type de base si le cache a retourné une définition incomplète, garantissant 
        l'héritage des propriétés de groupe (dateCreation, priorite).
        """
        schema: Dict[str, Any] = {"type": "object", "properties": {}}
        required_fields: List[str] = []
        target_content_node = complex_type_node
        is_extension = False 

        # --- BLOC 1: GESTION DE L'HÉRITAGE (Uniquement si le type est DERIVÉ) ---
        complex_content_node = complex_type_node.find(f"{XSD_NS}complexContent")
        if complex_content_node is not None:
            extension_node = complex_content_node.find(f"{XSD_NS}extension")
            
            if extension_node is not None:
                is_extension = True
                base_qname = extension_node.get("base")
                
                if base_qname and base_qname != "xs:anyType":
                    base_schema_result = self._get_type_schema(base_qname, complex_type_node, current_xsd_root)
                    resolved_base_schema = base_schema_result

                    # 1. RESOLUTION DE REF POUR FUSION (Étape critique)
                    if "$ref" in base_schema_result:
                        ref_name = base_schema_result["$ref"].split("/")[-1]
                        if hasattr(self, 'json_schema_definitions') and ref_name in self.json_schema_definitions:
                            resolved_base_schema = self.json_schema_definitions[ref_name]
                    
                    # 2. PRÉPARATION DE LA FUSION
                    base_props = resolved_base_schema.get("properties", {})
                    base_required_fields = resolved_base_schema.get("required", [])

                    # CORRECTION CRITIQUE DU CACHE: Si le schéma de base est un objet mais est vide,
                    # il s'agit d'une coquille incomplète du cache. On force la recherche du nœud XSD pour re-résoudre.
                    if resolved_base_schema.get("type") == "object" and not base_props and base_qname is not None:
                        
                        prefix, local_type_name = (base_qname.split(":") if ":" in base_qname else (None, base_qname))
                        base_node = None
                        context_root = current_xsd_root

                        # 2.1. RECHERCHE DU NŒUD XSD DE LA BASE (Logique réutilisée de _resolve_type)
                        for r_elem in self._get_search_roots(context_root, prefix, local_type_name):
                            for complex_type_node_temp in r_elem.findall(f"{XSD_NS}complexType"):
                                if complex_type_node_temp.get("name") == local_type_name:
                                    base_node = complex_type_node_temp
                                    break
                            if base_node is not None: break
                        
                        # 2.2. RE-PARSING MANUEL DES COMPOSANTS (Si le nœud est trouvé)
                        if base_node is not None:
                            # a) Résolution manuelle des attributs (AG_Metadonnees)
                            for attr_group_ref in base_node.findall(f"{XSD_NS}attributeGroup"):
                                group_ref_name = attr_group_ref.get("ref")
                                if group_ref_name:
                                    g_props, g_reqs = self._resolve_attribute_group(group_ref_name, current_xsd_root)
                                    base_props.update(g_props)
                                    base_required_fields.extend(g_reqs) 
                            
                            # b) Résolution manuelle de la séquence/group (G_InformationsBase)
                            sequence_node = base_node.find(f"{XSD_NS}sequence")
                            if sequence_node is not None:
                                s_props, s_reqs, _ = self._process_sequence_content(sequence_node, current_xsd_root) 
                                base_props.update(s_props)
                                base_required_fields.extend(s_reqs)
                                
                    # 3. FUSION
                    schema["properties"].update(base_props) 
                    required_fields.extend(base_required_fields) 
                        
                target_content_node = extension_node 


        # --- BLOC 2: TRAITEMENT DU CONTENU (Séquence/Choix/All) DU NŒUD COURANT (OU EXTENSION) ---
        
        sequence_node = target_content_node.find(f"{XSD_NS}sequence")
        choice_node = target_content_node.find(f"{XSD_NS}choice")
        all_node = target_content_node.find(f"{XSD_NS}all")

        if sequence_node is not None or all_node is not None:
            content_node = sequence_node if sequence_node is not None else all_node
            
            content_props, content_reqs, content_oneOf = self._process_sequence_content(content_node, current_xsd_root)
            
            if content_oneOf:
                schema["oneOf"] = content_oneOf
                del schema["type"]
                if "properties" in schema: del schema["properties"]
            else:
                schema["properties"].update(content_props)
                required_fields.extend(content_reqs)

        elif choice_node is not None and not is_extension:
             choice_schema_list = self._parse_choice(choice_node, current_xsd_root)
             if choice_schema_list:
                schema["oneOf"] = choice_schema_list
                del schema["type"]
                if "properties" in schema: del schema["properties"]

        # --- BLOC 3: TRAITEMENT DES ATTRIBUTS DU NŒUD COURANT (OU EXTENSION) ---
        
        # Groupes d'Attributs
        for attr_ref_node in target_content_node.findall(f"{XSD_NS}attributeGroup"):
            group_ref_name = attr_ref_node.get("ref")
            if group_ref_name:
                group_props, group_reqs = self._resolve_attribute_group(group_ref_name, current_xsd_root)
                
                if "properties" not in schema: schema["properties"] = {} 
                
                schema["properties"].update(group_props)
                required_fields.extend(group_reqs)
        
        # Attributs simples
        for attr_node in target_content_node.findall(f"{XSD_NS}attribute"):
            parsed_attr = self._parse_attribute_node(attr_node, current_xsd_root)
            if parsed_attr:
                attr_name, attr_schema, use = parsed_attr
                
                if "properties" not in schema: schema["properties"] = {} 

                schema["properties"][attr_name] = attr_schema
                if use == "required":
                    required_fields.append(attr_name)

        if target_content_node.find(f"{XSD_NS}anyAttribute") is not None:
            if "properties" not in schema: schema["properties"] = {}
            schema["additionalProperties"] = True
        
        # --- BLOC 4: FINALISATION ---
        if "properties" in schema and not schema["properties"]:
             del schema["properties"]
             if "type" in schema and "oneOf" not in schema:
                 del schema["type"]

        if required_fields:
            schema["required"] = sorted(list(set(required_fields)))
        
        return schema


    def _resolve_global_element(self, element_ref_qname: str, current_xsd_root: etree.Element) -> dict:
        """ 
        Résout une référence à un élément global (xs:element ref="..."). 
        """
        # ... (Logique de résolution d'élément global, similaire à _resolve_type) ...
        prefix, local_element_name = (element_ref_qname.split(":") if ":" in element_ref_qname else (None, element_ref_qname))

        found_node = None
        context_root = current_xsd_root

        for r_elem in self._get_search_roots(context_root, prefix, local_element_name):
            for element_node in r_elem.findall(f"{XSD_NS}element"):
                if element_node.get("name") == local_element_name:
                    found_node = element_node
                    break
            if found_node is not None: break
        
        if found_node is None:
            return {"type": "object"}

        definition_key = local_element_name

        if self._inline_definitions:
            return self._parse_element_definition_for_ref(found_node, current_xsd_root)
        else:
            if definition_key not in self.json_schema_definitions:
                self.json_schema_definitions[definition_key] = self._parse_element_definition_for_ref(found_node, current_xsd_root)
            return {"$ref": f"#/definitions/{definition_key}"}


    def _parse_element(self, element_node: etree.Element, current_xsd_root: etree.Element) -> dict:
        """ 
        Parse un élément XSD, gérant les références, les types, les contraintes d'occurrence (array), 
        les attributs inlines et les valeurs par défaut. 
        """
        # ... (Logique de parsing d'élément) ...
        schema: Dict[str, Any] = {}
        element_type = element_node.get("type")
        element_ref = element_node.get("ref")
        min_occurs = int(element_node.get("minOccurs", "1"))
        max_occurs = element_node.get("maxOccurs", "1")
        nillable = element_node.get("nillable", "false").lower() == "true"
        fixed_value = element_node.get("fixed")
        default_value = element_node.get("default")

        is_array = False
        if max_occurs == "unbounded" or (isinstance(max_occurs, str) and max_occurs.isdigit() and int(max_occurs) > 1):
            is_array = True

        element_schema = {}

        if element_ref:
            element_schema = self._resolve_global_element(element_ref, current_xsd_root)
        else:
            if element_type:
                element_schema = self._get_type_schema(element_type, element_node, current_xsd_root)
            
            complex_type_node = element_node.find(f"{XSD_NS}complexType")
            simple_type_node = element_node.find(f"{XSD_NS}simpleType")

            if complex_type_node is not None:
                element_schema = self._parse_complex_type(complex_type_node, current_xsd_root, parent_element_name=element_node.get("name"))
            elif simple_type_node is not None:
                element_schema = self._parse_simple_type(simple_type_node, current_xsd_root, parent_element_name=element_node.get("name"))

        # Gestion des attributs inlines et des groupes d'attributs
        for attribute in element_node.findall(f"{XSD_NS}attribute"):
            # ... (Ajout des attributs simples) ...
            parsed_attr = self._parse_attribute_node(attribute, current_xsd_root)
            if parsed_attr:
                attr_name, attr_schema, use = parsed_attr
                if "type" not in element_schema or element_schema["type"] != "object": element_schema["type"] = "object"
                if "properties" not in element_schema: element_schema["properties"] = {}
                element_schema["properties"][attr_name] = attr_schema
                if use == "required":
                    if "required" not in element_schema: element_schema["required"] = []
                    element_schema["required"].append(attr_name)
        
        for attr_group_ref in element_node.findall(f"{XSD_NS}attributeGroup"):
            # ... (Ajout des groupes d'attributs) ...
            group_ref_name = attr_group_ref.get("ref")
            if group_ref_name:
                group_props, group_reqs = self._resolve_attribute_group(group_ref_name, current_xsd_root)
                if "type" not in element_schema or element_schema["type"] != "object": element_schema["type"] = "object"
                if "properties" not in element_schema: element_schema["properties"] = {}
                element_schema["properties"].update(group_props)
                if "required" not in element_schema: element_schema["required"] = []
                for req_attr in group_reqs:
                    if req_attr not in element_schema["required"]: element_schema["required"].append(req_attr)


        # Documentation, fixed, default, nillable 
        annotation_node = element_node.find(f"{XSD_NS}annotation")
        if annotation_node is not None:
            documentation_node = annotation_node.find(f"{XSD_NS}documentation")
            if documentation_node is not None and documentation_node.text:
                element_schema["description"] = documentation_node.text.strip()

        if fixed_value is not None and not is_array:
            element_schema["const"] = self._convert_value_to_json_type(fixed_value, element_schema)
        elif default_value is not None and not is_array:
            element_schema["default"] = self._convert_value_to_json_type(default_value, element_schema)

        if nillable:
            # Ajout de 'null' si l'élément est nillable
            current_json_type = element_schema.get("type")
            if isinstance(current_json_type, str):
                element_schema["type"] = [current_json_type, "null"]
            elif isinstance(current_json_type, list) and "null" not in current_json_type:
                current_json_type.append("null")
            elif not current_json_type:
                element_schema["type"] = ["object", "null"]


        if is_array:
            # Gestion de maxOccurs > 1 ou "unbounded" -> conversion en type "array"
            schema["type"] = "array"
            schema["items"] = element_schema
            if min_occurs > 0:
                schema["minItems"] = min_occurs
            if max_occurs != "unbounded":
                schema["maxItems"] = int(max_occurs)
        else:
            schema = element_schema

        return schema


    def _parse_element_definition_for_ref(self, element_node: etree.Element, current_xsd_root: etree.Element) -> dict:
        """ 
        Parse la définition d'un élément global lorsqu'il est référencé. 
        Similaire à _parse_element, mais sans gestion des min/maxOccurs.
        """
        # ... (Logique de parsing de définition d'élément) ...
        schema: Dict[str, Any] = {}
        element_type = element_node.get("type")

        if element_type:
            schema = self._get_type_schema(element_type, element_node, current_xsd_root)
        else:
            complex_type_node = element_node.find(f"{XSD_NS}complexType")
            simple_type_node = element_node.find(f"{XSD_NS}simpleType")

            if complex_type_node is not None:
                schema = self._parse_complex_type(complex_type_node, current_xsd_root, parent_element_name=element_node.get("name"))
            elif simple_type_node is not None:
                schema = self._parse_simple_type(simple_type_node, current_xsd_root, parent_element_name=element_node.get("name"))
            else:
                schema["type"] = "object"
        
        # Gestion des attributs
        for attribute in element_node.findall(f"{XSD_NS}attribute"):
             # ... (Ajout des attributs simples) ...
            parsed_attr = self._parse_attribute_node(attribute, current_xsd_root)
            if parsed_attr:
                attr_name, attr_schema, use = parsed_attr
                if "type" not in schema or schema["type"] != "object": schema["type"] = "object"
                if "properties" not in schema: schema["properties"] = {}
                schema["properties"][attr_name] = attr_schema
                if use == "required":
                    if "required" not in schema: schema["required"] = []
                    schema["required"].append(attr_name)
        
        for attr_group_ref in element_node.findall(f"{XSD_NS}attributeGroup"):
            # ... (Ajout des groupes d'attributs) ...
            group_ref_name = attr_group_ref.get("ref")
            if group_ref_name:
                group_props, group_reqs = self._resolve_attribute_group(group_ref_name, current_xsd_root)
                if "type" not in schema or schema["type"] != "object": schema["type"] = "object"
                if "properties" not in schema: schema["properties"] = {}
                schema["properties"].update(group_props)
                if "required" not in schema: schema["required"] = []
                for req_attr in group_reqs:
                    if req_attr not in schema["required"]: schema["required"].append(req_attr)

        return schema


    def _parse_choice(self, choice_node: etree.Element, current_xsd_root: etree.Element) -> List[dict]:
        """
        Traite le contenu d'un xs:choice et retourne une liste d'options pour le 'oneOf'.
        """
        choice_options: List[dict] = []
        
        for child_node in choice_node.iterchildren():
            if child_node.tag is etree.Comment or child_node.tag is etree.ProcessingInstruction:
                continue

            tag_name = etree.QName(child_node).localname
            
            # --- 1. Élément simple au sein du choix (comme produitSimple) ---
            if tag_name == "element":
                element_schema, final_element_name, min_occurs = self._parse_element_for_content(child_node, current_xsd_root)
                if not final_element_name: continue
                
                # Un élément simple devient une option unique
                option = {"type": "object", "properties": {final_element_name: element_schema}}
                if min_occurs > 0:
                    option["required"] = [final_element_name]
                choice_options.append(option)
                
            # --- 2. Séquence ou All au sein du choix (l'option perdue : ligneArticle/taxe) ---
            elif tag_name == "sequence" or tag_name == "all":
                # Une séquence interne est une SEULE option pour le choix.
                # On utilise _process_sequence_content pour extraire ses propriétés.
                props, reqs, nested_oneOf = self._process_sequence_content(child_node, current_xsd_root)
                
                if nested_oneOf:
                    # Si la séquence contient elle-même un choix imbriqué, on aplatit.
                    choice_options.extend(nested_oneOf)
                else:
                    # La séquence simple devient une seule option
                    option = {"type": "object", "properties": props}
                    if reqs:
                        option["required"] = reqs
                    choice_options.append(option)

            # --- 3. Choix imbriqué ---
            elif tag_name == "choice":
                # Récursion pour les choix imbriqués
                nested_options = self._parse_choice(child_node, current_xsd_root)
                choice_options.extend(nested_options)
            
            # --- 4. Groupe au sein du choix ---
            elif tag_name == "group":
                group_ref_name = child_node.get("ref")
                if group_ref_name:
                    group_schema = self._resolve_model_group(group_ref_name, current_xsd_root)
                    
                    resolved_group_schema = group_schema
                    if "$ref" in group_schema:
                        ref_name = group_schema["$ref"].split("/")[-1]
                        if hasattr(self, 'json_schema_definitions') and ref_name in self.json_schema_definitions:
                            resolved_group_schema = self.json_schema_definitions[ref_name]
                    
                    # Le groupe est lui-même un choix (oneOf)
                    if resolved_group_schema.get("oneOf"):
                        choice_options.extend(resolved_group_schema["oneOf"])
                    # Le groupe est une séquence simple et doit être encapsulé comme une option
                    elif resolved_group_schema.get("properties"):
                        option = {"type": "object", "properties": resolved_group_schema["properties"]}
                        if resolved_group_schema.get("required"):
                            option["required"] = resolved_group_schema["required"]
                        choice_options.append(option)
            
        return choice_options


    def _parse_model_group_definition(self, group_node: etree.Element, current_xsd_root: etree.Element) -> dict:
        """ 
        Parse une définition de xs:group, en utilisant _process_sequence_content pour gérer son contenu. 
        """
        # ... (Logique de parsing de groupe de modèle) ...
        schema: Dict[str, Any] = {}
        
        sequence_node = group_node.find(f"{XSD_NS}sequence")
        all_node = group_node.find(f"{XSD_NS}all")
        choice_node = group_node.find(f"{XSD_NS}choice")

        if sequence_node is not None or all_node is not None:
            node_to_process = sequence_node if sequence_node is not None else all_node
            
            # Utilise la logique de séquence pour déterminer si le groupe est une séquence simple ou un oneOf complexe
            content_props, required_fields, oneOf_list = self._process_sequence_content(node_to_process, current_xsd_root)
            
            schema["type"] = "object"
            if oneOf_list:
                schema["oneOf"] = oneOf_list
            elif content_props:
                schema["properties"] = content_props
                if required_fields:
                    schema["required"] = required_fields

        elif choice_node is not None:
            # Gère un groupe qui est un choix pur
            choice_schema_list = self._parse_choice(choice_node, current_xsd_root)
            if choice_schema_list:
                schema["oneOf"] = choice_schema_list
            else:
                schema["type"] = "object"
        else:
            schema["type"] = "object"

        return schema


    def _resolve_model_group(self, group_ref_name: str, current_xsd_root: etree.Element) -> dict:
        """ 
        Résout une référence xs:group et retourne son schéma correspondant. 
        """
        # ... (Logique de résolution de groupe de modèle) ...
        prefix, local_group_name = (group_ref_name.split(":") if ":" in group_ref_name else (None, group_ref_name))
        
        found_node = None
        context_root = current_xsd_root

        for r_elem in self._get_search_roots(context_root, prefix, local_group_name):
            for group_node in r_elem.findall(f"{XSD_NS}group"):
                if group_node.get("name") == local_group_name:
                    found_node = group_node
                    break
            if found_node is not None: break
        
        if found_node is None:
            return {"type": "object"}

        definition_key = f"group_{local_group_name}"

        if self._inline_definitions:
            return self._parse_model_group_definition(found_node, current_xsd_root)
        else:
            if definition_key not in self.json_schema_definitions:
                self.json_schema_definitions[definition_key] = self._parse_model_group_definition(found_node, current_xsd_root)
            return {"$ref": f"#/definitions/{definition_key}"}


    def convert_xsd_to_json_schema(self, main_xsd_root: etree.Element) -> dict:
        """ 
        Fonction principale de conversion. 
        Elle génère la structure racine du schéma JSON, y compris le 'oneOf' 
        si plusieurs éléments globaux sont définis.
        """
        # ... (Logique de la fonction principale) ...
        root_element_nodes = main_xsd_root.findall(f"{XSD_NS}element")
        
        if not root_element_nodes:
            return {}
        
        element_schemas = []
        
        for element_node in root_element_nodes:
            main_element_name = element_node.get("name")
            
            element_schema = self._parse_element(element_node, main_xsd_root)
            
            if main_element_name:
                element_schemas.append({
                    "type": "object",
                    "properties": {
                        main_element_name: element_schema
                    },
                    "required": [main_element_name]
                })

        final_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": f"Root Schema for {main_xsd_root.get('targetNamespace', 'document')}",
        }
        
        if main_xsd_root.get('targetNamespace'):
             final_schema["$id"] = f"{main_xsd_root.get('targetNamespace', 'http://example.com')}/document.json"
        
        if len(element_schemas) == 1:
            # S'il n'y a qu'un seul élément racine, il devient le schéma principal.
            final_schema.update(element_schemas[0])
            final_schema["title"] = f"Schema for {root_element_nodes[0].get('name')}"
            
            if main_xsd_root.get('targetNamespace'):
                final_schema["$id"] = f"{main_xsd_root.get('targetNamespace', 'http://example.com')}/{root_element_nodes[0].get('name')}.json"

        elif len(element_schemas) > 1:
            # S'il y a plusieurs éléments racine globaux, on utilise 'oneOf'.
            final_schema["oneOf"] = element_schemas
        
        if self.json_schema_definitions:
            final_schema["definitions"] = self.json_schema_definitions
            
        return final_schema