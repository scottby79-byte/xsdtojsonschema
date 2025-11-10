import os
import zipfile
import tempfile
import json
from flask import Flask, request, render_template, jsonify
from werkzeug.utils import secure_filename # Pour sécuriser le nom du fichier
from xsdtojson.xsd_parser import XSDParser
from xsdtojson.json_schema_converter import XSDToJsonSchemaConverter

app = Flask(__name__)
# Définissez un répertoire pour les uploads sécurisés si vous ne travaillez pas avec tempfile
# app.config['UPLOAD_FOLDER'] = 'uploads'
# os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_xsd_to_json():
    if 'xsd_archive' not in request.files:
        return jsonify({"error": "Aucun fichier d'archive XSD n'a été fourni."}), 400

    zip_file = request.files['xsd_archive']
    if zip_file.filename == '':
        return jsonify({"error": "Aucun fichier sélectionné."}), 400
    if not secure_filename(zip_file.filename).endswith('.zip'):
        return jsonify({"error": "Le fichier doit être une archive ZIP."}), 400

    pretty_print = 'pretty' in request.form
    no_ref = 'no_ref' in request.form
    main_xsd_name = request.form.get('main_xsd_name', '').strip()

    # Utilisation d'un répertoire temporaire pour la décompression
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            zip_path = os.path.join(temp_dir, secure_filename(zip_file.filename))
            zip_file.save(zip_path)

            with zipfile.ZipFile(zip_path, 'r') as zf:
                # Extraire tous les fichiers dans le répertoire temporaire
                zf.extractall(temp_dir)

            input_xsd_path = None
            if main_xsd_name:
                # Normaliser le chemin principal pour gérer les sous-répertoires dans le zip
                input_xsd_path = os.path.join(temp_dir, main_xsd_name)
                if not os.path.exists(input_xsd_path):
                    # Si le chemin exact n'existe pas, essayer de trouver le fichier n'importe où dans le répertoire décompressé
                    found_path = None
                    for root, _, files in os.walk(temp_dir):
                        if main_xsd_name in files:
                            found_path = os.path.join(root, main_xsd_name)
                            break
                    if found_path:
                        input_xsd_path = found_path
                    else:
                        return jsonify({"error": f"Le fichier XSD principal '{main_xsd_name}' n'a pas été trouvé dans l'archive ou ses sous-répertoires."}), 400
            else:
                # Logique pour trouver le XSD principal si non spécifié (simplifié)
                # Cela suppose que le XSD principal est le seul ou qu'il est évident
                xsd_files_in_temp_dir = [f for f in os.listdir(temp_dir) if f.endswith('.xsd')]
                if len(xsd_files_in_temp_dir) == 1:
                    input_xsd_path = os.path.join(temp_dir, xsd_files_in_temp_dir[0])
                else:
                    # Plus complexe: parcourir et choisir un XSD principal si non spécifié
                    # Pour l'instant, force l'utilisateur à spécifier si plusieurs XSD ou structure complexe
                    return jsonify({"error": "Veuillez spécifier le nom du fichier XSD principal (ex: 'root.xsd') car l'archive contient plusieurs XSD ou une structure de répertoires."}), 400
            
            # La base_path pour le XSDParser doit être le répertoire où les imports/includes peuvent être trouvés
            # C'est souvent le répertoire parent du XSD principal
            search_paths = []            
            base_path_for_parser = os.path.dirname(input_xsd_path)

            search_paths.append(base_path_for_parser)
            search_paths = list(set(search_paths))
            
            xsd_parser = XSDParser()            
            main_xsd_root = xsd_parser.parse_xsd_file(input_xsd_path,search_paths)

            converter = XSDToJsonSchemaConverter(xsd_parser,inline_definitions=no_ref)
            json_schema_output = converter.convert_xsd_to_json_schema(main_xsd_root)

            if pretty_print:
                json_output_str = json.dumps(json_schema_output, indent=4, ensure_ascii=False)
            else:
                json_output_str = json.dumps(json_schema_output, ensure_ascii=False)

            return jsonify(json_schema_output) # Retourne le JSON directement

        except zipfile.BadZipFile:
            return jsonify({"error": "Le fichier téléchargé n'est pas une archive ZIP valide."}), 400
        except Exception as e:
            # Gérer les erreurs de manière plus spécifique si possible
            return jsonify({"error": f"Une erreur interne est survenue lors de la conversion : {str(e)}"}), 500

if __name__ == '__main__':
    # Lance l'application Flask
    # Pour un environnement de production, utilisez un serveur WSGI comme Gunicorn ou uWSGI
    app.run(debug=True, port=8080)