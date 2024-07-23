#import subprocess
#ssh = subprocess.Popen(["sbatch", "./test_slurm", "312","2b9c285bdf34b5df5378b572748da0512238ab31"])

try:
    from brainsharer.local_settings import DATABASES
except ImportError:
    DATABASES = {
        'default': {
            'NAME': 'brainsharer',                      # Or path to database file if using sqlite3.
            'USER': 'dklab',                      # Not used with sqlite3.
            'PASSWORD': '$pw4dklabdb',                  # Not used with sqlite3.
            'HOST': 'localhost',                      # Set to empty string for localhost. Not used with sqlite3.
        }
    }

host = DATABASES['default']['NAME']
password = DATABASES['default']['PASSWORD']
schema = DATABASES['default']['NAME']
host = DATABASES['default']['HOST']

print(host, password, schema, host)