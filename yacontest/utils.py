import os
import shutil


def clean_dir(dirname):
    for root, dirs, files in os.walk(dirname):
        for f in files:
            os.unlink(os.path.join(root, f))
        for d in dirs:
            shutil.rmtree(os.path.join(root, d))

def choice(prompt, variants, default=None):
    def get_number():
        ans = input()
        while not ans.isnumeric():
            print('Enter a number (0 to cancel choice):')
            ans = input()
        return int(ans)

    print(prompt)
    for i, var in enumerate(variants):
        print('{}) {}'.format(i + 1, var))

    ans = get_number()
    if 0 < ans <= len(variants):
        return variants[ans - 1]
    return default
