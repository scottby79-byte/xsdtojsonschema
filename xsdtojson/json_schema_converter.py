from lxml import etree
from xsdtojson.constants import XSD_NAMESPACE, XSD_TO_JSON_TYPE_MAP
from xsdtojson.xsd_parser import XSDParser
import logging

logger = logging.getLogger(__name__)
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
                    logger.warning(f"XSD type '{xsd_type_qname}' not found in XSD_TO_JSON_TYPE_MAP. Defaulting to 'string'.")
                    return "string" 
            else:
                return xsd_type_qname 

        full_xsd_type_uri_no_prefix = f"{XSD_NS}{xsd_type_qname}"
        if full_xsd_type_uri_no_prefix in XSD_TO_JSON_TYPE_MAP:
            return XSD_TO_JSON_TYPE_MAP[full_xsd_type_uri_no_prefix]
        logger.warning(f"XSD type '{xsd_type_qname}' not found in XSD_TO_JSON_TYPE_MAP. Defaulting to 'string'.")

        return xsd_type_qname


    def _get_search_roots(self, current_xsd_root: etree.Element, qname_prefix: Optional[str], qname_local_name: str) -> List[etree.Element]:
        """ 
        Utilise le parseur pour trouver les racines XSD pertinentes (gestion des imports et includes). 
        """        
        return self.xsd_parser.get_relevant_roots_for_qname(current_xsd_root, qname_prefix, qname_local_name)


    def _resolve_global_node(self, qname: str, current_xsd_root: etree.Element, xsd_tag: str) -> Tuple[Optional[etree.Element], Optional[etree.Element]]:
        """
        Aide générique pour résoudre un nœud XSD global (complexType, element, etc.) par son QName.
        Retourne le nœud trouvé et la racine du document où il a été trouvé.
        """
        prefix, local_name = (qname.split(":") if ":" in qname else (None, qname))
        
        for root_element in self._get_search_roots(current_xsd_root, prefix, local_name):
            for node in root_element.findall(f"{XSD_NS}{xsd_tag}"):
                if node.get("name") == local_name:
                    return node, root_element
        return None, None


    def _resolve_type(self, type_qname: str, current_xsd_root: etree.Element) -> dict:
        """ 
        Résout un type XSD défini par l'utilisateur (complexType ou simpleType) 
        et le convertit en $ref ou en schéma inline.
        """
        logger.debug(f"Resolving type: '{type_qname}'")
        
        found_node, found_in_root = self._resolve_global_node(type_qname, current_xsd_root, "complexType")
        if found_node is None:
            found_node, found_in_root = self._resolve_global_node(type_qname, current_xsd_root, "simpleType")

        if found_node is None or found_in_root is None:
            logger.warning(f"Could not resolve type '{type_qname}'. Returning default 'string'.")
            return {"type": "string"}

        local_type_name = type_qname.split(":")[-1]
        definition_key = local_type_name

        if self._inline_definitions:
            if etree.QName(found_node).localname == "complexType":
                logger.debug(f"Inlining complexType '{local_type_name}'.")
                return self._parse_complex_type(found_node, found_in_root)
            else: 
                logger.debug(f"Inlining simpleType '{local_type_name}'.")
                return self._parse_simple_type(found_node, found_in_root)
        else:
            if definition_key not in self.json_schema_definitions:
                logger.debug(f"Adding '{definition_key}' to definitions.")
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
            logger.debug(f"Type '{type_qname}' is a user-defined type. Resolving...")
            return self._resolve_type(json_type, current_xsd_root)
        else:
            logger.debug(f"Type '{type_qname}' is a built-in type, mapped to JSON type: '{json_type}'.")
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
        local_attribute_name = attribute_ref_qname.split(":")[-1]
        found_node, found_in_root = self._resolve_global_node(attribute_ref_qname, current_xsd_root, "attribute")
        
        if found_node is None or found_in_root is None:
            return local_attribute_name, {"type": "string"}, "optional"

        use = found_node.get("use", "optional") 
        # Utiliser found_in_root pour le contexte de parsing
        parsed_attr_info = self._parse_attribute_node(found_node, found_in_root)
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
            else:
                attr_schema["type"] = "string"
                logger.warning(f"Could not resolve global attribute reference '{attr_ref}'. Defaulting to type 'string'.")
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
        logger.debug(f"Parsing simpleType (parent: {parent_element_name or 'global'})")
        
        restriction_node = simple_type_node.find(f"{XSD_NS}restriction")
        if restriction_node is not None:
            base_qname = restriction_node.get("base")
            if base_qname:
                base_schema = self._get_type_schema(base_qname, simple_type_node, current_xsd_root)
                schema.update(base_schema)
            
            for child in restriction_node.iterchildren():
                tag_name = etree.QName(child).localname
                value = child.get("value") # Récupérer la valeur de la contrainte (facet)

                logger.debug(f"  - Found restriction facet: '{tag_name}' with value '{value}'")
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
                    except ValueError:
                        logger.warning(f"Invalid integer value for 'length' facet: '{value}'. Skipping.")
                
                # XSD minLength -> JSON minLength
                elif tag_name == "minLength" and value is not None:
                    try:
                        schema["minLength"] = int(value)
                    except ValueError:
                        logger.warning(f"Invalid integer value for 'minLength' facet: '{value}'. Skipping.")
                    
                # XSD maxLength -> JSON maxLength
                elif tag_name == "maxLength" and value is not None:
                    try:
                        schema["maxLength"] = int(value)
                    except ValueError:
                        logger.warning(f"Invalid integer value for 'maxLength' facet: '{value}'. Skipping.")

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
            logger.debug("  - Found list definition.")
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
            logger.debug("  - Found union definition.")
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
        logger.debug(f"Resolving attributeGroup: '{group_ref_qname}'")
        
        found_node, found_in_root = self._resolve_global_node(group_ref_qname, current_xsd_root, "attributeGroup")

        if found_node is None or found_in_root is None:
            logger.warning(f"Could not resolve attribute group '{group_ref_qname}'. Returning empty properties and required list.")
            return {}, []

        properties = {}
        required = []

        for attr_node in found_node.findall(f"{XSD_NS}attribute"):
            # Utiliser found_in_root pour le contexte de parsing
            parsed_attr = self._parse_attribute_node(attr_node, found_in_root)
            if parsed_attr:
                attr_name, attr_schema, use = parsed_attr
                properties[attr_name] = attr_schema
                if use == "required":
                    required.append(attr_name)

        for attr_group_ref in found_node.findall(f"{XSD_NS}attributeGroup"):
            nested_ref_name = attr_group_ref.get("ref")
            if nested_ref_name:
                # Utiliser found_in_root pour le contexte de parsing
                nested_props, nested_reqs = self._resolve_attribute_group(nested_ref_name, found_in_root)
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
    
    

    class SequenceProcessingState:
        """Maintient l'état lors du traitement d'une séquence XSD."""
        def __init__(self):
            self.properties: Dict[str, dict] = {}
            self.required: List[str] = []
            self.oneOf_options: List[dict] = []
            self.is_combining: bool = False


    # --- MÉTHODE CRUCIALE : GESTION DE LA SÉQUENCE ET DES CHOIX ---
    def _handle_sequence_element(self, element_node: etree.Element, current_xsd_root: etree.Element, state: SequenceProcessingState):
        """
        Traite un nœud <element> trouvé dans une séquence.
        
        Si le mode 'combining' est actif (à cause d'un choix précédent), l'élément
        est ajouté à toutes les options 'oneOf' existantes. Sinon, il est simplement
        ajouté à la liste des propriétés en cours.
        """
        element_schema, final_element_name, min_occurs = self._parse_element_for_content(element_node, current_xsd_root)
        if not final_element_name:
            return

        logger.debug(f"Processing element '{final_element_name}' in sequence. is_combining: {state.is_combining}")
        if state.is_combining:
            # Ajout à TOUTES les options oneOf existantes
            for option in state.oneOf_options:
                if final_element_name not in option.get("properties", {}):
                    option.setdefault("properties", {})[final_element_name] = element_schema
                    if min_occurs > 0:
                        option.setdefault("required", []).append(final_element_name)
        else:
            # Accumulation simple
            state.properties[final_element_name] = element_schema
            if min_occurs > 0:
                state.required.append(final_element_name)

    def _handle_sequence_group(self, group_node: etree.Element, current_xsd_root: etree.Element, state: SequenceProcessingState):
        """
        Traite un nœud <group> trouvé dans une séquence.
        
        Si le groupe se résout en un 'oneOf', il active le mode 'combining' et
        multiplie les options existantes. S'il se résout en une simple liste de
        propriétés, il les fusionne avec l'état actuel.
        """
        group_ref_name = group_node.get("ref")
        if not group_ref_name:
            return

        logger.debug(f"Processing group '{group_ref_name}' in sequence. is_combining: {state.is_combining}")
        group_schema = self._resolve_model_group(group_ref_name, current_xsd_root)
        
        resolved_group_schema = group_schema
        if "$ref" in group_schema:
            ref_name = group_schema["$ref"].split("/")[-1]
            if hasattr(self, 'json_schema_definitions') and ref_name in self.json_schema_definitions:
                resolved_group_schema = self.json_schema_definitions[ref_name]
        
        group_options = resolved_group_schema.get("oneOf", [])
        group_props = resolved_group_schema.get("properties", {})
        group_reqs = resolved_group_schema.get("required", [])

        if group_options:
            # Le groupe est un Choix (oneOf)
            state.is_combining = True
            if state.oneOf_options:
                # Combinaison (Choix * Choix)
                new_oneOf_options = []
                for existing_opt in state.oneOf_options:
                    for new_group_opt in group_options:
                        combined_properties = existing_opt.get("properties", {}).copy()
                        self._merge_properties_non_overwriting(combined_properties, new_group_opt.get("properties", {}))
                        combined_required = existing_opt.get("required", []).copy()
                        combined_required.extend(new_group_opt.get("required", []))
                        new_oneOf_options.append({"type": "object", "properties": combined_properties, "required": combined_required})
                state.oneOf_options = new_oneOf_options
            else:
                # Initialisation du oneOf avec les propriétés simples accumulées
                for group_opt in group_options:
                    combined_properties = state.properties.copy()
                    combined_properties.update(group_opt.get("properties", {}))
                    combined_required = state.required.copy()
                    combined_required.extend(group_opt.get("required", []))
                    state.oneOf_options.append({"type": "object", "properties": combined_properties, "required": combined_required})
                state.properties, state.required = {}, []
        elif group_props:
            # Le groupe est une Séquence simple
            if state.is_combining:
                for option in state.oneOf_options:
                    self._merge_properties_non_overwriting(option.setdefault("properties", {}), group_props)
                    option.setdefault("required", []).extend(group_reqs)
            else:
                state.properties.update(group_props)
                state.required.extend(group_reqs)

    def _handle_sequence_choice(self, choice_node: etree.Element, current_xsd_root: etree.Element, state: SequenceProcessingState):
        """
        Traite un nœud <choice> trouvé dans une séquence.
        
        Active le mode 'combining' et transforme les propriétés simples accumulées
        jusqu'à présent en une base pour chaque nouvelle option du choix. Si des
        choix précédents existaient, les nouvelles options sont ajoutées (aplaties).
        """
        state.is_combining = True
        logger.debug(f"Processing choice in sequence. Setting is_combining to True.")
        choice_schema_list = self._parse_choice(choice_node, current_xsd_root)
        
        if state.oneOf_options:
            # Aplatissement (Choix successifs)
            state.oneOf_options.extend(choice_schema_list)
        else:
            # Initialisation du oneOf avec les propriétés simples accumulées
            for choice_opt in choice_schema_list:
                combined_properties = state.properties.copy()
                combined_properties.update(choice_opt.get("properties", {}))
                combined_required = state.required.copy()
                combined_required.extend(choice_opt.get("required", []))
                state.oneOf_options.append({"type": "object", "properties": combined_properties, "required": combined_required})
            state.properties, state.required = {}, []

    def _handle_sequence_any(self, any_node: etree.Element, state: SequenceProcessingState):
        """
        Traite un nœud <any> trouvé dans une séquence.
        
        Ajoute 'additionalProperties: true' au contexte approprié (soit au niveau
        des propriétés de base, soit à chaque option 'oneOf' si le mode 'combining'
        est actif).
        """
        if not state.is_combining:
            logger.debug("Adding 'additionalProperties: true' due to xs:any in non-combining context.")
            state.properties["additionalProperties"] = True
        else:
            for option in state.oneOf_options:
                option["additionalProperties"] = True

    def _process_sequence_content(self, parent_node: etree.Element, current_xsd_root: etree.Element) -> Tuple[Dict[str, dict], List[str], Optional[List[dict]]]:
        """
        Traite le contenu d'un xs:sequence ou xs:all en répartissant chaque nœud enfant
        à des sous-méthodes de traitement spécialisées.
        
        Cette méthode orchestre la construction du schéma en gérant un état de traitement
        qui accumule les propriétés simples et gère la logique complexe de combinaison
        lorsqu'un choix est rencontré.
        """
        state = self.SequenceProcessingState()

        for child_node in parent_node.iterchildren():
            if child_node.tag is etree.Comment or child_node.tag is etree.ProcessingInstruction:
                continue

            tag_name = etree.QName(child_node).localname
            
            if tag_name == "element":
                self._handle_sequence_element(child_node, current_xsd_root, state)
            elif tag_name == "group":
                self._handle_sequence_group(child_node, current_xsd_root, state)
            elif tag_name == "choice":
                self._handle_sequence_choice(child_node, current_xsd_root, state)
            elif tag_name == "any":
                self._handle_sequence_any(child_node, state)
            
        # Nettoyage Final
        if state.oneOf_options:
            for option in state.oneOf_options:
                if "required" in option and not option["required"]:
                    del option["required"]
                if "type" not in option:
                    option["type"] = "object"

        return state.properties, state.required, state.oneOf_options if state.oneOf_options else None


    def _parse_attributes_and_groups(self, parent_node: etree.Element, current_xsd_root: etree.Element) -> Tuple[Dict[str, dict], List[str], bool]:
        """
        Analyse les nœuds enfants <attribute> et <attributeGroup> d'un nœud parent donné.
        
        Retours:
            - Un dictionnaire des propriétés d'attribut.
            - Une liste des noms d'attributs requis.
            - Un booléen indiquant si additionalProperties doit être vrai (en raison de <anyAttribute>).
        """
        attribute_properties = {}
        required_attributes = []
        has_any_attribute = False

        # Groupes d'Attributs
        for attr_ref_node in parent_node.findall(f"{XSD_NS}attributeGroup"):
            group_ref_name = attr_ref_node.get("ref")
            if group_ref_name:
                group_props, group_reqs = self._resolve_attribute_group(group_ref_name, current_xsd_root)
                attribute_properties.update(group_props)
                required_attributes.extend(group_reqs)
        
        # Attributs simples
        for attr_node in parent_node.findall(f"{XSD_NS}attribute"):
            parsed_attr = self._parse_attribute_node(attr_node, current_xsd_root)
            if parsed_attr:
                attr_name, attr_schema, use = parsed_attr
                attribute_properties[attr_name] = attr_schema
                if use == "required":
                    required_attributes.append(attr_name)

        if parent_node.find(f"{XSD_NS}anyAttribute") is not None:
            has_any_attribute = True
        
        return attribute_properties, required_attributes, has_any_attribute


    def _reparse_base_schema_if_incomplete(self, base_qname: str, resolved_base_schema: dict, current_xsd_root: etree.Element) -> Tuple[Dict[str, Any], List[str]]:
        """
        CORRECTION CRITIQUE DU CACHE: Si un schéma de base est résolu depuis le cache
        mais est une 'coquille' vide (ex: {"type": "object"}), cela peut indiquer une
        dépendance circulaire ou un ordre de parsing qui n'a pas entièrement peuplé
        la définition. Cette méthode force une nouvelle analyse du nœud XSD de base
        pour récupérer ses propriétés et attributs.
        """
        base_props = resolved_base_schema.get("properties", {})
        base_required = resolved_base_schema.get("required", [])

        is_empty_shell = resolved_base_schema.get("type") == "object" and not base_props and base_qname is not None
        if not is_empty_shell:
            return base_props, base_required

        logger.debug(f"Base schema for '{base_qname}' seems empty, attempting manual re-parse of its content.")
        
        # Recherche du nœud XSD de la base
        base_node, base_root = self._resolve_global_node(base_qname, current_xsd_root, "complexType")
        if base_node is None or base_root is None:
            base_node, base_root = self._resolve_global_node(base_qname, current_xsd_root, "simpleType")

        if base_node is None or base_root is None:
            logger.warning(f"Could not find XSD node for base type '{base_qname}' during re-parsing attempt. Inheritance might be incomplete.")
            return base_props, base_required

        # Re-parsing manuel des composants
        logger.debug(f"Manually re-parsing base type '{base_qname}' for attributes and content.")
        
        # a) Résolution manuelle des attributs
        attr_props, attr_reqs, _ = self._parse_attributes_and_groups(base_node, base_root)
        base_props.update(attr_props)
        base_required.extend(attr_reqs)
        
        # b) Résolution manuelle de la séquence/group
        sequence_node = base_node.find(f"{XSD_NS}sequence")
        if sequence_node is not None:
            s_props, s_reqs, _ = self._process_sequence_content(sequence_node, base_root) 
            base_props.update(s_props)
            base_required.extend(s_reqs)
            
        return base_props, base_required


    def _handle_complex_extension(self, extension_node: etree.Element, current_xsd_root: etree.Element) -> Tuple[Dict[str, Any], List[str]]:
        """
        Gère la logique d'extension <xs:extension>, en fusionnant les propriétés
        et les champs requis du type de base.
        """
        base_properties = {}
        base_required = []
        base_qname = extension_node.get("base")
        
        if not (base_qname and base_qname != "xs:anyType"):
            return base_properties, base_required

        logger.debug(f"  - Handling extension from base '{base_qname}'.")
        base_schema_result = self._get_type_schema(base_qname, extension_node, current_xsd_root)
        resolved_base_schema = base_schema_result

        # 1. Résolution de $ref pour obtenir le schéma de base complet
        if "$ref" in base_schema_result:
            ref_name = base_schema_result["$ref"].split("/")[-1]
            if hasattr(self, 'json_schema_definitions') and ref_name in self.json_schema_definitions:
                resolved_base_schema = self.json_schema_definitions[ref_name]
        
        # 2. Fusion des propriétés originales
        base_properties.update(resolved_base_schema.get("properties", {}))
        base_required.extend(resolved_base_schema.get("required", []))

        # 3. Re-parse si le schéma est une coquille vide (gestion du cache) et fusion
        reparsed_props, reparsed_reqs = self._reparse_base_schema_if_incomplete(base_qname, resolved_base_schema, current_xsd_root)
        base_properties.update(reparsed_props)
        base_required.extend(reparsed_reqs)

        return base_properties, base_required


    def _parse_complex_type(self, complex_type_node: etree.Element, current_xsd_root: etree.Element, parent_element_name: Optional[str] = None) -> dict:
        """ 
        Analyse un xs:complexType en gérant l'héritage, le contenu et les attributs.
        """
        logger.debug(f"Parsing complexType (parent: {parent_element_name or 'global'})")
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
                base_props, base_reqs = self._handle_complex_extension(extension_node, current_xsd_root)
                schema["properties"].update(base_props)
                required_fields.extend(base_reqs)
                target_content_node = extension_node 

        # --- BLOC 2: TRAITEMENT DU CONTENU (Séquence/Choix/All) DU NŒUD COURANT (OU EXTENSION) ---
        sequence_node = target_content_node.find(f"{XSD_NS}sequence")
        choice_node = target_content_node.find(f"{XSD_NS}choice")
        all_node = target_content_node.find(f"{XSD_NS}all")

        if sequence_node is not None or all_node is not None:
            content_node = sequence_node if sequence_node is not None else all_node
            logger.debug(f"  - Parsing content of sequence/all.")
            content_props, content_reqs, content_oneOf = self._process_sequence_content(content_node, current_xsd_root)
            
            if content_oneOf:
                schema["oneOf"] = content_oneOf
                if "type" in schema: del schema["type"]
                if "properties" in schema: del schema["properties"]
            else:
                schema["properties"].update(content_props)
                required_fields.extend(content_reqs)

        elif choice_node is not None and not is_extension:
             logger.debug(f"  - Parsing content of choice.")
             choice_schema_list = self._parse_choice(choice_node, current_xsd_root)
             if choice_schema_list:
                schema["oneOf"] = choice_schema_list
                if "type" in schema: del schema["type"]
                if "properties" in schema: del schema["properties"]

        # --- BLOC 3: TRAITEMENT DES ATTRIBUTS DU NŒUD COURANT (OU EXTENSION) ---
        attr_props, attr_reqs, has_any_attr = self._parse_attributes_and_groups(target_content_node, current_xsd_root)
        if attr_props:
            if "properties" not in schema:
                schema["properties"] = {}
            schema["properties"].update(attr_props)
            required_fields.extend(attr_reqs)
        
        if has_any_attr:
            schema["additionalProperties"] = True
        
        # --- BLOC 4: FINALISATION ---
        if "properties" in schema and not schema["properties"]:
             del schema["properties"]
             # Si un complexType n'a pas de propriétés, il ne doit pas être de type 'object'
             # sauf s'il a des attributs (géré au-dessus) ou hérite.
             if "type" in schema and "oneOf" not in schema and not is_extension:
                 del schema["type"]

        if required_fields:
            schema["required"] = sorted(list(set(required_fields)))
        
        return schema


    def _resolve_global_element(self, element_ref_qname: str, current_xsd_root: etree.Element) -> dict:
        """ 
        Résout une référence à un élément global (xs:element ref="..."). 
        """
        logger.debug(f"Resolving global element: '{element_ref_qname}'")
        
        found_node, found_in_root = self._resolve_global_node(element_ref_qname, current_xsd_root, "element")
        
        if found_node is None or found_in_root is None:
            logger.warning(f"Could not resolve global element reference '{element_ref_qname}'. Returning default 'object'.")
            return {"type": "object"}

        local_element_name = element_ref_qname.split(":")[-1]
        definition_key = local_element_name

        if self._inline_definitions:
            logger.debug(f"Inlining global element '{element_ref_qname}'.")
            return self._parse_element_definition_for_ref(found_node, found_in_root)
        else:
            logger.debug(f"Creating definition for global element '{element_ref_qname}'.")
            if definition_key not in self.json_schema_definitions:
                self.json_schema_definitions[definition_key] = self._parse_element_definition_for_ref(found_node, found_in_root)
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
        attr_props, attr_reqs, has_any_attr = self._parse_attributes_and_groups(element_node, current_xsd_root)
        if attr_props:
            if "type" not in element_schema or element_schema["type"] != "object":
                element_schema["type"] = "object"
            if "properties" not in element_schema:
                element_schema["properties"] = {}
            element_schema["properties"].update(attr_props)
            if "required" not in element_schema:
                element_schema["required"] = []
            element_schema["required"].extend(attr_reqs)
            element_schema["required"] = sorted(list(set(element_schema["required"])))

        if has_any_attr:
            element_schema["additionalProperties"] = True


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
        attr_props, attr_reqs, has_any_attr = self._parse_attributes_and_groups(element_node, current_xsd_root)
        if attr_props:
            if "type" not in schema or schema["type"] != "object":
                schema["type"] = "object"
            if "properties" not in schema:
                schema["properties"] = {}
            schema["properties"].update(attr_props)
            if "required" not in schema:
                schema["required"] = []
            schema["required"].extend(attr_reqs)
            schema["required"] = sorted(list(set(schema["required"])))

        if has_any_attr:
            schema["additionalProperties"] = True

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
        logger.debug(f"Resolving model group: '{group_ref_name}'")
        
        found_node, found_in_root = self._resolve_global_node(group_ref_name, current_xsd_root, "group")
        
        if found_node is None or found_in_root is None:
            logger.warning(f"Could not resolve model group reference '{group_ref_name}'. Returning default 'object'.")
            return {"type": "object"}

        local_group_name = group_ref_name.split(":")[-1]
        definition_key = f"group_{local_group_name}"

        if self._inline_definitions:
            logger.debug(f"Inlining model group '{group_ref_name}'.")
            return self._parse_model_group_definition(found_node, found_in_root)
        else:
            logger.debug(f"Creating definition for model group '{group_ref_name}'.")
            if definition_key not in self.json_schema_definitions:
                self.json_schema_definitions[definition_key] = self._parse_model_group_definition(found_node, found_in_root)
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