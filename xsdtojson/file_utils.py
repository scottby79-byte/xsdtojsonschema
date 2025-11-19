import os
import logging

logger = logging.getLogger(__name__)

class FileUtils:
    """
    Classe utilitaire pour la gestion des fichiers et des chemins.
    """
    @staticmethod
    def get_file_path(current_file_path: str, schema_location: str, search_paths: list) -> str | None:
        """
        Tente de trouver le fichier `schema_location` dans les `search_paths`.
        Privilégie les chemins relatifs au `current_file_path`.

        Args:
            current_file_path (str): Le chemin absolu du fichier XSD en cours de traitement.
            schema_location (str): Le chemin relatif ou nom de fichier spécifié dans 'schemaLocation'.
            search_paths (list): Une liste de répertoires où rechercher le fichier.

        Returns:
            str | None: Le chemin absolu du fichier trouvé, ou None si non trouvé.
        """
        logger.debug(f"Attempting to resolve schemaLocation: '{schema_location}'")
        # Essayer d'abord par rapport au fichier actuel
        base_dir = os.path.dirname(current_file_path)
        potential_path = os.path.normpath(os.path.join(base_dir, schema_location))
        logger.debug(f"Checking relative path: '{potential_path}'")
        if os.path.exists(potential_path):
            logger.debug(f"Found file at relative path: '{potential_path}'")
            return potential_path
        
        # Ensuite, rechercher dans tous les chemins de recherche fournis
        for search_path in search_paths:
            potential_path = os.path.normpath(os.path.join(search_path, schema_location))
            logger.debug(f"Checking in search path '{search_path}': '{potential_path}'")
            if os.path.exists(potential_path):
                logger.debug(f"Found file in search path: '{potential_path}'")
                return potential_path
        return None

    @staticmethod
    def get_root_source_path(root_element, all_xsd_roots: dict) -> str:
        """
        Trouve le chemin source d'un élément racine pour le débogage.

        Args:
            root_element: L'objet ElementTree du nœud racine.
            all_xsd_roots (dict): Dictionnaire de tous les éléments racines XSD chargés avec leurs chemins.

        Returns:
            str: Le chemin du fichier source ou une chaîne indiquant qu'il n'a pas été trouvé.
        """
        if root_element is None:
            return "No root element provided"
        for key, (r_elem, source_path) in all_xsd_roots.items():
            if r_elem is root_element:
                return source_path
        return "Unknown path (root not found in all_xsd_roots)"