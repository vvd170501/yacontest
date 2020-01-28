import os
import shutil


def clean_dir(dirname):
    for root, dirs, files in os.walk(dirname):
        for f in files:
            os.unlink(os.path.join(root, f))
        for d in dirs:
            shutil.rmtree(os.path.join(root, d))
