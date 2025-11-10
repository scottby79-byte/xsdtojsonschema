import argparse
import json
import os

from xsdtojson.xsd_parser import XSDParser
from xsdtojson.json_schema_converter import XSDToJsonSchemaConverter
from xsdtojson.file_utils import FileUtils # Pour la logique de chemin dans main également 

def main():
    parser = argparse.ArgumentParser(
        description="Convertit un fichier XSD ou une arborescence de fichiers XSD en JSON Schema."
    )
    parser.add_argument(
        "input_path",
        type=str,
        help="Le chemin vers le fichier XSD principal ou le répertoire contenant l'arborescence des fichiers XSD."
    )
    parser.add_argument(
        "-m", "--main-xsd",
        type=str,
        help="Nom du fichier XSD principal (si 'input_path' est un répertoire). Ex: 'root.xsd'."
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Le chemin vers le fichier de sortie JSON Schema (par défaut: <nom_fichier_xsd_principal>.json)."
    )
    parser.add_argument(
        "-p", "--pretty",
        action="store_true",
        help="Formate le JSON de sortie avec une indentation lisible."
    )
    parser.add_argument(
        "--no-ref",
        action="store_true",
        help="Désactive l'utilisation des références ($ref) vers les définitions. Les types seront inclus directement (inlining)."
    )


    args = parser.parse_args()

    input_path = args.input_path
    output_file_path = args.output
    main_xsd_filename = args.main_xsd
    inline_definitions = args.no_ref 

    xsd_parser = XSDParser()
    json_converter = XSDToJsonSchemaConverter(xsd_parser, inline_definitions=inline_definitions) 

    search_paths = []
    main_xsd_full_path = None

    if os.path.isdir(input_path):
        print(f"Scanning directory: {input_path}")
        
        # Collect all directories for search_paths using os.walk
        for root_dir, dirs, files in os.walk(input_path):
            search_paths.append(root_dir)
        # Ensure search_paths are unique
        search_paths = list(set(search_paths)) 
        
        if main_xsd_filename:
            print(f"  Searching for main XSD file '{main_xsd_filename}' in directory '{input_path}'...")
            found_main_xsd = False
            for root_dir, dirs, files in os.walk(input_path):
                for file_name in files:
                    if file_name == main_xsd_filename:
                        potential_main_path = os.path.normpath(os.path.join(root_dir, file_name))
                        if os.path.exists(potential_main_path) and os.path.isfile(potential_main_path):
                            main_xsd_full_path = potential_main_path
                            found_main_xsd = True
                            print(f"  (Debug: Found main XSD at: {main_xsd_full_path})")
                            break # Found the file, exit inner loop
                if found_main_xsd:
                    break # Found the file, exit outer loop
            
            if not main_xsd_full_path:
                print(f"Erreur: Le fichier XSD principal '{main_xsd_filename}' n'a pas été trouvé dans l'arborescence '{input_path}'.")
                print(f"  Vérifiez que le nom du fichier est correct et qu'il se trouve bien sous '{input_path}'.")
                return
        else:
            print("Pour un répertoire, il est fortement recommandé de spécifier le fichier XSD principal avec '-m' ou '--main-xsd'.")
            print("Tentative de détection du XSD principal (le premier .xsd trouvé dans le répertoire racine)...")
            
            potential_root_xsd_files = []
            # Only search directly in the input_path for a root XSD if -m is not provided
            for file_name in os.listdir(input_path):
                full_path = os.path.join(input_path, file_name)
                if file_name.endswith(".xsd") and os.path.isfile(full_path):
                    potential_root_xsd_files.append(full_path)
            
            if potential_root_xsd_files:
                main_xsd_full_path = os.path.normpath(potential_root_xsd_files[0])
                print(f"Utilisation de '{os.path.basename(main_xsd_full_path)}' comme XSD principal détecté.")
            else:
                print(f"Aucun fichier XSD principal n'a pu être détecté directement dans le répertoire '{input_path}'.")
                return

    elif os.path.isfile(input_path) and input_path.endswith(".xsd"):
        main_xsd_full_path = os.path.normpath(input_path)
        search_paths.append(os.path.dirname(main_xsd_full_path))
    else:
        print(f"Le chemin d'entrée '{input_path}' n'est ni un répertoire valide, ni un fichier XSD.")
        return

    print(f"\nStarting XSD parsing from: {main_xsd_full_path}")
    main_root_element = xsd_parser.parse_xsd_file(main_xsd_full_path, search_paths) # Pass the collected search_paths

    if main_root_element is None:
        print(f"Erreur: Impossible de charger le fichier XSD principal '{main_xsd_full_path}'.")
        return

    json_schema = json_converter.convert_xsd_to_json_schema(main_root_element)

    if json_schema:
        if not output_file_path:
            if os.path.isdir(input_path) and main_xsd_filename:
                base_name = os.path.splitext(main_xsd_filename)[0]
            elif os.path.isfile(input_path):
                base_name = os.path.splitext(os.path.basename(input_path))[0]
            else:
                base_name = "output_schema"
            output_file_path = f"{base_name}.json"
            
        try:
            with open(output_file_path, "w", encoding="utf-8") as f:
                if args.pretty:
                    json.dump(json_schema, f, indent=4, ensure_ascii=False)
                else:
                    json.dump(json_schema, f, ensure_ascii=False)
            print(f"Le JSON Schema a été généré avec succès dans '{output_file_path}'")
        except IOError as e:
            print(f"Erreur lors de l'écriture du fichier de sortie: {e}")

if __name__ == "__main__":
    main()