from huggingface_hub import HfApi
import secrets as pysecrets

api = HfApi()
user = api.whoami()["name"]
repo_id = f"{user}/luminarecs"
url = api.create_repo(repo_id=repo_id, repo_type="space", space_sdk="docker",
                      private=False, exist_ok=True)
print("SPACE:", url)

secrets = {
    "SECRET_KEY": pysecrets.token_urlsafe(48),
    "DB_NAME": "luminarecs_db",
    "DB_USER": "4Srr7NVBcb6BuJh.root",
    "DB_PASSWORD": "Y9X2A5LcPRkr0Wkk",
    "DB_HOST": "gateway01.ap-southeast-1.prod.aws.tidbcloud.com",
    "DB_PORT": "4000",
}
for k, v in secrets.items():
    api.add_space_secret(repo_id=repo_id, key=k, value=v)
    print("secret ok:", k)

variables = {
    "DEBUG": "False",
    "ALLOWED_HOSTS": f"{user.lower()}-luminarecs.hf.space",
    "CSRF_TRUSTED_ORIGINS": f"https://{user.lower()}-luminarecs.hf.space",
    "TRUST_PROXY": "True",
    "CACHE_BACKEND": "locmem",
    "DB_SSL_CA": "/usr/local/lib/python3.12/site-packages/certifi/cacert.pem",
    "GUNICORN_WORKERS": "2",
    "GUNICORN_THREADS": "4",
}
for k, v in variables.items():
    api.add_space_variable(repo_id=repo_id, key=k, value=v)
    print("variable ok:", k)

print("PUBLIC_URL: https://%s-luminarecs.hf.space" % user.lower())
print("VERIFY variables:", api.get_space_variables(repo_id=repo_id))
