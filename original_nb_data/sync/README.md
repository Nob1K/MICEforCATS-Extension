**If using for the first time, follow documentation in SETUP.md**

#### update.sh

A script that calls pull_all and commit the changes for you

#### pull.py

pulls a single file, usage: ```python pull.py <file_id> <output_path>```

#### pull_all.py

uses pull.py to pull all files registered in files.json (empty IDs are skipeed)

#### files.json

path in files.json is relative to original_files/