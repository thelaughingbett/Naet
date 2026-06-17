# dumping data
py -Xutf8 manage.py dumpdata -v 3   --format=json --indent=4   --natural-foreign --natural-primary -o  base/fixtures/data.json

python manage.py generate_mock_socials              # create/update both
python manage.py generate_mock_socials --clear      # wipe mock-* rows first, then regenerate
python manage.py generate_mock_socials --events-only
python manage.py generate_mock_socials --news-only

# migration hell

del base\migrations\0*.py