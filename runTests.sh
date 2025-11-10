#!/bin/sh
python3 xsdtojson.py ./tests/in/ -m ApplicationData.xsd -o ./tests/out/ApplicationData.ref.json -p
python3 xsdtojson.py ./tests/in/ -m ApplicationData.xsd -o ./tests/out/ApplicationData.no-ref.json -p --no-ref
python3 xsdtojson.py ./tests/in/ -m complete_test_schema.xsd -o ./tests/out/complete_test_schema.xsd.ref.json -p
python3 xsdtojson.py ./tests/in/ -m complete_test_schema.xsd -o ./tests/out/complete_test_schema.xsd.no-ref.json -p --no-ref
python3 xsdtojson.py ./tests/in/ -m FullFeatureTest.xsd -o ./tests/out/FullFeatureTest.ref.json -p
python3 xsdtojson.py ./tests/in/ -m FullFeatureTest.xsd -o ./tests/out/FullFeatureTest.no-ref.json -p --no-ref