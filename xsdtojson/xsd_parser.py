import os
import logging
from lxml import etree
from xsdtojson.file_utils import FileUtils
from xsdtojson.constants import XSD_NAMESPACE

# Configure le logger pour ce module
logger = logging.getLogger(__name__)

class XSDParser:
    """
    Gère le parsing des fichiers XSD, y compris les imports et includes.
    """
    def __init__(self):
        # Stores all parsed XSD roots along with their source paths.
        # Key: targetNamespace (for imports) or normalized file path (for includes/no targetNamespace)
        # Value: A tuple (root_element, normalized_file_path)
        self.all_xsd_roots = {}
        self.processed_files = set() # Keep track of files already processed to avoid infinite loops

    def parse_xsd_file(self, file_path: str, search_paths: list):
        """
        Parse un seul fichier XSD et ses imports/includes récursivement.

        Args:
            file_path (str): Le chemin du fichier XSD à parser.
            search_paths (list): Une liste de répertoires pour rechercher les fichiers importés/inclus.

        Returns:
            etree.Element | None: L'élément racine du fichier XSD si parsé avec succès, None sinon.
        """
        normalized_file_path = os.path.normpath(file_path)
        
        if normalized_file_path in self.processed_files:
            for (root_elem, source_path) in self.all_xsd_roots.values():
                if source_path == normalized_file_path:
                    logger.info(f"File already processed: {normalized_file_path}. Returning cached root.")
                    return root_elem
            return None

        self.processed_files.add(normalized_file_path)

        try:
            tree = etree.parse(normalized_file_path)
            root = tree.getroot()
            target_namespace = root.get("targetNamespace")
            
            root_info = (root, normalized_file_path)

            if target_namespace:
                if target_namespace not in self.all_xsd_roots:
                    self.all_xsd_roots[target_namespace] = root_info
                    logger.info(f"Stored root for NS '{target_namespace}': {normalized_file_path}")
                else:
                    logger.info(f"TargetNamespace '{target_namespace}' already exists from {self.all_xsd_roots[target_namespace][1]}. Keeping existing definition for NS lookup.")
            
            if normalized_file_path not in self.all_xsd_roots:
                self.all_xsd_roots[normalized_file_path] = root_info 
                logger.info(f"Stored root for path: {normalized_file_path}")

            # Process imports
            for imp in root.findall(f"{XSD_NAMESPACE}import"):
                schema_location = imp.get("schemaLocation")
                namespace = imp.get("namespace")
                if schema_location:
                    imported_file_path = FileUtils.get_file_path(normalized_file_path, schema_location, search_paths)
                    if imported_file_path:
                        logger.info(f"Importing: {imported_file_path} for namespace '{namespace}'")
                        self.parse_xsd_file(imported_file_path, search_paths)
                    else:
                        logger.warning(f"Imported schemaLocation '{schema_location}' not found for namespace '{namespace}' (referenced in {normalized_file_path})")

            # Process includes
            for inc in root.findall(f"{XSD_NAMESPACE}include"):
                schema_location = inc.get("schemaLocation")
                if schema_location:
                    included_file_path = FileUtils.get_file_path(normalized_file_path, schema_location, search_paths)
                    if included_file_path:
                        logger.info(f"Including: {included_file_path}")
                        self.parse_xsd_file(included_file_path, search_paths)
                    else:
                        logger.warning(f"Included schemaLocation '{schema_location}' not found (referenced in {normalized_file_path})")
            
            return root

        except etree.XMLSyntaxError as e:
            logger.error(f"Erreur de syntaxe XML dans le fichier XSD '{normalized_file_path}': {e}")
            return None
        except FileNotFoundError:
            logger.error(f"Le fichier XSD '{normalized_file_path}' n'a pas été trouvé.")
            return None
        except Exception as e:
            logger.error(f"Une erreur inattendue est survenue lors du parsing de '{normalized_file_path}': {e}")
            return None

    def get_relevant_roots_for_qname(self, current_xsd_root: etree.Element, qname_prefix: str | None, qname_local_name: str) -> list[etree.Element]:
        """
        Détermine les racines XSD pertinentes à rechercher pour un QName donné.
        Cela inclut la racine XSD du contexte actuel et toutes les racines importées/incluses.
        Si un préfixe est fourni, il tente de résoudre le namespace associé.
        """
        root_to_search_first = current_xsd_root
        
        if qname_prefix:
            ns_map = current_xsd_root.nsmap if current_xsd_root is not None else {}
            target_namespace_uri = ns_map.get(qname_prefix)

            if target_namespace_uri and target_namespace_uri in self.all_xsd_roots:
                root_to_search_first = self.all_xsd_roots[target_namespace_uri][0]
                logger.info(f"Resolved NS '{qname_prefix}' to '{target_namespace_uri}', searching in {FileUtils.get_root_source_path(root_to_search_first, self.all_xsd_roots)}")
            elif target_namespace_uri:
                logger.warning(f"Namespace URI '{target_namespace_uri}' for prefix '{qname_prefix}' (from '{qname_prefix}:{qname_local_name}') not found as a targetNamespace of any loaded XSD. Will search all loaded schemas.")
            else:
                # This could happen if the prefix is not declared in the current XSD but in an imported one.
                # We will still search all loaded schemas, but the warning is useful.
                logger.warning(f"Namespace prefix '{qname_prefix}' for '{qname_prefix}:{qname_local_name}' not resolved in current XSD ({FileUtils.get_root_source_path(current_xsd_root, self.all_xsd_roots) or 'unknown path'}). Will search all loaded schemas.")
        else:
            current_target_ns = current_xsd_root.get("targetNamespace") if current_xsd_root is not None else None
            if current_target_ns and current_target_ns in self.all_xsd_roots:
                root_to_search_first = self.all_xsd_roots[current_target_ns][0]
                logger.info(f"No prefix, using current targetNamespace '{current_target_ns}', searching in {FileUtils.get_root_source_path(root_to_search_first, self.all_xsd_roots)}")

        search_roots = [root_to_search_first]
        for key, value_tuple in self.all_xsd_roots.items():
            r_elem = value_tuple[0]
            if r_elem is not root_to_search_first: # Avoid duplicating the first root if it's already added
                search_roots.append(r_elem)
       
        unique_search_roots = []
        seen_roots_ids = set()
        for r_elem in search_roots:
            if id(r_elem) not in seen_roots_ids:
                unique_search_roots.append(r_elem)
                seen_roots_ids.add(id(r_elem))
        return unique_search_roots
